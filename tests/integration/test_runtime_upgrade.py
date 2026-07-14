from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tarfile
import threading
import time
import zipfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import agentharness.runtime_upgrade as runtime_upgrade
from agentharness.cli import create_parser, main
from agentharness.runtime_upgrade import (
    CandidateContractError,
    SchemaSequenceError,
    UpgradePlanningError,
    UpgradeRequest,
    load_upgrade_request,
    plan_upgrade,
    rollback_to_base_lock,
)

TARGETS = (
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
)
ROOT = Path(__file__).resolve().parents[2]


def _identity(core: str, schema: int = 1) -> dict[str, object]:
    return {
        "core_version": core,
        "schema_version": schema,
        "bundled_plugins": {},
        "compatibility_provider_version": core,
    }


def _zipapp(
    identity: dict[str, object],
    *,
    contracts: dict[str, bool] | None = None,
    report_identity: dict[str, object] | None = None,
) -> bytes:
    report = {
        "protocol_version": 1,
        "identity": report_identity or identity,
        "contracts": contracts
        or {"plugin": True, "schema": True, "migration": True},
    }
    main_source = (
        "import json, sys\n"
        "if sys.argv[1:] != ['runtime-contract']:\n"
        "    raise SystemExit(2)\n"
        f"print(json.dumps({report!r}, sort_keys=True))\n"
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED) as archive:
        identity_member = zipfile.ZipInfo(
            "agentharness-runtime-identity.json", (1980, 1, 1, 0, 0, 0)
        )
        archive.writestr(
            identity_member,
            json.dumps(identity, sort_keys=True, separators=(",", ":")),
        )
        main_member = zipfile.ZipInfo("__main__.py", (1980, 1, 1, 0, 0, 0))
        archive.writestr(main_member, main_source)
    return stream.getvalue()


