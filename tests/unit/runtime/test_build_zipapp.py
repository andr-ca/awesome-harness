from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
PY_YAML_FILES = (
    "__init__.py",
    "composer.py",
    "constructor.py",
    "cyaml.py",
    "dumper.py",
    "emitter.py",
    "error.py",
    "events.py",
    "loader.py",
    "nodes.py",
    "parser.py",
    "reader.py",
    "representer.py",
    "resolver.py",
    "scanner.py",
    "serializer.py",
    "tokens.py",
)
FASTJSONSCHEMA_FILES = (
    "__init__.py",
    "__main__.py",
    "draft04.py",
    "draft06.py",
    "draft07.py",
    "exceptions.py",
    "generator.py",
    "indent.py",
    "ref_resolver.py",
    "version.py",
)


def _load_builder() -> ModuleType:
    path = ROOT / "tools/runtime/build-zipapp.py"
    spec = importlib.util.spec_from_file_location("build_zipapp", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_source(root: Path) -> Path:
    source = root / "source"
    package = source / "agentharness"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (package / "__main__.py").write_text("raise SystemExit(0)\n")
    return source


def test_core_identity_reports_nonliteral_constant(tmp_path: Path) -> None:
    builder = _load_builder()
    source = _make_source(tmp_path)
    (source / "agentharness/__init__.py").write_text(
        "__version__ = calculate_version()\nRESULT_SCHEMA_VERSION = 1\n"
    )

    with pytest.raises(builder.ZipappBuildError, match="not literal"):
        builder._core_identity(source)


def _tar_member(
    name: str, payload: bytes, mode: int = 0o644
) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = mode
    info.mtime = 1_700_000_000
    return info, payload


def _make_pyyaml(
    path: Path,
    *,
    extra: tuple[str, int] | None = None,
    source_example: tuple[str, int] | None = None,
) -> None:
    with tarfile.open(path, "w:gz") as archive:
        members = [
            _tar_member("pyyaml-6.0.3/PKG-INFO", b"Name: PyYAML\nVersion: 6.0.3\n"),
            _tar_member("pyyaml-6.0.3/LICENSE", b"PyYAML license\n"),
        ]
        members.extend(
            _tar_member(f"pyyaml-6.0.3/lib/yaml/{name}", b"# yaml\n")
            for name in PY_YAML_FILES
        )
        if extra is not None:
            members.append(
                _tar_member(f"pyyaml-6.0.3/lib/yaml/{extra[0]}", b"x", extra[1])
            )
        if source_example is not None:
            members.append(
                _tar_member(
                    f"pyyaml-6.0.3/examples/{source_example[0]}",
                    b"x",
                    source_example[1],
                )
            )
        for info, payload in members:
            archive.addfile(info, io.BytesIO(payload))


def _make_fastjsonschema(path: Path, *, extra: tuple[str, int] | None = None) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in FASTJSONSCHEMA_FILES:
            info = zipfile.ZipInfo(f"fastjsonschema/{name}")
            info.external_attr = 0o644 << 16
            archive.writestr(info, "# fastjsonschema\n")
        metadata = zipfile.ZipInfo("fastjsonschema-2.21.2.dist-info/METADATA")
        metadata.external_attr = 0o644 << 16
        archive.writestr(metadata, "Name: fastjsonschema\nVersion: 2.21.2\n")
        wheel = zipfile.ZipInfo("fastjsonschema-2.21.2.dist-info/WHEEL")
        wheel.external_attr = 0o644 << 16
        archive.writestr(wheel, "Root-Is-Purelib: true\nTag: py3-none-any\n")
        for name in ("AUTHORS", "LICENSE"):
            license_info = zipfile.ZipInfo(
                f"fastjsonschema-2.21.2.dist-info/licenses/{name}"
            )
            license_info.external_attr = 0o644 << 16
            archive.writestr(license_info, f"fastjsonschema {name}\n")
        if extra is not None:
            info = zipfile.ZipInfo(f"fastjsonschema/{extra[0]}")
            info.external_attr = extra[1] << 16
            archive.writestr(info, "x")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_lock(path: Path, pyyaml: Path, fastjsonschema: Path) -> None:
    path.write_text(
        "--no-binary PyYAML\n"
        "--only-binary fastjsonschema\n\n"
        f"PyYAML==6.0.3 --hash=sha256:{_sha256(pyyaml)}\n"
        f"fastjsonschema==2.21.2 --hash=sha256:{_sha256(fastjsonschema)}\n"
    )


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    source = _make_source(tmp_path)
    pyyaml = tmp_path / "pyyaml-6.0.3.tar.gz"
    fastjsonschema = tmp_path / "fastjsonschema-2.21.2-py3-none-any.whl"
    lock = tmp_path / "requirements-runtime.lock"
    _make_pyyaml(pyyaml)
    _make_fastjsonschema(fastjsonschema)
    _make_lock(lock, pyyaml, fastjsonschema)
    return source, pyyaml, fastjsonschema, lock


def test_requirements_lock_requires_hash_pinned_source_and_universal_wheel(
    tmp_path: Path,
) -> None:
    builder = _load_builder()
    _, pyyaml, fastjsonschema, lock = _inputs(tmp_path)

    requirements = builder.load_requirements(lock)

    assert (
        requirements.pyyaml.version,
        requirements.pyyaml.sha256,
        requirements.fastjsonschema.version,
        requirements.fastjsonschema.sha256,
        pyyaml.name,
        fastjsonschema.name,
    ) == (
        "6.0.3",
        _sha256(pyyaml),
        "2.21.2",
        _sha256(fastjsonschema),
        "pyyaml-6.0.3.tar.gz",
        "fastjsonschema-2.21.2-py3-none-any.whl",
    )


def test_zipapps_are_byte_identical_across_temporary_directories(
    tmp_path: Path,
) -> None:
    builder = _load_builder()
    first = tmp_path / "one"
    second = tmp_path / "different-parent" / "two"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    first_inputs = _inputs(first)
    second_inputs = _inputs(second)
    first_output = first / "agentharness.pyz"
    second_output = second / "agentharness.pyz"

    builder.build_zipapp(first_output, *first_inputs)
    builder.build_zipapp(second_output, *second_inputs)

    assert first_output.read_bytes() == second_output.read_bytes()


def test_zipapp_contains_dependency_licenses_and_identity(tmp_path: Path) -> None:
    builder = _load_builder()
    inputs = _inputs(tmp_path)
    output = tmp_path / "agentharness.pyz"

    builder.build_zipapp(output, *inputs)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        identity = json.loads(archive.read("agentharness-runtime-identity.json"))
        entrypoint = archive.read("__main__.py")
    assert (
        {
            "licenses/PyYAML-LICENSE",
            "licenses/fastjsonschema-LICENSE",
            "licenses/fastjsonschema-AUTHORS",
        }.issubset(names),
        identity,
        entrypoint,
    ) == (
        True,
        {
            "bundled_plugins": {},
            "compatibility_provider_version": "0.1.0",
            "core_version": "0.1.0",
            "schema_version": 1,
        },
        b"from agentharness.cli import main\nraise SystemExit(main())\n",
    )


@pytest.mark.parametrize("extension", ["module.so", "module.dylib", "module.dll"])
def test_builder_rejects_native_dependency_payloads(
    tmp_path: Path, extension: str
) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    _make_fastjsonschema(fastjsonschema, extra=(extension, 0o644))
    _make_lock(lock, pyyaml, fastjsonschema)

    with pytest.raises(builder.ZipappBuildError, match="native"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )


def test_builder_rejects_executable_dependency_payload(tmp_path: Path) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    _make_fastjsonschema(fastjsonschema, extra=("payload.py", 0o755))
    _make_lock(lock, pyyaml, fastjsonschema)

    with pytest.raises(builder.ZipappBuildError, match="executable"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )


def test_builder_rejects_unexpected_dependency_inventory(tmp_path: Path) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    _make_pyyaml(pyyaml, extra=("surprise.py", 0o644))
    _make_lock(lock, pyyaml, fastjsonschema)

    with pytest.raises(builder.ZipappBuildError, match="inventory"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )


def test_builder_rejects_duplicate_selected_pyyaml_member(tmp_path: Path) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    with tarfile.open(pyyaml, "w:gz") as archive:
        members = [
            _tar_member("pyyaml-6.0.3/PKG-INFO", b"Name: PyYAML\nVersion: 6.0.3\n"),
            _tar_member("pyyaml-6.0.3/LICENSE", b"license"),
        ]
        members.extend(
            _tar_member(f"pyyaml-6.0.3/lib/yaml/{name}", b"x") for name in PY_YAML_FILES
        )
        members.append(_tar_member("pyyaml-6.0.3/lib/yaml/__init__.py", b"again"))
        for info, payload in members:
            archive.addfile(info, io.BytesIO(payload))
    _make_lock(lock, pyyaml, fastjsonschema)
    with pytest.raises(builder.ZipappBuildError, match="duplicate"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )


def test_builder_enforces_dependency_member_and_path_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    monkeypatch.setattr(builder, "MAX_MEMBERS", 1)
    with pytest.raises(builder.ZipappBuildError, match="member-count"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )
    monkeypatch.setattr(builder, "MAX_PATH_BYTES", 4)
    with pytest.raises(builder.ZipappBuildError, match="unsafe"):
        builder._safe_archive_path("too-long")


def test_builder_enforces_dependency_member_size_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    monkeypatch.setattr(builder, "MAX_MEMBER_BYTES", 1)
    with pytest.raises(builder.ZipappBuildError, match="member.*size"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )


def test_builder_rejects_artifact_hash_mismatch(tmp_path: Path) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    pyyaml.write_bytes(pyyaml.read_bytes() + b"tampered")

    with pytest.raises(builder.ZipappBuildError, match="SHA-256"):
        builder.build_zipapp(
            tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
        )


def test_requirements_lock_rejects_wrong_package_version(tmp_path: Path) -> None:
    builder = _load_builder()
    _, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    lock.write_text(lock.read_text().replace("PyYAML==6.0.3", "PyYAML==6.0.2"))

    with pytest.raises(builder.ZipappBuildError, match="PyYAML==6.0.3"):
        builder.load_requirements(lock)


@pytest.mark.parametrize(
    "extra",
    [
        "PyYAML==6.0.3 --hash=sha256:" + "0" * 64,
        "fastjsonschema==2.21.2 --hash=sha256:" + "0" * 64,
        "requests==2.0.0 --hash=sha256:" + "0" * 64,
        "malformed requirement",
    ],
)
def test_requirements_lock_rejects_duplicate_or_extra_entries(
    tmp_path: Path, extra: str
) -> None:
    builder = _load_builder()
    _, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    lock.write_text(lock.read_text() + extra + "\n")
    with pytest.raises(builder.ZipappBuildError, match="exactly|unexpected|duplicate"):
        builder.load_requirements(lock)


def test_builder_ignores_interpreter_cache_files(tmp_path: Path) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    cache = source / "agentharness/__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-312.pyc").write_bytes(b"cache")

    builder.build_zipapp(
        tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
    )


