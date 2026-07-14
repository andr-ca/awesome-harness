#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import base64
import binascii
import hashlib
import json
import sys
import tarfile
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agentharness.runtime_lock import (  # noqa: E402
    EXPECTED_LIMITS,
    MIRROR_HOST_PATTERN,
    RuntimeLockError,
    load_runtime_manifest,
    validate_consumer_lock,
)

ZIPAPP_TARBALL_PATH = "package/dist/agentharness.pyz"
MAX_PACKED_BYTES = 268_435_456
MAX_JSON_BYTES = 1_048_576
MAX_MEMBERS = 100_000
MAX_PATH_BYTES = 4_096
MAX_EMBEDDED_JSON_BYTES = 1_048_576


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeLockError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> object:
    try:
        with path.open("rb") as source:
            payload = source.read(MAX_JSON_BYTES + 1)
        if len(payload) > MAX_JSON_BYTES:
            raise RuntimeLockError(f"JSON input exceeds size limit: {path}")
        return json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeLockError(f"cannot read JSON input {path}: {error}") from error


def _json_bytes(payload: bytes, field: str) -> object:
    if len(payload) > MAX_EMBEDDED_JSON_BYTES:
        raise RuntimeLockError(f"{field} exceeds JSON size limit")
    try:
        return json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeLockError(f"{field} is invalid: {error}") from error


def _authenticated_bytes(path: Path) -> tuple[bytes, bytes]:
    if not path.is_file() or path.stat().st_size > MAX_PACKED_BYTES:
        raise RuntimeLockError("npm tarball is missing or exceeds the compressed limit")
    digest = hashlib.sha512()
    chunks: list[bytes] = []
    total = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            total += len(chunk)
            if total > MAX_PACKED_BYTES:
                raise RuntimeLockError("npm tarball exceeds compressed limit")
            digest.update(chunk)
            chunks.append(chunk)
    return b"".join(chunks), digest.digest()


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise RuntimeLockError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeLockError(f"{field} must be a non-empty string")
    return value


def _sri_digest(value: object, field: str) -> tuple[str, bytes]:
    sri = _string(value, field)
    if not sri.startswith("sha512-"):
        raise RuntimeLockError(f"{field} must use SHA-512 integrity")
    try:
        digest = base64.b64decode(sri[7:], validate=True)
    except binascii.Error as error:
        raise RuntimeLockError(f"{field} is not valid base64") from error
    if len(digest) != 64:
        raise RuntimeLockError(f"{field} is not a SHA-512 integrity digest")
    return sri, digest


def _safe_member(member: tarfile.TarInfo) -> None:
    path = PurePosixPath(member.name)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\x00" in member.name
        or len(member.name.encode("utf-8")) > MAX_PATH_BYTES
    ):
        raise RuntimeLockError(f"unsafe npm tarball member: {member.name!r}")
    if member.issym() or member.islnk() or member.isdev() or member.isfifo():
        raise RuntimeLockError(f"unsupported npm tarball member: {member.name!r}")


