#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agentharness.runtime_lock import (  # noqa: E402
    RuntimeLockError,
    load_consumer_lock,
    load_runtime_manifest,
)


def _digests(path: Path, limit: int) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    total = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            total += len(chunk)
            if total > limit:
                raise RuntimeLockError("runtime artifact exceeds compressed-size limit")
            sha256.update(chunk)
            sha512.update(chunk)
    return sha256.hexdigest(), sha512.hexdigest()


def verify_runtime_lock(
    manifest_path: Path,
    *,
    consumer_lock_path: Path | None = None,
    artifact_directory: Path | None = None,
    require_artifacts: bool = True,
) -> None:
    manifest = load_runtime_manifest(manifest_path)
    if consumer_lock_path is not None:
        load_consumer_lock(consumer_lock_path)
    if artifact_directory is None:
        if require_artifacts:
            raise RuntimeLockError("--require-artifacts needs --artifact-directory")
        return
    for runtime in manifest.runtimes:
        filename = unquote(Path(urlparse(runtime.url).path).name)
        encoded_filename = Path(urlparse(runtime.url).path).name
        candidates = [
            artifact_directory / filename,
            artifact_directory / encoded_filename,
        ]
        artifact = next((path for path in candidates if path.is_file()), None)
        if artifact is None:
            if require_artifacts:
                raise RuntimeLockError(
                    f"runtime artifact is missing: {filename}; seed "
                    ".tool-cache/runtime-artifacts or pass --artifact-directory"
                )
            continue
        sha256, sha512 = _digests(artifact, 268_435_456)
        if sha256 != runtime.sha256:
            raise RuntimeLockError(
                f"runtime artifact SHA-256 mismatch: {runtime.target}"
            )
        if sha512 != runtime.sha512:
            raise RuntimeLockError(
                f"runtime artifact SHA-512 mismatch: {runtime.target}"
            )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify reviewed runtime trust material"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "runtime/python-build-standalone.lock.json",
    )
    parser.add_argument("--consumer-lock", type=Path)
    parser.add_argument(
        "--artifact-directory",
        type=Path,
        default=ROOT / ".tool-cache/runtime-artifacts",
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="validate structure only; skip artifact-byte verification",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        verify_runtime_lock(
            args.manifest,
            consumer_lock_path=args.consumer_lock,
            artifact_directory=args.artifact_directory,
            require_artifacts=not getattr(args, "structure_only", False),
        )
    except (OSError, RuntimeLockError) as error:
        print(f"runtime lock verification failed: {error}", file=sys.stderr)
        return 1
    print(f"verified {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
