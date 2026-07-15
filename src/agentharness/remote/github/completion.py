"""Completion gate — exact-head CI and review state verification."""

from __future__ import annotations

from dataclasses import dataclass

from agentharness.remote.github.reviews import ReviewSignals


@dataclass(frozen=True)
class CompletionDecision:
    """Whether a PR is ready to complete (merge)."""

    is_complete: bool
    blocking_reasons: list[str]


def evaluate_completion(
    signals: ReviewSignals,
    expected_head: str,
) -> CompletionDecision:
    """Evaluate whether *signals* satisfy the completion gate.

    Completion requires ALL of:
    - The PR head SHA matches expected_head (catches stale CI)
    - The PR is approved (not pending/no-decision/changes-requested)
    - No unresolved threads (unacknowledged comments)
    - No failing checks
    """
    reasons: list[str] = []
    if signals.head_sha != expected_head:
        reasons.append(
            f"head SHA mismatch: expected {expected_head!r}, "
            f"got {signals.head_sha!r} (stale CI)"
        )
    if not signals.approved:
        if signals.changes_requested:
            reasons.append("reviewer has requested changes")
        else:
            reasons.append(
                "PR not approved: review is pending or no decision yet"
            )
    if signals.unresolved_thread_count > 0:
        reasons.append(
            f"{signals.unresolved_thread_count} unresolved thread(s) "
            "(unacknowledged comments)"
        )
    if signals.failing_check_count > 0:
        reasons.append(f"{signals.failing_check_count} failing check(s)")
    return CompletionDecision(is_complete=not reasons, blocking_reasons=reasons)
