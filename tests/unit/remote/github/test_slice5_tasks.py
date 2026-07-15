"""Tests for Tasks 2-7 of Slice 5 (protection, reviews, completion, decommission)."""

from __future__ import annotations

from agentharness.remote.github.completion import (
    evaluate_completion,
)
from agentharness.remote.github.decommission import (
    DecommissionStage,
    DecommissionState,
    advance_decommission,
)
from agentharness.remote.github.models import PRState
from agentharness.remote.github.reviews import ReviewSignals, extract_signals
from agentharness.remote.github.rulesets import build_ruleset_config


class TestReviewSignals:
    def test_approved_pr_has_correct_signals(self) -> None:
        pr = PRState(
            number=1,
            head_sha="abc",
            is_draft=False,
            review_decision="APPROVED",
            unresolved_threads=0,
            passing_checks=["CI"],
            failing_checks=[],
        )
        signals = extract_signals(pr)
        assert signals.approved
        assert not signals.changes_requested
        assert signals.is_completion_eligible

    def test_changes_requested_blocks_completion(self) -> None:
        pr = PRState(
            number=2,
            head_sha="abc",
            is_draft=False,
            review_decision="CHANGES_REQUESTED",
            unresolved_threads=0,
            passing_checks=["CI"],
            failing_checks=[],
        )
        signals = extract_signals(pr)
        assert not signals.is_completion_eligible

    def test_unresolved_threads_block_completion(self) -> None:
        pr = PRState(
            number=3,
            head_sha="abc",
            is_draft=False,
            review_decision="APPROVED",
            unresolved_threads=2,
            passing_checks=["CI"],
            failing_checks=[],
        )
        signals = extract_signals(pr)
        assert not signals.is_completion_eligible


class TestCompletionGate:
    def _make_signals(self, **overrides: object) -> ReviewSignals:
        defaults = {
            "pr_number": 1,
            "head_sha": "expected",
            "approved": True,
            "changes_requested": False,
            "unresolved_thread_count": 0,
            "passing_check_count": 1,
            "failing_check_count": 0,
        }
        defaults.update(overrides)
        return ReviewSignals(**defaults)  # type: ignore[arg-type]

    def test_all_conditions_met_is_complete(self) -> None:
        signals = self._make_signals()
        decision = evaluate_completion(signals, expected_head="expected")
        assert decision.is_complete

    def test_sha_mismatch_blocks(self) -> None:
        signals = self._make_signals(head_sha="wrong")
        decision = evaluate_completion(signals, expected_head="expected")
        assert not decision.is_complete

    def test_not_approved_blocks(self) -> None:
        signals = self._make_signals(approved=False)
        decision = evaluate_completion(signals, expected_head="expected")
        assert not decision.is_complete

    def test_failing_checks_block(self) -> None:
        signals = self._make_signals(failing_check_count=1)
        decision = evaluate_completion(signals, expected_head="expected")
        assert not decision.is_complete

    def test_blocking_reasons_populated(self) -> None:
        signals = self._make_signals(approved=False, failing_check_count=2)
        decision = evaluate_completion(signals, expected_head="expected")
        assert len(decision.blocking_reasons) == 2


class TestDecommissionStateMachine:
    def test_full_happy_path(self) -> None:
        state = DecommissionState(stage=DecommissionStage.NOT_STARTED)
        state = advance_decommission(state, "pr_opened")
        assert state.stage == DecommissionStage.PR1_OPEN
        state = advance_decommission(state, "pr_merged")
        assert state.stage == DecommissionStage.PR1_MERGED
        state = advance_decommission(state, "pr_opened")
        assert state.stage == DecommissionStage.PR2_OPEN
        state = advance_decommission(state, "pr_merged")
        assert state.stage == DecommissionStage.PR2_MERGED
        state = advance_decommission(state, "pr_opened")
        assert state.stage == DecommissionStage.PR3_OPEN
        state = advance_decommission(state, "pr_merged")
        assert state.stage == DecommissionStage.COMPLETE

    def test_invalid_event_does_not_advance(self) -> None:
        state = DecommissionState(stage=DecommissionStage.NOT_STARTED)
        # can't merge without opening first
        new_state = advance_decommission(state, "pr_merged")
        assert new_state.stage == DecommissionStage.NOT_STARTED


class TestRulesets:
    def test_build_ruleset_config(self) -> None:
        cfg = build_ruleset_config("policy-gate", ["CI", "lint"])
        assert cfg.name == "policy-gate"
        assert cfg.enforcement == "active"
        assert "CI" in cfg.required_contexts
