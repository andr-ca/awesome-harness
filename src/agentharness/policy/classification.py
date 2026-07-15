"""Policy change classification — semantic labelling of file changes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChangeClass(StrEnum):
    CODE = "code"
    DOCS = "docs"
    CONFIG = "config"
    TESTS = "tests"
    GENERATED = "generated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Classification:
    path: str
    change_class: ChangeClass


def classify_path(path: str) -> ChangeClass:
    """Classify a file path into a ChangeClass based on common conventions."""
    p = path.lower()
    if p.startswith("tests/") or p.startswith("test/") or "test_" in p.split("/")[-1]:
        return ChangeClass.TESTS
    if any(p.endswith(ext) for ext in (".md", ".rst", ".txt")):
        if "docs/" in p or p.startswith("docs/") or p in ("readme.md", "changelog.md"):
            return ChangeClass.DOCS
    cfg_exts = (".yaml", ".yml", ".toml", ".json", ".ini", ".cfg")
    if any(p.endswith(ext) for ext in cfg_exts):
        return ChangeClass.CONFIG
    if any(p.endswith(ext) for ext in (".py", ".ts", ".js", ".go", ".rs")):
        return ChangeClass.CODE
    if p.startswith(".github/") or p.startswith("tools/"):
        return ChangeClass.CONFIG
    return ChangeClass.UNKNOWN


def classify_changes(paths: list[str]) -> list[Classification]:
    """Return a classification for each path in *paths*."""
    return [Classification(path=p, change_class=classify_path(p)) for p in paths]
