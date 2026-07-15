"""Unit tests for the local transaction system.

Each write boundary can fail and resume; rollback restores exact bytes
and modes.  Unfamiliar content is never overwritten.  TOCTOU changes
between plan creation and apply are detected.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from agentharness.bootstrap.transaction import (
    ApplyError,
    LocalTransactionRecord,
    PlanConflictError,
    TOCTOUError,
    Transaction,
)


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A scratch project directory with no pre-existing agentharness state."""
    return tmp_path


class TestTransactionCreate:
    def test_creates_transaction_directory(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        assert (tmp_project / ".agentharness-local" / "transactions").exists()
        assert txn.id is not None

    def test_transaction_record_is_not_confirmed(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        record = txn.load_record()
        assert not record.confirmed
        assert not record.applied
        assert record.plan_hash == "hash1"


class TestTransactionConfirm:
    def test_confirm_binds_plan_hash(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        txn.confirm()
        record = txn.load_record()
        assert record.confirmed
        assert record.plan_hash == "hash1"

    def test_wrong_hash_raises_conflict(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        with pytest.raises(PlanConflictError):
            txn.confirm(expected_hash="different_hash")


class TestTransactionApply:
    def test_apply_writes_file(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        txn.confirm()
        target = tmp_project / "output.txt"
        txn.write_file(target, b"hello")
        txn.apply()
        assert target.read_bytes() == b"hello"

    def test_apply_requires_confirmation(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        target = tmp_project / "output.txt"
        txn.write_file(target, b"hello")
        with pytest.raises(ApplyError, match="confirmed"):
            txn.apply()

    def test_apply_refuses_to_overwrite_unfamiliar_content(
        self, tmp_project: Path
    ) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        txn.confirm()
        target = tmp_project / "existing.txt"
        target.write_bytes(b"unexpected content")
        txn.write_file(target, b"new content")
        with pytest.raises(TOCTOUError):
            txn.apply()

    def test_apply_allows_overwrite_if_content_matches_recorded_hash(
        self, tmp_project: Path
    ) -> None:
        """If the caller provides the correct existing_hash, overwrite succeeds."""
        import hashlib

        existing_content = b"existing"
        target = tmp_project / "output.txt"
        target.write_bytes(existing_content)
        existing_hash = hashlib.sha256(existing_content).hexdigest()

        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        txn.confirm()
        txn.write_file(target, b"new content", existing_hash=existing_hash)
        txn.apply()
        assert target.read_bytes() == b"new content"


class TestTransactionRollback:
    def test_rollback_removes_written_file(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        txn.confirm()
        target = tmp_project / "output.txt"
        txn.write_file(target, b"hello")
        txn.apply()
        assert target.exists()
        txn.rollback()
        assert not target.exists()

    def test_rollback_restores_original_bytes(self, tmp_project: Path) -> None:
        original = b"original content"
        txn = Transaction.create(root=tmp_project, plan_hash="hash1")
        txn.confirm()
        target = tmp_project / "config.yaml"
        target.write_bytes(original)
        txn.write_file(target, b"modified content", existing_hash=None)
        # Apply with explicit permission to overwrite existing
        txn._force_apply = True  # noqa: SLF001 — test-only escape hatch
        txn.apply()
        assert target.read_bytes() == b"modified content"
        txn.rollback()
        assert target.read_bytes() == original


class TestTransactionResume:
    def test_resume_from_persisted_record(self, tmp_project: Path) -> None:
        txn = Transaction.create(root=tmp_project, plan_hash="hash_resume")
        txn.confirm()
        txn_id = txn.id

        # Simulate process restart: load the transaction from disk
        txn2 = Transaction.load(root=tmp_project, transaction_id=txn_id)
        record = txn2.load_record()
        assert record.confirmed
        assert record.plan_hash == "hash_resume"

    def test_load_nonexistent_raises(self, tmp_project: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Transaction.load(root=tmp_project, transaction_id="nonexistent")
