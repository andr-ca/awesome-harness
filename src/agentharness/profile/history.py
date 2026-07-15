"""Profile history — tracks the provenance of applied profile changes.

History records are immutable once written; each entry captures the
plan hash, timestamp, and a redacted summary of what changed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class HistoryEntry:
    """A single record in the bootstrap profile history."""

    timestamp: str  # ISO 8601 UTC
    plan_hash: str
    summary: str


class ProfileHistory:
    """Reads and appends to the profile history log.

    The log is a newline-delimited JSON file where each line is one
    HistoryEntry.  Entries are never modified; only appended.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def entries(self) -> list[HistoryEntry]:
        """Return all history entries in chronological order."""
        if not self._path.exists():
            return []
        result = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            result.append(
                HistoryEntry(
                    timestamp=data["timestamp"],
                    plan_hash=data["plan_hash"],
                    summary=data["summary"],
                )
            )
        return result

    def append(self, plan_hash: str, summary: str) -> None:
        """Append a new entry to the history log."""
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "plan_hash": plan_hash,
            "summary": summary,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
