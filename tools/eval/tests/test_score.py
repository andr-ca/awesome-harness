"""Tests for tools/eval/score.py against hand-written correct/broken
fixtures — the scorer itself makes no LLM calls, so these are ordinary
deterministic unit tests, not evals."""
import shutil
import sys
from pathlib import Path

import pytest

EVAL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_ROOT))

from score import score  # noqa: E402

_NO_GO = pytest.mark.skipif(
    shutil.which("go") is None, reason="go is not installed on this machine"
)

TASKS = [
    "python-input-validation",
    "python-bugfix-average",
    pytest.param("go-error-handling", marks=_NO_GO),
]


@pytest.mark.parametrize("task_id", TASKS)
def test_correct_fixture_scores_perfectly(task_id):
    result = score(
        EVAL_ROOT / "tasks" / task_id, EVAL_ROOT / "fixtures" / task_id / "correct"
    )
    assert result["overall_score"] == 1.0
    assert result["tests_pass"] is True
    assert result["edge_cases_pass"] is True
    assert result["task_id"] == task_id


@pytest.mark.parametrize("task_id", TASKS)
def test_broken_fixture_fails_tests(task_id):
    result = score(
        EVAL_ROOT / "tasks" / task_id, EVAL_ROOT / "fixtures" / task_id / "broken"
    )
    assert result["overall_score"] < 1.0
    assert result["tests_pass"] is False
    assert result["edge_cases_pass"] is False


def test_unsupported_language_raises(tmp_path):
    task_dir = tmp_path / "task"
    (task_dir / "tests").mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        "id: unsupported\nlanguage: rust\nentry_module: main.rs\n"
        "coverage_threshold: 80\nprompt: n/a\n"
    )
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()

    with pytest.raises(ValueError, match="unsupported language"):
        score(task_dir, candidate_dir)
