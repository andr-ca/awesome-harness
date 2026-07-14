from __future__ import annotations

import hashlib
import os
import re
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO, BinaryIO, cast
from urllib.parse import urljoin, urlparse

_READ_CHUNK_BYTES = 1024 * 1024
_ARTIFACT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_MAX_ARTIFACT_BYTES = 256 * 1024 * 1024


class ArtifactAcquisitionError(RuntimeError):
    """Raised when a locked artifact cannot be acquired safely."""


class ArtifactIntegrityError(ArtifactAcquisitionError):
    """Raised when acquired bytes do not match committed trust material."""


@dataclass(frozen=True, slots=True)
class LockedArtifact:
    name: str
    url: str
    sha256: str | None
    sha512: str
    max_bytes: int

    def __post_init__(self) -> None:
        if _ARTIFACT_NAME_PATTERN.fullmatch(self.name) is None:
            raise ValueError("artifact name must be a safe cache identifier")
        parsed = urlparse(self.url)
        if (
            parsed.scheme not in ("https", "file")
            or parsed.username is not None
            or parsed.password is not None
            or (parsed.scheme == "https" and parsed.hostname is None)
            or (parsed.scheme == "file" and parsed.netloc not in ("", "localhost"))
            or (parsed.scheme == "file" and (parsed.query or parsed.fragment))
        ):
            raise ValueError("artifact URL must be a credential-free HTTPS or file URL")
        if self.sha256 is not None and (
            len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            raise ValueError("artifact SHA-256 must be lowercase hexadecimal")
        if len(self.sha512) != 128 or any(
            character not in "0123456789abcdef" for character in self.sha512
        ):
            raise ValueError("artifact SHA-512 must be lowercase hexadecimal")
        if not 0 < self.max_bytes <= _MAX_ARTIFACT_BYTES:
            raise ValueError("artifact size limit is outside the supported range")


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    name: str
    path: Path
    sha256: str
    sha512: str


@dataclass(frozen=True, slots=True)
class _StagedArtifact:
    verified: VerifiedArtifact
    destination: Path


def _same_identity(left: LockedArtifact, right: LockedArtifact) -> bool:
    return replace(left, url=right.url) == right


def with_mirror(
    artifact: LockedArtifact,
    mirror_url: str,
    *,
    allowed_https_hosts: tuple[str, ...] = (),
    allow_file: bool = False,
    expected: LockedArtifact | None = None,
) -> LockedArtifact:
    """Return the same lock identity with only its acquisition URL replaced."""
    reference = expected if expected is not None else artifact
    if not _same_identity(artifact, reference):
        raise ValueError("a mirror may only replace the source URL")

    parsed = urlparse(mirror_url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("mirror URLs cannot contain credentials")
    if parsed.scheme == "https":
        hostname = parsed.hostname
        if hostname is None or hostname not in allowed_https_hosts:
            raise ValueError("HTTPS mirror host is not allowed by the base lock")
    elif parsed.scheme == "file":
        if not allow_file or parsed.netloc not in ("", "localhost"):
            raise ValueError("file mirrors are not enabled for this operation")
    else:
        raise ValueError("mirror URL must use HTTPS or an explicitly enabled file URL")
    return replace(artifact, url=mirror_url)


def _open_source(
    artifact: LockedArtifact,
    *,
    allowed_https_hosts: tuple[str, ...],
    allow_file: bool,
    max_redirects: int,
) -> BinaryIO:
    class NoAutomaticRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(
            self,
            _request: urllib.request.Request,
            _file_pointer: IO[bytes],
            _code: int,
            _message: str,
            _headers: object,
            _new_url: str,
        ) -> None:
            return None

    opener = urllib.request.build_opener(NoAutomaticRedirect)
    current_url = artifact.url
    redirects = 0
    while True:
        if not _source_url_allowed(
            current_url,
            allowed_https_hosts=allowed_https_hosts,
            allow_file=allow_file,
        ):
            raise ArtifactAcquisitionError(
                f"{artifact.name} source is not allowed"
            )
        try:
            return cast(BinaryIO, opener.open(current_url, timeout=30))  # noqa: S310
        except urllib.error.HTTPError as error:
            if error.code not in (301, 302, 303, 307, 308):
                raise ArtifactAcquisitionError(
                    f"{artifact.name} source is unavailable"
                ) from error
            location = error.headers.get("Location")
            if not isinstance(location, str) or redirects >= max_redirects:
                raise ArtifactAcquisitionError(
                    f"{artifact.name} redirect is not allowed"
                ) from error
            next_url = urljoin(current_url, location)
            if not _source_url_allowed(
                next_url,
                allowed_https_hosts=allowed_https_hosts,
                allow_file=allow_file,
            ):
                raise ArtifactAcquisitionError(
                    f"{artifact.name} source is not allowed"
                ) from error
            current_url = next_url
            redirects += 1
        except (OSError, ValueError, urllib.error.URLError) as error:
            raise ArtifactAcquisitionError(
                f"{artifact.name} source is unavailable"
            ) from error


def _source_url_allowed(
    url: str,
    *,
    allowed_https_hosts: tuple[str, ...],
    allow_file: bool,
) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in allowed_https_hosts
        and parsed.username is None
        and parsed.password is None
    ) or (
        parsed.scheme == "file"
        and allow_file
        and parsed.netloc in ("", "localhost")
        and not parsed.query
        and not parsed.fragment
    )


def _stage_artifact(
    artifact: LockedArtifact,
    cache_dir: Path,
    *,
    allowed_https_hosts: tuple[str, ...] = (),
    allow_file: bool = False,
    max_redirects: int = 3,
) -> _StagedArtifact:
    """Acquire and verify one artifact without making it cache-visible."""
    destination = cache_dir / f"{artifact.name}-{artifact.sha512}"
    temporary_path: Path | None = None
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    total = 0
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with _open_source(
            artifact,
            allowed_https_hosts=allowed_https_hosts,
            allow_file=allow_file,
            max_redirects=max_redirects,
        ) as source:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{artifact.name}-", suffix=".part", dir=cache_dir
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as temporary:
                while chunk := source.read(_READ_CHUNK_BYTES):
                    total += len(chunk)
                    if total > artifact.max_bytes:
                        raise ArtifactAcquisitionError(
                            f"{artifact.name} exceeds its locked size limit"
                        )
                    sha256.update(chunk)
                    sha512.update(chunk)
                    temporary.write(chunk)
                temporary.flush()
                os.fsync(temporary.fileno())
        actual_sha256 = sha256.hexdigest()
        actual_sha512 = sha512.hexdigest()
        if artifact.sha256 is not None and actual_sha256 != artifact.sha256:
            raise ArtifactIntegrityError(
                f"{artifact.name} failed locked SHA-256 verification"
            )
        if actual_sha512 != artifact.sha512:
            raise ArtifactIntegrityError(
                f"{artifact.name} failed locked SHA-512 verification"
            )
        if temporary_path is None:  # pragma: no cover - mkstemp always assigns it
            raise ArtifactAcquisitionError(f"{artifact.name} source is unavailable")
        staged = VerifiedArtifact(
            name=artifact.name,
            path=temporary_path,
            sha256=actual_sha256,
            sha512=actual_sha512,
        )
        temporary_path = None
        return _StagedArtifact(verified=staged, destination=destination)
    except ArtifactAcquisitionError:
        raise
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise ArtifactAcquisitionError(
            f"{artifact.name} source is unavailable"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _promote_staged_artifact(staged: _StagedArtifact) -> VerifiedArtifact:
    try:
        os.replace(staged.verified.path, staged.destination)
    except OSError as error:
        raise ArtifactAcquisitionError(
            f"{staged.verified.name} could not be promoted to the verified cache"
        ) from error
    return replace(staged.verified, path=staged.destination)


def _discard_staged_artifact(staged: _StagedArtifact | None) -> None:
    if staged is not None:
        staged.verified.path.unlink(missing_ok=True)


def acquire_artifact(
    artifact: LockedArtifact,
    cache_dir: Path,
    *,
    allowed_https_hosts: tuple[str, ...] = (),
    allow_file: bool = False,
    max_redirects: int = 3,
) -> VerifiedArtifact:
    """Acquire, verify, and atomically promote one immutable artifact."""
    staged = _stage_artifact(
        artifact,
        cache_dir,
        allowed_https_hosts=allowed_https_hosts,
        allow_file=allow_file,
        max_redirects=max_redirects,
    )
    try:
        return _promote_staged_artifact(staged)
    finally:
        _discard_staged_artifact(staged)
