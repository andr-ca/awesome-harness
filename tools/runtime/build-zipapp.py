#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

PY_YAML_VERSION = "6.0.3"
FASTJSONSCHEMA_VERSION = "2.21.2"
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
NATIVE_SUFFIXES = (".so", ".dylib", ".dll", ".pyd")
NORMALIZED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIPAPP_PATH = "dist/agentharness.pyz"
MAX_COMPRESSED_BYTES = 268_435_456
MAX_EXPANDED_BYTES = 1_073_741_824
MAX_MEMBER_BYTES = 268_435_456
MAX_MEMBERS = 100_000
MAX_PATH_BYTES = 4_096
MAX_REQUIREMENTS_BYTES = 1_048_576


class ZipappBuildError(ValueError):
    """Raised when an input cannot produce the reviewed runtime payload."""


@dataclass(frozen=True, slots=True)
class LockedRequirement:
    name: str
    version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeRequirements:
    pyyaml: LockedRequirement
    fastjsonschema: LockedRequirement


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_requirements(path: Path) -> RuntimeRequirements:
    try:
        with path.open("rb") as source:
            payload = source.read(MAX_REQUIREMENTS_BYTES + 1)
        if len(payload) > MAX_REQUIREMENTS_BYTES:
            raise ZipappBuildError("runtime requirements exceed size limit")
        content = payload.decode("utf-8").replace("\\\n", " ")
    except (OSError, UnicodeError) as error:
        raise ZipappBuildError(f"cannot read runtime requirements: {error}") from error
    if "--no-binary PyYAML" not in content:
        raise ZipappBuildError("runtime lock must require the PyYAML source artifact")
    if "--only-binary fastjsonschema" not in content:
        raise ZipappBuildError(
            "runtime lock must require the fastjsonschema universal wheel"
        )
    pattern = re.compile(
        r"^(PyYAML|fastjsonschema)==([^\s]+)\s+--hash=sha256:([0-9a-f]{64})$",
        re.IGNORECASE,
    )
    declarations: list[LockedRequirement] = []
    allowed_directives = {"--no-binary PyYAML", "--only-binary fastjsonschema"}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line in allowed_directives:
            continue
        match = pattern.fullmatch(line)
        if match is None:
            raise ZipappBuildError("unexpected runtime requirement declaration")
        declarations.append(LockedRequirement(*match.groups()))
    if len(declarations) != 2:
        raise ZipappBuildError("runtime lock must contain exactly two requirements")
    found: dict[str, LockedRequirement] = {}
    for declaration in declarations:
        key = declaration.name.lower()
        if key in found:
            raise ZipappBuildError(f"duplicate runtime requirement: {declaration.name}")
        found[key] = declaration
    if set(found) != {"pyyaml", "fastjsonschema"}:
        raise ZipappBuildError(
            "runtime lock must contain exactly PyYAML and fastjsonschema"
        )
    pyyaml = found["pyyaml"]
    fastjsonschema = found["fastjsonschema"]
    if pyyaml.version != PY_YAML_VERSION:
        raise ZipappBuildError(f"runtime lock must pin PyYAML=={PY_YAML_VERSION}")
    if fastjsonschema.version != FASTJSONSCHEMA_VERSION:
        raise ZipappBuildError(
            f"runtime lock must pin fastjsonschema=={FASTJSONSCHEMA_VERSION}"
        )
    return RuntimeRequirements(pyyaml=pyyaml, fastjsonschema=fastjsonschema)


def _verify_artifact(path: Path, requirement: LockedRequirement) -> bytes:
    if not path.is_file():
        raise ZipappBuildError(f"missing {requirement.name} artifact: {path}")
    if path.stat().st_size > MAX_COMPRESSED_BYTES:
        raise ZipappBuildError(f"{requirement.name} artifact exceeds size limit")
    with path.open("rb") as source:
        payload = source.read(MAX_COMPRESSED_BYTES + 1)
    if len(payload) > MAX_COMPRESSED_BYTES:
        raise ZipappBuildError(f"{requirement.name} artifact exceeds size limit")
    if hashlib.sha256(payload).hexdigest() != requirement.sha256:
        raise ZipappBuildError(f"{requirement.name} artifact SHA-256 mismatch")
    return payload