def test_builder_ignores_executable_sdist_examples_not_in_payload(
    tmp_path: Path,
) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    _make_pyyaml(pyyaml, source_example=("tool.py", 0o755))
    _make_lock(lock, pyyaml, fastjsonschema)

    builder.build_zipapp(
        tmp_path / "agentharness.pyz", source, pyyaml, fastjsonschema, lock
    )


def test_builder_main_uses_explicit_verified_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    output = tmp_path / "dist/agentharness.pyz"
    monkeypatch.setattr(
        builder,
        "_arguments",
        lambda: argparse.Namespace(
            output=output,
            source_root=source,
            requirements_lock=lock,
            cache_dir=tmp_path,
            pyyaml_sdist=pyyaml,
            fastjsonschema_wheel=fastjsonschema,
            check_reproducible=False,
        ),
    )

    assert (builder.main(), output.is_file()) == (0, True)


def test_builder_main_reports_missing_cached_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    builder = _load_builder()
    monkeypatch.setattr(
        builder,
        "_arguments",
        lambda: argparse.Namespace(
            output=tmp_path / "agentharness.pyz",
            source_root=tmp_path,
            requirements_lock=tmp_path / "requirements-runtime.lock",
            cache_dir=tmp_path,
            pyyaml_sdist=None,
            fastjsonschema_wheel=None,
            check_reproducible=False,
        ),
    )

    result = builder.main()
    error = capsys.readouterr().err
    assert (result, "expected exactly one" in error, "seed" in error) == (
        1,
        True,
        True,
    )


def test_builder_main_checks_two_independent_builds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _load_builder()
    source, pyyaml, fastjsonschema, lock = _inputs(tmp_path)
    output = tmp_path / "dist/agentharness.pyz"
    monkeypatch.setattr(
        builder,
        "_arguments",
        lambda: argparse.Namespace(
            output=output,
            source_root=source,
            requirements_lock=lock,
            cache_dir=tmp_path,
            pyyaml_sdist=pyyaml,
            fastjsonschema_wheel=fastjsonschema,
            check_reproducible=True,
        ),
    )
    assert builder.main() == 0
