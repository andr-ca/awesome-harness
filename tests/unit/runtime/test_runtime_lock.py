from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

try:
    import fastjsonschema
except ModuleNotFoundError:
    runtime_wheel = next(
        (Path(__file__).resolve().parents[3] / ".tool-cache/runtime-artifacts").glob(
            "fastjsonschema-2.21.2-py3-none-any.whl"
        )
    )
    sys.path.insert(0, str(runtime_wheel))
    import fastjsonschema

from agentharness.runtime_lock import (
    SUPPORTED_RUNTIME_TARGETS,
    RuntimeLockError,
    load_runtime_manifest,
    validate_consumer_lock,
)

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_MANIFEST = ROOT / "runtime/python-build-standalone.lock.json"
SCHEMA = ROOT / "src/agentharness/schemas/runtime-lock-v1.json"


def _load_lock_builder() -> ModuleType:
    return _load_tool("build-runtime-lock.py")


def _load_tool(filename: str) -> ModuleType:
    path = ROOT / "tools/runtime" / filename
    module_name = filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_packed_package(
    tmp_path: Path,
    *,
    name: str = "agentharness-toolkit",
    version: str = "0.2.0",
    core_version: str = "0.1.0",
) -> tuple[Path, Path, Path]:
    zipapp = io.BytesIO()
    with zipfile.ZipFile(zipapp, "w") as archive:
        archive.writestr(
            "agentharness-runtime-identity.json",
            json.dumps(
                {
                    "bundled_plugins": {},
                    "compatibility_provider_version": "0.1.0",
                    "core_version": core_version,
                    "schema_version": 1,
                },
                sort_keys=True,
            ),
        )
    tarball = tmp_path / f"{name}-{version}.tgz"
    with tarfile.open(tarball, "w:gz") as archive:
        package_json = json.dumps({"name": name, "version": version}).encode()
        package_info = tarfile.TarInfo("package/package.json")
        package_info.size = len(package_json)
        archive.addfile(package_info, io.BytesIO(package_json))
        zipapp_info = tarfile.TarInfo("package/dist/agentharness.pyz")
        zipapp_info.size = len(zipapp.getvalue())
        archive.addfile(zipapp_info, io.BytesIO(zipapp.getvalue()))
    digest = hashlib.sha512(tarball.read_bytes()).digest()
    sri = "sha512-" + base64.b64encode(digest).decode("ascii")
    pack_result = tmp_path / "pack-result.json"
    pack_result.write_text(
        json.dumps(
            [
                {
                    "filename": tarball.name,
                    "name": name,
                    "version": version,
                    "integrity": sri,
                }
            ]
        )
    )
    registry_metadata = tmp_path / "registry.json"
    registry_metadata.write_text(
        json.dumps(
            {
                "name": name,
                "version": version,
                "dist": {
                    "integrity": sri,
                    "tarball": (
                        f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz"
                    ),
                },
            }
        )
    )
    return tarball, pack_result, registry_metadata


def _trusted_build_inputs(tmp_path: Path, tarball: Path) -> dict[str, Path]:
    with tarfile.open(tarball, "r:gz") as archive:
        member = archive.extractfile("package/dist/agentharness.pyz")
        assert member is not None
        digest = hashlib.sha512(member.read()).hexdigest()
    digest_path = tmp_path / "agentharness.pyz.sha512"
    digest_path.write_text(f"{digest}  agentharness.pyz\n")
    return {
        "trusted_package_path": ROOT / "package.json",
        "trusted_source_root": ROOT / "src",
        "expected_zipapp_digest_path": digest_path,
    }


def _consumer_lock() -> dict[str, Any]:
    runtimes = json.loads(RUNTIME_MANIFEST.read_text())["runtimes"]
    return {
        "schema_version": 1,
        "package": {
            "name": "agentharness-toolkit",
            "version": "0.2.0",
            "registry_url": "https://registry.npmjs.org",
            "tarball_url": (
                "https://registry.npmjs.org/agentharness-toolkit/-/"
                "agentharness-toolkit-0.2.0.tgz"
            ),
            "registry_sri": "sha512-"
            + base64.b64encode(bytes.fromhex("01" * 64)).decode("ascii"),
            "sha512": "01" * 64,
            "allowed_mirror_url": "https://artifacts.example.test/npm/",
        },
        "zipapp": {
            "path": "package/dist/agentharness.pyz",
            "sha512": "02" * 64,
            "core_version": "0.1.0",
            "schema_version": 1,
            "bundled_plugins": {},
            "compatibility_provider_version": "0.1.0",
        },
        "runtimes": runtimes,
        "acquisition": {
            "selected_target": "x86_64-unknown-linux-gnu",
            "selected_source": "upstream",
            "mirror_policy": {
                "require_https": True,
                "require_matching_digest": True,
                "allowed_runtime_mirror_hosts": ["artifacts.example.test"],
            },
            "limits": {
                "max_compressed_bytes": 268_435_456,
                "max_expanded_bytes": 1_073_741_824,
                "max_member_bytes": 268_435_456,
                "max_members": 100_000,
                "max_redirects": 3,
                "max_path_bytes": 4_096,
            },
            "bootstrap_protocol_version": 1,
        },
    }


