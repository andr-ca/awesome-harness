"""Policy compiler — transforms declared requirements into deterministic gate plans.

The compiler is a pure function: given the same requirements, it always
produces the same EffectivePolicy with the same hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from agentharness.policy.results import (
    CompiledRequirement,
    EffectivePolicy,
    GateKind,
    GatePlan,
)
from agentharness.policy.scope import ScopeExpression

_COMPILER_VERSION = "0.1.0"

# Capability prefixes that are too expensive to run at fast (commit/push) gates.
# Assigning one of these to COMMIT or PUSH raises CompileError (AC-17).
_EXPENSIVE_ONLY_PREFIXES: frozenset[str] = frozenset(
    [
        "python.mutation",
    ]
)

# Gates where expensive-only capabilities are allowed.
_EXPENSIVE_GATES: frozenset[GateKind] = frozenset(
    [GateKind.CI, GateKind.COMPLETION]
)


class CompileError(ValueError):
    """Raised when the policy cannot be compiled."""


@dataclass(frozen=True)
class PolicyRequirement:
    """A single declared requirement to be compiled into a gate plan."""

    requirement_id: str
    gate: GateKind
    capability_id: str
    mode: str  # "strict", "warn", "grace"
    scope: ScopeExpression


def compile_policy(requirements: list[PolicyRequirement]) -> EffectivePolicy:
    """Compile *requirements* into a deterministic EffectivePolicy.

    Raises CompileError if:
    - requirements is empty
    - any two requirements share the same requirement_id

    Sorting is by (gate, requirement_id) — stable across process restarts.
    """
    if not requirements:
        raise CompileError("cannot compile an empty requirement list")

    seen_ids: set[str] = set()
    for req in requirements:
        if req.requirement_id in seen_ids:
            raise CompileError(
                f"duplicate requirement id: {req.requirement_id!r}"
            )
        seen_ids.add(req.requirement_id)
        # AC-17: expensive-only capabilities must not appear at fast gates.
        if req.gate not in _EXPENSIVE_GATES:
            for prefix in _EXPENSIVE_ONLY_PREFIXES:
                if req.capability_id == prefix or req.capability_id.startswith(
                    f"{prefix}."
                ):
                    raise CompileError(
                        f"capability {req.capability_id!r} is expensive and "
                        f"may only be assigned to gates"
                        f" {sorted(_EXPENSIVE_GATES)} "
                        f"(assigned to {req.gate!r}"
                        f" in requirement {req.requirement_id!r})"
                    )

    # Group by gate kind
    by_gate: dict[GateKind, list[PolicyRequirement]] = {
        g: [] for g in GateKind
    }
    for req in requirements:
        by_gate[req.gate].append(req)

    # Build gate plans — only include gates that have at least one requirement
    gate_plans: list[GatePlan] = []
    for gate_kind in sorted(GateKind):
        gate_reqs = sorted(by_gate[gate_kind], key=lambda r: r.requirement_id)
        if not gate_reqs:
            continue
        compiled = [
            CompiledRequirement(
                requirement_id=r.requirement_id,
                capability_id=r.capability_id,
                mode=r.mode,
                scope=r.scope,
            )
            for r in gate_reqs
        ]
        gate_plans.append(GatePlan(gate=gate_kind, requirements=compiled))

    canonical = _canonical_json(gate_plans)
    policy_hash = hashlib.sha256(canonical.encode()).hexdigest()

    return EffectivePolicy(policy_hash=policy_hash, gate_plans=gate_plans)


def _canonical_json(gate_plans: list[GatePlan]) -> str:
    """Produce a deterministic JSON representation of the gate plans."""
    data = {
        "compiler_version": _COMPILER_VERSION,
        "gates": [
            {
                "gate": str(plan.gate),
                "requirements": [
                    {
                        "id": req.requirement_id,
                        "capability": req.capability_id,
                        "mode": req.mode,
                        "includes": [
                            p.pattern for p in req.scope.includes
                        ],
                        "excludes": [
                            p.pattern for p in req.scope.excludes
                        ],
                    }
                    for req in plan.requirements
                ],
            }
            for plan in gate_plans
        ],
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