def _packed_files(tarball: bytes) -> tuple[Mapping[str, object], bytes]:
    package_json: bytes | None = None
    zipapp: bytes | None = None
    try:
        with tarfile.open(
            fileobj=__import__("io").BytesIO(tarball), mode="r:gz"
        ) as archive:
            names: set[str] = set()
            files: set[str] = set()
            expanded = 0
            count = 0
            for member in archive:
                count += 1
                if count > MAX_MEMBERS:
                    raise RuntimeLockError("npm tarball exceeds member-count limit")
                _safe_member(member)
                if (
                    member.isfile()
                    and member.size > EXPECTED_LIMITS["max_member_bytes"]
                ):
                    raise RuntimeLockError("npm tarball member exceeds size limit")
                if member.name in names:
                    raise RuntimeLockError(
                        f"duplicate npm tarball member: {member.name}"
                    )
                parents = PurePosixPath(member.name).parents
                if any(parent.as_posix() in files for parent in parents):
                    raise RuntimeLockError("npm tarball has a file/directory collision")
                if member.isfile() and any(
                    existing.startswith(member.name.rstrip("/") + "/")
                    for existing in names
                ):
                    raise RuntimeLockError("npm tarball has a file/directory collision")
                names.add(member.name)
                if member.isfile():
                    files.add(member.name)
                expanded += member.size
                if expanded > EXPECTED_LIMITS["max_expanded_bytes"]:
                    raise RuntimeLockError("npm tarball exceeds expanded-size limit")
                if not member.isfile() or member.name not in {
                    "package/package.json",
                    ZIPAPP_TARBALL_PATH,
                }:
                    continue
                selected_limit = (
                    MAX_EMBEDDED_JSON_BYTES
                    if member.name == "package/package.json"
                    else MAX_PACKED_BYTES
                )
                if member.size > selected_limit:
                    raise RuntimeLockError(
                        f"{member.name} exceeds selected member size limit"
                    )
                if member.size > MAX_PACKED_BYTES:
                    raise RuntimeLockError(
                        f"packed member exceeds limit: {member.name}"
                    )
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeLockError(f"cannot read packed member: {member.name}")
                payload = source.read(selected_limit + 1)
                if len(payload) > selected_limit:
                    raise RuntimeLockError(
                        f"{member.name} exceeds selected member size limit"
                    )
                if len(payload) != member.size:
                    raise RuntimeLockError(
                        f"{member.name} declared length does not match body"
                    )
                if member.name == "package/package.json":
                    package_json = payload
                else:
                    zipapp = payload
    except (OSError, tarfile.TarError) as error:
        raise RuntimeLockError(f"cannot inspect npm tarball: {error}") from error
    if package_json is None or zipapp is None:
        raise RuntimeLockError("npm tarball must contain package.json and the zipapp")
    package = _mapping(
        _json_bytes(package_json, "packed package.json"), "packed package.json"
    )
    return package, zipapp


def _zipapp_identity(payload: bytes) -> tuple[str, Mapping[str, object]]:
    digest = hashlib.sha512(payload).hexdigest()
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(payload)) as archive:
            infos = [
                info
                for info in archive.infolist()
                if info.filename == "agentharness-runtime-identity.json"
            ]
            if len(infos) != 1:
                raise RuntimeLockError(
                    "packed zipapp identity manifest is missing or duplicate"
                )
            info = infos[0]
            if (
                info.file_size > MAX_EMBEDDED_JSON_BYTES
                or info.compress_size > MAX_EMBEDDED_JSON_BYTES
            ):
                raise RuntimeLockError("packed zipapp identity exceeds size limit")
            identity = _mapping(
                _json_bytes(archive.read(info), "packed zipapp identity"),
                "packed zipapp identity",
            )
    except (UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, KeyError) as error:
        raise RuntimeLockError(f"packed zipapp identity is invalid: {error}") from error
    expected = {
        "core_version",
        "schema_version",
        "bundled_plugins",
        "compatibility_provider_version",
    }
    if set(identity) != expected:
        raise RuntimeLockError("packed zipapp identity inventory is unexpected")
    if not isinstance(identity["bundled_plugins"], Mapping):
        raise RuntimeLockError("packed bundled_plugins identity must be an object")
    return digest, identity


def _trusted_identity(source_root: Path) -> dict[str, object]:
    init_path = source_root / "agentharness/__init__.py"
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise RuntimeLockError(f"cannot read trusted core identity: {error}") from error
    constants: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"__version__", "RESULT_SCHEMA_VERSION"}
        ):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError) as error:
                raise RuntimeLockError(
                    "trusted core identity constant is not literal"
                ) from error
    version = constants.get("__version__")
    schema = constants.get("RESULT_SCHEMA_VERSION")
    if not isinstance(version, str) or not isinstance(schema, int):
        raise RuntimeLockError("trusted core identity constants are invalid")
    return {
        "bundled_plugins": {},
        "compatibility_provider_version": version,
        "core_version": version,
        "schema_version": schema,
    }