def test_reviewed_runtime_manifest_has_exact_supported_targets() -> None:
    manifest = load_runtime_manifest(RUNTIME_MANIFEST)

    assert tuple(runtime.target for runtime in manifest.runtimes) == tuple(
        SUPPORTED_RUNTIME_TARGETS
    )


def test_reviewed_runtime_manifest_uses_immutable_https_release_assets() -> None:
    manifest = load_runtime_manifest(RUNTIME_MANIFEST)

    assert {
        (
            runtime.url.startswith(
                "https://github.com/astral-sh/python-build-standalone/"
                "releases/download/20260510/"
            ),
            len(runtime.sha256),
            len(runtime.sha512),
            runtime.archive_prefix,
            runtime.interpreter_path,
        )
        for runtime in manifest.runtimes
    } == {(True, 64, 128, "python/", "python/bin/python3")}


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda lock: lock["runtimes"].append(lock["runtimes"][0]), "duplicate"),
        (lambda lock: lock["runtimes"][0].pop("sha256"), "sha256"),
        (lambda lock: lock["runtimes"][0].pop("sha512"), "sha512"),
        (
            lambda lock: lock["runtimes"][0].update(url="http://example.test/x"),
            "HTTPS",
        ),
        (
            lambda lock: lock["runtimes"][0].update(target="riscv64-linux"),
            "supported",
        ),
    ],
)
def test_runtime_manifest_rejects_unsafe_or_ambiguous_entries(
    tmp_path: Path,
    mutation: Any,
    message: str,
) -> None:
    document = json.loads(RUNTIME_MANIFEST.read_text())
    mutation(document)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(document))

    with pytest.raises(RuntimeLockError, match=message):
        load_runtime_manifest(path)


def test_consumer_schema_is_closed_and_requires_every_section() -> None:
    schema = json.loads(SCHEMA.read_text())

    assert schema["required"] == [
        "schema_version",
        "package",
        "zipapp",
        "runtimes",
        "acquisition",
    ]
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda lock: lock["runtimes"].__setitem__(
            1, {**lock["runtimes"][0], "sha256": "ab" * 32}
        ),
        lambda lock: lock["runtimes"][0].update(target="unsupported-target"),
        lambda lock: lock["runtimes"][0].update(unknown=True),
        lambda lock: lock["runtimes"][0].pop("interpreter_path"),
        lambda lock: lock["acquisition"]["limits"].update(unknown=1),
    ],
)
def test_executed_consumer_schema_rejects_target_and_closure_violations(
    mutation: Any,
) -> None:
    validator = fastjsonschema.compile(json.loads(SCHEMA.read_text()))
    document = _consumer_lock()
    mutation(document)
    with pytest.raises(fastjsonschema.JsonSchemaException):
        validator(document)


def test_executed_consumer_schema_accepts_complete_lock() -> None:
    validator = fastjsonschema.compile(json.loads(SCHEMA.read_text()))
    validator(_consumer_lock())


def test_runtime_manifest_rejects_target_filename_mismatch(tmp_path: Path) -> None:
    document = json.loads(RUNTIME_MANIFEST.read_text())
    document["runtimes"][0]["url"] = document["runtimes"][1]["url"]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(document))
    with pytest.raises(RuntimeLockError, match="filename|URL"):
        load_runtime_manifest(path)


def test_json_loader_rejects_duplicate_keys_and_oversized_input(tmp_path: Path) -> None:
    from agentharness.runtime_lock import load_json_document

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(RuntimeLockError, match="duplicate"):
        load_json_document(duplicate)
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (1_048_576 + 1))
    with pytest.raises(RuntimeLockError, match="size"):
        load_json_document(oversized)


def test_complete_consumer_lock_preserves_exact_identity_and_limits() -> None:
    lock = validate_consumer_lock(_consumer_lock())

    assert (
        lock.package.name,
        lock.package.version,
        lock.package.registry_url,
        lock.package.tarball_url,
        lock.package.registry_sri,
        lock.package.sha512,
        lock.zipapp.path,
        lock.zipapp.core_version,
        lock.zipapp.schema_version,
        dict(lock.zipapp.bundled_plugins),
        lock.zipapp.compatibility_provider_version,
        lock.acquisition.selected_target,
        lock.acquisition.selected_source,
        lock.acquisition.limits.max_compressed_bytes,
        lock.acquisition.limits.max_expanded_bytes,
        lock.acquisition.limits.max_member_bytes,
        lock.acquisition.limits.max_members,
        lock.acquisition.limits.max_redirects,
        lock.acquisition.limits.max_path_bytes,
        lock.acquisition.bootstrap_protocol_version,
    ) == (
        "agentharness-toolkit",
        "0.2.0",
        "https://registry.npmjs.org",
        "https://registry.npmjs.org/agentharness-toolkit/-/agentharness-toolkit-0.2.0.tgz",
        "sha512-" + base64.b64encode(bytes.fromhex("01" * 64)).decode("ascii"),
        "01" * 64,
        "package/dist/agentharness.pyz",
        "0.1.0",
        1,
        {},
        "0.1.0",
        "x86_64-unknown-linux-gnu",
        "upstream",
        268_435_456,
        1_073_741_824,
        268_435_456,
        100_000,
        3,
        4_096,
        1,
    )


