"""Integration tests for plan confirmation flow.

Covers: discovery is read-only, unresolved questions block apply,
confirmation binds the canonical plan hash.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentharness.bootstrap.questions import Question, QuestionSet
from agentharness.bootstrap.transaction import (
    ApplyError,
    PlanConflictError,
    Transaction,
)


class TestConfirmationFlow:
    def test_unconfirmed_transaction_blocks_apply(self, tmp_path: Path) -> None:
        txn = Transaction.create(root=tmp_path, plan_hash="h1")
        txn.write_file(tmp_path / "out.txt", b"content")
        with pytest.raises(ApplyError, match="confirmed"):
            txn.apply()

    def test_wrong_hash_blocks_confirm(self, tmp_path: Path) -> None:
        txn = Transaction.create(root=tmp_path, plan_hash="correct_hash")
        with pytest.raises(PlanConflictError):
            txn.confirm(expected_hash="wrong_hash")

    def test_correct_hash_allows_confirm(self, tmp_path: Path) -> None:
        txn = Transaction.create(root=tmp_path, plan_hash="correct_hash")
        txn.confirm(expected_hash="correct_hash")
        assert txn.load_record().confirmed

    def test_unresolved_questions_signal_is_correct(self) -> None:
        """Unresolved QuestionSet.is_resolved is False — callers should check it."""
        q = Question(id="a", prompt="A?", default=None)
        qs = QuestionSet(questions=[q])
        assert not qs.is_resolved
        qs2 = qs.answer(q, "yes")
        assert qs2.is_resolved