def _expected_zipapp_digest(path: Path) -> str:
    try:
        fields = path.read_text(encoding="ascii").split()
    except (OSError, UnicodeError) as error:
        raise RuntimeLockError(f"cannot read trusted zipapp digest: {error}") from error
    if len(fields) != 2 or fields[1] != "agentharness.pyz" or len(fields[0]) != 128:
        raise RuntimeLockError("trusted zipapp digest file is malformed")
    return fields[0]


def _runtime_documents(path: Path) -> list[dict[str, str]]:
    manifest = load_runtime_manifest(path)
    return [
        {
            "target": runtime.target,
            "url": runtime.url,
            "sha256": runtime.sha256,
            "sha512": runtime.sha512,
            "archive_prefix": runtime.archive_prefix,
            "interpreter_path": runtime.interpreter_path,
        }
        for runtime in manifest.runtimes
    ]


def build_consumer_lock(
    *,
    pack_result_path: Path,
    registry_metadata_path: Path,
    runtime_manifest_path: Path,
    tarball_path: Path,
    allowed_mirror_url: str,
    selected_target: str,
    runtime_mirror_hosts: tuple[str, ...],
    trusted_package_path: Path,
    trusted_source_root: Path,
    expected_zipapp_digest_path: Path,
) -> dict[str, object]:
    pack_result = _load_json(pack_result_path)
    if not isinstance(pack_result, list) or len(pack_result) != 1:
        raise RuntimeLockError(
            "npm pack --json result must contain exactly one package"
        )
    packed = _mapping(pack_result[0], "npm pack result")
    registry = _mapping(_load_json(registry_metadata_path), "registry metadata")
    dist = _mapping(registry.get("dist"), "registry metadata dist")
    trusted_package = _mapping(_load_json(trusted_package_path), "trusted package.json")
    trusted_name = _string(trusted_package.get("name"), "trusted package name")
    trusted_version = _string(trusted_package.get("version"), "trusted package version")
    names = {
        _string(packed.get("name"), "pack name"),
        _string(registry.get("name"), "registry name"),
    }
    versions = {
        _string(packed.get("version"), "pack version"),
        _string(registry.get("version"), "registry version"),
    }
    if _string(packed.get("filename"), "pack filename") != tarball_path.name:
        raise RuntimeLockError(
            "npm pack filename does not identify the supplied tarball"
        )
    pack_sri, pack_digest = _sri_digest(packed.get("integrity"), "pack integrity")
    registry_sri, registry_digest = _sri_digest(
        dist.get("integrity"), "registry integrity"
    )
    tarball_bytes, actual_digest = _authenticated_bytes(tarball_path)
    if pack_digest != actual_digest or registry_digest != actual_digest:
        raise RuntimeLockError("npm pack, registry, and tarball integrity do not match")
    if pack_sri != registry_sri:
        raise RuntimeLockError("npm pack and registry integrity strings differ")
    package, zipapp = _packed_files(tarball_bytes)
    names.add(_string(package.get("name"), "packed package name"))
    versions.add(_string(package.get("version"), "packed package version"))
    if names != {trusted_name} or versions != {trusted_version}:
        raise RuntimeLockError("npm package name/version identities do not match")
    tarball_url = _string(dist.get("tarball"), "registry tarball URL")
    expected_tarball_url = (
        f"https://registry.npmjs.org/{trusted_name}/-/"
        f"{trusted_name}-{trusted_version}.tgz"
    )
    if tarball_url != expected_tarball_url:
        raise RuntimeLockError(
            "registry tarball URL must use the canonical HTTPS registry"
        )
    mirror = urlparse(allowed_mirror_url)
    if (
        mirror.scheme != "https"
        or not mirror.netloc
        or mirror.username is not None
        or mirror.query
        or mirror.fragment
        or not allowed_mirror_url.endswith("/")
    ):
        raise RuntimeLockError("allowed package mirror must use HTTPS")
    if len(runtime_mirror_hosts) != len(set(runtime_mirror_hosts)):
        raise RuntimeLockError("runtime mirror hosts contain a duplicate")
    if any(
        MIRROR_HOST_PATTERN.fullmatch(host) is None for host in runtime_mirror_hosts
    ):
        raise RuntimeLockError("runtime mirror hosts must be DNS hostnames")
    zipapp_digest = hashlib.sha512(zipapp).hexdigest()
    if zipapp_digest != _expected_zipapp_digest(expected_zipapp_digest_path):
        raise RuntimeLockError("packed zipapp digest does not match trusted build")
    _, identity = _zipapp_identity(zipapp)
    if dict(identity) != _trusted_identity(trusted_source_root):
        raise RuntimeLockError("packed zipapp identity does not match trusted source")
    version = next(iter(versions))
    document: dict[str, object] = {
        "schema_version": 1,
        "package": {
            "name": trusted_name,
            "version": version,
            "registry_url": "https://registry.npmjs.org",
            "tarball_url": tarball_url,
            "registry_sri": registry_sri,
            "sha512": actual_digest.hex(),
            "allowed_mirror_url": allowed_mirror_url,
        },
        "zipapp": {
            "path": ZIPAPP_TARBALL_PATH,
            "sha512": zipapp_digest,
            "core_version": identity["core_version"],
            "schema_version": identity["schema_version"],
            "bundled_plugins": identity["bundled_plugins"],
            "compatibility_provider_version": identity[
                "compatibility_provider_version"
            ],
        },
        "runtimes": _runtime_documents(runtime_manifest_path),
        "acquisition": {
            "selected_target": selected_target,
            "selected_source": "upstream",
            "mirror_policy": {
                "require_https": True,
                "require_matching_digest": True,
                "allowed_runtime_mirror_hosts": list(runtime_mirror_hosts),
            },
            "limits": dict(EXPECTED_LIMITS),
            "bootstrap_protocol_version": 1,
        },
    }
    validate_consumer_lock(document)
    return document


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an exact consumer runtime lock from packed bytes"
    )
    parser.add_argument("--pack-result", required=True, type=Path)
    parser.add_argument("--registry-metadata", required=True, type=Path)
    parser.add_argument("--tarball", required=True, type=Path)
    parser.add_argument(
        "--runtime-manifest",
        type=Path,
        default=ROOT / "runtime/python-build-standalone.lock.json",
    )
    parser.add_argument("--allowed-mirror-url", required=True)
    parser.add_argument("--selected-target", required=True)
    parser.add_argument("--runtime-mirror-host", action="append", default=[])
    parser.add_argument(
        "--trusted-package-json", type=Path, default=ROOT / "package.json"
    )
    parser.add_argument("--trusted-source-root", type=Path, default=ROOT / "src")
    parser.add_argument(
        "--expected-zipapp-digest",
        type=Path,
        default=ROOT / "dist/agentharness.pyz.sha512",
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        document = build_consumer_lock(
            pack_result_path=args.pack_result,
            registry_metadata_path=args.registry_metadata,
            runtime_manifest_path=args.runtime_manifest,
            tarball_path=args.tarball,
            allowed_mirror_url=args.allowed_mirror_url,
            selected_target=args.selected_target,
            runtime_mirror_hosts=tuple(args.runtime_mirror_host),
            trusted_package_path=getattr(
                args, "trusted_package_json", ROOT / "package.json"
            ),
            trusted_source_root=getattr(args, "trusted_source_root", ROOT / "src"),
            expected_zipapp_digest_path=getattr(
                args,
                "expected_zipapp_digest",
                ROOT / "dist/agentharness.pyz.sha512",
            ),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    except (OSError, RuntimeLockError) as error:
        print(f"runtime lock build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