def _safe_archive_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\x00" in name
        or len(name.encode("utf-8")) > MAX_PATH_BYTES
    ):
        raise ZipappBuildError(f"unsafe dependency archive path: {name!r}")
    return path


def _reject_payload(path: PurePosixPath, mode: int) -> None:
    if path.name.lower().endswith(NATIVE_SUFFIXES):
        raise ZipappBuildError(f"native dependency payload is forbidden: {path}")
    if stat.S_IMODE(mode) & 0o111:
        raise ZipappBuildError(f"executable dependency payload is forbidden: {path}")


def _read_pyyaml(path: bytes) -> tuple[dict[str, bytes], dict[str, bytes]]:
    package: dict[str, bytes] = {}
    licenses: dict[str, bytes] = {}
    version: str | None = None
    selected_members: set[str] = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(path), mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) > MAX_MEMBERS:
                raise ZipappBuildError("PyYAML source exceeds member-count limit")
            expanded = 0
            for member in members:
                member_path = _safe_archive_path(member.name)
                if member.size > MAX_MEMBER_BYTES:
                    raise ZipappBuildError("PyYAML member exceeds size limit")
                expanded += member.size
                if expanded > MAX_EXPANDED_BYTES:
                    raise ZipappBuildError("PyYAML source exceeds expanded-size limit")
                if (
                    member.issym()
                    or member.islnk()
                    or member.isdev()
                    or member.isfifo()
                ):
                    raise ZipappBuildError(
                        "PyYAML source contains an unsupported member"
                    )
                if not member.isfile():
                    continue
                source = archive.extractfile(member)
                if source is None:
                    raise ZipappBuildError(f"cannot read PyYAML member: {member.name}")
                payload = source.read()
                if member_path.name == "PKG-INFO":
                    version = _metadata_version(payload, "PyYAML")
                if member_path.name == "LICENSE" and len(member_path.parts) == 2:
                    if "licenses/PyYAML-LICENSE" in selected_members:
                        raise ZipappBuildError("duplicate selected PyYAML member")
                    selected_members.add("licenses/PyYAML-LICENSE")
                    _reject_payload(member_path, member.mode)
                    licenses["licenses/PyYAML-LICENSE"] = payload
                marker = ("lib", "yaml")
                if marker[0] in member_path.parts:
                    index = member_path.parts.index(marker[0])
                    if member_path.parts[index : index + 2] == marker:
                        relative = member_path.parts[index + 2 :]
                        if relative:
                            destination = "yaml/" + "/".join(relative)
                            if destination in selected_members:
                                raise ZipappBuildError(
                                    "duplicate selected PyYAML member"
                                )
                            selected_members.add(destination)
                            _reject_payload(member_path, member.mode)
                            package[destination] = payload
    except (OSError, tarfile.TarError) as error:
        raise ZipappBuildError(
            f"cannot inspect PyYAML source artifact: {error}"
        ) from error
    if version != PY_YAML_VERSION:
        raise ZipappBuildError(f"PyYAML package version must be {PY_YAML_VERSION}")
    expected = {f"yaml/{name}" for name in PY_YAML_FILES}
    if set(package) != expected:
        raise ZipappBuildError(
            "PyYAML pure-Python package inventory differs from review"
        )
    if set(licenses) != {"licenses/PyYAML-LICENSE"}:
        raise ZipappBuildError("PyYAML license is missing")
    return package, licenses


def _metadata_version(payload: bytes, expected_name: str) -> str | None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ZipappBuildError(f"{expected_name} metadata is not UTF-8") from error
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields.setdefault(key, value)
    if fields.get("Name", "").lower() != expected_name.lower():
        raise ZipappBuildError(f"unexpected package metadata for {expected_name}")
    return fields.get("Version")


