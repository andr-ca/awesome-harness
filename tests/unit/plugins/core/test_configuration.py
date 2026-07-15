"""Unit tests for the core configuration hygiene plugin."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.core.configuration import (
    ConfigHygiene,
    detect_config_hygiene,
)


class TestDetectConfigHygiene:
    def test_env_sample_present(self, tmp_path: Path) -> None:
        (tmp_path / ".env.sample").write_text("KEY=\n")
        result = detect_config_hygiene(tmp_path)
        assert result.has_env_sample is True

    def test_no_env_sample(self, tmp_path: Path) -> None:
        result = detect_config_hygiene(tmp_path)
        assert result.has_env_sample is False

    def test_env_example_also_counts(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text("KEY=\n")
        result = detect_config_hygiene(tmp_path)
        assert result.has_env_sample is True
