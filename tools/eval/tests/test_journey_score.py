"""Tests for tools/eval/journey_score.py against hand-written correct/violating
scenario sessions — the scorer itself makes no LLM calls, so these are ordinary
deterministic unit tests, not evals."""
import sys
from pathlib import Path

import pytest

EVAL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_ROOT))

from journey_run import SessionResult, run_scenario  # noqa: E402
from journey_score import load_rubric, load_session, score  # noqa: E402

SCENARIOS = [
    "skill-triggering",
    "refuse-publish-without-authority",
    "preserve-existing-hooks",
]


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_correct_scenario_scores_perfectly(scenario_id):
    """Correct scenario sessions should achieve overall_score == 1.0."""
    scenario_dir = EVAL_ROOT / "scenarios" / scenario_id
    session_path = scenario_dir / "correct" / "session.json"

    session = load_session(session_path)
    rubric = load_rubric(scenario_dir)
    result = score(session, rubric)

    msg = f"Scenario {scenario_id} correct session should score 1.0"
    assert result["overall_score"] == 1.0, msg


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_violating_scenario_scores_below_perfect(scenario_id):
    """Violating scenario sessions should achieve overall_score < 1.0."""
    scenario_dir = EVAL_ROOT / "scenarios" / scenario_id
    session_path = scenario_dir / "violating" / "session.json"

    session = load_session(session_path)
    rubric = load_rubric(scenario_dir)
    result = score(session, rubric)

    msg = f"Scenario {scenario_id} violating session should score < 1.0"
    assert result["overall_score"] < 1.0, msg


def test_run_scenario_with_fake_agent():
    """run_scenario with a fake invoke_agent produces a ledger entry end-to-end."""

    def _fake_agent(
        scenario_id: str, scenario_dir: Path, harness_installed: bool
    ) -> SessionResult:
        """Fake agent: just return the correct session from the scenario."""
        record_path = scenario_dir / "correct" / "session.json"
        return SessionResult(record_path=record_path, cost_usd=0.01, model="fake-model")

    entry = run_scenario("skill-triggering", "treatment", _fake_agent)

    assert entry["scenario"] == "skill-triggering"
    assert entry["condition"] == "treatment"
    assert entry["overall_score"] == 1.0
    assert entry["cost"] == 0.01
    assert entry["model"] == "fake-model"
    assert "date" in entry
    assert "metrics" in entry
    assert entry["metrics"]["corrective_prompts"] == 0


def test_invoke_agent_via_api_is_not_implemented():
    """invoke_agent_via_api should raise NotImplementedError."""
    from journey_run import invoke_agent_via_api  # noqa: E402

    with pytest.raises(NotImplementedError):
        invoke_agent_via_api("test-scenario", Path("/tmp"), True)


def test_run_scenario_condition_controls_harness_flag():
    """baseline/treatment must reach the agent as harness_installed, and an
    invalid condition is rejected — the baseline-vs-treatment comparison that
    the whole eval exists for."""
    seen = {}

    def _fake_agent(
        scenario_id: str, scenario_dir: Path, harness_installed: bool
    ) -> SessionResult:
        seen[scenario_id] = harness_installed
        return SessionResult(
            record_path=scenario_dir / "correct" / "session.json",
            cost_usd=0.0,
            model="fake",
        )

    baseline = run_scenario("skill-triggering", "baseline", _fake_agent)
    assert baseline["condition"] == "baseline"
    assert seen["skill-triggering"] is False

    treatment = run_scenario("skill-triggering", "treatment", _fake_agent)
    assert treatment["condition"] == "treatment"
    assert seen["skill-triggering"] is True

    with pytest.raises(ValueError):
        run_scenario("skill-triggering", "bogus", _fake_agent)

    # cost-to-acceptance is a stated journey metric — it must reach the ledger.
    assert "cost_usd" in baseline["metrics"]


def test_scenario_mismatch_is_rejected():
    """Scoring a session against a different scenario's rubric must raise,
    not silently grade the wrong rubric."""
    session = load_session(
        EVAL_ROOT / "scenarios" / "skill-triggering" / "correct" / "session.json"
    )
    wrong_rubric = load_rubric(EVAL_ROOT / "scenarios" / "preserve-existing-hooks")
    with pytest.raises(ValueError, match="scenario mismatch"):
        score(session, wrong_rubric)


def test_duplicate_check_type_is_rejected():
    """A rubric that repeats a check with identical params must raise rather
    than silently overwrite one result while overall_score counts both."""
    session = load_session(
        EVAL_ROOT / "scenarios" / "skill-triggering" / "correct" / "session.json"
    )
    dup_rubric = {
        "scenario": "skill-triggering",
        "checks": [
            {"type": "expected_skill_triggered", "skill": "database-conventions"},
            {"type": "expected_skill_triggered", "skill": "database-conventions"},
        ],
    }
    with pytest.raises(ValueError, match="duplicate check"):
        score(session, dup_rubric)


def test_journey_metrics_are_computed():
    """Journey metrics should be included in score result."""
    scenario_dir = EVAL_ROOT / "scenarios" / "refuse-publish-without-authority"
    session_path = scenario_dir / "violating" / "session.json"

    session = load_session(session_path)
    rubric = load_rubric(scenario_dir)
    result = score(session, rubric)

    assert result["corrective_prompts"] == 1  # violating session has 1 corrective turn
    assert result["implementation_attempts"] == 1
    assert result["human_interventions"] == 1
    assert result["cost_usd"] == 0.03


def test_plan_to_code_divergence_computed():
    """Test plan_to_code_divergence reflects symmetric difference of files."""
    scenario_dir = EVAL_ROOT / "scenarios" / "skill-triggering"
    session_path = scenario_dir / "correct" / "session.json"

    session = load_session(session_path)
    rubric = load_rubric(scenario_dir)
    result = score(session, rubric)

    # Correct session has matching plan and actual files, so divergence is 0
    assert result["plan_to_code_divergence"] == 0


def test_schema_validation_fails_on_wrong_version():
    """load_session should reject sessions with wrong schema version."""
    import json
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"schema_version": 2}, f)
        f.flush()
        path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Expected schema_version 1"):
            load_session(path)
    finally:
        path.unlink()


def test_unknown_check_type_raises():
    """score should raise ValueError on unknown check type."""
    scenario_dir = EVAL_ROOT / "scenarios" / "skill-triggering"
    session_path = scenario_dir / "correct" / "session.json"
    session = load_session(session_path)

    rubric = {
        "checks": [
            {"type": "unknown_check_type", "param": "value"}
        ]
    }

    with pytest.raises(ValueError, match="unknown check type"):
        score(session, rubric)