def _read_fastjsonschema(
    path: bytes, filename: str
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    if not filename.lower().endswith("-py3-none-any.whl"):
        raise ZipappBuildError("fastjsonschema input must be a py3-none-any wheel")
    package: dict[str, bytes] = {}
    licenses: dict[str, bytes] = {}
    version: str | None = None
    pure = False
    try:
        with zipfile.ZipFile(io.BytesIO(path)) as archive:
            seen: set[str] = set()
            members = archive.infolist()
            if len(members) > MAX_MEMBERS:
                raise ZipappBuildError(
                    "fastjsonschema wheel exceeds member-count limit"
                )
            expanded = 0
            for info in members:
                member_path = _safe_archive_path(info.filename)
                if info.filename in seen:
                    raise ZipappBuildError("fastjsonschema wheel has duplicate members")
                seen.add(info.filename)
                if info.file_size > MAX_MEMBER_BYTES:
                    raise ZipappBuildError("fastjsonschema member exceeds size limit")
                expanded += info.file_size
                if expanded > MAX_EXPANDED_BYTES:
                    raise ZipappBuildError(
                        "fastjsonschema wheel exceeds expanded-size limit"
                    )
                if info.is_dir():
                    continue
                mode = (info.external_attr >> 16) & 0xFFFF
                _reject_payload(member_path, mode)
                payload = archive.read(info)
                if (
                    len(member_path.parts) == 2
                    and member_path.parts[0] == "fastjsonschema"
                ):
                    package[info.filename] = payload
                if (
                    member_path.name == "METADATA"
                    and ".dist-info" in member_path.parts[0]
                ):
                    version = _metadata_version(payload, "fastjsonschema")
                if member_path.name == "WHEEL" and ".dist-info" in member_path.parts[0]:
                    text = payload.decode("utf-8")
                    pure = (
                        "Root-Is-Purelib: true" in text and "Tag: py3-none-any" in text
                    )
                if "licenses" in member_path.parts and member_path.name in {
                    "LICENSE",
                    "AUTHORS",
                }:
                    licenses[f"licenses/fastjsonschema-{member_path.name}"] = payload
    except (OSError, UnicodeError, zipfile.BadZipFile) as error:
        raise ZipappBuildError(
            f"cannot inspect fastjsonschema wheel: {error}"
        ) from error
    if version != FASTJSONSCHEMA_VERSION or not pure:
        raise ZipappBuildError(
            "fastjsonschema package version or wheel tag is unexpected"
        )
    expected = {f"fastjsonschema/{name}" for name in FASTJSONSCHEMA_FILES}
    if set(package) != expected:
        raise ZipappBuildError("fastjsonschema package inventory differs from review")
    expected_licenses = {
        "licenses/fastjsonschema-AUTHORS",
        "licenses/fastjsonschema-LICENSE",
    }
    if set(licenses) != expected_licenses:
        raise ZipappBuildError("fastjsonschema licenses are missing")
    return package, licenses


def _source_payload(source_root: Path) -> dict[str, bytes]:
    package_root = source_root / "agentharness"
    if not package_root.is_dir():
        raise ZipappBuildError(f"application package is missing: {package_root}")
    payload: dict[str, bytes] = {}
    for path in sorted(package_root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise ZipappBuildError(
                f"application source cannot contain symlinks: {path}"
            )
        if path.is_file():
            relative = path.relative_to(source_root).as_posix()
            if path.suffix not in {".py", ".json"}:
                raise ZipappBuildError(
                    f"unexpected application source file: {relative}"
                )
            payload[relative] = path.read_bytes()
    if "agentharness/__main__.py" not in payload:
        raise ZipappBuildError("application package is missing __main__.py")
    return payload


def _core_identity(source_root: Path) -> Mapping[str, object]:
    init_path = source_root / "agentharness/__init__.py"
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise ZipappBuildError(f"cannot read core identity: {error}") from error
    values: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            if node.targets[0].id in {"__version__", "RESULT_SCHEMA_VERSION"}:
                try:
                    values[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError) as error:
                    raise ZipappBuildError(
                        "core identity constant is not literal"
                    ) from error
    core_version = values.get("__version__")
    schema_version = values.get("RESULT_SCHEMA_VERSION", 1)
    if not isinstance(core_version, str) or not isinstance(schema_version, int):
        raise ZipappBuildError("core identity constants are missing or invalid")
    return {
        "bundled_plugins": {},
        "compatibility_provider_version": core_version,
        "core_version": core_version,
        "schema_version": schema_version,
    }


def _write_archive(output: Path, payload: Mapping[str, bytes]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(b"#!/usr/bin/env python3\n")
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name in sorted(payload):
                info = zipfile.ZipInfo(name, NORMALIZED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, payload[name])
    os.chmod(temporary_path, 0o755)
    os.replace(temporary_path, output)


def build_zipapp(
    output: Path,
    source_root: Path,
    pyyaml_sdist: Path,
    fastjsonschema_wheel: Path,
    requirements_lock: Path,
) -> str:
    requirements = load_requirements(requirements_lock)
    pyyaml_bytes = _verify_artifact(pyyaml_sdist, requirements.pyyaml)
    fastjsonschema_bytes = _verify_artifact(
        fastjsonschema_wheel, requirements.fastjsonschema
    )
    payload = _source_payload(source_root)
    pyyaml_payload, pyyaml_licenses = _read_pyyaml(pyyaml_bytes)
    fast_payload, fast_licenses = _read_fastjsonschema(
        fastjsonschema_bytes, fastjsonschema_wheel.name
    )
    for collection in (pyyaml_payload, pyyaml_licenses, fast_payload, fast_licenses):
        overlap = set(payload) & set(collection)
        if overlap:
            raise ZipappBuildError(f"duplicate zipapp path: {sorted(overlap)[0]}")
        payload.update(collection)
    payload["__main__.py"] = (
        b"from agentharness.cli import main\nraise SystemExit(main())\n"
    )
    payload["agentharness-runtime-identity.json"] = (
        json.dumps(_core_identity(source_root), sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    _write_archive(output, payload)
    digest = _sha512(output)
    output.with_name(output.name + ".sha512").write_text(
        f"{digest}  {output.name}\n", encoding="ascii"
    )
    return digest


def _find_artifact(cache: Path, patterns: Iterable[str], label: str) -> Path:
    matches = sorted(path for pattern in patterns for path in cache.glob(pattern))
    if len(matches) != 1:
        raise ZipappBuildError(
            f"expected exactly one cached {label} artifact in {cache}; "
            f"found {len(matches)}; seed the hash-pinned artifact in that cache "
            "or pass its explicit artifact option"
        )
    return matches[0]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the reproducible agentharness zipapp"
    )
    parser.add_argument("--output", type=Path, default=ROOT / ZIPAPP_PATH)
    parser.add_argument("--source-root", type=Path, default=ROOT / "src")
    parser.add_argument(
        "--requirements-lock", type=Path, default=ROOT / "requirements-runtime.lock"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=ROOT / ".tool-cache/runtime-artifacts"
    )
    parser.add_argument("--pyyaml-sdist", type=Path)
    parser.add_argument("--fastjsonschema-wheel", type=Path)
    parser.add_argument("--check-reproducible", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        pyyaml = args.pyyaml_sdist or _find_artifact(
            args.cache_dir, ("pyyaml-6.0.3.tar.gz", "PyYAML-6.0.3.tar.gz"), "PyYAML"
        )
        fastjsonschema = args.fastjsonschema_wheel or _find_artifact(
            args.cache_dir,
            ("fastjsonschema-2.21.2-py3-none-any.whl",),
            "fastjsonschema",
        )
        if args.check_reproducible:
            with (
                tempfile.TemporaryDirectory() as first,
                tempfile.TemporaryDirectory() as second,
            ):
                first_output = Path(first) / "agentharness.pyz"
                second_output = Path(second) / "agentharness.pyz"
                first_digest = build_zipapp(
                    first_output,
                    args.source_root,
                    pyyaml,
                    fastjsonschema,
                    args.requirements_lock,
                )
                second_digest = build_zipapp(
                    second_output,
                    args.source_root,
                    pyyaml,
                    fastjsonschema,
                    args.requirements_lock,
                )
                if (
                    first_digest != second_digest
                    or first_output.read_bytes() != second_output.read_bytes()
                ):
                    raise ZipappBuildError("zipapp builds are not byte-identical")
        digest = build_zipapp(
            args.output,
            args.source_root,
            pyyaml,
            fastjsonschema,
            args.requirements_lock,
        )
    except ZipappBuildError as error:
        print(f"runtime zipapp build failed: {error}", file=sys.stderr)
        return 1
    print(f"built {args.output} sha512:{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
