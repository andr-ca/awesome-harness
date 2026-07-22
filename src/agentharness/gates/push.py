"""Push gate — parse Git ref update stdin and validate outgoing revisions."""

from __future__ import annotations

import sys
from pathlib import Path

from agentharness.authority.loader import load_effective_authority
from agentharness.authority.operations import decide
from agentharness.gates.context import PushContext


def read_push_context(repo_root: Path, stdin_text: str | None = None) -> PushContext:
    """Parse Git's pre-push stdin into a PushContext.

    Git passes lines of the form:
        <local-ref> <local-sha> <remote-ref> <remote-sha>

    We record (local_ref, old_sha, new_sha) for each update.
    """
    text = stdin_text if stdin_text is not None else sys.stdin.read()
    updates: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local_ref, local_sha, _remote_ref, remote_sha = parts[:4]
            updates.append((local_ref, remote_sha, local_sha))
    return PushContext(repo_root=repo_root, ref_updates=updates)


def check_authority(
    repo_root: Path, context: PushContext
) -> tuple[bool, str | None]:
    """Check if push operation is authorized under the authority contract.

    Returns:
        (allowed, reason) where allowed is True if push is authorized,
        and reason is None if allowed or a string explaining why if refused.
    """
    try:
        contract = load_effective_authority(repo_root)
    except ValueError:
        # If authority contract is malformed, deny push
        return False, "Failed to load authority contract"

    # Check each ref being pushed
    for local_ref, _, _ in context.ref_updates:
        # Extract branch name from refs/heads/X or use full ref
        branch_target = local_ref
        if local_ref.startswith("refs/heads/"):
            branch_target = local_ref[len("refs/heads/") :]

        decision = decide(contract, "push", branch_target)
        if not decision.allowed:
            return False, decision.reason

    return True, None
