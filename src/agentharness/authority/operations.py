"""Decision logic for authority contracts."""

from __future__ import annotations

import fnmatch
from datetime import UTC, datetime

from agentharness.authority import Contract, Decision, Operation


def decide(
    contract: Contract,
    operation: Operation | str,
    target: str | None = None,
    now: datetime | None = None,
) -> Decision:
    """Evaluate whether an operation is allowed under the contract.

    Args:
        contract: The authority contract to evaluate against.
        operation: The operation name (or Operation enum).
        target: Optional target string (e.g., branch name for push operations).
        now: Current time (defaults to UTC now). Must be timezone-aware.

    Returns:
        Decision with allowed=True if granted, False otherwise.
        On refusal, ``reason`` is a human-readable string: ``"not granted"``,
        ``"revoked"``, ``"grant expired at <timestamp>"``, or
        ``"grant has invalid expiry format: <value>"``.
    """
    if now is None:
        now = datetime.now(UTC)

    # Normalize operation to string
    op_name = (
        operation.value if isinstance(operation, Operation) else str(operation)
    )

    # Check if operation is revoked
    if op_name in contract.revoked:
        return Decision(allowed=False, reason="revoked")

    # Find a matching grant
    for grant in contract.grants:
        if op_name not in grant.operations:
            continue

        # Check target match
        # - If grant has no target restriction, matches any target
        # - If grant specifies target, check if target matches pattern
        # - If grant specifies target but we have no target, skip
        if grant.target is not None:
            if target is None:
                # Grant requires target but checking with none
                continue
            if not fnmatch.fnmatch(target, grant.target):
                # Target doesn't match pattern
                continue

        # Check expiry
        if grant.expires is not None:
            try:
                # Handle 'Z' suffix (ISO 8601 UTC) and explicit '+00:00'
                # fromisoformat doesn't handle 'Z', so normalize
                if grant.expires.endswith("Z"):
                    expires_str = grant.expires.rstrip("Z") + "+00:00"
                else:
                    expires_str = grant.expires
                expires_dt = datetime.fromisoformat(expires_str)
                if now >= expires_dt:
                    return Decision(
                        allowed=False,
                        reason=f"grant expired at {grant.expires}",
                    )
            except (ValueError, TypeError):
                # Invalid expiry format — treat as expired
                return Decision(
                    allowed=False,
                    reason=f"grant has invalid expiry format: {grant.expires}",
                )

        # Grant matches
        return Decision(allowed=True)

    # No matching grant found
    return Decision(allowed=False, reason="not granted")
