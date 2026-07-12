#!/usr/bin/env python3
"""Orchestrates one eval task under baseline (no harness) and treatment
(harness installed via harness-link.sh init) conditions, scores both
with score.py, and appends the results to the ledger.

`invoke_agent_via_api` — the one piece that would drive a live coding
agent against the Anthropic API and spend real money per call — is not
implemented here. `run_condition`'s `invoke_agent` parameter is an
injected dependency precisely so the orchestration logic (condition
setup, scoring, ledger writing) can be exercised in tests with a fake
agent that costs nothing and produces a deterministic result. Actually
running this against the real API is a deliberate, separate step the
user triggers explicitly — see tools/eval/README.md.
"""
import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, NamedTuple

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent.parent
HARNESS_LINK = REPO_ROOT / "tools" / "setup" / "harness-link.sh"

sys.path.insert(0, str(EVAL_ROOT))
from score import load_task, score  # noqa: E402


class AgentResult(NamedTuple):
    output_dir: Path
    cost_usd: float
    model: str


InvokeAgent = Callable[[str, Path, bool], AgentResult]


def invoke_agent_via_api(
    task_prompt: str, workdir: Path, harness_installed: bool
) -> AgentResult:
    """Real implementation: drive a live coding-agent session against the
    Anthropic API, working in `workdir`, then return where its output
    landed and what it cost. Deliberately not implemented — wiring this
    up and spending real API credits is a follow-up the user triggers
    explicitly (see tools/eval/README.md's "Running a real eval"
    section), not something this module does on its own."""
    raise NotImplementedError(
        "invoke_agent_via_api requires ANTHROPIC_API_KEY and spends real money "
        "per call — not implemented here. See tools/eval/README.md."
    )


def run_condition(
    task_id: str, condition: str, invoke_agent: InvokeAgent
) -> dict:
    """Set up one condition (baseline or treatment) for task_id, hand it
    to invoke_agent, score the result, and return a ledger entry. Pass a
    fake invoke_agent in tests; this function itself makes no network
    calls."""
    if condition not in ("baseline", "treatment"):
        raise ValueError(f"condition must be 'baseline' or 'treatment', got {condition!r}")

    task_dir = EVAL_ROOT / "tasks" / task_id
    task = load_task(task_dir)
    harness_installed = condition == "treatment"

    workdir = Path(tempfile.mkdtemp(prefix=f"agentharness-eval-{condition}-"))
    try:
        shutil.copytree(task_dir / "starter", workdir, dirs_exist_ok=True)
        if harness_installed:
            subprocess.run(
                ["bash", str(HARNESS_LINK), "init", str(workdir)],
                check=True,
                capture_output=True,
                text=True,
            )

        agent_result = invoke_agent(task["prompt"], workdir, harness_installed)
        result = score(task_dir, agent_result.output_dir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return {
        "date": datetime.date.today().isoformat(),
        "task": task_id,
        "condition": condition,
        "score": result["overall_score"],
        "cost": agent_result.cost_usd,
        "model": agent_result.model,
    }


def append_to_ledger(entry: dict, ledger_path: Path) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Task id under tools/eval/tasks/")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=EVAL_ROOT / "results" / "ledger.jsonl",
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
