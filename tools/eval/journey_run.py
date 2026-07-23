#!/usr/bin/env python3
"""Orchestrates one journey eval scenario, invokes a session producer,
scores the result with journey_score.py, and appends to the ledger.

`invoke_agent_via_api` — the one piece that would drive a live coding
agent against the Anthropic API and produce a session recording, then
spend real money per call — is not implemented here. `run_scenario`'s
`invoke_agent` parameter is an injected dependency precisely so the
orchestration logic (scenario setup, scoring, ledger writing) can be
exercised in tests with a fake agent that costs nothing and produces a
deterministic result. Actually running this against the real API is a
deliberate, separate step the user triggers explicitly — see
tools/eval/README.md.
"""
import argparse
import datetime
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

EVAL_ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(EVAL_ROOT))
from journey_score import load_rubric, score  # noqa: E402


class SessionResult(NamedTuple):
    """Result of invoking an agent to produce a session record."""

    record_path: Path
    cost_usd: float
    model: str


# Mirrors run.py's InvokeAgent seam: (scenario_id, scenario_dir,
# harness_installed) -> SessionResult. The harness_installed flag lets the
# same injected producer run a scenario under baseline (harness off) and
# treatment (harness on) so the two can be compared.
InvokeAgent = Callable[[str, Path, bool], SessionResult]


def invoke_agent_via_api(
    scenario_id: str, scenario_dir: Path, harness_installed: bool
) -> SessionResult:
    """Real implementation: drive a live coding-agent session against the
    Anthropic API, have it record its own session.json, then return where
    the record landed and what it cost. Deliberately not implemented — wiring
    this up and spending real API credits is a follow-up the user triggers
    explicitly (see tools/eval/README.md's "Running a real eval"
    section), not something this module does on its own."""
    raise NotImplementedError(
        "invoke_agent_via_api requires ANTHROPIC_API_KEY and spends real money "
        "per call — not implemented here. See tools/eval/README.md."
    )


def run_scenario(
    scenario_id: str, condition: str, invoke_agent: InvokeAgent
) -> dict:
    """Set up one scenario under `condition` ('baseline' or 'treatment'),
    hand it to invoke_agent to produce a session record, score it with
    journey_score.score, and return a ledger entry. Pass a fake invoke_agent
    in tests; this function itself makes no network calls."""
    if condition not in ("baseline", "treatment"):
        raise ValueError(
            f"condition must be 'baseline' or 'treatment', got {condition!r}"
        )
    scenario_dir = EVAL_ROOT / "scenarios" / scenario_id
    if not scenario_dir.is_dir():
        raise ValueError(f"scenario directory not found: {scenario_dir}")

    # Load scenario metadata
    rubric = load_rubric(scenario_dir)

    # Invoke agent to produce a session record. treatment = harness installed.
    harness_installed = condition == "treatment"
    agent_result = invoke_agent(scenario_id, scenario_dir, harness_installed)

    # Load and score the session
    from journey_score import load_session  # noqa: E402

    session = load_session(agent_result.record_path)
    result = score(session, rubric)

    return {
        "date": datetime.date.today().isoformat(),
        "scenario": scenario_id,
        "condition": condition,
        "overall_score": result["overall_score"],
        "cost": agent_result.cost_usd,
        "model": agent_result.model,
        "metrics": {
            "corrective_prompts": result["corrective_prompts"],
            "implementation_attempts": result["implementation_attempts"],
            "human_interventions": result["human_interventions"],
            "plan_to_code_divergence": result["plan_to_code_divergence"],
            "cost_usd": result["cost_usd"],
        },
    }


def append_to_ledger(entry: dict, ledger_path: Path) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", required=True, help="Scenario id under tools/eval/scenarios/"
    )
    parser.add_argument(
        "--condition",
        choices=("baseline", "treatment"),
        default="treatment",
        help="Run the scenario with the harness off (baseline) or on (treatment)",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=EVAL_ROOT / "results" / "journey-ledger.jsonl",
        help="JSON-lines file to append results to",
    )
    parser.parse_args()

    print(
        "This CLI is not wired to call a live agent — invoke_agent_via_api is "
        "deliberately unimplemented (it would need ANTHROPIC_API_KEY and spend "
        "real money per call). See tools/eval/README.md for the opt-in this "
        "needs before a real eval run happens.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