@pytest.mark.parametrize(
    "path",
    [
        ("package", "name"),
        ("package", "version"),
        ("package", "registry_url"),
        ("package", "tarball_url"),
        ("package", "registry_sri"),
        ("package", "sha512"),
        ("package", "allowed_mirror_url"),
        ("zipapp", "path"),
        ("zipapp", "sha512"),
        ("zipapp", "core_version"),
        ("zipapp", "schema_version"),
        ("zipapp", "bundled_plugins"),
        ("zipapp", "compatibility_provider_version"),
        ("acquisition", "selected_target"),
        ("acquisition", "selected_source"),
        ("acquisition", "mirror_policy"),
        ("acquisition", "limits"),
        ("acquisition", "bootstrap_protocol_version"),
    ],
)
def test_consumer_lock_rejects_missing_identity_or_policy_fields(
    path: tuple[str, str],
) -> None:
    document = copy.deepcopy(_consumer_lock())
    del document[path[0]][path[1]]

    with pytest.raises(RuntimeLockError, match=path[1]):
        validate_consumer_lock(document)


def test_consumer_lock_rejects_noncanonical_package_identity() -> None:
    document = _consumer_lock()
    document["package"]["name"] = "another-package"

    with pytest.raises(RuntimeLockError, match="agentharness-toolkit"):
        validate_consumer_lock(document)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "registry_sri",
            "sha512-" + base64.b64encode(bytes(64)).decode(),
            "registry_sri",
        ),
        ("registry_url", "https://registry.example.test", "registry_url"),
        (
            "tarball_url",
            "https://registry.npmjs.org/other/-/other-0.2.0.tgz",
            "tarball_url",
        ),
    ],
)
def test_public_consumer_validator_rejects_package_identity_contradictions(
    field: str, value: str, message: str
) -> None:
    document = _consumer_lock()
    document["package"][field] = value

    with pytest.raises(RuntimeLockError, match=message):
        validate_consumer_lock(document)


@pytest.mark.parametrize(
    ("host", "valid"),
    [
        ("artifacts.example.test", True),
        ("mirror-1.example.com", True),
        ("localhost", False),
        ("127.0.0.1", False),
        ("host.example:443", False),
        ("user@host.example", False),
        ("bad/host.example", False),
        ("bad host.example", False),
        ("-bad.example", False),
    ],
)
def test_mirror_host_corpus_has_schema_and_handwritten_validator_parity(
    host: str, valid: bool
) -> None:
    builder = _load_lock_builder()
    document = _consumer_lock()
    document["acquisition"]["mirror_policy"]["allowed_runtime_mirror_hosts"] = [host]
    validator = fastjsonschema.compile(json.loads(SCHEMA.read_text()))
    assert (builder.MIRROR_HOST_PATTERN.fullmatch(host) is not None) is valid

    for validate, error in (
        (validate_consumer_lock, RuntimeLockError),
        (validator, fastjsonschema.JsonSchemaException),
    ):
        if valid:
            validate(document)
        else:
            with pytest.raises(error):
                validate(document)


def test_consumer_lock_rejects_weakened_archive_limits() -> None:
    document = _consumer_lock()
    document["acquisition"]["limits"]["max_redirects"] = 4

    with pytest.raises(RuntimeLockError, match="max_redirects"):
        validate_consumer_lock(document)


def test_builder_uses_real_pack_integrity_and_packed_zipapp_identity(
    tmp_path: Path,
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)

    document = builder.build_consumer_lock(
        pack_result_path=pack_result,
        registry_metadata_path=registry_metadata,
        runtime_manifest_path=RUNTIME_MANIFEST,
        tarball_path=tarball,
        allowed_mirror_url="https://artifacts.example.test/npm/",
        selected_target="x86_64-unknown-linux-gnu",
        runtime_mirror_hosts=("artifacts.example.test",),
        **_trusted_build_inputs(tmp_path, tarball),
    )

    digest = hashlib.sha512(tarball.read_bytes()).hexdigest()
    assert (
        document["package"]["name"],
        document["package"]["version"],
        document["package"]["registry_sri"],
        document["package"]["sha512"],
        document["zipapp"]["path"],
        document["zipapp"]["core_version"],
        document["zipapp"]["schema_version"],
        document["zipapp"]["bundled_plugins"],
        document["zipapp"]["compatibility_provider_version"],
    ) == (
        "agentharness-toolkit",
        "0.2.0",
        json.loads(pack_result.read_text())[0]["integrity"],
        digest,
        "package/dist/agentharness.pyz",
        "0.1.0",
        1,
        {},
        "0.1.0",
    )