def _tar(entries: tuple[tuple[str, bytes, int], ...]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as output:
        for name, payload, mode in entries:
            item = tarfile.TarInfo(name)
            item.size = len(payload)
            item.mode = mode
            item.mtime = 0
            output.addfile(item, io.BytesIO(payload))
    return gzip.compress(stream.getvalue(), mtime=0)


def _runtime_archive() -> bytes:
    system_python = Path("/usr/bin/python3")
    interpreter_path = (
        system_python if system_python.is_file() else Path(sys.executable)
    )
    interpreter = f'#!/bin/sh\nexec "{interpreter_path}" "$@"\n'.encode()
    return _tar((("python/bin/python3", interpreter, 0o755),))


def _npm_archive(version: str, pyz: bytes) -> bytes:
    package = json.dumps(
        {"name": "agentharness-toolkit", "version": version},
        separators=(",", ":"),
    ).encode()
    return _tar(
        (
            ("package/package.json", package, 0o644),
            ("package/dist/agentharness.pyz", pyz, 0o644),
        )
    )


def _lock(
    *,
    version: str,
    identity: dict[str, object],
    npm: bytes,
    pyz: bytes,
    runtime: bytes,
    package_mirror: str,
    runtime_mirror_host: str,
) -> dict[str, object]:
    npm_sha = hashlib.sha512(npm).digest()
    runtime_items = []
    for target in TARGETS:
        filename = (
            f"cpython-3.12.13%2B20260510-{target}-"
            "install_only_stripped.tar.gz"
        )
        runtime_items.append(
            {
                "target": target,
                "url": (
                    "https://github.com/astral-sh/python-build-standalone/"
                    f"releases/download/20260510/{filename}"
                ),
                "sha256": hashlib.sha256(runtime).hexdigest(),
                "sha512": hashlib.sha512(runtime).hexdigest(),
                "archive_prefix": "python/",
                "interpreter_path": "python/bin/python3",
            }
        )
    return {
        "schema_version": 1,
        "package": {
            "name": "agentharness-toolkit",
            "version": version,
            "registry_url": "https://registry.npmjs.org",
            "tarball_url": (
                "https://registry.npmjs.org/agentharness-toolkit/-/"
                f"agentharness-toolkit-{version}.tgz"
            ),
            "registry_sri": "sha512-" + base64.b64encode(npm_sha).decode(),
            "sha512": npm_sha.hex(),
            "allowed_mirror_url": package_mirror,
        },
        "zipapp": {
            "path": "package/dist/agentharness.pyz",
            "sha512": hashlib.sha512(pyz).hexdigest(),
            **identity,
        },
        "runtimes": runtime_items,
        "acquisition": {
            "selected_target": TARGETS[0],
            "selected_source": "upstream",
            "mirror_policy": {
                "require_https": True,
                "require_matching_digest": True,
                "allowed_runtime_mirror_hosts": [runtime_mirror_host],
            },
            "limits": {
                "max_compressed_bytes": 268435456,
                "max_expanded_bytes": 1073741824,
                "max_member_bytes": 268435456,
                "max_members": 100000,
                "max_redirects": 3,
                "max_path_bytes": 4096,
            },
            "bootstrap_protocol_version": 1,
        },
    }


@dataclass(frozen=True)
class UpgradeFixture:
    request: UpgradeRequest
    base_lock: Path
    candidate_lock: Path
    unrelated_script: Path


class _ArtifactHandler(BaseHTTPRequestHandler):
    payloads: dict[str, bytes] = {}
    partial_paths: set[str] = set()

    def do_GET(self) -> None:  # noqa: N802
        payload = self.payloads.get(self.path)
        if payload is None:
            self.send_error(404)
            return
        self.send_response(200)
        expected_length = (
            len(payload) + 100
            if self.path in self.partial_paths
            else len(payload)
        )
        self.send_header("Content-Length", str(expected_length))
        self.end_headers()
        if self.path in self.partial_paths:
            self.wfile.write(payload[: max(1, len(payload) // 2)])
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
        else:
            self.wfile.write(payload)

    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextmanager
def _https_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payloads: dict[str, bytes],
) -> Iterator[str]:
    certificate = tmp_path / "cert.pem"
    private_key = tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=mirror.example.test",
            "-addext",
            "subjectAltName=DNS:mirror.example.test",
            "-keyout",
            str(private_key),
            "-out",
            str(certificate),
        ],
        check=True,
        capture_output=True,
    )
    _ArtifactHandler.payloads = payloads
    _ArtifactHandler.partial_paths = set()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ArtifactHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, private_key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original = socket.getaddrinfo

    def local_dns(host: str, port: int, *args: object, **kwargs: object) -> object:
        if host == "mirror.example.test":
            return original("127.0.0.1", port, *args, **kwargs)
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", local_dns)
    monkeypatch.setenv("SSL_CERT_FILE", str(certificate))
    monkeypatch.setenv("NO_PROXY", "mirror.example.test")
    try:
        yield f"https://mirror.example.test:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextmanager
def _fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    base_identity: dict[str, object] | None = None,
    candidate_identity: dict[str, object] | None = None,
    sandbox_stub: bool = True,
) -> Iterator[UpgradeFixture]:
    if sandbox_stub:
        monkeypatch.setattr(
            runtime_upgrade,
            "_sandbox_prefix",
            lambda **_kwargs: (),
            raising=False,
        )
    current_identity = base_identity or _identity("0.1.0")
    next_identity = candidate_identity or _identity("0.2.0")
    runtime = _runtime_archive()
    base_pyz = _zipapp(current_identity)
    candidate_pyz = _zipapp(next_identity)
    base_version = str(current_identity["core_version"])
    candidate_version = str(next_identity["core_version"])
    base_npm = _npm_archive(base_version, base_pyz)
    candidate_npm = _npm_archive(candidate_version, candidate_pyz)
    with _https_artifacts(
        tmp_path,
        monkeypatch,
        {"/package.tgz": candidate_npm, "/runtime.tar.gz": runtime},
    ) as origin:
        base_lock_document = _lock(
            version=base_version,
            identity=current_identity,
            npm=base_npm,
            pyz=base_pyz,
            runtime=runtime,
            package_mirror=f"{origin}/package.tgz",
            runtime_mirror_host="mirror.example.test",
        )
        candidate_lock_document = _lock(
            version=candidate_version,
            identity=next_identity,
            npm=candidate_npm,
            pyz=candidate_pyz,
            runtime=runtime,
            package_mirror=f"{origin}/package.tgz",
            runtime_mirror_host="mirror.example.test",
        )
        base_lock = tmp_path / "base.lock.json"
        candidate_lock = tmp_path / "candidate.lock.json"
        base_lock.write_text(json.dumps(base_lock_document), encoding="utf-8")
        candidate_lock.write_text(
            json.dumps(candidate_lock_document), encoding="utf-8"
        )
        unrelated = tmp_path / "unrelated.py"
        unrelated.write_text(
            "from pathlib import Path\nPath('UNRELATED-RAN').write_text('bad')\n",
            encoding="utf-8",
        )
        yield UpgradeFixture(
            request=UpgradeRequest(
                base_lock_path=base_lock,
                candidate_lock_path=candidate_lock,
                cache_dir=tmp_path / "cache",
                package_mirror_url=f"{origin}/package.tgz",
                runtime_mirror_url=f"{origin}/runtime.tar.gz",
            ),
            base_lock=base_lock,
            candidate_lock=candidate_lock,
            unrelated_script=unrelated,
        )


