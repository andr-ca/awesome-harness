from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlparse

SUPPORTED_RUNTIME_TARGETS = (
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
)
EXPECTED_RELEASE = "20260510"
EXPECTED_PYTHON_VERSION = "3.12.13"
EXPECTED_ARTIFACT_FLAVOR = "install_only_stripped.tar.gz"
MAX_JSON_BYTES = 1_048_576
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHA512_PATTERN = re.compile(r"^[0-9a-f]{128}$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
MIRROR_HOST_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
EXPECTED_LIMITS = MappingProxyType(
    {
        "max_compressed_bytes": 268_435_456,
        "max_expanded_bytes": 1_073_741_824,
        "max_member_bytes": 268_435_456,
        "max_members": 100_000,
        "max_redirects": 3,
        "max_path_bytes": 4_096,
    }
)


class RuntimeLockError(ValueError):
    """Raised when runtime trust material is malformed or inconsistent."""


@dataclass(frozen=True, slots=True)
class RuntimeArtifact:
    target: str
    url: str
    sha256: str
    sha512: str
    archive_prefix: str
    interpreter_path: str


@dataclass(frozen=True, slots=True)
class RuntimeManifest:
    schema_version: int
    python_version: str
    release: str
    artifact_flavor: str
    runtimes: tuple[RuntimeArtifact, ...]


@dataclass(frozen=True, slots=True)
class PackageIdentity:
    name: str
    version: str
    registry_url: str
    tarball_url: str
    registry_sri: str
    sha512: str
    allowed_mirror_url: str


@dataclass(frozen=True, slots=True)
class ZipappIdentity:
    path: str
    sha512: str
    core_version: str
    schema_version: int
    bundled_plugins: Mapping[str, str]
    compatibility_provider_version: str


@dataclass(frozen=True, slots=True)
class MirrorPolicy:
    require_https: bool
    require_matching_digest: bool
    allowed_runtime_mirror_hosts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    max_compressed_bytes: int
    max_expanded_bytes: int
    max_member_bytes: int
    max_members: int
    max_redirects: int
    max_path_bytes: int


@dataclass(frozen=True, slots=True)
class AcquisitionPolicy:
    selected_target: str
    selected_source: str
    mirror_policy: MirrorPolicy
    limits: ArchiveLimits
    bootstrap_protocol_version: int


@dataclass(frozen=True, slots=True)
class ConsumerRuntimeLock:
    schema_version: int
    package: PackageIdentity
    zipapp: ZipappIdentity
    runtimes: tuple[RuntimeArtifact, ...]
    acquisition: AcquisitionPolicy


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeLockError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_document(path: Path) -> Mapping[str, object]:
    try:
        with path.open("rb") as source:
            payload = source.read(MAX_JSON_BYTES + 1)
        if len(payload) > MAX_JSON_BYTES:
            raise RuntimeLockError("runtime lock exceeds the JSON size limit")
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeLockError(f"cannot read runtime lock {path}: {error}") from error
    return _object_value(value, "document")


def _object_value(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise RuntimeLockError(f"{field} must be an object")
    return value


def _closed_object(
    value: object, field: str, expected: Sequence[str]
) -> Mapping[str, object]:
    document = _object_value(value, field)
    missing = set(expected) - set(document)
    unknown = set(document) - set(expected)
    if missing:
        raise RuntimeLockError(f"{field} missing required field: {sorted(missing)[0]}")
    if unknown:
        raise RuntimeLockError(f"{field} has unknown field: {sorted(unknown)[0]}")
    return document


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeLockError(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeLockError(f"{field} must be an integer")
    return value


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise RuntimeLockError(f"{field} must be a boolean")
    return value


def _https_url(value: object, field: str) -> str:
    url = _string(value, field)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None:
        raise RuntimeLockError(f"{field} must use HTTPS without credentials")
    return url


def _digest(value: object, field: str, pattern: re.Pattern[str]) -> str:
    digest = _string(value, field)
    if pattern.fullmatch(digest) is None:
        raise RuntimeLockError(f"{field} is not a lowercase hexadecimal digest")
    return digest


def _version(value: object, field: str) -> str:
    version = _string(value, field)
    if VERSION_PATTERN.fullmatch(version) is None:
        raise RuntimeLockError(f"{field} is not an exact semantic version")
    return version


def _runtime(value: object, *, require_immutable_url: bool) -> RuntimeArtifact:
    fields = ("target", "url", "sha256", "sha512", "archive_prefix", "interpreter_path")
    item = _closed_object(value, "runtime", fields)
    target = _string(item["target"], "runtime.target")
    if target not in SUPPORTED_RUNTIME_TARGETS:
        raise RuntimeLockError(f"runtime target is not supported: {target}")
    url = _https_url(item["url"], "runtime.url")
    immutable_prefix = (
        "https://github.com/astral-sh/python-build-standalone/"
        f"releases/download/{EXPECTED_RELEASE}/"
    )
    if require_immutable_url and not url.startswith(immutable_prefix):
        raise RuntimeLockError("runtime.url must be an immutable release URL")
    expected_filename = (
        f"cpython-{EXPECTED_PYTHON_VERSION}+{EXPECTED_RELEASE}-{target}-"
        f"{EXPECTED_ARTIFACT_FLAVOR}"
    )
    if require_immutable_url and url != immutable_prefix + expected_filename.replace(
        "+", "%2B"
    ):
        raise RuntimeLockError("runtime URL filename does not match its target")
    archive_prefix = _string(item["archive_prefix"], "runtime.archive_prefix")
    interpreter_path = _string(item["interpreter_path"], "runtime.interpreter_path")
    if archive_prefix != "python/":
        raise RuntimeLockError("runtime.archive_prefix must be python/")
    if interpreter_path != "python/bin/python3":
        raise RuntimeLockError("runtime.interpreter_path must be python/bin/python3")
    return RuntimeArtifact(
        target=target,
        url=url,
        sha256=_digest(item["sha256"], "runtime.sha256", SHA256_PATTERN),
        sha512=_digest(item["sha512"], "runtime.sha512", SHA512_PATTERN),
        archive_prefix=archive_prefix,
        interpreter_path=interpreter_path,
    )


def _runtime_list(
    value: object, *, require_immutable_url: bool
) -> tuple[RuntimeArtifact, ...]:
    if not isinstance(value, list):
        raise RuntimeLockError("runtimes must be an array")
    runtimes = tuple(
        _runtime(item, require_immutable_url=require_immutable_url) for item in value
    )
    targets = tuple(runtime.target for runtime in runtimes)
    if len(set(targets)) != len(targets):
        raise RuntimeLockError("duplicate runtime target")
    if set(targets) != set(SUPPORTED_RUNTIME_TARGETS) or len(targets) != 4:
        raise RuntimeLockError(
            "runtimes must contain exactly the four supported targets"
        )
    return runtimes


def load_runtime_manifest(path: Path) -> RuntimeManifest:
    document = _closed_object(
        load_json_document(path),
        "runtime manifest",
        ("schema_version", "python_version", "release", "artifact_flavor", "runtimes"),
    )
    schema_version = _integer(document["schema_version"], "schema_version")
    python_version = _string(document["python_version"], "python_version")
    release = _string(document["release"], "release")
    flavor = _string(document["artifact_flavor"], "artifact_flavor")
    if (schema_version, python_version, release, flavor) != (
        1,
        EXPECTED_PYTHON_VERSION,
        EXPECTED_RELEASE,
        EXPECTED_ARTIFACT_FLAVOR,
    ):
        raise RuntimeLockError("runtime manifest release identity is not supported")
    return RuntimeManifest(
        schema_version=schema_version,
        python_version=python_version,
        release=release,
        artifact_flavor=flavor,
        runtimes=_runtime_list(document["runtimes"], require_immutable_url=True),
    )


def _package(value: object) -> PackageIdentity:
    fields = (
        "name",
        "version",
        "registry_url",
        "tarball_url",
        "registry_sri",
        "sha512",
        "allowed_mirror_url",
    )
    item = _closed_object(value, "package", fields)
    name = _string(item["name"], "package.name")
    if name != "agentharness-toolkit":
        raise RuntimeLockError("package.name must be agentharness-toolkit")
    sri = _string(item["registry_sri"], "package.registry_sri")
    if not sri.startswith("sha512-"):
        raise RuntimeLockError("package.registry_sri must use SHA-512")
    try:
        sri_bytes = base64.b64decode(sri[7:], validate=True)
        if len(sri_bytes) != 64:
            raise RuntimeLockError("package.registry_sri must contain a SHA-512 digest")
    except binascii.Error as error:
        raise RuntimeLockError("package.registry_sri is not valid base64") from error
    version = _version(item["version"], "package.version")
    sha512 = _digest(item["sha512"], "package.sha512", SHA512_PATTERN)
    if sri_bytes.hex() != sha512:
        raise RuntimeLockError("package.registry_sri and package.sha512 disagree")
    registry_url = _https_url(item["registry_url"], "package.registry_url")
    if registry_url != "https://registry.npmjs.org":
        raise RuntimeLockError(
            "package.registry_url must be the canonical npm registry"
        )
    tarball_url = _https_url(item["tarball_url"], "package.tarball_url")
    expected_tarball = f"{registry_url}/{name}/-/{name}-{version}.tgz"
    if tarball_url != expected_tarball:
        raise RuntimeLockError("package.tarball_url is not canonical for name/version")
    return PackageIdentity(
        name=name,
        version=version,
        registry_url=registry_url,
        tarball_url=tarball_url,
        registry_sri=sri,
        sha512=sha512,
        allowed_mirror_url=_https_url(
            item["allowed_mirror_url"], "package.allowed_mirror_url"
        ),
    )


def _zipapp(value: object) -> ZipappIdentity:
    fields = (
        "path",
        "sha512",
        "core_version",
        "schema_version",
        "bundled_plugins",
        "compatibility_provider_version",
    )
    item = _closed_object(value, "zipapp", fields)
    path = _string(item["path"], "zipapp.path")
    if path != "package/dist/agentharness.pyz":
        raise RuntimeLockError("zipapp.path must be package/dist/agentharness.pyz")
    plugins = _object_value(item["bundled_plugins"], "zipapp.bundled_plugins")
    normalized_plugins = {
        key: _version(version, f"zipapp.bundled_plugins.{key}")
        for key, version in plugins.items()
    }
    schema_version = _integer(item["schema_version"], "zipapp.schema_version")
    if schema_version != 1:
        raise RuntimeLockError("zipapp.schema_version must be 1")
    return ZipappIdentity(
        path=path,
        sha512=_digest(item["sha512"], "zipapp.sha512", SHA512_PATTERN),
        core_version=_version(item["core_version"], "zipapp.core_version"),
        schema_version=schema_version,
        bundled_plugins=MappingProxyType(normalized_plugins),
        compatibility_provider_version=_version(
            item["compatibility_provider_version"],
            "zipapp.compatibility_provider_version",
        ),
    )


def _acquisition(value: object) -> AcquisitionPolicy:
    item = _closed_object(
        value,
        "acquisition",
        (
            "selected_target",
            "selected_source",
            "mirror_policy",
            "limits",
            "bootstrap_protocol_version",
        ),
    )
    selected_target = _string(item["selected_target"], "acquisition.selected_target")
    if selected_target not in SUPPORTED_RUNTIME_TARGETS:
        raise RuntimeLockError("acquisition.selected_target is not supported")
    selected_source = _string(item["selected_source"], "acquisition.selected_source")
    if selected_source not in ("upstream", "mirror"):
        raise RuntimeLockError("acquisition.selected_source must be upstream or mirror")
    mirror = _closed_object(
        item["mirror_policy"],
        "acquisition.mirror_policy",
        ("require_https", "require_matching_digest", "allowed_runtime_mirror_hosts"),
    )
    hosts = mirror["allowed_runtime_mirror_hosts"]
    if not isinstance(hosts, list) or not all(
        isinstance(host, str) and host for host in hosts
    ):
        raise RuntimeLockError("allowed_runtime_mirror_hosts must be an array of hosts")
    if len(hosts) != len(set(hosts)):
        raise RuntimeLockError("allowed_runtime_mirror_hosts contains a duplicate")
    if any(MIRROR_HOST_PATTERN.fullmatch(host) is None for host in hosts):
        raise RuntimeLockError(
            "allowed_runtime_mirror_hosts must contain DNS hostnames"
        )
    require_https = _boolean(mirror["require_https"], "require_https")
    require_digest = _boolean(
        mirror["require_matching_digest"], "require_matching_digest"
    )
    if not require_https or not require_digest:
        raise RuntimeLockError(
            "mirror policy cannot weaken HTTPS or digest verification"
        )
    limits_document = _closed_object(
        item["limits"], "acquisition.limits", tuple(EXPECTED_LIMITS)
    )
    parsed_limits = {
        key: _integer(limits_document[key], f"acquisition.limits.{key}")
        for key in EXPECTED_LIMITS
    }
    for key, expected in EXPECTED_LIMITS.items():
        if parsed_limits[key] != expected:
            raise RuntimeLockError(f"acquisition.limits.{key} must be {expected}")
    protocol = _integer(
        item["bootstrap_protocol_version"], "bootstrap_protocol_version"
    )
    if protocol != 1:
        raise RuntimeLockError("bootstrap_protocol_version must be 1")
    return AcquisitionPolicy(
        selected_target=selected_target,
        selected_source=selected_source,
        mirror_policy=MirrorPolicy(require_https, require_digest, tuple(hosts)),
        limits=ArchiveLimits(**parsed_limits),
        bootstrap_protocol_version=protocol,
    )


def validate_consumer_lock(value: object) -> ConsumerRuntimeLock:
    document = _closed_object(
        value,
        "consumer runtime lock",
        ("schema_version", "package", "zipapp", "runtimes", "acquisition"),
    )
    schema_version = _integer(document["schema_version"], "schema_version")
    if schema_version != 1:
        raise RuntimeLockError("schema_version must be 1")
    runtimes = _runtime_list(document["runtimes"], require_immutable_url=True)
    acquisition = _acquisition(document["acquisition"])
    if acquisition.selected_target not in {runtime.target for runtime in runtimes}:
        raise RuntimeLockError("selected target has no runtime entry")
    return ConsumerRuntimeLock(
        schema_version,
        _package(document["package"]),
        _zipapp(document["zipapp"]),
        runtimes,
        acquisition,
    )


def load_consumer_lock(path: Path) -> ConsumerRuntimeLock:
    return validate_consumer_lock(load_json_document(path))