def test_builder_rejects_pack_integrity_mismatch(tmp_path: Path) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    metadata = json.loads(registry_metadata.read_text())
    metadata["dist"]["integrity"] = "sha512-AQ=="
    registry_metadata.write_text(json.dumps(metadata))

    with pytest.raises(RuntimeLockError, match="integrity"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=(),
            **_trusted_build_inputs(tmp_path, tarball),
        )


def test_builder_rejects_mutually_consistent_forged_package_version(
    tmp_path: Path,
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(
        tmp_path, version="9.9.9"
    )
    with pytest.raises(RuntimeLockError, match="trusted|version"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=(),
            **_trusted_build_inputs(tmp_path, tarball),
        )


def test_builder_rejects_zipapp_not_matching_trusted_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    trusted = _trusted_build_inputs(tmp_path, tarball)
    trusted["expected_zipapp_digest_path"].write_text(
        f"{'0' * 128}  agentharness.pyz\n"
    )
    monkeypatch.setattr(
        builder.zipfile,
        "ZipFile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("zip opened before digest verification")
        ),
    )
    with pytest.raises(RuntimeLockError, match="zipapp.*digest|digest.*zipapp"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=(),
            **trusted,
        )


def test_builder_rejects_bad_npm_digest_before_tar_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    trusted = _trusted_build_inputs(tmp_path, tarball)
    tarball.write_bytes(tarball.read_bytes() + b"tamper")
    monkeypatch.setattr(
        builder.tarfile,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("tar opened before digest verification")
        ),
    )
    with pytest.raises(RuntimeLockError, match="integrity"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=(),
            **trusted,
        )


@pytest.mark.parametrize(
    "payload",
    [b'{"name":"a","name":"b","version":"0.2.0"}', b" " * 1_048_577],
)
def test_packed_package_json_is_bounded_and_duplicate_aware(
    tmp_path: Path, payload: bytes
) -> None:
    builder = _load_lock_builder()
    tarball = tmp_path / "package.tgz"
    with tarfile.open(tarball, "w:gz") as archive:
        info = tarfile.TarInfo("package/package.json")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
        z = tarfile.TarInfo("package/dist/agentharness.pyz")
        z.size = 1
        archive.addfile(z, io.BytesIO(b"x"))
    with pytest.raises(RuntimeLockError, match="duplicate|size"):
        builder._packed_files(tarball.read_bytes())


def test_oversized_declared_package_json_rejects_before_extract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = _load_lock_builder()
    member = tarfile.TarInfo("package/package.json")
    member.size = builder.MAX_EMBEDDED_JSON_BYTES + 1

    class FakeArchive:
        def __enter__(self) -> FakeArchive:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self):
            return iter((member,))

        def extractfile(self, _member: tarfile.TarInfo):
            raise AssertionError("oversized package JSON body was read")

    monkeypatch.setattr(builder.tarfile, "open", lambda **_kwargs: FakeArchive())
    with pytest.raises(RuntimeLockError, match="package.json.*size|size.*package.json"):
        builder._packed_files(b"authenticated")


def test_package_json_declared_length_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = _load_lock_builder()
    package = tarfile.TarInfo("package/package.json")
    package.size = 2
    zipapp = tarfile.TarInfo("package/dist/agentharness.pyz")
    zipapp.size = 1

    class ShortStream(io.BytesIO):
        pass

    class FakeArchive:
        def __enter__(self) -> FakeArchive:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self):
            return iter((package, zipapp))

        def extractfile(self, member: tarfile.TarInfo):
            return ShortStream(b"{" if member is package else b"x")

    monkeypatch.setattr(builder.tarfile, "open", lambda **_kwargs: FakeArchive())
    with pytest.raises(RuntimeLockError, match="length"):
        builder._packed_files(b"authenticated")


@pytest.mark.parametrize(
    ("payload", "limit"),
    [
        (b'{"core_version":"0.1.0","core_version":"9.9.9"}', 1024),
        (b" " * 33, 32),
    ],
)
def test_packed_identity_json_is_bounded_and_duplicate_aware(
    payload: bytes, limit: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_lock_builder()
    monkeypatch.setattr(builder, "MAX_EMBEDDED_JSON_BYTES", limit)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("agentharness-runtime-identity.json", payload)
    with pytest.raises(RuntimeLockError, match="duplicate|size"):
        builder._zipapp_identity(stream.getvalue())


def test_builder_rejects_fabricated_packed_identity(tmp_path: Path) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(
        tmp_path, core_version="9.9.9"
    )
    with pytest.raises(RuntimeLockError, match="identity"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=(),
            **_trusted_build_inputs(tmp_path, tarball),
        )


def test_lock_builder_bounds_and_disambiguates_json(tmp_path: Path) -> None:
    builder = _load_lock_builder()
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"name":"a","name":"b"}')
    with pytest.raises(RuntimeLockError, match="duplicate"):
        builder._load_json(duplicate)
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (builder.MAX_JSON_BYTES + 1))
    with pytest.raises(RuntimeLockError, match="size"):
        builder._load_json(oversized)


