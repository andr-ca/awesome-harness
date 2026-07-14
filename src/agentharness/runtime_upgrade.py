from __future__ import annotations

import copy
import errno
import functools
import hashlib
import json
import os
import platform
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from agentharness import RESULT_SCHEMA_VERSION, __version__
from agentharness.runtime import (
    ArtifactAcquisitionError,
    LockedArtifact,
    VerifiedArtifact,
    _discard_staged_artifact,
    _promote_staged_artifact,
    _stage_artifact,
    _StagedArtifact,
    with_mirror,
)
from agentharness.runtime_lock import (
    ConsumerRuntimeLock,
    RuntimeArtifact,
    RuntimeLockError,
    load_json_document,
    validate_consumer_lock,
)

_MAX_CONTRACT_BYTES = 64 * 1024
_CONTRACT_TIMEOUT_SECONDS = 30
_MAX_CONTRACT_DEPTH = 8
_MAX_CONTRACT_ITEMS = 64
_MAX_CONTRACT_STRING_BYTES = 1024


class UpgradePlanningError(RuntimeError):
    """Raised when a base-authoritative upgrade plan cannot be produced."""


class CandidateContractError(UpgradePlanningError):
    """Raised when the verified candidate pair fails its isolated contract."""


class SchemaSequenceError(UpgradePlanningError):
    """Raised when an upgrade attempts an unsafe schema transition."""


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    core_version: str
    schema_version: int
    bundled_plugins: tuple[tuple[str, str], ...]
    compatibility_provider_version: str


type LockScalar = str | int | bool | None
type LockValue = LockScalar | Mapping[str, "LockValue"] | list["LockValue"]
type LockDocument = Mapping[str, LockValue]
type LockDiff = tuple[tuple[str, LockScalar, LockScalar], ...]


@dataclass(frozen=True, slots=True)
class UpgradeRequest:
    base_lock_path: Path
    candidate_lock_path: Path
    cache_dir: Path
    package_mirror_url: str | None = None
    runtime_mirror_url: str | None = None


@dataclass(frozen=True, slots=True)
class UpgradePlan:
    evaluator: RuntimeIdentity
    candidate: RuntimeIdentity
    package: VerifiedArtifact
    runtime: VerifiedArtifact
    contracts: tuple[str, ...]
    lock_diff: LockDiff


def _identity(lock: ConsumerRuntimeLock) -> RuntimeIdentity:
    return RuntimeIdentity(
        core_version=lock.zipapp.core_version,
        schema_version=lock.zipapp.schema_version,
        bundled_plugins=tuple(sorted(lock.zipapp.bundled_plugins.items())),
        compatibility_provider_version=lock.zipapp.compatibility_provider_version,
    )


def _flatten_lock(value: LockValue, *, prefix: str = "") -> dict[str, LockScalar]:
    if isinstance(value, Mapping):
        flattened: dict[str, LockScalar] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise UpgradePlanningError("runtime lock contains an invalid key")
            path = f"{prefix}.{key}" if prefix else key
            flattened.update(_flatten_lock(value[key], prefix=path))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            flattened.update(_flatten_lock(item, prefix=f"{prefix}[{index}]"))
        return flattened
    if value is None or isinstance(value, (str, int, bool)):
        return {prefix: value}
    raise UpgradePlanningError("runtime lock contains an unsupported value")


def deterministic_lock_diff(before: LockDocument, after: LockDocument) -> LockDiff:
    old = _flatten_lock(before)
    new = _flatten_lock(after)
    if set(old) != set(new):
        raise UpgradePlanningError("candidate lock changes the protected lock shape")
    return tuple(
        (path, old[path], new[path])
        for path in sorted(old)
        if old[path] != new[path]
    )


def _diff_path_allowed(path: str) -> bool:
    exact = {
        "package.version",
        "package.tarball_url",
        "package.registry_sri",
        "package.sha512",
        "zipapp.sha512",
        "zipapp.core_version",
        "zipapp.schema_version",
        "zipapp.compatibility_provider_version",
    }
    if path in exact or path.startswith("zipapp.bundled_plugins."):
        return True
    return path.startswith("runtimes[") and path.endswith(
        (".url", ".sha256", ".sha512")
    )


