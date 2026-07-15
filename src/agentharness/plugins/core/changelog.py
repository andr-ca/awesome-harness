"""Changelog policy plugin for the core bundle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ChangelogStrategy(StrEnum):
    TOWNCRIER = "towncrier"
    KEEPACHANGELOG = "keepachangelog"
    MONOLITHIC = "monolithic"
    ABSENT = "absent"


@dataclass(frozen=True)
class ChangelogPolicy:
    strategy: ChangelogStrategy


def detect_changelog_policy(root: Path) -> ChangelogPolicy:
    """Detect changelog strategy in *root*. Read-only."""
    if (root / "changelog.d").exists() or (root / "newsfragments").exists():
        return ChangelogPolicy(strategy=ChangelogStrategy.TOWNCRIER)

    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        text = changelog.read_text(encoding="utf-8", errors="replace")
        if "Keep a Changelog" in text:
            return ChangelogPolicy(strategy=ChangelogStrategy.KEEPACHANGELOG)
        return ChangelogPolicy(strategy=ChangelogStrategy.MONOLITHIC)

    return ChangelogPolicy(strategy=ChangelogStrategy.ABSENT)