def test_base_lock_selects_and_executes_only_verified_candidate_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        plan = plan_upgrade(fixture.request)

    assert plan.evaluator.core_version == "0.1.0"
    assert plan.candidate.core_version == "0.2.0"
    assert plan.contracts == ("migration", "plugin", "schema")
    assert not (tmp_path / "UNRELATED-RAN").exists()
    assert plan.package.path.exists() and plan.runtime.path.exists()


def test_arbitrary_candidate_bytes_cannot_delegate_to_unrelated_host_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        candidate = json.loads(fixture.candidate_lock.read_text(encoding="utf-8"))
        candidate["package"]["sha512"] = hashlib.sha512(b"arbitrary").hexdigest()
        candidate["package"]["registry_sri"] = "sha512-" + base64.b64encode(
            hashlib.sha512(b"arbitrary").digest()
        ).decode()
        fixture.candidate_lock.write_text(json.dumps(candidate), encoding="utf-8")

        with pytest.raises(UpgradePlanningError):
            plan_upgrade(fixture.request)

    assert not (tmp_path / "UNRELATED-RAN").exists()


def test_base_runtime_identity_must_match_separately_trusted_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        base = json.loads(fixture.base_lock.read_text(encoding="utf-8"))
        base["package"]["version"] = "9.9.9"
        base["package"]["tarball_url"] = (
            "https://registry.npmjs.org/agentharness-toolkit/-/"
            "agentharness-toolkit-9.9.9.tgz"
        )
        fixture.base_lock.write_text(json.dumps(base), encoding="utf-8")

        with pytest.raises(UpgradePlanningError, match="running base runtime"):
            plan_upgrade(fixture.request)


def test_candidate_policy_weakening_is_rejected_before_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        candidate = json.loads(fixture.candidate_lock.read_text(encoding="utf-8"))
        candidate["acquisition"]["mirror_policy"]["require_matching_digest"] = False
        fixture.candidate_lock.write_text(json.dumps(candidate), encoding="utf-8")

        with pytest.raises(UpgradePlanningError):
            plan_upgrade(fixture.request)


def test_mirror_can_change_only_url_not_candidate_trust_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        candidate = json.loads(fixture.candidate_lock.read_text(encoding="utf-8"))
        candidate["zipapp"]["sha512"] = "f" * 128
        fixture.candidate_lock.write_text(json.dumps(candidate), encoding="utf-8")

        with pytest.raises(UpgradePlanningError):
            plan_upgrade(fixture.request)


def test_schema_breaking_runtime_and_schema_single_pr_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(
        tmp_path, monkeypatch, candidate_identity=_identity("0.2.0", schema=2)
    ) as fixture:
        with pytest.raises(
            (SchemaSequenceError, UpgradePlanningError), match="two PRs"
        ):
            plan_upgrade(fixture.request)


def test_backward_compatible_runtime_pr_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        plan = plan_upgrade(fixture.request)

    assert plan.candidate.schema_version == 1


def test_schema_pr_is_allowed_after_backward_compatible_runtime_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("agentharness.runtime_upgrade.__version__", "0.2.0")
    with _fixture(
        tmp_path,
        monkeypatch,
        base_identity=_identity("0.2.0", schema=1),
        candidate_identity=_identity("0.2.0", schema=2),
    ) as fixture:
        plan = plan_upgrade(fixture.request)

    assert (plan.evaluator.schema_version, plan.candidate.schema_version) == (1, 2)


def test_candidate_contract_failure_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity("0.2.0")
    with _fixture(tmp_path, monkeypatch, candidate_identity=identity) as fixture:
        pyz = _zipapp(
            identity,
            contracts={"plugin": True, "schema": True, "migration": False},
        )
        npm = _npm_archive(
            "0.2.0",
            pyz,
        )
        candidate = json.loads(fixture.candidate_lock.read_text(encoding="utf-8"))
        npm_sha = hashlib.sha512(npm).digest()
        candidate["package"]["sha512"] = npm_sha.hex()
        candidate["package"]["registry_sri"] = (
            "sha512-" + base64.b64encode(npm_sha).decode()
        )
        candidate["zipapp"]["sha512"] = hashlib.sha512(pyz).hexdigest()
        fixture.candidate_lock.write_text(json.dumps(candidate), encoding="utf-8")
        _ArtifactHandler.payloads["/package.tgz"] = npm
        with pytest.raises(CandidateContractError, match="migration contract failed"):
            plan_upgrade(fixture.request)


