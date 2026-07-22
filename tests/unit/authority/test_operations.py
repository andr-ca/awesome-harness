"""Tests for authority decision logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agentharness.authority import Contract, Grant, Operation
from agentharness.authority.operations import decide


class TestDecideBasics:
    """Test basic allow/deny decisions."""

    def test_empty_contract_denies_all(self) -> None:
        """Empty contract grants nothing."""
        contract = Contract(schema_version=1, grants=(), revoked=())
        decision = decide(contract, "push")
        assert not decision.allowed
        assert decision.reason == "not granted"

    def test_single_grant_allows_operation(self) -> None:
        """A grant of 'push' allows push operations."""
        grant = Grant(operations=(Operation.PUSH,))
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        decision = decide(contract, "push")
        assert decision.allowed
        assert decision.reason is None

    def test_operation_not_in_grant(self) -> None:
        """Operation not in any grant is denied."""
        grant = Grant(operations=(Operation.PUSH,))
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        decision = decide(contract, "commit")
        assert not decision.allowed
        assert decision.reason == "not granted"

    def test_multiple_operations_in_grant(self) -> None:
        """Grant with multiple operations allows all of them."""
        grant = Grant(operations=(Operation.PUSH, Operation.COMMIT))
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        assert decide(contract, "push").allowed
        assert decide(contract, "commit").allowed
        assert not decide(contract, "pr-create").allowed


class TestTargetMatching:
    """Test target pattern matching with fnmatch."""

    def test_target_none_matches_any_target(self) -> None:
        """Grant with no target matches any target."""
        grant = Grant(operations=(Operation.PUSH,), target=None)
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        assert decide(contract, "push", target="main").allowed
        assert decide(contract, "push", target="fix/x").allowed
        assert decide(contract, "push", target="").allowed

    def test_exact_target_match(self) -> None:
        """Exact target string matches."""
        grant = Grant(operations=(Operation.PUSH,), target="main")
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        assert decide(contract, "push", target="main").allowed
        assert not decide(contract, "push", target="develop").allowed

    def test_wildcard_target_match(self) -> None:
        """Wildcard patterns match targets."""
        grant = Grant(operations=(Operation.PUSH,), target="fix/*")
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        assert decide(contract, "push", target="fix/x").allowed
        assert decide(contract, "push", target="fix/bug-123").allowed
        assert not decide(contract, "push", target="feature/x").allowed

    def test_operation_target_none_with_grant_target_requires_no_match(self) -> None:
        """When target is None but grant has target, grant is skipped."""
        grant = Grant(operations=(Operation.PUSH,), target="main")
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        # No target provided to decide, grant requires "main", so no match
        decision = decide(contract, "push", target=None)
        # The grant specifies target="main" and we passed target=None, so fnmatch
        # is never called. We skip the grant and find no other match.
        assert not decision.allowed


class TestExpiry:
    """Test grant expiry logic."""

    def test_grant_without_expiry_never_expires(self) -> None:
        """Grant with no expiry is always valid."""
        grant = Grant(operations=(Operation.PUSH,), expires=None)
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        now = datetime.now(UTC)
        decision = decide(contract, "push", now=now)
        assert decision.allowed

    def test_grant_expires_at_time(self) -> None:
        """Grant expires at the specified time."""
        future = datetime.now(UTC) + timedelta(hours=1)
        expires = future.replace(microsecond=0).isoformat()
        grant = Grant(operations=(Operation.PUSH,), expires=expires)
        contract = Contract(schema_version=1, grants=(grant,), revoked=())

        # Before expiry: allowed
        before = future - timedelta(minutes=1)
        assert decide(contract, "push", now=before).allowed

        # At expiry: denied (>= check)
        at_time = future
        decision = decide(contract, "push", now=at_time)
        assert not decision.allowed
        assert "expired" in decision.reason

        # After expiry: denied
        after = future + timedelta(minutes=1)
        assert not decide(contract, "push", now=after).allowed

    def test_expiry_with_z_suffix(self) -> None:
        """Expiry string with 'Z' suffix (ISO 8601 UTC) is handled."""
        future = datetime.now(UTC) + timedelta(hours=1)
        # Create a timestamp without the timezone suffix, then add 'Z'
        expires = future.replace(microsecond=0, tzinfo=None).isoformat() + "Z"
        grant = Grant(operations=(Operation.PUSH,), expires=expires)
        contract = Contract(schema_version=1, grants=(grant,), revoked=())

        before = future - timedelta(minutes=1)
        assert decide(contract, "push", now=before).allowed

    def test_invalid_expiry_format_treated_as_expired(self) -> None:
        """Invalid expiry format is treated as already expired."""
        grant = Grant(operations=(Operation.PUSH,), expires="not-a-timestamp")
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        decision = decide(contract, "push")
        assert not decision.allowed
        assert "invalid" in decision.reason


class TestRevocation:
    """Test operation revocation."""

    def test_revoked_operation_denied_even_if_granted(self) -> None:
        """Revoked operation is denied even if a grant lists it."""
        grant = Grant(operations=(Operation.PUSH, Operation.COMMIT))
        contract = Contract(
            schema_version=1, grants=(grant,), revoked=("push",)
        )
        assert not decide(contract, "push").allowed
        assert decide(contract, "commit").allowed

    def test_multiple_revocations(self) -> None:
        """Multiple operations can be revoked."""
        grant = Grant(
            operations=(
                Operation.PUSH,
                Operation.COMMIT,
                Operation.PR_CREATE,
            )
        )
        contract = Contract(
            schema_version=1,
            grants=(grant,),
            revoked=("push", "commit"),
        )
        assert not decide(contract, "push").allowed
        assert not decide(contract, "commit").allowed
        assert decide(contract, "pr-create").allowed


class TestComplexScenarios:
    """Test complex, multi-grant scenarios."""

    def test_multiple_grants_same_operation_different_targets(self) -> None:
        """Multiple grants can refine the same operation on different targets."""
        grant1 = Grant(operations=(Operation.PUSH,), target="main")
        grant2 = Grant(operations=(Operation.PUSH,), target="fix/*")
        contract = Contract(schema_version=1, grants=(grant1, grant2), revoked=())

        assert decide(contract, "push", target="main").allowed
        assert decide(contract, "push", target="fix/x").allowed
        assert not decide(contract, "push", target="develop").allowed

    def test_grant_with_all_fields(self) -> None:
        """Grant with all optional fields works correctly."""
        future = datetime.now(UTC) + timedelta(hours=1)
        expires = future.replace(microsecond=0).isoformat()
        grant = Grant(
            operations=(Operation.PUSH,),
            target="fix/*",
            expires=expires,
            granted_by="operator (session 2026-07-22)",
        )
        contract = Contract(schema_version=1, grants=(grant,), revoked=())

        # Should match: operation, target, not expired
        assert decide(contract, "push", target="fix/bug-123").allowed

        # Should not match: target doesn't match
        assert not decide(contract, "push", target="feature/x").allowed

    def test_scenario_push_with_expiry_and_target(self) -> None:
        """Real scenario: push on fix/* until tomorrow."""
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        expires = tomorrow.replace(microsecond=0).isoformat()

        grant = Grant(
            operations=(Operation.PUSH,),
            target="fix/*",
            expires=expires,
            granted_by="andrey (session 2026-07-22)",
        )
        contract = Contract(schema_version=1, grants=(grant,), revoked=())

        # Push to fix/bug-123 should be allowed
        assert decide(contract, "push", target="fix/bug-123").allowed

        # Push to main should be denied
        assert not decide(contract, "push", target="main").allowed

        # Push to feature/x should be denied (wrong target)
        assert not decide(contract, "push", target="feature/x").allowed


class TestOperationNormalization:
    """Test that operations can be passed as strings or enum values."""

    def test_string_operation_name(self) -> None:
        """String operation names work."""
        grant = Grant(operations=(Operation.PUSH,))
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        assert decide(contract, "push").allowed

    def test_enum_operation(self) -> None:
        """Operation enum values work."""
        grant = Grant(operations=(Operation.PUSH,))
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        assert decide(contract, Operation.PUSH).allowed


class TestDecisionReason:
    """Test that decision reasons are informative."""

    def test_not_granted_reason(self) -> None:
        """'not granted' reason when no matching grant."""
        contract = Contract(schema_version=1, grants=(), revoked=())
        decision = decide(contract, "push")
        assert decision.reason == "not granted"

    def test_revoked_reason(self) -> None:
        """'revoked' reason when operation is revoked."""
        grant = Grant(operations=(Operation.PUSH,))
        contract = Contract(
            schema_version=1, grants=(grant,), revoked=("push",)
        )
        decision = decide(contract, "push")
        assert decision.reason == "revoked"

    def test_expired_reason(self) -> None:
        """Expired reason includes expiry time."""
        past = datetime.now(UTC) - timedelta(hours=1)
        expires = past.replace(microsecond=0).isoformat()
        grant = Grant(operations=(Operation.PUSH,), expires=expires)
        contract = Contract(schema_version=1, grants=(grant,), revoked=())
        decision = decide(contract, "push")
        assert "expired" in decision.reason
        assert expires in decision.reason
