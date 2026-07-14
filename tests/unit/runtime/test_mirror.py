from __future__ import annotations

import hashlib
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from agentharness.runtime import (
    ArtifactAcquisitionError,
    ArtifactIntegrityError,
    LockedArtifact,
    acquire_artifact,
    with_mirror,
)


def _artifact(source: Path, *, digest: str | None = None) -> LockedArtifact:
    payload = source.read_bytes()
    return LockedArtifact(
        name="runtime",
        url=source.as_uri(),
        sha256=hashlib.sha256(payload).hexdigest(),
        sha512=digest or hashlib.sha512(payload).hexdigest(),
        max_bytes=1024,
    )


def test_https_mirror_changes_only_the_source_url(tmp_path: Path) -> None:
    source = tmp_path / "runtime.tar.gz"
    source.write_bytes(b"trusted-runtime")
    locked = _artifact(source)

    mirrored = with_mirror(
        locked,
        "https://artifacts.example.test/runtime.tar.gz",
        allowed_https_hosts=("artifacts.example.test",),
    )

    assert mirrored == LockedArtifact(
        name=locked.name,
        url="https://artifacts.example.test/runtime.tar.gz",
        sha256=locked.sha256,
        sha512=locked.sha512,
        max_bytes=locked.max_bytes,
    )


def test_file_mirror_is_integrity_equivalent(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream.tar.gz"
    mirror = tmp_path / "mirror.tar.gz"
    upstream.write_bytes(b"same immutable bytes")
    mirror.write_bytes(upstream.read_bytes())
    locked = _artifact(upstream)
    mirrored = with_mirror(locked, mirror.as_uri(), allow_file=True)

    acquired = acquire_artifact(mirrored, tmp_path / "cache", allow_file=True)

    assert (acquired.sha256, acquired.sha512, acquired.path.read_bytes()) == (
        locked.sha256,
        locked.sha512,
        upstream.read_bytes(),
    )


def test_mirror_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "runtime.tar.gz"
    source.write_bytes(b"tampered")
    locked = _artifact(source, digest="0" * 128)

    with pytest.raises(ArtifactIntegrityError, match="runtime.*SHA-512"):
        acquire_artifact(locked, tmp_path / "cache", allow_file=True)

    assert list((tmp_path / "cache").glob("*")) == []


def test_unavailable_source_has_bounded_redacted_failure(tmp_path: Path) -> None:
    secret_path = tmp_path / "token-secret" / "missing.tar.gz"
    locked = LockedArtifact(
        name="runtime",
        url=secret_path.as_uri(),
        sha256="0" * 64,
        sha512="0" * 128,
        max_bytes=1024,
    )

    with pytest.raises(ArtifactAcquisitionError) as raised:
        acquire_artifact(locked, tmp_path / "cache", allow_file=True)

    message = str(raised.value)
    assert message == "runtime source is unavailable"
    assert "token-secret" not in message


def test_mirror_rejects_identity_or_digest_substitution(tmp_path: Path) -> None:
    source = tmp_path / "runtime.tar.gz"
    source.write_bytes(b"trusted-runtime")
    locked = _artifact(source)

    with pytest.raises(ValueError, match="only replace the source URL"):
        with_mirror(
            locked,
            "https://artifacts.example.test/runtime.tar.gz",
            allowed_https_hosts=("artifacts.example.test",),
            expected=LockedArtifact(
                name=locked.name,
                url=locked.url,
                sha256="f" * 64,
                sha512=locked.sha512,
                max_bytes=locked.max_bytes,
            ),
        )


@pytest.mark.parametrize("name", ("../runtime", "runtime/name", ".runtime"))
def test_artifact_name_cannot_escape_digest_cache(name: str, tmp_path: Path) -> None:
    source = tmp_path / "runtime.tar.gz"
    source.write_bytes(b"trusted-runtime")

    with pytest.raises(ValueError, match="artifact name"):
        LockedArtifact(
            name=name,
            url=source.as_uri(),
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            sha512=hashlib.sha512(source.read_bytes()).hexdigest(),
            max_bytes=1024,
        )


def test_file_source_requires_explicit_offline_authority(tmp_path: Path) -> None:
    source = tmp_path / "runtime.tar.gz"
    source.write_bytes(b"trusted-runtime")

    with pytest.raises(ArtifactAcquisitionError, match="source is not allowed"):
        acquire_artifact(_artifact(source), tmp_path / "cache")


def test_https_redirect_is_rejected_before_unapproved_destination_is_contacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"trusted-runtime"
    contacts = {"destination": 0}

    class DestinationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            contacts["destination"] += 1
            self.send_response(200)
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            return

    destination = ThreadingHTTPServer(("127.0.0.1", 0), DestinationHandler)
    destination_thread = threading.Thread(
        target=destination.serve_forever, daemon=True
    )
    destination_thread.start()

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(302)
            self.send_header(
                "Location",
                f"http://127.0.0.1:{destination.server_port}/metadata",
            )
            self.end_headers()

        def log_message(self, _format: str, *_args: object) -> None:
            return

    certificate = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
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
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        check=True,
        capture_output=True,
    )
    redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    redirect.socket = context.wrap_socket(redirect.socket, server_side=True)
    redirect_thread = threading.Thread(target=redirect.serve_forever, daemon=True)
    redirect_thread.start()
    monkeypatch.setenv("SSL_CERT_FILE", str(certificate))
    monkeypatch.setenv("NO_PROXY", "localhost")
    artifact = LockedArtifact(
        name="runtime",
        url=f"https://localhost:{redirect.server_port}/runtime.tar.gz",
        sha256=hashlib.sha256(payload).hexdigest(),
        sha512=hashlib.sha512(payload).hexdigest(),
        max_bytes=1024,
    )
    try:
        with pytest.raises(ArtifactAcquisitionError, match="source is not allowed"):
            acquire_artifact(
                artifact,
                tmp_path / "cache",
                allowed_https_hosts=("localhost",),
            )
        assert contacts["destination"] == 0
    finally:
        redirect.shutdown()
        destination.shutdown()
        redirect.server_close()
        destination.server_close()
        redirect_thread.join()
        destination_thread.join()