def test_candidate_self_report_must_match_verified_zipapp_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity("0.2.0")
    with _fixture(tmp_path, monkeypatch, candidate_identity=identity) as fixture:
        pyz = _zipapp(identity, report_identity=_identity("9.9.9"))
        npm = _npm_archive("0.2.0", pyz)
        candidate = json.loads(fixture.candidate_lock.read_text(encoding="utf-8"))
        npm_sha = hashlib.sha512(npm).digest()
        candidate["package"]["sha512"] = npm_sha.hex()
        candidate["package"]["registry_sri"] = (
            "sha512-" + base64.b64encode(npm_sha).decode()
        )
        candidate["zipapp"]["sha512"] = hashlib.sha512(pyz).hexdigest()
        fixture.candidate_lock.write_text(json.dumps(candidate), encoding="utf-8")
        _ArtifactHandler.payloads["/package.tgz"] = npm

        with pytest.raises(CandidateContractError, match="verified bytes"):
            plan_upgrade(fixture.request)


def test_candidate_contract_rejects_boolean_schema_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _identity("0.2.0")
    boolean_identity = {**identity, "schema_version": True}
    with _fixture(tmp_path, monkeypatch, candidate_identity=identity) as fixture:
        pyz = _zipapp(identity, report_identity=boolean_identity)
        npm = _npm_archive("0.2.0", pyz)
        candidate = json.loads(fixture.candidate_lock.read_text(encoding="utf-8"))
        npm_sha = hashlib.sha512(npm).digest()
        candidate["package"]["sha512"] = npm_sha.hex()
        candidate["package"]["registry_sri"] = (
            "sha512-" + base64.b64encode(npm_sha).decode()
        )
        candidate["zipapp"]["sha512"] = hashlib.sha512(pyz).hexdigest()
        fixture.candidate_lock.write_text(json.dumps(candidate), encoding="utf-8")
        _ArtifactHandler.payloads["/package.tgz"] = npm

        with pytest.raises(CandidateContractError, match="invalid"):
            plan_upgrade(fixture.request)


@pytest.mark.parametrize(
    "value",
    [
        1.5,
        2**63,
        "x" * 1025,
        [True] * 65,
        {str(index): True for index in range(65)},
        [[[[[[[[[True]]]]]]]]],
    ],
)
def test_candidate_contract_json_bounds_are_closed_and_stable(value: object) -> None:
    with pytest.raises(CandidateContractError, match="JSON is invalid"):
        runtime_upgrade._bounded_contract_value(value)


def test_required_candidate_sandbox_unavailable_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(**_kwargs: object) -> tuple[str, ...]:
        raise CandidateContractError("required OS sandbox is unavailable")

    monkeypatch.setattr(
        runtime_upgrade,
        "_sandbox_prefix",
        unavailable,
        raising=False,
    )
    with _fixture(tmp_path, monkeypatch, sandbox_stub=False) as fixture:
        with pytest.raises(CandidateContractError, match="sandbox"):
            plan_upgrade(fixture.request)


