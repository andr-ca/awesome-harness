"""Profile operations — explain and validate the effective profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileExplanation:
    """Human-readable explanation of why a policy applies."""

    requirement_id: str
    gate: str
    mode: str
    rationale: str


def explain_profile(compiled_policy: Any) -> list[ProfileExplanation]:
    """Return human-readable explanations for each requirement in the policy."""
    explanations = []
    for gate_plan in compiled_policy.gate_plans:
        for req in gate_plan.requirements:
            explanations.append(
                ProfileExplanation(
                    requirement_id=req.requirement_id,
                    gate=str(gate_plan.gate),
                    mode=req.mode,
                    rationale=(
                        f"{req.mode.capitalize()} requirement for "
                        f"{req.capability_id}"
                    ),
                )
            )
    return explanations
