"""Unit tests for change classification."""

from __future__ import annotations

from agentharness.policy.classification import (
    ChangeClass,
    classify_changes,
    classify_path,
)


class TestClassifyPath:
    def test_python_code(self) -> None:
        assert classify_path("src/agentharness/cli.py") == ChangeClass.CODE

    def test_go_code(self) -> None:
        assert classify_path("cmd/main.go") == ChangeClass.CODE

    def test_tests(self) -> None:
        assert classify_path("tests/unit/test_cli.py") == ChangeClass.TESTS

    def test_config_yaml(self) -> None:
        assert classify_path(".github/workflows/ci.yml") == ChangeClass.CONFIG

    def test_markdown_in_docs(self) -> None:
        assert classify_path("docs/ARCHITECTURE.md") == ChangeClass.DOCS

    def test_unknown_extension(self) -> None:
        assert classify_path("some/file.xyz") == ChangeClass.UNKNOWN


class TestClassifyChanges:
    def test_multiple_paths(self) -> None:
        classifications = classify_changes(["src/a.py", "tests/test_a.py"])
        kinds = {c.change_class for c in classifications}
        assert ChangeClass.CODE in kinds
        assert ChangeClass.TESTS in kinds

    def test_result_length_matches_input(self) -> None:
        paths = ["a.py", "b.go", "c.md"]
        result = classify_changes(paths)
        assert len(result) == 3