def test_sandbox_probe_timeout_is_a_stable_domain_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime_upgrade.platform, "system", lambda: "Linux")

    def timeout(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(("bwrap",), 5)

    monkeypatch.setattr(runtime_upgrade.subprocess, "run", timeout)
    with pytest.raises(CandidateContractError, match="sandbox"):
        runtime_upgrade._sandbox_prefix(
            readonly_paths=(), writable_dir=tmp_path
        )


def test_rollback_restores_exact_base_lock(tmp_path: Path) -> None:
    active = tmp_path / "runtime.lock"
    base = tmp_path / "runtime.lock.base"
    active.write_text('{"candidate":true}\n', encoding="utf-8")
    base.write_text('{"base":true}\n', encoding="utf-8")

    rollback_to_base_lock(active, base)

    assert active.read_bytes() == base.read_bytes()


def test_cli_requires_separately_trusted_base_lock() -> None:
    arguments = create_parser().parse_args(
        [
            "runtime",
            "plan-upgrade",
            "--base-lock",
            "base.lock.json",
            "--request",
            "upgrade-request.json",
            "--json",
        ]
    )
    assert (arguments.base_lock, arguments.request, arguments.as_json) == (
        Path("base.lock.json"),
        Path("upgrade-request.json"),
        True,
    )


def test_request_cannot_supply_commands_identities_digests_or_authority(
    tmp_path: Path,
) -> None:
    base_lock = tmp_path / "trusted-base.lock.json"
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "candidate_lock": "candidate.lock.json",
                "cache_dir": "cache",
                "package_mirror_url": None,
                "runtime_mirror_url": None,
                "candidate_command": [sys.executable, "unrelated.py"],
                "base_identity": {"core_version": "9.9.9"},
                "allow_file_sources": True,
                "sha512": "0" * 128,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(UpgradePlanningError, match="invalid shape"):
        load_upgrade_request(request_path, trusted_base_lock=base_lock)

def test_cli_runtime_plan_upgrade_uses_candidate_lock_not_request_trust_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        request_path = tmp_path / "request.json"
        request_path.write_text(
            json.dumps(
                {
                    "candidate_lock": str(fixture.candidate_lock),
                    "cache_dir": str(tmp_path / "cli-cache"),
                    "package_mirror_url": fixture.request.package_mirror_url,
                    "runtime_mirror_url": fixture.request.runtime_mirror_url,
                }
            ),
            encoding="utf-8",
        )
        exit_code = main(
            [
                "runtime",
                "plan-upgrade",
                "--base-lock",
                str(fixture.base_lock),
                "--request",
                str(request_path),
                "--json",
            ]
        )

    result = json.loads(capsys.readouterr().out)
    assert (exit_code, result["code"], result["details"]["candidate_core_version"]) == (
        0,
        "runtime_upgrade_planned",
        "0.2.0",
    )


def test_cli_invalid_runtime_mirror_is_a_stable_domain_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        request_path = tmp_path / "invalid-mirror-request.json"
        request_path.write_text(
            json.dumps(
                {
                    "candidate_lock": str(fixture.candidate_lock),
                    "cache_dir": str(tmp_path / "cli-cache"),
                    "package_mirror_url": fixture.request.package_mirror_url,
                    "runtime_mirror_url": "http://mirror.example.test/runtime.tar.gz",
                }
            ),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "runtime",
                "plan-upgrade",
                "--base-lock",
                str(fixture.base_lock),
                "--request",
                str(request_path),
                "--json",
            ]
        )

    result = json.loads(capsys.readouterr().out)
    assert (exit_code, result["code"], result["outcome"]) == (
        1,
        "runtime_upgrade_rejected",
        "error",
    )


def test_cli_invalid_runtime_mirror_human_output_has_no_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        request_path = tmp_path / "invalid-mirror-human-request.json"
        request_path.write_text(
            json.dumps(
                {
                    "candidate_lock": str(fixture.candidate_lock),
                    "cache_dir": str(tmp_path / "cli-cache"),
                    "package_mirror_url": fixture.request.package_mirror_url,
                    "runtime_mirror_url": "file:///tmp/runtime.tar.gz",
                }
            ),
            encoding="utf-8",
        )
        exit_code = main(
            [
                "runtime",
                "plan-upgrade",
                "--base-lock",
                str(fixture.base_lock),
                "--request",
                str(request_path),
            ]
        )

    output = capsys.readouterr()
    assert exit_code == 1
    assert "Runtime upgrade is not admissible" in output.out
    assert "Traceback" not in output.out + output.err


@pytest.mark.parametrize("partial_path", ["/package.tgz", "/runtime.tar.gz"])
def test_interrupted_acquisition_is_transactional_for_candidate_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, partial_path: str
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        base_before = fixture.base_lock.read_bytes()
        _ArtifactHandler.partial_paths.add(partial_path)

        with pytest.raises(UpgradePlanningError):
            plan_upgrade(fixture.request)

        assert fixture.base_lock.read_bytes() == base_before
        assert not tuple(fixture.request.cache_dir.rglob("*.part"))
        assert not tuple(fixture.request.cache_dir.rglob("package-*"))
        assert not tuple(fixture.request.cache_dir.rglob("runtime-*"))


def test_concurrent_planners_publish_one_atomic_candidate_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        with ThreadPoolExecutor(max_workers=2) as executor:
            plans = tuple(
                executor.map(lambda _index: plan_upgrade(fixture.request), range(2))
            )

    pair_parents = {
        (plan.package.path.parent, plan.runtime.path.parent) for plan in plans
    }
    assert len(pair_parents) == 1
    package_parent, runtime_parent = next(iter(pair_parents))
    assert package_parent == runtime_parent
    assert package_parent.parent == fixture.request.cache_dir / "pairs"
    assert len(tuple((fixture.request.cache_dir / "pairs").iterdir())) == 1
    assert not tuple((fixture.request.cache_dir / ".transactions").glob("*"))


