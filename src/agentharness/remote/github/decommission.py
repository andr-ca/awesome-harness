"""Protected three-PR decommission state machine.

Decommission proceeds through three PRs:
  1. PR 1: Remove policy requirements from the committed profile
  2. PR 2: Remove policy gates from GitHub (branch protection, workflows)
  3. PR 3: Archive operational history

Each PR must complete before the next is opened.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DecommissionStage(StrEnum):
    NOT_STARTED = "not_started"
    PR1_OPEN = "pr1_open"
    PR1_MERGED = "pr1_merged"
    PR2_OPEN = "pr2_open"
    PR2_MERGED = "pr2_merged"
    PR3_OPEN = "pr3_open"
    COMPLETE = "complete"


@dataclass(frozen=True)
class DecommissionState:
    """The current state of the decommission process."""

    stage: DecommissionStage
    pr1_number: int | None = None
    pr2_number: int | None = None
    pr3_number: int | None = None


def advance_decommission(state: DecommissionState, event: str) -> DecommissionState:
    """Advance the decommission state machine on *event*.

    Valid events: "pr_opened", "pr_merged"

    Raises ValueError on invalid transitions — the decommission machine
    is fail-closed: an unexpected event is an error, not a no-op.
    """
    if state.stage == DecommissionStage.NOT_STARTED and event == "pr_opened":
        return DecommissionState(stage=DecommissionStage.PR1_OPEN)
    if state.stage == DecommissionStage.PR1_OPEN and event == "pr_merged":
        return DecommissionState(stage=DecommissionStage.PR1_MERGED)
    if state.stage == DecommissionStage.PR1_MERGED and event == "pr_opened":
        return DecommissionState(stage=DecommissionStage.PR2_OPEN)
    if state.stage == DecommissionStage.PR2_OPEN and event == "pr_merged":
        return DecommissionState(stage=DecommissionStage.PR2_MERGED)
    if state.stage == DecommissionStage.PR2_MERGED and event == "pr_opened":
        return DecommissionState(stage=DecommissionStage.PR3_OPEN)
    if state.stage == DecommissionStage.PR3_OPEN and event == "pr_merged":
        return DecommissionState(stage=DecommissionStage.COMPLETE)
    raise ValueError(
        f"Invalid decommission transition: {event!r} from stage {state.stage!r}. "
        "Decommission is fail-closed — unexpected events are errors."
    )
