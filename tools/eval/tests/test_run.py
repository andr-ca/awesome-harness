"""Tests for tools/eval/run.py's orchestration logic — condition setup,
scoring, and ledger writing — using a fake `invoke_agent` that costs
nothing and makes no network calls. invoke_agent_via_api (the real,
API-calling implementation) is intentionally not exercised here; see
its own docstring in run.py."""
import json
import shutil
import sys
from pathlib import Path

import pytest

EVAL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_ROOT))

import run as run_module  # noqa: E402
from run import AgentResult, append_to_ledger, run_condition  # noqa: E402

TASK_ID = "python-input-validation"


def _fake_agent_copying(fixture: str):
    """Return an invoke_agent stand-in that overwrites the starter's
    entry_module with the given hand-written fixture, simulating "the
    agent produced this file" without calling anything."""

    def _invoke(task_prompt: str, workdir: Path, harness_installed: bool) -> AgentResult:
        src = EVAL_ROOT / "fixtures" / TASK_ID / fixture / "discount.py"
        shutil.copy(src, workdir / "discount.py")
        return AgentResult(output_dir=workdir, cost_usd=0.01, model="fake-model-v1")

    return _invoke


def test_run_condition_baseline_scores_a_correct_candidate():
    entry = run_condition(TASK_ID, "baseline", _fake_agent_copying("correct"))
    assert entry["task"] == TASK_ID
    assert entry["condition"] == "baseline"
    assert entry["score"] == 1.0
    assert entry["cost"] == 0.01
    assert entry["model"] == "fake-model-v1"
    assert entry["date"]


def test_run_condition_scores_a_broken_candidate_below_one():
    entry = run_condition(TASK_ID, "baseline", _fake_agent_copying("broken"))
    assert entry["score"] < 1.0


def test_run_condition_treatment_installs_the_harness_before_invoking_agent():
    seen = {}

    def _invoke(task_prompt: str, workdir: Path, harness_installed: bool) -> AgentResult:
        seen["harness_installed_flag"] = harness_installed
        seen["claude_dir_exists"] = (workdir / ".claude" / "skills").is_dir()
        shutil.copy(
            EVAL_ROOT / "fixtures" / TASK_ID / "correct" / "discount.py",
            workdir / "discount.py",
        )
        return AgentResult(output_dir=workdir, cost_usd=0.0, model="fake")

    entry = run_condition(TASK_ID, "treatment", _invoke)
    assert seen["harness_installed_flag"] is True
    assert seen["claude_dir_exists"] is True
    assert entry["condition"] == "treatment"


def test_run_condition_baseline_does_not_install_the_harness():
    seen = {}

    def _invoke(task_prompt: str, workdir: Path, harness_installed: bool) -> AgentResult:
        seen["claude_dir_exists"] = (workdir / ".claude").exists()
        shutil.copy(
            EVAL_ROOT / "fixtures" / TASK_ID / "correct" / "discount.py",
            workdir / "discount.py",
        )
        return AgentResult(output_dir=workdir, cost_usd=0.0, model="fake")

    run_condition(TASK_ID, "baseline", _invoke)
    assert seen["claude_dir_exists"] is False


def test_run_condition_rejects_an_unknown_condition():
    with pytest.raises(ValueError, match="condition must be"):
        run_condition(TASK_ID, "bogus", _fake_agent_copying("correct"))


def test_append_to_ledger_writes_one_json_line_per_call(tmp_path):
    ledger = tmp_path / "nested" / "ledger.jsonl"
    append_to_ledger({"a": 1}, ledger)
    append_to_ledger({"a": 2}, ledger)

    lines = ledger.read_text().splitlines()
    assert [json.loads(line) for line in lines] == [{"a": 1}, {"a": 2}]


def test_invoke_agent_via_api_is_not_implemented():
    with pytest.raises(NotImplementedError):
        run_module.invoke_agent_via_api("prompt", Path("/tmp"), False)


def test_main_refuses_to_run_without_a_real_agent(capsys, monkeypatch):
    # main() parses --task from sys.argv; supply one so argparse doesn't
    # fail the test for an unrelated reason (missing required arg).
    monkeypatch.setattr(sys, "argv", ["run.py", "--task", TASK_ID])
    exit_code = run_module.main()
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not wired to call a live agent" in captured.err