@pytest.mark.parametrize("failed_promotion", [1, 2])
def test_pair_promotion_fault_cleans_only_owned_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_promotion: int,
) -> None:
    original = runtime_upgrade._promote_staged_artifact
    calls = 0

    def fail_at_boundary(staged: object) -> object:
        nonlocal calls
        calls += 1
        if calls == failed_promotion:
            raise runtime_upgrade.ArtifactAcquisitionError("injected promotion fault")
        return original(staged)  # type: ignore[arg-type]

    monkeypatch.setattr(
        runtime_upgrade, "_promote_staged_artifact", fail_at_boundary
    )
    with _fixture(tmp_path, monkeypatch) as fixture:
        base_before = fixture.base_lock.read_bytes()
        with pytest.raises(UpgradePlanningError, match="promotion fault"):
            plan_upgrade(fixture.request)

    assert fixture.base_lock.read_bytes() == base_before
    assert not tuple((fixture.request.cache_dir / "pairs").glob("*"))
    assert not tuple((fixture.request.cache_dir / ".transactions").glob("*"))


def test_faulting_planner_never_unlinks_another_planners_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        first = plan_upgrade(fixture.request)
        pair_dir = first.package.path.parent
        before = {path.name: path.read_bytes() for path in pair_dir.iterdir()}

        def fail_owned_promotion(_staged: object) -> object:
            raise runtime_upgrade.ArtifactAcquisitionError("owned fault")

        monkeypatch.setattr(
            runtime_upgrade, "_promote_staged_artifact", fail_owned_promotion
        )
        with pytest.raises(UpgradePlanningError, match="owned fault"):
            plan_upgrade(fixture.request)

    assert {path.name: path.read_bytes() for path in pair_dir.iterdir()} == before
    assert not tuple((fixture.request.cache_dir / ".transactions").glob("*"))


def test_transaction_root_symlink_is_rejected_without_touching_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _fixture(tmp_path, monkeypatch) as fixture:
        external = tmp_path / "external-transactions"
        external.mkdir()
        sentinel = external / "sentinel"
        sentinel.write_text("keep", encoding="utf-8")
        fixture.request.cache_dir.mkdir()
        (fixture.request.cache_dir / ".transactions").symlink_to(
            external, target_is_directory=True
        )

        with pytest.raises(UpgradePlanningError, match="transaction cache"):
            plan_upgrade(fixture.request)

    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert {path.name for path in external.iterdir()} == {"sentinel"}


def test_owned_atomic_pair_is_removed_if_post_rename_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_validation(*_args: object, **_kwargs: object) -> object:
        raise CandidateContractError("injected pair validation fault")

    monkeypatch.setattr(
        runtime_upgrade, "_existing_candidate_pair", fail_validation
    )
    with _fixture(tmp_path, monkeypatch) as fixture:
        with pytest.raises(CandidateContractError, match="validation fault"):
            plan_upgrade(fixture.request)

    assert not tuple((fixture.request.cache_dir / "pairs").glob("*"))
    assert not tuple((fixture.request.cache_dir / ".transactions").glob("*"))


