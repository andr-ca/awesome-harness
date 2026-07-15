"""Unit tests for the core repository policy plugin."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.core.repository import (
    detect_repository,
)

_HERE = Path(__file__).parent.parent.parent.parent
FIXTURES = _HERE / "fixtures" / "repository-policy"


class TestDetectRepository:
    def test_with_env_sample_detected(self) -> None:
        result = detect_repository(FIXTURES / "with-env-sample")
        assert result.has_env_sample is True

    def test_no_env_sample(self) -> None:
        result = detect_repository(FIXTURES / "no-env-sample")
        assert result.has_env_sample is False

    def test_detection_does_not_mutate(self, tmp_path: Path) -> None:
        before = set(tmp_path.rglob("*"))
        detect_repository(tmp_path)
        assert set(tmp_path.rglob("*")) == before
