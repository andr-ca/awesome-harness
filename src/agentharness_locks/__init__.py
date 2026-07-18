"""Multi-agent coordination — per-feature lock files for concurrent agent workflows.

When an agent starts working on a feature, it creates a lock file under
`.agentharness-locks/<feature-slug>.json`. A second agent detecting the lock
creates its own worktree on a fresh branch rather than conflicting.

Lock file format:
  {
    "agent_id":   "<unique session ID>",
    "feature":    "<human-readable description>",
    "branch":     "<current branch name>",
    "worktree":   "<path to worktree, or null>",
    "started_at": "<ISO 8601 UTC>",
    "pid":        <process ID>
  }

Stale detection: if `pid` is not an active OS process, the lock is stale.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

_LOCKS_DIR = ".agentharness-locks"


@dataclass
class AgentLock:
    """An active or stale agent lock record."""

    agent_id: str
    feature: str
    branch: str
    worktree: str | None
    started_at: str
    pid: int

    def is_stale(self) -> bool:
        """Return True if the process that created this lock is no longer alive."""
        try:
            os.kill(self.pid, 0)
            return False
        except (ProcessLookupError, PermissionError):
            return True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _slug(feature: str) -> str:
    """Return a filesystem-safe slug for *feature*."""
    slug = feature.lower().replace(" ", "-").replace("/", "-")
    # Trim to a reasonable length + add a content hash suffix for uniqueness
    trimmed = slug[:40]
    h = hashlib.sha256(feature.encode()).hexdigest()[:8]
    return f"{trimmed}-{h}"


def lock_path(project_root: Path, feature: str) -> Path:
    """Return the path to the lock file for *feature*."""
    return project_root / _LOCKS_DIR / f"{_slug(feature)}.json"


def acquire_lock(
    project_root: Path,
    feature: str,
    branch: str,
    worktree: str | None = None,
) -> AgentLock:
    """Acquire a lock for *feature* in *project_root*.

    Raises FileExistsError if a non-stale lock already exists for *feature*.
    Uses O_CREAT|O_EXCL to atomically create the lock file, eliminating the
    TOCTOU race between the existence check and the write.
    """
    path = lock_path(project_root, feature)
    path.parent.mkdir(parents=True, exist_ok=True)

    lock = AgentLock(
        agent_id=_make_agent_id(),
        feature=feature,
        branch=branch,
        worktree=worktree,
        started_at=datetime.now(tz=UTC).isoformat(),
        pid=os.getpid(),
    )

    while True:
        try:
            # Atomic create: fails immediately if the file already exists,
            # regardless of what another process is doing concurrently.
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(lock.to_dict(), fh, indent=2, sort_keys=True)
                fh.write("\n")
            return lock
        except FileExistsError:
            # The file exists — check if the lock is stale.
            try:
                existing = _load_lock(path)
                if not existing.is_stale():
                    raise FileExistsError(
                        f"Feature {feature!r} is already locked by agent "
                        f"{existing.agent_id!r} on branch {existing.branch!r} "
                        f"(pid {existing.pid}). Create a new branch or wait."
                    )
                # Stale lock — delete and retry.
                path.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError):
                # Corrupted lock — delete and retry.
                path.unlink(missing_ok=True)


def release_lock(project_root: Path, feature: str, agent_id: str) -> bool:
    """Release the lock for *feature* if it belongs to *agent_id*.

    Returns True if the lock was released, False if it didn't exist or
    belonged to a different agent.
    """
    path = lock_path(project_root, feature)
    if not path.exists():
        return False
    try:
        existing = _load_lock(path)
        if existing.agent_id != agent_id:
            return False
    except (json.JSONDecodeError, KeyError):
        # Cannot prove ownership of a corrupt lock — refuse to release it.
        return False
    path.unlink(missing_ok=True)
    return True


def check_lock(project_root: Path, feature: str) -> AgentLock | None:
    """Return the active lock for *feature*, or None if absent/stale."""
    path = lock_path(project_root, feature)
    if not path.exists():
        return None
    try:
        lock = _load_lock(path)
        if lock.is_stale():
            path.unlink(missing_ok=True)
            return None
        return lock
    except (json.JSONDecodeError, KeyError):
        return None


def list_locks(project_root: Path) -> list[AgentLock]:
    """Return all non-stale locks in *project_root*."""
    locks_dir = project_root / _LOCKS_DIR
    if not locks_dir.exists():
        return []
    active = []
    for p in sorted(locks_dir.glob("*.json")):
        try:
            lock = _load_lock(p)
            if lock.is_stale():
                p.unlink(missing_ok=True)
            else:
                active.append(lock)
        except (json.JSONDecodeError, KeyError):
            pass
    return active


def suggest_branch(feature: str) -> str:
    """Suggest a unique branch name for a second agent working on *feature*."""
    ts = int(time.time())
    slug = _slug(feature)[:20]
    return f"feat/{slug}-agent-{ts}"


def _load_lock(path: Path) -> AgentLock:
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentLock(
        agent_id=data["agent_id"],
        feature=data["feature"],
        branch=data["branch"],
        worktree=data.get("worktree"),
        started_at=data["started_at"],
        pid=int(data["pid"]),
    )


def _atomic_write(path: Path, lock: AgentLock) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(lock.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _make_agent_id() -> str:
    import uuid
    return str(uuid.uuid4())
