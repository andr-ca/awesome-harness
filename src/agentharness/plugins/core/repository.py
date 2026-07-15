"""Core repository policy detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class RepositoryKind(StrEnum):
    GIT = "git"
    BARE = "bare"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RepositoryDetection:
    kind: RepositoryKind
    has_env_sample: bool


def detect_repository(root: Path) -> RepositoryDetection:
    """Detect repository policy characteristics in *root*. Read-only."""
    has_git = (root / ".git").exists()
    kind = RepositoryKind.GIT if has_git else RepositoryKind.UNKNOWN
    has_env = (root / ".env.sample").exists() or (root / ".env.example").exists()
    return RepositoryDetection(kind=kind, has_env_sample=has_env)
