"""Policy change range — canonical hashing of committed file changes."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChangedFile:
    """A single changed file in a commit or push."""

    path: str
    status: str  # "A", "M", "D", "R", "C", etc.


@dataclass(frozen=True)
class ChangeRange:
    """A canonical, hashable representation of a set of file changes."""

    files: list[ChangedFile]
    range_hash: str


def compute_change_range(
    repo_root: Path,
    base_ref: str,
    head_ref: str = "HEAD",
) -> ChangeRange:
    """Compute a hash of file changes between *base_ref* and *head_ref*.

    Uses `git diff --name-status`. Returns an empty range if git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", f"{base_ref}..{head_ref}"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return _empty_range()
        files = _parse_diff_output(result.stdout)
    except (FileNotFoundError, PermissionError):
        return _empty_range()

    canonical = _canonical_sort(files)
    range_hash = hashlib.sha256(canonical.encode()).hexdigest()
    return ChangeRange(files=files, range_hash=range_hash)


def _parse_diff_output(output: str) -> list[ChangedFile]:
    files = []
    for line in output.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status, path = parts[0][0], parts[1]
            files.append(ChangedFile(path=path, status=status))
    return sorted(files, key=lambda f: f.path)


def _canonical_sort(files: list[ChangedFile]) -> str:
    parts = (f"{f.status}\t{f.path}" for f in sorted(files, key=lambda f: f.path))
    return "\0".join(parts)


def _empty_range() -> ChangeRange:
    empty_hash = hashlib.sha256(b"").hexdigest()
    return ChangeRange(files=[], range_hash=empty_hash)
