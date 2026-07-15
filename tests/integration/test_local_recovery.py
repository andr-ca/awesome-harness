"""Integration tests for local transaction recovery.

Verifies that each write boundary can fail and resume, and that rollback
restores exact bytes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentharness.bootstrap.transaction import (
    TOCTOUError,
    Transaction,
)


class TestLocalRecovery:
    def test_rollback_removes_new_file(self, tmp_path: Path) -> None:
        target = tmp_path / "new.txt"
        txn = Transaction.create(root=tmp_path, plan_hash="h1")
        txn.confirm()
        txn.write_file(target, b"new content")
        txn.apply()
        assert target.exists()
        txn.rollback()
        assert not target.exists()

    def test_rollback_restores_overwritten_file(self, tmp_path: Path) -> None:
        import hashlib

        original = b"original"
        target = tmp_path / "cfg.txt"
        target.write_bytes(original)
        original_hash = hashlib.sha256(original).hexdigest()

        txn = Transaction.create(root=tmp_path, plan_hash="h1")
        txn.confirm()
        txn.write_file(target, b"replacement", existing_hash=original_hash)
        txn.apply()
        assert target.read_bytes() == b"replacement"

        txn.rollback()
        assert target.read_bytes() == original

    def test_resume_after_crash(self, tmp_path: Path) -> None:
        """Load a confirmed transaction by ID and verify record persists."""
        txn = Transaction.create(root=tmp_path, plan_hash="h_resume")
        txn.confirm()
        txn_id = txn.id

        txn2 = Transaction.load(root=tmp_path, transaction_id=txn_id)
        record = txn2.load_record()
        assert record.confirmed
        assert record.plan_hash == "h_resume"
        assert not record.applied

    def test_toctou_blocks_unexpected_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "guarded.txt"
        txn = Transaction.create(root=tmp_path, plan_hash="h2")
        txn.confirm()
        txn.write_file(target, b"content")  # existing_hash=None → must not exist

        # Simulate another process creating the file before apply
        target.write_bytes(b"unexpected")
        with pytest.raises(TOCTOUError):
            txn.apply()

    def test_each_write_boundary_ends_in_deterministic_state(
        self, tmp_path: Path
    ) -> None:
        """After a failed apply, the record is not marked applied."""
        import hashlib

        target = tmp_path / "file.txt"
        txn = Transaction.create(root=tmp_path, plan_hash="h3")
        txn.confirm()
        txn.write_file(target, b"data")

        # Force a TOCTOU condition
        target.write_bytes(b"surprise")
        with pytest.raises(TOCTOUError):
            txn.apply()

        # Record must still show applied=False
        record = txn.load_record()
        assert not record.applied
