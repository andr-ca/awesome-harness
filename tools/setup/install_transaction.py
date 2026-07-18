"""Preflight planning, collision classification, and crash-safe apply
for harness-link.sh's existing-surface integration. Orchestrates
block_installer.py; owns state schema v2. See
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md.
"""
from __future__ import annotations

import json
from pathlib import Path

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