def _protected_diff(before: LockDocument, after: LockDocument) -> LockDiff:
    difference = deterministic_lock_diff(before, after)
    forbidden = tuple(path for path, _, _ in difference if not _diff_path_allowed(path))
    if forbidden:
        raise UpgradePlanningError(
            f"candidate changes protected runtime policy: {forbidden[0]}"
        )
    return difference


def _verify_schema_sequence(base: RuntimeIdentity, candidate: RuntimeIdentity) -> None:
    if candidate.schema_version < base.schema_version:
        raise SchemaSequenceError("runtime schema downgrades are not allowed")
    if candidate.schema_version > base.schema_version + 1:
        raise SchemaSequenceError("runtime schema upgrades must be sequential")
    if (
        candidate.schema_version != base.schema_version
        and candidate.core_version != base.core_version
    ):
        raise SchemaSequenceError(
            "a breaking schema upgrade requires two PRs: runtime first, schema second"
        )


def _candidate_schema_identity(document: Mapping[str, object]) -> tuple[str, int]:
    zipapp = document.get("zipapp")
    if not isinstance(zipapp, Mapping):
        raise UpgradePlanningError("candidate runtime lock is invalid")
    core = zipapp.get("core_version")
    schema = zipapp.get("schema_version")
    if (
        not isinstance(core, str)
        or isinstance(schema, bool)
        or not isinstance(schema, int)
    ):
        raise UpgradePlanningError("candidate runtime identity is invalid")
    return core, schema


def _validate_candidate_lock(
    document: Mapping[str, object], base: ConsumerRuntimeLock
) -> ConsumerRuntimeLock:
    core, schema = _candidate_schema_identity(document)
    base_identity = _identity(base)
    _verify_schema_sequence(
        base_identity,
        RuntimeIdentity(core, schema, (), base_identity.compatibility_provider_version),
    )
    try:
        return validate_consumer_lock(document)
    except RuntimeLockError as original:
        if schema != base.zipapp.schema_version + 1 or core != base.zipapp.core_version:
            raise UpgradePlanningError(
                "candidate runtime lock is invalid"
            ) from original
        normalized = copy.deepcopy(document)
        normalized_zipapp = normalized.get("zipapp")
        if not isinstance(normalized_zipapp, dict):
            raise UpgradePlanningError(
                "candidate runtime lock is invalid"
            ) from original
        normalized_zipapp["schema_version"] = base.zipapp.schema_version
        try:
            parsed = validate_consumer_lock(normalized)
        except RuntimeLockError as error:
            raise UpgradePlanningError("candidate runtime lock is invalid") from error
        return replace(
            parsed,
            zipapp=replace(parsed.zipapp, schema_version=schema),
        )


def _load_locks(
    request: UpgradeRequest,
) -> tuple[
    Mapping[str, object],
    ConsumerRuntimeLock,
    Mapping[str, object],
    ConsumerRuntimeLock,
]:
    try:
        base_document = load_json_document(request.base_lock_path)
        base = validate_consumer_lock(base_document)
        candidate_document = load_json_document(request.candidate_lock_path)
    except RuntimeLockError as error:
        raise UpgradePlanningError("runtime lock is unavailable or invalid") from error
    if (
        base.package.version != __version__
        or base.zipapp.core_version != __version__
        or base.zipapp.schema_version != RESULT_SCHEMA_VERSION
        or base.zipapp.compatibility_provider_version != __version__
        or base.zipapp.bundled_plugins
    ):
        raise UpgradePlanningError(
            "trusted base lock does not match the running base runtime"
        )
    candidate = _validate_candidate_lock(candidate_document, base)
    return base_document, base, candidate_document, candidate


def _selected_runtime(lock: ConsumerRuntimeLock) -> RuntimeArtifact:
    for runtime in lock.runtimes:
        if runtime.target == lock.acquisition.selected_target:
            return runtime
    raise UpgradePlanningError("candidate selected runtime is missing")