@pytest.mark.parametrize(
    "member_name", ["package/package.json", "package/dist/agentharness.pyz"]
)
def test_lock_builder_rejects_duplicate_npm_tar_members(
    tmp_path: Path, member_name: str
) -> None:
    builder = _load_lock_builder()
    tarball = tmp_path / "duplicate.tgz"
    with tarfile.open(tarball, "w:gz") as archive:
        for _ in range(2):
            payload = b"{}"
            info = tarfile.TarInfo(member_name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(RuntimeLockError, match="duplicate"):
        builder._packed_files(tarball.read_bytes())


@pytest.mark.parametrize(
    "tarball_url",
    [
        "https://evil.example/agentharness-toolkit-0.2.0.tgz",
        "https://registry.npmjs.org/other/-/other-0.2.0.tgz",
        "http://registry.npmjs.org/agentharness-toolkit/-/agentharness-toolkit-0.2.0.tgz",
    ],
)
def test_lock_builder_rejects_noncanonical_registry_tarball(
    tmp_path: Path, tarball_url: str
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    metadata = json.loads(registry_metadata.read_text())
    metadata["dist"]["tarball"] = tarball_url
    registry_metadata.write_text(json.dumps(metadata))
    with pytest.raises(RuntimeLockError, match="canonical"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=(),
            **_trusted_build_inputs(tmp_path, tarball),
        )


def test_lock_builder_rejects_file_directory_collision(tmp_path: Path) -> None:
    builder = _load_lock_builder()
    tarball = tmp_path / "collision.tgz"
    with tarfile.open(tarball, "w:gz") as archive:
        payload = b"x"
        parent = tarfile.TarInfo("package")
        parent.size = len(payload)
        archive.addfile(parent, io.BytesIO(payload))
        child = tarfile.TarInfo("package/package.json")
        child.size = len(payload)
        archive.addfile(child, io.BytesIO(payload))
    with pytest.raises(RuntimeLockError, match="collision"):
        builder._packed_files(tarball.read_bytes())


@pytest.mark.parametrize("payload", [b'{"assets":[],"assets":[]}', b" " * 33])
def test_updater_rejects_duplicate_or_oversized_api_json(
    payload: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    monkeypatch.setattr(updater, "MAX_API_BYTES", 32)
    monkeypatch.setattr(
        updater.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse(payload, updater.API_URL),
    )
    with pytest.raises(updater.RuntimeManifestUpdateError, match="duplicate|size"):
        updater.build_review_manifest()


class _FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, url: str) -> None:
        super().__init__(payload)
        self._url = url

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def geturl(self) -> str:
        return self._url


def test_updater_builds_manifest_from_immutable_release_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    payloads = {target: f"runtime:{target}".encode() for target in updater.TARGETS}
    assets = []
    for target, payload in payloads.items():
        name = (
            f"cpython-{updater.PYTHON_VERSION}+{updater.RELEASE}-"
            f"{target}-{updater.FLAVOR}"
        )
        assets.append(
            {
                "name": name,
                "browser_download_url": (
                    "https://github.com/astral-sh/python-build-standalone/"
                    f"releases/download/{updater.RELEASE}/"
                    f"{name.replace('+', '%2B')}"
                ),
                "digest": f"sha256:{hashlib.sha256(payload).hexdigest()}",
            }
        )

    def urlopen(request: Any, timeout: int) -> _FakeResponse:
        del timeout
        url = request.full_url
        if url == updater.API_URL:
            return _FakeResponse(json.dumps({"assets": assets}).encode(), url)
        target = next(target for target in updater.TARGETS if target in url)
        return _FakeResponse(payloads[target], url)

    monkeypatch.setattr(updater.urllib.request, "urlopen", urlopen)

    document = updater.build_review_manifest()

    assert [runtime["sha512"] for runtime in document["runtimes"]] == [
        hashlib.sha512(payloads[target]).hexdigest() for target in updater.TARGETS
    ]


def test_updater_main_writes_reviewed_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    output = tmp_path / "runtime.json"
    document = {"schema_version": 1}
    monkeypatch.setattr(
        updater,
        "_arguments",
        lambda: argparse.Namespace(output=output, check=False),
    )
    monkeypatch.setattr(updater, "build_review_manifest", lambda: document)

    assert (updater.main(), json.loads(output.read_text())) == (0, document)


def test_verifier_checks_cached_sha256_and_sha512(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    manifest = load_runtime_manifest(RUNTIME_MANIFEST)
    expected: dict[tuple[str, str], str] = {}
    for runtime in manifest.runtimes:
        filename = Path(runtime.url).name
        (tmp_path / filename).write_bytes(b"cached")
        expected[(filename, "sha256")] = runtime.sha256
        expected[(filename, "sha512")] = runtime.sha512
    monkeypatch.setattr(
        verifier,
        "_digests",
        lambda path, _limit: (
            expected[(path.name, "sha256")],
            expected[(path.name, "sha512")],
        ),
    )

    verifier.verify_runtime_lock(
        RUNTIME_MANIFEST,
        artifact_directory=tmp_path,
        require_artifacts=True,
    )


def test_verifier_requires_explicit_artifact_directory() -> None:
    verifier = _load_tool("verify-runtime-lock.py")

    with pytest.raises(RuntimeLockError, match="artifact-directory"):
        verifier.verify_runtime_lock(
            RUNTIME_MANIFEST,
            artifact_directory=None,
            require_artifacts=True,
        )


def test_verifier_main_reports_validation_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    monkeypatch.setattr(
        verifier,
        "_arguments",
        lambda: argparse.Namespace(
            manifest=RUNTIME_MANIFEST,
            consumer_lock=None,
            artifact_directory=None,
            require_artifacts=False,
            structure_only=True,
        ),
    )
    monkeypatch.setattr(
        verifier,
        "verify_runtime_lock",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeLockError("bad lock")),
    )

    assert (verifier.main(), "bad lock" in capsys.readouterr().err) == (1, True)


def test_lock_builder_main_writes_validated_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    output = tmp_path / "runtime.lock"
    monkeypatch.setattr(
        builder,
        "_arguments",
        lambda: argparse.Namespace(
            pack_result=pack_result,
            registry_metadata=registry_metadata,
            tarball=tarball,
            runtime_manifest=RUNTIME_MANIFEST,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_host=[],
            trusted_package_json=ROOT / "package.json",
            trusted_source_root=ROOT / "src",
            expected_zipapp_digest=_trusted_build_inputs(tmp_path, tarball)[
                "expected_zipapp_digest_path"
            ],
            output=output,
        ),
    )

    assert (builder.main(), json.loads(output.read_text())["schema_version"]) == (0, 1)


def test_updater_rejects_non_https_asset_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    monkeypatch.setattr(
        updater.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse(b"payload", "http://unsafe.test/x"),
    )
    with pytest.raises(updater.RuntimeManifestUpdateError, match="HTTPS"):
        updater._download_digests("https://example.test/runtime")


def test_updater_check_rejects_changed_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    output = tmp_path / "runtime.json"
    output.write_text("{}\n")
    monkeypatch.setattr(
        updater,
        "_arguments",
        lambda: argparse.Namespace(output=output, check=True),
    )
    monkeypatch.setattr(updater, "build_review_manifest", lambda: {"schema_version": 1})
    assert (updater.main(), "differs" in capsys.readouterr().err) == (1, True)


def test_verifier_rejects_missing_required_cached_artifact(tmp_path: Path) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    with pytest.raises(RuntimeLockError, match="missing.*seed.*artifact-directory"):
        verifier.verify_runtime_lock(
            RUNTIME_MANIFEST,
            artifact_directory=tmp_path,
            require_artifacts=True,
        )


def test_verifier_rejects_cached_digest_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    runtime = load_runtime_manifest(RUNTIME_MANIFEST).runtimes[0]
    (tmp_path / Path(runtime.url).name).write_bytes(b"bad")
    monkeypatch.setattr(verifier, "_digests", lambda *_args: ("0" * 64, "0" * 128))
    with pytest.raises(RuntimeLockError, match="SHA-256 mismatch"):
        verifier.verify_runtime_lock(
            RUNTIME_MANIFEST,
            artifact_directory=tmp_path,
        )


def test_verifier_main_reports_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    monkeypatch.setattr(
        verifier,
        "_arguments",
        lambda: argparse.Namespace(
            manifest=RUNTIME_MANIFEST,
            consumer_lock=None,
            artifact_directory=None,
            require_artifacts=False,
            structure_only=True,
        ),
    )
    assert (verifier.main(), "verified" in capsys.readouterr().out) == (0, True)


def test_lock_builder_main_reports_domain_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder = _load_lock_builder()
    monkeypatch.setattr(
        builder,
        "_arguments",
        lambda: argparse.Namespace(
            pack_result=tmp_path / "missing.json",
            registry_metadata=tmp_path / "missing-registry.json",
            tarball=tmp_path / "missing.tgz",
            runtime_manifest=RUNTIME_MANIFEST,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_host=[],
            output=tmp_path / "runtime.lock",
        ),
    )
    assert (builder.main(), "failed" in capsys.readouterr().err) == (1, True)


def test_verifier_hashes_file_bytes(tmp_path: Path) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    artifact = tmp_path / "artifact"
    artifact.write_bytes(b"artifact bytes")
    assert verifier._digests(artifact, 1024) == (
        hashlib.sha256(b"artifact bytes").hexdigest(),
        hashlib.sha512(b"artifact bytes").hexdigest(),
    )


def test_verifier_allows_absent_optional_artifact_directory(tmp_path: Path) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    verifier.verify_runtime_lock(
        RUNTIME_MANIFEST,
        artifact_directory=tmp_path,
        require_artifacts=False,
    )


def test_verifier_rejects_cached_sha512_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    runtime = load_runtime_manifest(RUNTIME_MANIFEST).runtimes[0]
    (tmp_path / Path(runtime.url).name).write_bytes(b"bad")
    monkeypatch.setattr(
        verifier,
        "_digests",
        lambda *_args: (runtime.sha256, "0" * 128),
    )
    with pytest.raises(RuntimeLockError, match="SHA-512 mismatch"):
        verifier.verify_runtime_lock(
            RUNTIME_MANIFEST,
            artifact_directory=tmp_path,
        )


def test_verifier_loads_optional_consumer_lock(tmp_path: Path) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    consumer_lock = tmp_path / "runtime.lock"
    consumer_lock.write_text(json.dumps(_consumer_lock()))
    verifier.verify_runtime_lock(
        RUNTIME_MANIFEST,
        consumer_lock_path=consumer_lock,
        require_artifacts=False,
    )


def test_updater_rejects_unexpected_release_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    monkeypatch.setattr(
        updater.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse(b"[]", updater.API_URL),
    )
    with pytest.raises(updater.RuntimeManifestUpdateError, match="shape"):
        updater.build_review_manifest()


def test_lock_builder_rejects_duplicate_runtime_mirror_hosts(tmp_path: Path) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    with pytest.raises(RuntimeLockError, match="duplicate"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=("same.example", "same.example"),
            **_trusted_build_inputs(tmp_path, tarball),
        )


def test_lock_builder_rejects_mirror_host_rejected_by_shared_corpus(
    tmp_path: Path,
) -> None:
    builder = _load_lock_builder()
    tarball, pack_result, registry_metadata = _make_packed_package(tmp_path)
    with pytest.raises(RuntimeLockError, match="DNS hostnames"):
        builder.build_consumer_lock(
            pack_result_path=pack_result,
            registry_metadata_path=registry_metadata,
            runtime_manifest_path=RUNTIME_MANIFEST,
            tarball_path=tarball,
            allowed_mirror_url="https://artifacts.example.test/npm/",
            selected_target="x86_64-unknown-linux-gnu",
            runtime_mirror_hosts=("host.example:443",),
            **_trusted_build_inputs(tmp_path, tarball),
        )


def test_verifier_opens_artifact_once_for_both_digests() -> None:
    verifier = _load_tool("verify-runtime-lock.py")

    class ReplacedPath:
        opens = 0

        def open(self, mode: str) -> io.BytesIO:
            assert mode == "rb"
            self.opens += 1
            return io.BytesIO(b"authenticated" if self.opens == 1 else b"replaced")

    artifact = ReplacedPath()
    assert verifier._digests(artifact, 1024) == (
        hashlib.sha256(b"authenticated").hexdigest(),
        hashlib.sha512(b"authenticated").hexdigest(),
    )
    assert artifact.opens == 1


def test_verifier_streaming_hash_enforces_actual_byte_limit(tmp_path: Path) -> None:
    verifier = _load_tool("verify-runtime-lock.py")
    artifact = tmp_path / "oversized"
    artifact.write_bytes(b"12345")

    with pytest.raises(RuntimeLockError, match="compressed-size limit"):
        verifier._digests(artifact, 4)


@pytest.mark.parametrize(
    "redirect_url",
    [
        "http://api.github.com/releases/1",
        "https://evil.example/releases/1",
        "https://user@api.github.com/releases/1",
        "https://api.github.com:444/releases/1",
    ],
)
def test_updater_rejects_unapproved_release_api_redirect(
    redirect_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    updater = _load_tool("update-runtime-lock.py")
    monkeypatch.setattr(
        updater.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse(b"{}", redirect_url),
    )

    with pytest.raises(updater.RuntimeManifestUpdateError, match="release API"):
        updater.build_review_manifest()


def test_trusted_identity_reports_nonliteral_constant(tmp_path: Path) -> None:
    builder = _load_lock_builder()
    package = tmp_path / "agentharness"
    package.mkdir()
    (package / "__init__.py").write_text(
        "__version__ = calculate_version()\nRESULT_SCHEMA_VERSION = 1\n"
    )

    with pytest.raises(RuntimeLockError, match="not literal"):
        builder._trusted_identity(tmp_path)


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
    assert not (snapshot / "dist/agentharness.pyz").exists()
    assert not (snapshot / ".tool-cache").exists()
    assert not (snapshot / "node_modules").exists()
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


def _seed_packaging_cache(snapshot: Path) -> Path:
    source_cache = ROOT / ".tool-cache/runtime-artifacts"
    runtime_document = json.loads(RUNTIME_MANIFEST.read_text())
    names = {
        "pyyaml-6.0.3.tar.gz",
        "fastjsonschema-2.21.2-py3-none-any.whl",
        *(Path(runtime["url"]).name for runtime in runtime_document["runtimes"]),
    }
    assert len(names) == 6
    cache = snapshot / ".tool-cache/runtime-artifacts"
    cache.mkdir(parents=True)
    for name in sorted(names):
        source = source_cache / name
        if not source.is_file():
            pytest.fail(
                f"required pinned packaging fixture is missing: {source}; "
                "seed the runtime artifact cache before running the integration test"
            )
        shutil.copy2(source, cache / name)
    assert {path.name for path in cache.iterdir()} == names
    return cache


def test_real_npm_pack_builds_and_verifies_consumer_lock(tmp_path: Path) -> None:
    snapshot = _tracked_package_snapshot(tmp_path)
    cache = _seed_packaging_cache(snapshot)
    output_directory = tmp_path / "packed"
    output_directory.mkdir()
    assert not (snapshot / "dist/agentharness.pyz").exists()

    completed = subprocess.run(
        [
            "npm",
            "pack",
            "--json",
            "--pack-destination",
            str(output_directory),
        ],
        cwd=snapshot,
        check=True,
        capture_output=True,
        text=True,
    )
    json_start = completed.stdout.find("[\n  {")
    assert json_start >= 0, completed.stdout
    packed, _ = json.JSONDecoder().raw_decode(completed.stdout[json_start:])
    assert isinstance(packed, list) and len(packed) == 1
    pack_result = tmp_path / "pack-result.json"
    pack_result.write_text(json.dumps(packed))
    tarball = output_directory / packed[0]["filename"]
    with tarfile.open(tarball, "r:gz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        expected = {
            "package/package.json",
            "package/bin/cli.js",
            "package/dist/agentharness.pyz",
            "package/runtime/python-build-standalone.lock.json",
            "package/.claude/skills/agentic-loops/agent_loop.py",
        }
        assert expected <= set(members)
        assert all(members[name].isfile() for name in expected)
        zipapp_member = archive.extractfile("package/dist/agentharness.pyz")
        assert zipapp_member is not None
        zipapp_bytes = zipapp_member.read()
    with zipfile.ZipFile(io.BytesIO(zipapp_bytes)) as zipapp:
        identity = json.loads(zipapp.read("agentharness-runtime-identity.json"))
    assert identity == {
        "bundled_plugins": {},
        "compatibility_provider_version": "0.1.0",
        "core_version": "0.1.0",
        "schema_version": 1,
    }
    registry_metadata = tmp_path / "registry.json"
    registry_metadata.write_text(
        json.dumps(
            {
                "name": packed[0]["name"],
                "version": packed[0]["version"],
                "dist": {
                    "integrity": packed[0]["integrity"],
                    "tarball": (
                        "https://registry.npmjs.org/agentharness-toolkit/-/"
                        f"agentharness-toolkit-{packed[0]['version']}.tgz"
                    ),
                },
            }
        )
    )
    consumer_lock = tmp_path / "runtime.lock.json"
    subprocess.run(
        [
            "python3",
            "tools/runtime/build-runtime-lock.py",
            "--pack-result",
            str(pack_result),
            "--registry-metadata",
            str(registry_metadata),
            "--tarball",
            str(tarball),
            "--allowed-mirror-url",
            "https://artifacts.example.test/npm/",
            "--selected-target",
            "x86_64-unknown-linux-gnu",
            "--runtime-mirror-host",
            "artifacts.example.test",
            "--output",
            str(consumer_lock),
        ],
        cwd=snapshot,
        check=True,
    )
    subprocess.run(
        [
            "python3",
            "tools/runtime/verify-runtime-lock.py",
            "--consumer-lock",
            str(consumer_lock),
            "--artifact-directory",
            str(cache),
        ],
        cwd=snapshot,
        check=True,
    )


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda builder: builder._mapping([], "input"), "object"),
        (lambda builder: builder._string("", "input"), "non-empty"),
        (lambda builder: builder._sri_digest("sha256-AQ==", "input"), "SHA-512"),
        (lambda builder: builder._sri_digest("sha512-!", "input"), "base64"),
    ],
)
def test_lock_builder_rejects_malformed_boundary_values(
    operation: Any, message: str
) -> None:
    builder = _load_lock_builder()
    with pytest.raises(RuntimeLockError, match=message):
        operation(builder)


@pytest.mark.parametrize("name", ["../escape", "/absolute"])
def test_lock_builder_rejects_unsafe_tar_paths(name: str) -> None:
    builder = _load_lock_builder()
    member = tarfile.TarInfo(name)
    with pytest.raises(RuntimeLockError, match="unsafe"):
        builder._safe_member(member)
