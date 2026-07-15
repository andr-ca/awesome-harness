"""Python plugin fixture matrix test (AC-19).

Exercises each Python fixture directory through the PythonPlugin and asserts:
1. The plugin passes the full compliance contract for every fixture.
2. The CheckResult's FindingCode values match expected detection outcomes.

This test is the 'Contract report enumerating all capability IDs' required by
AC-19's release evidence column.

Note: The PythonPlugin exposes python.environment and python.task_runner.
Mutation, quality, and runtime-quality detection are exercised separately in
tests/unit/plugins/python/ using the lower-level detection functions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentharness.plugins.api import FindingCode
from agentharness.plugins.python.plugin import PythonPlugin
from tests.contract.plugin_compliance import assert_plugin_compliant

FIXTURES = Path(__file__).parent.parent / "fixtures" / "python"


def _run(subdir: str) -> dict[str, FindingCode]:
    """Run the Python plugin against *subdir* and return capability → code map."""
    plugin = PythonPlugin()
    result = assert_plugin_compliant(plugin, {"project_root": str(FIXTURES / subdir)})
    return {f.capability: f.code for f in result.findings}


class TestPythonPluginFixtureMatrix:
    """AC-19: Python plugin passes contract and fixture matrix."""

    # ------------------------------------------------------------------
    # environment fixtures
    # ------------------------------------------------------------------

    def test_pyproject_only_environment_pass(self) -> None:
        codes = _run("environment/pyproject-only")
        assert codes["python.environment"] == FindingCode.PASS

    def test_requirements_only_environment_pass(self) -> None:
        codes = _run("environment/requirements-only")
        assert codes["python.environment"] == FindingCode.PASS

    def test_poetry_project_environment_pass(self) -> None:
        codes = _run("environment/poetry-project")
        assert codes["python.environment"] == FindingCode.PASS

    def test_no_python_marker_environment_skip(self) -> None:
        codes = _run("environment/no-python-marker")
        assert codes["python.environment"] == FindingCode.SKIP

    # ------------------------------------------------------------------
    # tasks fixtures
    # ------------------------------------------------------------------

    def test_tox_only_task_runner_pass(self) -> None:
        codes = _run("tasks/tox-only")
        assert codes["python.task_runner"] == FindingCode.PASS

    def test_nox_only_task_runner_pass(self) -> None:
        codes = _run("tasks/nox-only")
        assert codes["python.task_runner"] == FindingCode.PASS

    def test_tox_and_nox_task_runner_pass(self) -> None:
        codes = _run("tasks/tox-and-nox")
        assert codes["python.task_runner"] == FindingCode.PASS

    def test_make_only_task_runner_pass(self) -> None:
        codes = _run("tasks/make-only")
        assert codes["python.task_runner"] == FindingCode.PASS

    def test_no_runner_task_runner_warn(self) -> None:
        """No task runner detected → WARN (project should add one)."""
        codes = _run("tasks/no-runner")
        assert codes["python.task_runner"] == FindingCode.WARN

    # ------------------------------------------------------------------
    # All fixtures pass the compliance contract (no undeclared capabilities,
    # no secret leakage, valid plugin_id on every result)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "subdir",
        [
            "environment/pyproject-only",
            "environment/requirements-only",
            "environment/poetry-project",
            "environment/no-python-marker",
            "tasks/tox-only",
            "tasks/nox-only",
            "tasks/tox-and-nox",
            "tasks/make-only",
            "tasks/no-runner",
        ],
    )
    def test_compliance_contract_for_all_fixtures(self, subdir: str) -> None:
        """Every fixture must pass the full plugin compliance contract (AC-19)."""
        plugin = PythonPlugin()
        # assert_plugin_compliant raises ComplianceError on any violation
        result = assert_plugin_compliant(plugin, {"project_root": str(FIXTURES / subdir)})  # noqa: E501
        assert result.plugin_id == plugin.metadata.plugin_id