def _locked_artifacts(
    request: UpgradeRequest, candidate: ConsumerRuntimeLock
) -> tuple[
    LockedArtifact,
    LockedArtifact,
    tuple[str, ...],
    tuple[str, ...],
]:
    package = LockedArtifact(
        name="package",
        url=candidate.package.tarball_url,
        sha256=None,
        sha512=candidate.package.sha512,
        max_bytes=candidate.acquisition.limits.max_compressed_bytes,
    )
    runtime_identity = _selected_runtime(candidate)
    runtime = LockedArtifact(
        name="runtime",
        url=runtime_identity.url,
        sha256=runtime_identity.sha256,
        sha512=runtime_identity.sha512,
        max_bytes=candidate.acquisition.limits.max_compressed_bytes,
    )
    package_host = urlparse(candidate.package.tarball_url).hostname
    package_mirror_host = urlparse(candidate.package.allowed_mirror_url).hostname
    package_hosts = tuple(
        host
        for host in (
            package_host,
            package_mirror_host,
        )
        if host is not None
    )
    runtime_hosts = (
        "github.com",
        "release-assets.githubusercontent.com",
        "objects.githubusercontent.com",
        *candidate.acquisition.mirror_policy.allowed_runtime_mirror_hosts,
    )
    try:
        if request.package_mirror_url is not None:
            if request.package_mirror_url != candidate.package.allowed_mirror_url:
                raise UpgradePlanningError(
                    "package mirror is not authorized by the lock"
                )
            package = with_mirror(
                package,
                request.package_mirror_url,
                allowed_https_hosts=package_hosts,
            )
        if request.runtime_mirror_url is not None:
            runtime = with_mirror(
                runtime,
                request.runtime_mirror_url,
                allowed_https_hosts=(
                    candidate.acquisition.mirror_policy.allowed_runtime_mirror_hosts
                ),
            )
    except ValueError as error:
        raise UpgradePlanningError(
            "candidate mirror is invalid or unauthorized"
        ) from error
    return package, runtime, package_hosts, runtime_hosts


def _trusted_system_tool(path: Path) -> Path:
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as error:
        raise CandidateContractError("required OS sandbox is unavailable") from error
    if (
        not path.is_file()
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
        or path.is_symlink()
    ):
        raise CandidateContractError("required OS sandbox is not trusted")
    return path


def _trusted_node() -> Path:
    configured = shutil.which("node")
    if configured is None:
        raise CandidateContractError("trusted Node runtime is unavailable")
    path = Path(configured)
    if path.is_symlink():
        try:
            link = path.lstat()
        except OSError as error:
            raise CandidateContractError(
                "trusted Node runtime is unavailable"
            ) from error
        if link.st_uid not in (0, os.getuid()):
            raise CandidateContractError("trusted Node runtime is unavailable")
        path = path.resolve()
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as error:
        raise CandidateContractError("trusted Node runtime is unavailable") from error
    if (
        not path.is_file()
        or metadata.st_uid not in (0, os.getuid())
        or metadata.st_mode & 0o022
        or path.is_symlink()
    ):
        raise CandidateContractError("trusted Node runtime is unavailable")
    return path


