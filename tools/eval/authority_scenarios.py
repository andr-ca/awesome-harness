"""Deterministic test scenarios for authority contract evaluation.

This module provides a set of fixed test cases (scenarios) that verify
the authority decision logic works correctly in key use cases.
No API calls, no random state — just test cases and a scorer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from agentharness.authority import Contract, Grant, Operation
from agentharness.authority.operations import decide


class AuthorityScenario(NamedTuple):
    """A single authority test scenario."""

    name: str
    contract: Contract
    operation: str
    target: str | None
    now: datetime
    expected_allowed: bool
    expected_reason: str | None


def _now() -> datetime:
    """Current time for scenario tests (fixed, not live)."""
    return datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)


def _future(hours: int = 1) -> str:
    """ISO 8601 timestamp N hours from now()."""
    dt = _now() + timedelta(hours=hours)
    return dt.replace(microsecond=0).isoformat()


def _past(hours: int = 1) -> str:
    """ISO 8601 timestamp N hours ago."""
    dt = _now() - timedelta(hours=hours)
    return dt.replace(microsecond=0).isoformat()


AUTHORITY_SCENARIOS: list[AuthorityScenario] = [
    # Basic allow/deny
    AuthorityScenario(
        name="empty_contract_denies_push",
        contract=Contract(
            schema_version=1,
            grants=(),
            revoked=(),
        ),
        operation="push",
        target=None,
        now=_now(),
        expected_allowed=False,
        expected_reason="not granted",
    ),
    AuthorityScenario(
        name="single_grant_allows_operation",
        contract=Contract(
            schema_version=1,
            grants=(Grant(operations=(Operation.PUSH,)),),
            revoked=(),
        ),
        operation="push",
        target=None,
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    # Target matching
    AuthorityScenario(
        name="grant_with_wildcard_target_matches_branch",
        contract=Contract(
            schema_version=1,
            grants=(Grant(operations=(Operation.PUSH,), target="fix/*"),),
            revoked=(),
        ),
        operation="push",
        target="fix/bug-123",
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    AuthorityScenario(
        name="grant_with_wildcard_target_rejects_other_branch",
        contract=Contract(
            schema_version=1,
            grants=(Grant(operations=(Operation.PUSH,), target="fix/*"),),
            revoked=(),
        ),
        operation="push",
        target="feature/x",
        now=_now(),
        expected_allowed=False,
        expected_reason="not granted",
    ),
    AuthorityScenario(
        name="grant_without_target_matches_any_target",
        contract=Contract(
            schema_version=1,
            grants=(Grant(operations=(Operation.PUSH,), target=None),),
            revoked=(),
        ),
        operation="push",
        target="anything",
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    # Expiry
    AuthorityScenario(
        name="grant_expires_at_specified_time",
        contract=Contract(
            schema_version=1,
            grants=(Grant(operations=(Operation.PUSH,), expires=_future(hours=2)),),
            revoked=(),
        ),
        operation="push",
        target=None,
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    AuthorityScenario(
        name="grant_denied_after_expiry",
        contract=Contract(
            schema_version=1,
            grants=(Grant(operations=(Operation.PUSH,), expires=_past(hours=1)),),
            revoked=(),
        ),
        operation="push",
        target=None,
        now=_now(),
        expected_allowed=False,
        expected_reason=None,
    ),
    # Revocation
    AuthorityScenario(
        name="revoked_operation_denied_even_if_granted",
        contract=Contract(
            schema_version=1,
            grants=(
                Grant(
                    operations=(Operation.PUSH, Operation.COMMIT),
                ),
            ),
            revoked=("push",),
        ),
        operation="push",
        target=None,
        now=_now(),
        expected_allowed=False,
        expected_reason="revoked",
    ),
    AuthorityScenario(
        name="non_revoked_operation_allowed",
        contract=Contract(
            schema_version=1,
            grants=(
                Grant(
                    operations=(Operation.PUSH, Operation.COMMIT),
                ),
            ),
            revoked=("push",),
        ),
        operation="commit",
        target=None,
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    # Complex scenario: scoped, expiring grant
    AuthorityScenario(
        name="real_scenario_push_fix_until_tomorrow",
        contract=Contract(
            schema_version=1,
            grants=(
                Grant(
                    operations=(Operation.PUSH,),
                    target="fix/*",
                    expires=_future(hours=24),
                    granted_by="andrey (session 2026-07-22)",
                ),
            ),
            revoked=(),
        ),
        operation="push",
        target="fix/bug-123",
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    AuthorityScenario(
        name="real_scenario_push_main_denied",
        contract=Contract(
            schema_version=1,
            grants=(
                Grant(
                    operations=(Operation.PUSH,),
                    target="fix/*",
                    expires=_future(hours=24),
                ),
            ),
            revoked=(),
        ),
        operation="push",
        target="main",
        now=_now(),
        expected_allowed=False,
        expected_reason="not granted",
    ),
    # Multiple operations
    AuthorityScenario(
        name="grant_multiple_operations",
        contract=Contract(
            schema_version=1,
            grants=(
                Grant(
                    operations=(Operation.PUSH, Operation.COMMIT, Operation.PR_CREATE),
                ),
            ),
            revoked=(),
        ),
        operation="pr-create",
        target=None,
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
    # Backward compat: contract overrides flag
    AuthorityScenario(
        name="backward_compat_flag_grants_all_operations",
        contract=Contract(
            schema_version=1,
            grants=(
                Grant(
                    operations=(
                        Operation.COMMIT,
                        Operation.PUSH,
                        Operation.PR_CREATE,
                        Operation.PR_MERGE,
                        Operation.ISSUE_CREATE,
                        Operation.FS_WRITE_OUTSIDE_REPO,
                        Operation.EXTERNAL_MESSAGE,
                        Operation.DESTRUCTIVE_FS,
                    ),
                    granted_by=".agentharness-publish-mode flag",
                ),
            ),
            revoked=(),
        ),
        operation="push",
        target="anything",
        now=_now(),
        expected_allowed=True,
        expected_reason=None,
    ),
]


def score_scenarios() -> dict[str, bool]:
    """Score all authority scenarios.

    Returns:
        dict of {scenario_name: passed}
    """
    results: dict[str, bool] = {}

    for scenario in AUTHORITY_SCENARIOS:
        decision = decide(
            scenario.contract, scenario.operation, scenario.target, scenario.now
        )

        # Check allowed
        if decision.allowed != scenario.expected_allowed:
            results[scenario.name] = False
            continue

        # Check reason if provided
        if scenario.expected_reason is not None:
            if decision.reason != scenario.expected_reason:
                results[scenario.name] = False
                continue

        results[scenario.name] = True

    return results


if __name__ == "__main__":
    import json

    results = score_scenarios()
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Authority scenarios: {passed}/{total} passed")
    if passed < total:
        print("\nFailed scenarios:")
        for name, result in results.items():
            if not result:
                print(f"  - {name}")
    print(json.dumps(results, indent=2))

    import sys

    sys.exit(0 if passed == total else 1)
