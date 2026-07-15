"""Integration tests for publish authority boundary (AC-25).

AC-25: Publication checks never broaden publish authority.

Verifies that completion gating decisions report PR readiness (merge-
readiness) only and never imply or grant push/publish authority beyond
what is explicitly configured. Publish authority lives in the
.agentharness-publish-mode flag file (read by `audit --json` as
`publish_mode_active`); it is a separate dimension from PR completion.
"""

from __future__ import annotations

from agentharness.remote.github.completion import (
    evaluate_completion,
)
from agentharness.remote.github.reviews import ReviewSignals


def _signals(
    *,
    approved: bool = True,
    changes_requested: bool = False,
    unresolved_threads: int = 0,
    passing_checks: int = 2,
    failing_checks: int = 0,
    head_sha: str = "abc123",
) -> ReviewSignals:
    return ReviewSignals(
        pr_number=1,
        head_sha=head_sha,
        approved=approved,
        changes_requested=changes_requested,
        unresolved_thread_count=unresolved_threads,
        passing_check_count=passing_checks,
        failing_check_count=failing_checks,
    )


class TestPublishAuthorityNeverBroadened:
    """AC-25: completion decision is PR-readiness only, not authority grant."""

    def test_complete_decision_has_no_authority_grant(self) -> None:
        """A passing completion decision must not add publish_authorized or similar."""
        decision = evaluate_completion(_signals(), expected_head="abc123")
        assert decision.is_complete
        # The decision exposes only is_complete and blocking_reasons —
        # there must be no publish_authority, can_push, or authority fields.
        decision_fields = set(vars(decision).keys())
        authority_fields = {
            f for f in decision_fields
            if any(
                kw in f.lower()
                for kw in ("authority", "publish", "push", "merge_ok")
            )
        }
        assert authority_fields == set(), (
            f"CompletionDecision must not contain authority fields: {authority_fields}"
        )

    def test_incomplete_decision_also_lacks_authority_fields(self) -> None:
        """A blocking decision must also not introduce authority fields."""
        decision = evaluate_completion(
            _signals(approved=False),
            expected_head="abc123",
        )
        assert not decision.is_complete
        decision_fields = set(vars(decision).keys())
        authority_fields = {
            f for f in decision_fields
            if any(
                kw in f.lower()
                for kw in ("authority", "publish", "push", "merge_ok")
            )
        }
        assert authority_fields == set()

    def test_all_clear_does_not_bypass_authority_requirement(self) -> None:
        """is_complete=True means 'PR is ready to merge', not 'agent may push'.

        The distinction: publish authority comes from .agentharness-publish-mode
        (an operator flag), not from PR state. An agent checking completion must
        still check the authority flag independently.
        """
        decision = evaluate_completion(_signals(), expected_head="abc123")
        assert decision.is_complete
        # is_complete is purely a PR-readiness signal
        assert isinstance(decision.is_complete, bool)
        assert isinstance(decision.blocking_reasons, list)
        # No additional fields were added that could imply authority
        expected_fields = {"is_complete", "blocking_reasons"}
        actual_fields = set(vars(decision).keys())
        assert actual_fields == expected_fields, (
            f"CompletionDecision grew unexpected fields: "
            f"{actual_fields - expected_fields}"
        )

    def test_stale_head_blocks_even_with_approvals(self) -> None:
        """A fully-approved PR with stale head must be blocked — not complete."""
        decision = evaluate_completion(
            _signals(approved=True, failing_checks=0),
            expected_head="newer-sha",  # different from signals head_sha
        )
        assert not decision.is_complete
        assert any("stale" in r.lower() or "mismatch" in r.lower() for r in decision.blocking_reasons)  # noqa: E501