def _sandbox_prefix(
    *, readonly_paths: tuple[Path, ...], writable_dir: Path
) -> tuple[str, ...]:
    system = platform.system()
    if system == "Linux":
        bwrap = _trusted_system_tool(Path("/usr/bin/bwrap"))
        try:
            probe = subprocess.run(
                [
                    str(bwrap),
                    "--unshare-all",
                    "--die-with-parent",
                    "--ro-bind",
                    "/usr",
                    "/usr",
                    *(
                        argument
                        for system_path in (
                            Path("/bin"),
                            Path("/lib"),
                            Path("/lib64"),
                        )
                        if system_path.exists()
                        for argument in (
                            "--ro-bind",
                            str(system_path),
                            str(system_path),
                        )
                    ),
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "/usr/bin/true",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CandidateContractError(
                "required Linux bubblewrap sandbox is unavailable"
            ) from error
        if probe.returncode != 0:
            raise CandidateContractError(
                "required Linux bubblewrap sandbox is unavailable"
            )
        directories = {writable_dir, *(path.parent for path in readonly_paths)}
        parent_directories = {
            parent
            for directory in directories
            for parent in (directory, *directory.parents)
            if parent != Path("/")
        }
        prefix: list[str] = [
            str(bwrap),
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
        ]
        for system_path in (Path("/bin"), Path("/lib"), Path("/lib64")):
            if system_path.exists():
                prefix.extend(("--ro-bind", str(system_path), str(system_path)))
        prefix.extend(("--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"))
        for directory in sorted(parent_directories, key=lambda item: len(item.parts)):
            prefix.extend(("--dir", str(directory)))
        for path in readonly_paths:
            prefix.extend(("--ro-bind", str(path), str(path)))
        prefix.extend(("--bind", str(writable_dir), str(writable_dir), "--"))
        return tuple(prefix)
    if system == "Darwin":
        sandbox_exec = _trusted_system_tool(Path("/usr/bin/sandbox-exec"))
        readable_paths = (
            *readonly_paths,
            writable_dir,
            Path("/usr"),
            Path("/bin"),
            Path("/System"),
            Path("/Library"),
        )
        allowed_reads = " ".join(
            f"(subpath {json.dumps(str(path))})" for path in readable_paths
        )
        profile_text = (
            "(version 1)(deny default)(allow process*)"
            f"(allow file-read* {allowed_reads})"
            f"(allow file-write* (subpath {json.dumps(str(writable_dir))}))"
            "(deny network*)"
        )
        return (str(sandbox_exec), "-p", profile_text)
    raise CandidateContractError("required OS sandbox is unsupported")


def _bounded_contract_value(value: object, *, depth: int = 0) -> None:
    if depth > _MAX_CONTRACT_DEPTH:
        raise CandidateContractError("candidate contract JSON is invalid")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > _MAX_CONTRACT_STRING_BYTES:
            raise CandidateContractError("candidate contract JSON is invalid")
        return
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -(2**63) <= value < 2**63:
            raise CandidateContractError("candidate contract JSON is invalid")
        return
    if isinstance(value, list):
        if len(value) > _MAX_CONTRACT_ITEMS:
            raise CandidateContractError("candidate contract JSON is invalid")
        for item in value:
            _bounded_contract_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > _MAX_CONTRACT_ITEMS:
            raise CandidateContractError("candidate contract JSON is invalid")
        for key, item in value.items():
            if len(key.encode("utf-8")) > _MAX_CONTRACT_STRING_BYTES:
                raise CandidateContractError("candidate contract JSON is invalid")
            _bounded_contract_value(item, depth=depth + 1)
        return
    raise CandidateContractError("candidate contract JSON is invalid")


def _current_user_task_count() -> int:
    if platform.system() != "Linux":
        return 384
    uid = os.getuid()
    count = 0
    for process_dir in Path("/proc").glob("[0-9]*"):
        try:
            status = (process_dir / "status").read_text(
                encoding="utf-8", errors="replace"
            )
            uid_line = next(
                line for line in status.splitlines() if line.startswith("Uid:")
            )
            if int(uid_line.split()[1]) == uid:
                count += sum(1 for _entry in (process_dir / "task").iterdir())
        except (OSError, StopIteration, ValueError):
            continue
    return count


def _apply_candidate_limits(process_limit: int) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    file_size = 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_size, file_size))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (process_limit, process_limit))
    address_space = 4 * 1024 * 1024 * 1024
    if hasattr(resource, "RLIMIT_AS"):
        resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))


def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 0.25
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            process.wait(timeout=1)
            return
        time.sleep(0.01)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=1)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    raise CandidateContractError("candidate process group could not be reaped")


