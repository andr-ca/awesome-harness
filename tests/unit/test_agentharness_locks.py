"""Unit tests for src/agentharness_locks/__init__.py"""
from __future__ import annotations

import json
import os

import pytest

from agentharness_locks import (
    acquire_lock,
    check_lock,
    list_locks,
    release_lock,
)

# ---------------------------------------------------------------------------
# acquire_lock
# ---------------------------------------------------------------------------


def test_acquire_creates_lock_file(tmp_path):
    lock = acquire_lock(tmp_path, "my-feature", branch="feat/x")
    lock_file = tmp_path / ".agentharness-locks"
    files = list(lock_file.glob("*.json"))
    assert len(files) == 1
    assert lock.feature == "my-feature"
    assert lock.branch == "feat/x"


def test_acquire_returns_lock_with_current_pid(tmp_path):
    lock = acquire_lock(tmp_path, "f1", branch="b1")
    assert lock.pid == os.getpid()


def test_acquire_refuses_active_lock(tmp_path):
    lock = acquire_lock(tmp_path, "conflict", branch="b1")
    with pytest.raises(FileExistsError, match="already locked"):
        acquire_lock(tmp_path, "conflict", branch="b2")
    # First lock is still intact
    assert check_lock(tmp_path, "conflict") is not None
    assert check_lock(tmp_path, "conflict").agent_id == lock.agent_id


def test_acquire_overwrites_stale_lock(tmp_path, monkeypatch):
    """A lock whose pid is no longer alive (stale) should be replaced."""
    # Acquire with a fake dead pid
    first = acquire_lock(tmp_path, "stale-feature", branch="b1")
    # Overwrite the file with a stale pid (0 is never a real user process)
    path = list((tmp_path / ".agentharness-locks").glob("*.json"))[0]
    data = json.loads(path.read_text())
    data["pid"] = 999999999  # almost certainly not alive
    path.write_text(json.dumps(data))

    # Acquiring again should succeed because the old lock is stale
    second = acquire_lock(tmp_path, "stale-feature", branch="b2")
    assert second.branch == "b2"
    assert second.agent_id != first.agent_id


def test_acquire_overwrites_corrupt_lock(tmp_path):
    """A corrupt lock file should be silently replaced."""
    locks_dir = tmp_path / ".agentharness-locks"
    locks_dir.mkdir(parents=True)
    # Write corrupt JSON to the expected slot
    acquire_lock(tmp_path, "corrupt-test", branch="b1")
    path = list(locks_dir.glob("*.json"))[0]
    path.write_text("NOT JSON")

    lock_b = acquire_lock(tmp_path, "corrupt-test", branch="b2")
    assert lock_b.branch == "b2"


# ---------------------------------------------------------------------------
# release_lock
# ---------------------------------------------------------------------------


def test_release_succeeds_for_owner(tmp_path):
    lock = acquire_lock(tmp_path, "rel-feat", branch="b1")
    released = release_lock(tmp_path, "rel-feat", lock.agent_id)
    assert released is True
    assert check_lock(tmp_path, "rel-feat") is None


def test_release_fails_for_wrong_agent(tmp_path):
    acquire_lock(tmp_path, "owned-feat", branch="b1")
    released = release_lock(tmp_path, "owned-feat", "wrong-agent-id")
    assert released is False
    # Lock still present
    assert check_lock(tmp_path, "owned-feat") is not None


def test_release_fails_for_corrupt_lock(tmp_path):
    """Cannot prove ownership of a corrupt lock — refuse to release."""
    lock = acquire_lock(tmp_path, "corrupt-rel", branch="b1")
    path = list((tmp_path / ".agentharness-locks").glob("*.json"))[0]
    path.write_text("GARBAGE")
    released = release_lock(tmp_path, "corrupt-rel", lock.agent_id)
    assert released is False
    # Corrupt file still on disk (we didn't delete it)
    assert path.exists()


def test_release_returns_false_if_no_lock(tmp_path):
    released = release_lock(tmp_path, "nonexistent", "any-id")
    assert released is False


# ---------------------------------------------------------------------------
# check_lock / list_locks
# ---------------------------------------------------------------------------


def test_check_lock_returns_none_for_missing_feature(tmp_path):
    assert check_lock(tmp_path, "missing") is None


def test_list_locks_returns_active_only(tmp_path):
    lock_a = acquire_lock(tmp_path, "feat-a", branch="b1")
    lock_b = acquire_lock(tmp_path, "feat-b", branch="b2")

    locks = list_locks(tmp_path)
    assert len(locks) == 2
    ids = {lock.agent_id for lock in locks}
    assert lock_a.agent_id in ids
    assert lock_b.agent_id in ids
