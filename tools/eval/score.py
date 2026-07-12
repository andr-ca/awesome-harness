#!/usr/bin/env python3
"""Deterministic scorer for tools/eval/tasks/*.

Given a task directory (tools/eval/tasks/<id>/) and a candidate directory
containing an implementation of that task, copies the task's hidden
tests in alongside the candidate code and runs the language's real
tooling (ruff + pytest/coverage for Python, go vet + go test for Go) —
the same tools tools/check.sh already runs on this repo's own code. No
LLM calls; the result depends only on the candidate code and the task's
fixed hidden tests, so the same inputs always produce the same score.

Rubric (drawn from patterns/testing/COMPLETION_CHECKLIST.md): tests
pass, coverage meets the task's threshold, lint is clean, and the hidden
suite's edge-case tests (named with an "edge"/"Edge" marker) pass.
overall_score is the fraction of those four criteria met.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def load_task(task_dir: Path) -> dict:
    return yaml.safe_load((task_dir / "task.yaml").read_text())


def _stage(task_dir: Path, candidate_dir: Path) -> Path:
    """Copy candidate code + this task's hidden tests into a scratch dir."""
    scratch = Path(tempfile.mkdtemp(prefix="agentharness-eval-"))
    shutil.copytree(candidate_dir, scratch, dirs_exist_ok=True)
    shutil.copytree(task_dir / "tests", scratch, dirs_exist_ok=True)
    return scratch


def _score_python(task: dict, task_dir: Path, scratch: Path) -> dict:
    module = Path(task["entry_module"]).stem
    # Run only this task's own hidden test files, not a blanket recursive
    # collection — a treatment-condition candidate dir may have a full
    # harness install (.claude/skills/...) alongside it, and letting
    # pytest discover *those* skills' own test_*.py files would corrupt
    # this task's pass/fail count with unrelated tests.
    test_files = sorted(p.name for p in (task_dir / "tests").glob("*.py"))
    lint = subprocess.run(
        ["ruff", "check", "."], cwd=scratch, capture_output=True, text=True
    )
    test_run = subprocess.run(
        [
            "python3",
            "-m",
            "pytest",
            "-v",
            f"--cov={module}",
            "--cov-report=term-missing",
            *test_files,
        ],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    output = test_run.stdout + test_run.stderr

    coverage_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
    coverage_pct = float(coverage_match.group(1)) if coverage_match else 0.0

    test_results = re.findall(r"::(test_\S+)\s+(PASSED|FAILED)", output)
    edge_results = [status for name, status in test_results if "edge" in name]
    edge_cases_pass = bool(edge_results) and all(s == "PASSED" for s in edge_results)

    return {
        "tests_pass": test_run.returncode == 0,
        "coverage_pct": coverage_pct,
        "coverage_met": coverage_pct >= task["coverage_threshold"],
        "lint_clean": lint.returncode == 0,
        "edge_cases_pass": edge_cases_pass,
        "raw_test_output": output,
    }


def _score_go(task: dict, task_dir: Path, scratch: Path) -> dict:
    # `.` not `./...`: scope vet/test to this task's own package root, not
    # anything a treatment-condition harness install may have dropped
    # alongside it in scratch.
    vet = subprocess.run(
        ["go", "vet", "."], cwd=scratch, capture_output=True, text=True
    )
    test_run = subprocess.run(
        ["go", "test", ".", "-v", "-cover"],
        cwd=scratch,
        capture_output=True,
        text=True,
    )
    output = test_run.stdout + test_run.stderr

    coverage_match = re.search(r"coverage:\s+([\d.]+)%\s+of statements", output)
    coverage_pct = float(coverage_match.group(1)) if coverage_match else 0.0

    test_results = re.findall(r"--- (PASS|FAIL): (\S+)", output)
    edge_results = [status for status, name in test_results if "Edge" in name]
    edge_cases_pass = bool(edge_results) and all(s == "PASS" for s in edge_results)

    return {
        "tests_pass": test_run.returncode == 0,
        "coverage_pct": coverage_pct,
        "coverage_met": coverage_pct >= task["coverage_threshold"],
        "lint_clean": vet.returncode == 0,
        "edge_cases_pass": edge_cases_pass,
        "raw_test_output": output,
    }


_SCORERS = {"python": _score_python, "go": _score_go}


def score(task_dir: Path, candidate_dir: Path) -> dict:
    task = load_task(task_dir)
    language = task["language"]
    if language not in _SCORERS:
        raise ValueError(f"unsupported language: {language}")

    scratch = _stage(task_dir, candidate_dir)
    try:
        result = _SCORERS[language](task, task_dir, scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    criteria = ["tests_pass", "coverage_met", "lint_clean", "edge_cases_pass"]
    result["overall_score"] = sum(1 for c in criteria if result[c]) / len(criteria)
    result["task_id"] = task["id"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", required=True, type=Path, help="Path to tools/eval/tasks/<id>/"
    )
    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="Directory containing the candidate's implementation",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Include raw test tool output"
    )
    args = parser.parse_args()

    result = score(args.task, args.candidate)
    if not args.verbose:
        result = {k: v for k, v in result.items() if k != "raw_test_output"}
    print(json.dumps(result, indent=2))
    return 0 if result["overall_score"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
