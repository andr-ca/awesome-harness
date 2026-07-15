"""Agent source integration — ensures canonical agent files
are updated before generation.
"""

from __future__ import annotations

from pathlib import Path


def find_canonical_source(root: Path) -> Path | None:
    """Return the canonical agent source file (CLAUDE.md) if it exists."""
    candidate = root / "CLAUDE.md"
    return candidate if candidate.exists() else None


def list_generated_clients(root: Path) -> list[Path]:
    """Return the list of files that would be regenerated from canonical source."""
    candidates = [
        root / "AGENTS.md",
        root / "GEMINI.md",
        root / ".github" / "copilot-instructions.md",
    ]
    return [p for p in candidates if p.exists()]