def _run_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
    max_output_bytes: int,
) -> bytes:
    process_limit = _current_user_task_count() + 128
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            start_new_session=True,
            preexec_fn=functools.partial(_apply_candidate_limits, process_limit),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CandidateContractError(
            "verified candidate contract could not run"
        ) from error
    if process.stdout is None:  # pragma: no cover - PIPE always supplies it
        _kill_process_tree(process)
        raise CandidateContractError("candidate contract report is invalid")
    output = bytearray()
    deadline = time.monotonic() + timeout_seconds
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process_tree(process)
                raise CandidateContractError("candidate contract timed out")
            events = selector.select(min(remaining, 0.05))
            for _key, _mask in events:
                chunk = os.read(process.stdout.fileno(), 65536)
                if chunk:
                    output.extend(chunk)
                    if len(output) > max_output_bytes:
                        _kill_process_tree(process)
                        raise CandidateContractError(
                            "candidate contract output exceeds its size limit"
                        )
                elif process.poll() is not None:
                    return_code = process.returncode
                    _kill_process_tree(process)
                    if return_code != 0:
                        raise CandidateContractError(
                            "verified candidate contract failed"
                        )
                    return bytes(output)
    finally:
        selector.close()
        process.stdout.close()


def _reject_duplicate_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CandidateContractError(
                f"candidate contract has duplicate field: {key}"
            )
        result[key] = value
    return result


