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

    Completion requires:
    - The PR's head SHA matches *expected_head*
    - The PR is approved
    - No changes requested
    - No unresolved threads
    - No failing checks
    """
    reasons: list[str] = []
    if signals.head_sha != expected_head:
        reasons.append(
            f"head SHA mismatch: expected {expected_head!r}, "
            f"got {signals.head_sha!r}"
        )
    if not signals.approved:
        reasons.append("PR has not been approved")
    if signals.changes_requested:
        reasons.append("reviewer has requested changes")
    if signals.unresolved_thread_count > 0:
        reasons.append(
            f"{signals.unresolved_thread_count} unresolved thread(s)"
        )
    if signals.failing_check_count > 0:
        reasons.append(
            f"{signals.failing_check_count} failing check(s)"
        )
    return CompletionDecision(is_complete=not reasons, blocking_reasons=reasons)
