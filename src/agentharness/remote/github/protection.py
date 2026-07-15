"""GitHub branch protection — read, plan, apply, and verify."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agentharness.remote.github.models import ProtectionPlan, ProtectionState

if TYPE_CHECKING:
    from agentharness.remote.github.api import GitHubClient


@dataclass(frozen=True)
class ReconcileResult:
    """The result of a protection reconciliation operation."""

    plan: ProtectionPlan
    applied: bool
    current_state: ProtectionState | None
    matches_plan: bool


def plan_protection(
    desired: ProtectionPlan,
    current: ProtectionState | None,
) -> ReconcileResult:
    """Compute whether the desired protection matches the current state."""
    if current is None:
        return ReconcileResult(
            plan=desired,
            applied=False,
            current_state=None,
            matches_plan=False,
        )

    matches = (
        current.is_protected
        and current.required_approvals >= desired.required_approvals
        and current.dismiss_stale_reviews == desired.dismiss_stale_reviews
        and current.require_code_owner_reviews
        >= desired.require_code_owner_reviews
        and all(
            ctx in current.required_contexts
            for ctx in desired.required_contexts
        )
    )
    return ReconcileResult(
        plan=desired,
        applied=False,
        current_state=current,
        matches_plan=matches,
    )


def apply_protection(
    client: GitHubClient,
    owner: str,
    repo: str,
    plan: ProtectionPlan,
) -> ReconcileResult:
    """Apply *plan* to the GitHub branch and read back the result.

    Writes only the fields declared in *plan*; unrelated settings are
    preserved.  Raises APIError if the write or read-back fails.
    """
    path = f"/repos/{owner}/{repo}/branches/{plan.branch}/protection"
    body = {
        "required_pull_request_reviews": {
            "required_approving_review_count": plan.required_approvals,
            "dismiss_stale_reviews": plan.dismiss_stale_reviews,
            "require_code_owner_reviews": plan.require_code_owner_reviews,
        },
        "required_status_checks": {
            "strict": True,
            "contexts": plan.required_contexts,
        },
        "enforce_admins": True,
        "restrictions": None,
    }
    client.put(path, body)

    # Read back to verify
    result = client.get(path)
    reviews = result.get("required_pull_request_reviews") or {}
    checks = result.get("required_status_checks") or {}
    current = ProtectionState(
        branch=plan.branch,
        is_protected=True,
        required_approvals=reviews.get("required_approving_review_count", 0),
        dismiss_stale_reviews=reviews.get("dismiss_stale_reviews", False),
        require_code_owner_reviews=reviews.get("require_code_owner_reviews", False),
        required_contexts=checks.get("contexts", []),
    )
    return plan_protection(plan, current)