def test_atomic_rename_is_irreversible_after_consumer_observes_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_rename = runtime_upgrade.os.rename
    original_validation = runtime_upgrade._existing_candidate_pair
    observed: dict[str, bytes] = {}

    def observe_rename(source: Path, destination: Path) -> None:
        original_rename(source, destination)
        observed.update(
            {path.name: path.read_bytes() for path in destination.iterdir()}
        )

    def reject_public_validation(
        destination: Path, *args: object, **kwargs: object
    ) -> object:
        if destination.parent.name == "pairs":
            raise CandidateContractError("post-rename validation must not run")
        return original_validation(destination, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(runtime_upgrade.os, "rename", observe_rename)
    monkeypatch.setattr(
        runtime_upgrade, "_existing_candidate_pair", reject_public_validation
    )
    with _fixture(tmp_path, monkeypatch) as fixture:
        plan = plan_upgrade(fixture.request)

    assert observed
    assert {
        path.name: path.read_bytes() for path in plan.package.path.parent.iterdir()
    } == observed


def test_ci_requires_real_linux_and_macos_sandbox_contracts() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    sandbox_job = workflow.split("  runtime-upgrade-sandbox:", 1)[1].split(
        "\n  shellcheck:", 1
    )[0]
    assert "os: [ubuntu-latest, macos-14]" in sandbox_job
    assert "runs-on: ${{ matrix.os }}" in sandbox_job
    assert 'AGENTHARNESS_REQUIRE_SANDBOX_TEST: "1"' in sandbox_job
    assert "test_real_os_sandbox_blocks_host_writes_and_network" in sandbox_job
    assert (
        "test_real_packed_base_runtime_plans_upgrade_without_source_checkout"
        in sandbox_job
    )


def test_bounded_runner_kills_process_tree_on_output_flood(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "descendant-ran"
    script = tmp_path / "flood.py"
    script.write_text(
        """import pathlib
import subprocess
import sys
import time

subprocess.Popen(
    [sys.executable, "-c", "import pathlib,signal,time; "
     "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
     f"pathlib.Path({(sys.argv[1] + '.ready')!r}).write_text('ready'); "
     "time.sleep(1); "
     f"pathlib.Path({sys.argv[1]!r}).write_text('bad')"]
)
while not pathlib.Path(sys.argv[1] + ".ready").exists():
    time.sleep(0.01)
sys.stdout.write("x" * 1_000_000)
sys.stdout.flush()
""",
        encoding="utf-8",
    )
    started = time.monotonic()
    with pytest.raises(CandidateContractError, match="output"):
        runtime_upgrade._run_bounded_process(  # type: ignore[attr-defined]
            (sys.executable, str(script), str(marker)),
            cwd=tmp_path,
            environment={"PATH": os.environ.get("PATH", "")},
            timeout_seconds=2,
            max_output_bytes=4096,
        )
    assert time.monotonic() - started < 1
    time.sleep(1.2)
    assert not marker.exists()


def test_bounded_runner_kills_process_tree_on_timeout(tmp_path: Path) -> None:
    marker = tmp_path / "timed-out-descendant-ran"
    script = tmp_path / "timeout.py"
    script.write_text(
        """import subprocess
import sys
import time

subprocess.Popen(
    [sys.executable, "-c", "import pathlib,time; time.sleep(1); "
     f"pathlib.Path({sys.argv[1]!r}).write_text('bad')"]
)
time.sleep(10)
""",
        encoding="utf-8",
    )
    started = time.monotonic()
    with pytest.raises(CandidateContractError, match="timed out"):
        runtime_upgrade._run_bounded_process(
            (sys.executable, str(script), str(marker)),
            cwd=tmp_path,
            environment={"PATH": os.environ.get("PATH", "")},
            timeout_seconds=0.2,
            max_output_bytes=4096,
        )
    assert time.monotonic() - started < 1
    time.sleep(1.2)
    assert not marker.exists()


def test_bounded_runner_cleans_descendants_after_success(tmp_path: Path) -> None:
    marker = tmp_path / "successful-descendant-ran"
    script = tmp_path / "successful-parent.py"
    script.write_text(
        """import subprocess
import sys

subprocess.Popen(
    [sys.executable, "-c", "import pathlib,signal,time; "
     "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(1); "
     f"pathlib.Path({sys.argv[1]!r}).write_text('bad')"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print('{"ok":true}')
""",
        encoding="utf-8",
    )
    report = runtime_upgrade._run_bounded_process(
        (sys.executable, str(script), str(marker)),
        cwd=tmp_path,
        environment={"PATH": os.environ.get("PATH", "")},
        timeout_seconds=2,
        max_output_bytes=4096,
    )
    assert json.loads(report) == {"ok": True}
    time.sleep(1.2)
    assert not marker.exists()


def test_real_os_sandbox_blocks_host_writes_and_network(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside" / "escaped"
    writable = tmp_path / "private-work"
    writable.mkdir()
    script = tmp_path / "sandbox_probe.py"
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    script.write_text(
        """import json
import pathlib
import socket
import sys

outside = pathlib.Path(sys.argv[1])
writable = pathlib.Path(sys.argv[2])
port = int(sys.argv[3])
try:
    outside.write_text("escaped")
    outside_write = True
except OSError:
    outside_write = False
network = socket.socket().connect_ex(("127.0.0.1", port)) == 0
(writable / "inside").write_text("ok")
print(json.dumps({"network": network, "outside_write": outside_write}))
""",
        encoding="utf-8",
    )
    try:
        prefix = runtime_upgrade._sandbox_prefix(
            readonly_paths=(script,), writable_dir=writable
        )
    except CandidateContractError as error:
        listener.close()
        if os.environ.get("AGENTHARNESS_REQUIRE_SANDBOX_TEST") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    try:
        report = runtime_upgrade._run_bounded_process(
            (
                *prefix,
                "/usr/bin/python3",
                str(script),
                str(outside),
                str(writable),
                str(port),
            ),
            cwd=writable,
            environment={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            timeout_seconds=5,
            max_output_bytes=4096,
        )
    finally:
        listener.close()
    assert json.loads(report) == {"network": False, "outside_write": False}
    assert (writable / "inside").read_text(encoding="utf-8") == "ok"
    assert not outside.exists()


def _tracked_package_snapshot(destination: Path) -> Path:
    snapshot = destination / "package-source"
    snapshot.mkdir()
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    for encoded_path in tracked:
        if not encoded_path:
            continue
        relative = Path(encoded_path.decode("utf-8"))
        source = ROOT / relative
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            target.symlink_to(source.readlink())
        else:
            shutil.copy2(source, target)
    subprocess.run(["git", "init", "--quiet"], cwd=snapshot, check=True)
    subprocess.run(["git", "add", "--all"], cwd=snapshot, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=packaging-test@example.invalid",
            "-c",
            "user.name=Packaging Test",
            "commit",
            "--quiet",
            "-m",
            "tracked package snapshot",
        ],
        cwd=snapshot,
        check=True,
    )
    return snapshot


def _seed_packaging_dependencies(snapshot: Path) -> None:
    cache = snapshot / ".tool-cache/runtime-artifacts"
    cache.mkdir(parents=True)
    for name in (
        "pyyaml-6.0.3.tar.gz",
        "fastjsonschema-2.21.2-py3-none-any.whl",
    ):
        source = ROOT / ".tool-cache/runtime-artifacts" / name
        assert source.is_file(), f"missing pinned packaging fixture: {source}"
        shutil.copy2(source, cache / name)


def test_real_packed_base_runtime_plans_upgrade_without_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sandbox_probe = tmp_path / "sandbox-probe"
    sandbox_probe.mkdir()
    try:
        runtime_upgrade._sandbox_prefix(
            readonly_paths=(), writable_dir=sandbox_probe
        )
    except CandidateContractError as error:
        if os.environ.get("AGENTHARNESS_REQUIRE_SANDBOX_TEST") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    snapshot = _tracked_package_snapshot(tmp_path)
    _seed_packaging_dependencies(snapshot)
    packed_dir = tmp_path / "packed"
    packed_dir.mkdir()
    packed = subprocess.run(
        ["npm", "pack", "--json", "--pack-destination", str(packed_dir)],
        cwd=snapshot,
        check=True,
        capture_output=True,
        text=True,
    )
    json_start = packed.stdout.find("[\n  {")
    assert json_start >= 0, packed.stdout
    result, _ = json.JSONDecoder().raw_decode(packed.stdout[json_start:])
    tarball = packed_dir / result[0]["filename"]
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with tarfile.open(tarball, "r:gz") as archive:
        archive.extractall(extracted, filter="data")
    packaged_root = extracted / "package"
    bootstrapper = packaged_root / "templates/bootstrap/verify-runtime.mjs"
    assert bootstrapper.is_file()
    assert {
        path.relative_to(packaged_root).as_posix()
        for path in (packaged_root / "templates").rglob("*")
        if path.is_file()
    } == {"templates/bootstrap/verify-runtime.mjs"}

    shutil.rmtree(snapshot)
    assert not snapshot.exists()
    upgrade_tmp = tmp_path / "upgrade"
    upgrade_tmp.mkdir()
    with _fixture(upgrade_tmp, monkeypatch) as fixture:
        request_path = tmp_path / "upgrade-request.json"
        request_path.write_text(
            json.dumps(
                {
                    "candidate_lock": str(fixture.candidate_lock),
                    "cache_dir": str(tmp_path / "packaged-cache"),
                    "package_mirror_url": fixture.request.package_mirror_url,
                    "runtime_mirror_url": fixture.request.runtime_mirror_url,
                }
            ),
            encoding="utf-8",
        )
        dns_shim = tmp_path / "dns-shim"
        dns_shim.mkdir()
        (dns_shim / "sitecustomize.py").write_text(
            """import socket

_getaddrinfo = socket.getaddrinfo


def _local_test_dns(host, port, *args, **kwargs):
    if host == \"mirror.example.test\":
        host = \"127.0.0.1\"
    return _getaddrinfo(host, port, *args, **kwargs)


socket.getaddrinfo = _local_test_dns
""",
            encoding="utf-8",
        )
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "SSL_CERT_FILE": os.environ["SSL_CERT_FILE"],
            "NO_PROXY": os.environ["NO_PROXY"],
            "PYTHONPATH": str(dns_shim),
        }
        completed = subprocess.run(
            [
                sys.executable,
                str(packaged_root / "dist/agentharness.pyz"),
                "runtime",
                "plan-upgrade",
                "--base-lock",
                str(fixture.base_lock),
                "--request",
                str(request_path),
                "--json",
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["code"] == "runtime_upgrade_planned"