def _run_verified_candidate(
    candidate_lock: Mapping[str, object],
    cache_dir: Path,
    package: VerifiedArtifact,
    runtime: VerifiedArtifact,
    expected: RuntimeIdentity,
) -> tuple[str, ...]:
    bootstrapper = _trusted_bootstrapper_path()
    if bootstrapper is None:
        raise CandidateContractError("trusted runtime bootstrapper is unavailable")
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="candidate-contract-", dir=cache_dir
        ) as workdir:
            work_path = Path(workdir)
            lock_snapshot = work_path / "candidate.lock.json"
            lock_snapshot.write_text(
                json.dumps(candidate_lock, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            node = _trusted_node()
            sandbox_prefix = _sandbox_prefix(
                readonly_paths=(
                    node,
                    bootstrapper,
                    lock_snapshot,
                    package.path,
                    runtime.path,
                ),
                writable_dir=work_path,
            )
            command = (
                *sandbox_prefix,
                str(node),
                str(bootstrapper),
                "--lock",
                str(lock_snapshot),
                "--cache",
                str(work_path / "execution-cache"),
                "--authenticated-npm-archive",
                str(package.path),
                "--authenticated-runtime-archive",
                str(runtime.path),
                "--",
                "runtime-contract",
            )
            report_bytes = _run_bounded_process(
                command,
                cwd=Path(workdir),
                environment=environment,
                timeout_seconds=_CONTRACT_TIMEOUT_SECONDS,
                max_output_bytes=_MAX_CONTRACT_BYTES,
            )
    except OSError as error:
        raise CandidateContractError(
            "verified candidate contract could not run"
        ) from error
    try:
        report = json.loads(
            report_bytes,
            object_pairs_hook=_reject_duplicate_fields,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                CandidateContractError("candidate contract report is invalid")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise CandidateContractError("candidate contract report is invalid") from error
    _bounded_contract_value(report)
    expected_identity = {
        "core_version": expected.core_version,
        "schema_version": expected.schema_version,
        "bundled_plugins": dict(expected.bundled_plugins),
        "compatibility_provider_version": expected.compatibility_provider_version,
    }
    if not isinstance(report, dict) or set(report) != {
        "protocol_version",
        "identity",
        "contracts",
    }:
        raise CandidateContractError("candidate contract report is invalid")
    identity = report["identity"]
    if (
        type(report["protocol_version"]) is not int
        or report["protocol_version"] != 1
        or not isinstance(identity, dict)
        or set(identity) != {
            "core_version",
            "schema_version",
            "bundled_plugins",
            "compatibility_provider_version",
        }
        or not isinstance(identity["core_version"], str)
        or type(identity["schema_version"]) is not int
        or not isinstance(identity["compatibility_provider_version"], str)
        or not isinstance(identity["bundled_plugins"], dict)
        or not all(
            isinstance(name, str) and isinstance(version, str)
            for name, version in identity["bundled_plugins"].items()
        )
    ):
        raise CandidateContractError("candidate contract report is invalid")
    if identity != expected_identity:
        raise CandidateContractError("candidate identity does not match verified bytes")
    contracts = report["contracts"]
    if not isinstance(contracts, dict) or set(contracts) != {
        "plugin",
        "schema",
        "migration",
    }:
        raise CandidateContractError("candidate contract report is incomplete")
    for name in ("plugin", "schema", "migration"):
        if type(contracts[name]) is not bool or contracts[name] is not True:
            raise CandidateContractError(f"candidate {name} contract failed")
    return tuple(sorted(contracts))


def _cached_artifact(
    path: Path, locked: LockedArtifact
) -> VerifiedArtifact:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise CandidateContractError("candidate pair cache is invalid")
        sha256 = hashlib.sha256()
        sha512 = hashlib.sha512()
        total = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                if total > locked.max_bytes:
                    raise CandidateContractError("candidate pair cache is invalid")
                sha256.update(chunk)
                sha512.update(chunk)
    except OSError as error:
        raise CandidateContractError("candidate pair cache is invalid") from error
    actual_sha256 = sha256.hexdigest()
    actual_sha512 = sha512.hexdigest()
    if actual_sha512 != locked.sha512 or (
        locked.sha256 is not None and actual_sha256 != locked.sha256
    ):
        raise CandidateContractError("candidate pair cache is invalid")
    return VerifiedArtifact(locked.name, path, actual_sha256, actual_sha512)


def _pair_destination(
    cache_dir: Path, package: LockedArtifact, runtime: LockedArtifact
) -> Path:
    identity = hashlib.sha256(
        f"{package.sha512}:{runtime.sha512}".encode("ascii")
    ).hexdigest()
    return cache_dir / "pairs" / identity


def _existing_candidate_pair(
    destination: Path,
    package_lock: LockedArtifact,
    runtime_lock: LockedArtifact,
) -> tuple[VerifiedArtifact, VerifiedArtifact]:
    try:
        metadata = destination.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or destination.is_symlink():
            raise CandidateContractError("candidate pair cache is invalid")
        names = {path.name for path in destination.iterdir()}
    except OSError as error:
        raise CandidateContractError("candidate pair cache is invalid") from error
    expected_names = {
        f"package-{package_lock.sha512}",
        f"runtime-{runtime_lock.sha512}",
    }
    if names != expected_names:
        raise CandidateContractError("candidate pair cache is invalid")
    return (
        _cached_artifact(destination / f"package-{package_lock.sha512}", package_lock),
        _cached_artifact(destination / f"runtime-{runtime_lock.sha512}", runtime_lock),
    )


def _ensure_private_cache_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        metadata = path.lstat()
    except OSError as error:
        raise UpgradePlanningError(
            "candidate transaction cache is unavailable"
        ) from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise UpgradePlanningError("candidate transaction cache is not private")


def _trusted_bootstrapper_path() -> Path | None:
    candidates = (
        Path(sys.argv[0]).resolve().parent.parent
        / "templates/bootstrap/verify-runtime.mjs",
        Path(__file__).resolve().parents[2]
        / "templates/bootstrap/verify-runtime.mjs",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def plan_upgrade(request: UpgradeRequest) -> UpgradePlan:
    """Plan an upgrade using only base-trusted locks and verified candidate bytes."""
    base_document, base, candidate_document, candidate = _load_locks(request)
    base_identity = _identity(base)
    candidate_identity = _identity(candidate)
    _verify_schema_sequence(base_identity, candidate_identity)
    lock_diff = _protected_diff(
        cast(LockDocument, base_document),
        cast(LockDocument, candidate_document),
    )
    package_lock, runtime_lock, package_hosts, runtime_hosts = _locked_artifacts(
        request, candidate
    )
    transactions_root = request.cache_dir / ".transactions"
    pairs_root = request.cache_dir / "pairs"
    transaction_dir: Path | None
    _ensure_private_cache_directory(transactions_root)
    _ensure_private_cache_directory(pairs_root)
    try:
        transaction_dir = Path(
            tempfile.mkdtemp(prefix="candidate-", dir=transactions_root)
        )
    except OSError as error:
        raise UpgradePlanningError(
            "candidate transaction cache is unavailable"
        ) from error
    staged_package: _StagedArtifact | None = None
    staged_runtime: _StagedArtifact | None = None
    try:
        staged_package = _stage_artifact(
            package_lock,
            transaction_dir,
            allowed_https_hosts=package_hosts,
            max_redirects=candidate.acquisition.limits.max_redirects,
        )
        staged_runtime = _stage_artifact(
            runtime_lock,
            transaction_dir,
            allowed_https_hosts=runtime_hosts,
            max_redirects=candidate.acquisition.limits.max_redirects,
        )
        contracts = _run_verified_candidate(
            candidate_document,
            transaction_dir,
            staged_package.verified,
            staged_runtime.verified,
            candidate_identity,
        )
        _promote_staged_artifact(staged_package)
        _promote_staged_artifact(staged_runtime)
        private_package, private_runtime = _existing_candidate_pair(
            transaction_dir, package_lock, runtime_lock
        )
        destination = _pair_destination(request.cache_dir, package_lock, runtime_lock)
        try:
            os.rename(transaction_dir, destination)
            transaction_dir = None
            package = replace(
                private_package, path=destination / private_package.path.name
            )
            runtime = replace(
                private_runtime, path=destination / private_runtime.path.name
            )
        except OSError as error:
            if error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                raise ArtifactAcquisitionError(
                    "candidate pair could not be promoted atomically"
                ) from error
            package, runtime = _existing_candidate_pair(
                destination, package_lock, runtime_lock
            )
    except ArtifactAcquisitionError as error:
        raise UpgradePlanningError(str(error)) from error
    finally:
        _discard_staged_artifact(staged_package)
        _discard_staged_artifact(staged_runtime)
        if transaction_dir is not None:
            shutil.rmtree(transaction_dir, ignore_errors=True)
    return UpgradePlan(
        evaluator=base_identity,
        candidate=candidate_identity,
        package=package,
        runtime=runtime,
        contracts=contracts,
        lock_diff=lock_diff,
    )


def load_upgrade_request(path: Path, *, trusted_base_lock: Path) -> UpgradeRequest:
    try:
        document = load_json_document(path)
    except RuntimeLockError as error:
        raise UpgradePlanningError(
            "upgrade request is unavailable or invalid"
        ) from error
    expected = {
        "candidate_lock",
        "cache_dir",
        "package_mirror_url",
        "runtime_mirror_url",
    }
    if set(document) != expected:
        raise UpgradePlanningError("upgrade request has an invalid shape")

    def path_value(name: str) -> Path:
        value = document[name]
        if not isinstance(value, str) or not value or len(value) > 4096:
            raise UpgradePlanningError("upgrade request contains an invalid path")
        return Path(value)

    def optional_url(name: str) -> str | None:
        value = document[name]
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 4096
        ):
            raise UpgradePlanningError("upgrade request contains an invalid mirror")
        return value

    return UpgradeRequest(
        base_lock_path=trusted_base_lock,
        candidate_lock_path=path_value("candidate_lock"),
        cache_dir=path_value("cache_dir"),
        package_mirror_url=optional_url("package_mirror_url"),
        runtime_mirror_url=optional_url("runtime_mirror_url"),
    )


def rollback_to_base_lock(active_lock: Path, base_lock: Path) -> None:
    """Atomically restore the exact base-authoritative lock bytes."""
    try:
        base_bytes = base_lock.read_bytes()
    except OSError as error:
        raise UpgradePlanningError("base runtime lock is unavailable") from error
    active_lock.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{active_lock.name}-", suffix=".part", dir=active_lock.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(base_bytes)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, active_lock)
        temporary = None
    except OSError as error:
        raise UpgradePlanningError("base runtime lock could not be restored") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
