#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = "20260510"
PYTHON_VERSION = "3.12.13"
FLAVOR = "install_only_stripped.tar.gz"
TARGETS = (
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
)
MAX_BYTES = 268_435_456
MAX_API_BYTES = 4_194_304
API_URL = (
    "https://api.github.com/repos/astral-sh/python-build-standalone/"
    f"releases/tags/{RELEASE}"
)


class RuntimeManifestUpdateError(RuntimeError):
    """Raised when immutable upstream release data cannot be reviewed safely."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeManifestUpdateError(f"duplicate release JSON key: {key}")
        result[key] = value
    return result


def _download_digests(url: str) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    size = 0
    request = urllib.request.Request(
        url, headers={"User-Agent": "agentharness-runtime-lock/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.geturl().split(":", 1)[0] != "https":
                raise RuntimeManifestUpdateError(
                    "runtime asset redirected away from HTTPS"
                )
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise RuntimeManifestUpdateError(
                        "runtime asset exceeds compressed limit"
                    )
                sha256.update(chunk)
                sha512.update(chunk)
    except (OSError, urllib.error.URLError) as error:
        raise RuntimeManifestUpdateError(
            f"cannot download runtime asset: {error}"
        ) from error
    return sha256.hexdigest(), sha512.hexdigest()


def build_review_manifest() -> dict[str, object]:
    request = urllib.request.Request(
        API_URL, headers={"User-Agent": "agentharness-runtime-lock/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final = urllib.parse.urlparse(response.geturl())
            if final.scheme != "https" or final.netloc != "api.github.com":
                raise RuntimeManifestUpdateError(
                    "release API redirected outside approved HTTPS GitHub host"
                )
            payload = response.read(MAX_API_BYTES + 1)
            if len(payload) > MAX_API_BYTES:
                raise RuntimeManifestUpdateError("release API JSON exceeds size limit")
            release = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise RuntimeManifestUpdateError(
            f"cannot read immutable release metadata: {error}"
        ) from error
    if not isinstance(release, dict) or not isinstance(release.get("assets"), list):
        raise RuntimeManifestUpdateError("release metadata has an unexpected shape")
    assets = release["assets"]
    runtimes: list[dict[str, str]] = []
    for target in TARGETS:
        expected_name = f"cpython-{PYTHON_VERSION}+{RELEASE}-{target}-{FLAVOR}"
        matches = [
            asset
            for asset in assets
            if isinstance(asset, dict) and asset.get("name") == expected_name
        ]
        if len(matches) != 1:
            raise RuntimeManifestUpdateError(
                f"expected exactly one release asset for {target}"
            )
        url = matches[0].get("browser_download_url")
        upstream_digest = matches[0].get("digest")
        expected_url = (
            "https://github.com/astral-sh/python-build-standalone/releases/"
            f"download/{RELEASE}/{expected_name.replace('+', '%2B')}"
        )
        if url != expected_url:
            raise RuntimeManifestUpdateError(
                f"release asset URL is not immutable: {target}"
            )
        sha256, sha512 = _download_digests(url)
        if upstream_digest != f"sha256:{sha256}":
            raise RuntimeManifestUpdateError(
                f"upstream SHA-256 does not match bytes: {target}"
            )
        runtimes.append(
            {
                "target": target,
                "url": url,
                "sha256": sha256,
                "sha512": sha512,
                "archive_prefix": "python/",
                "interpreter_path": "python/bin/python3",
            }
        )
    return {
        "schema_version": 1,
        "python_version": PYTHON_VERSION,
        "release": RELEASE,
        "artifact_flavor": FLAVOR,
        "runtimes": runtimes,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review and update the pinned Python runtimes"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "runtime/python-build-standalone.lock.json",
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        document = build_review_manifest()
        content = json.dumps(document, indent=2) + "\n"
        if args.check:
            if args.output.read_text(encoding="utf-8") != content:
                raise RuntimeManifestUpdateError(
                    "committed runtime manifest differs from upstream"
                )
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=args.output.parent, delete=False
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            temporary_path.replace(args.output)
    except (OSError, RuntimeManifestUpdateError) as error:
        print(f"runtime manifest update failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
