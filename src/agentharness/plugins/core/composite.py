"""Core composite command detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompositeCommand:
    name: str
    path: str


def detect_composite_commands(root: Path) -> list[CompositeCommand]:
    """Detect composite quality commands in *root*. Read-only."""
    cmds: list[CompositeCommand] = []
    check_sh = root / "tools" / "check.sh"
    if check_sh.exists():
        cmds.append(CompositeCommand(name="check.sh", path=str(check_sh)))
    return cmds
