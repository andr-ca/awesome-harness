"""Preflight planning, collision classification, and crash-safe apply
for harness-link.sh's existing-surface integration. Orchestrates
block_installer.py; owns state schema v2. See
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md.
"""
from __future__ import annotations

import json
import sys
from enum import Enum, auto
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import block_installer as bi  # noqa: E402

SCHEMA_VERSION = 2

_V2_LIST_FIELDS = ("managed_blocks", "overwritten_files", "collision_decisions")


def _fresh_v2_skeleton() -> dict:
    return {"schema_version": SCHEMA_VERSION, **{k: [] for k in _V2_LIST_FIELDS}}


def load_state(path: Path) -> dict:
    """Load state, migrating v1 -> v2 in memory (schema migration policy
    tracked as F-12; this only adds the new v2 list fields, never
    rewrites v1 fields). Missing file returns a fresh v2 skeleton with
    no other fields — callers merge in mode/skills/etc. themselves."""
    path = Path(path)
    if not path.exists():
        return _fresh_v2_skeleton()
    data = json.loads(path.read_text())
    if data.get("schema_version") == SCHEMA_VERSION:
        return data
    data["schema_version"] = SCHEMA_VERSION
    for field in _V2_LIST_FIELDS:
        data.setdefault(field, [])
    return data


def save_state(path: Path, data: dict) -> None:
    path = Path(path)
    path.write_text(json.dumps(data, indent=2) + "\n")


class Classification(Enum):
    CREATE = auto()               # nothing there yet, write it
    BLOCK_MANAGED = auto()        # supported instructions file: insert/replace block
    WHOLE_FILE_COLLISION = auto() # generated whole-file surface already occupied
    HARD_FAIL = auto()            # malformed markers, symlink, or non-regular file


def classify_path(path: Path, *, is_block_surface: bool) -> Classification:
    """Classify a target path per spec section 4's three-way rule.
    is_block_surface=True for CLAUDE.md/AGENTS.md/GEMINI.md/copilot
    files (block-managed); False for directory-style generated assets
    like .cursor/rules/*.mdc (whole-file collision candidates)."""
    path = Path(path)

    if path.is_symlink():
        return Classification.HARD_FAIL
    if path.exists() and not path.is_file():
        return Classification.HARD_FAIL

    if not path.exists():
        return (
            Classification.BLOCK_MANAGED
            if is_block_surface
            else Classification.CREATE
        )

    if is_block_surface:
        try:
            bi.find_blocks(path.read_text(), "core-instructions")
        except bi.MarkerError:
            return Classification.HARD_FAIL
        return Classification.BLOCK_MANAGED

    return Classification.WHOLE_FILE_COLLISION
