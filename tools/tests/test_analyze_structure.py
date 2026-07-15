"""Tests for tools/analyze_structure.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the tools module importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.analyze_structure import (
    analyze,
    generate_guarded_paths,
    recommend_structure,
)


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """A completely empty project directory."""
    return tmp_path


@pytest.fixture
def early_project(tmp_path: Path) -> Path:
    """A project with just a README (early stage)."""
    (tmp_path / "README.md").write_text("# My Project\n")
    return tmp_path


@pytest.fixture
def established_project(tmp_path: Path) -> Path:
    """An established Python project."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".gitignore").write_text("__pycache__/\n")
    return tmp_path


class TestAnalyze:
    def test_empty_project_is_not_established(self, empty_project: Path) -> None:
        report = analyze(empty_project)
        assert not report["is_established"]

    def test_early_project_is_not_established(self, early_project: Path) -> None:
        report = analyze(early_project)
        assert not report["is_established"]

    def test_established_project_is_established(self, established_project: Path) -> None:
        report = analyze(established_project)
        assert report["is_established"]

    def test_detects_config_signals(self, established_project: Path) -> None:
        report = analyze(established_project)
        assert "pyproject.toml" in report["config_signals"]

    def test_detects_established_dirs(self, established_project: Path) -> None:
        report = analyze(established_project)
        assert "src" in report["established_dirs"]
        assert "tests" in report["established_dirs"]

    def test_nonexistent_root_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            analyze(tmp_path / "nonexistent")


class TestGenerateGuardedPaths:
    def test_established_guards_root(self, established_project: Path) -> None:
        report = analyze(established_project)
        config = generate_guarded_paths(report)
        assert config["guard_root_level_new_items"] is True

    def test_early_project_does_not_guard_root(self, empty_project: Path) -> None:
        report = analyze(empty_project)
        config = generate_guarded_paths(report)
        assert config["guard_root_level_new_items"] is False

    def test_guarded_dirs_include_established(self, established_project: Path) -> None:
        report = analyze(established_project)
        config = generate_guarded_paths(report)
        dirs = config["guarded_dirs"]
        assert any("src/" in d or d == "src/" for d in dirs)

    def test_schema_version_present(self, established_project: Path) -> None:
        report = analyze(established_project)
        config = generate_guarded_paths(report)
        assert config["schema_version"] == 1

    def test_config_is_json_serializable(self, established_project: Path) -> None:
        report = analyze(established_project)
        config = generate_guarded_paths(report)
        json.dumps(config)  # Should not raise


class TestRecommendStructure:
    def test_early_project_recommends_dirs(self, early_project: Path) -> None:
        report = analyze(early_project)
        rec = recommend_structure(report)
        assert rec["is_early_stage"]
        assert "src" in rec["recommended_dirs_to_create"]

    def test_established_not_early_stage(self, established_project: Path) -> None:
        report = analyze(established_project)
        rec = recommend_structure(report)
        assert not rec["is_early_stage"]

    def test_existing_dirs_not_recommended(self, established_project: Path) -> None:
        report = analyze(established_project)
        rec = recommend_structure(report)
        # src/ already exists — should not be recommended again
        assert "src" not in rec["recommended_dirs_to_create"]
