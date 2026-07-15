"""Unit tests for Python linting and formatting tool detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.linting import (
    LintToolKind,
    detect_lint_tools,
)

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "python" / "quality"  # noqa: E501


class TestDetectLintTools:
    def test_ruff_only(self) -> None:
        tools = detect_lint_tools(FIXTURES / "ruff-only")
        kinds = {t.kind for t in tools}
        assert LintToolKind.RUFF in kinds

    def test_black_only(self) -> None:
        tools = detect_lint_tools(FIXTURES / "black-only")
        kinds = {t.kind for t in tools}
        assert LintToolKind.BLACK in kinds

    def test_ruff_and_mypy(self) -> None:
        tools = detect_lint_tools(FIXTURES / "ruff-and-mypy")
        kinds = {t.kind for t in tools}
        assert LintToolKind.RUFF in kinds

    def test_no_quality_tools_returns_empty(self) -> None:
        tools = detect_lint_tools(FIXTURES / "no-quality-tools")
        assert tools == []

    def test_detection_is_deterministic(self) -> None:
        path = FIXTURES / "ruff-and-mypy"
        run1 = detect_lint_tools(path)
        run2 = detect_lint_tools(path)
        assert [t.kind for t in run1] == [t.kind for t in run2]

    def test_detection_does_not_mutate_project(self, tmp_path) -> None:
        before = set(tmp_path.rglob("*"))
        detect_lint_tools(tmp_path)
        after = set(tmp_path.rglob("*"))
        assert before == after
