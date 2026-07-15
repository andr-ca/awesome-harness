"""Unit tests for composite command detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.core.composite import (
    detect_composite_commands,
)


class TestDetectCompositeCommands:
    def test_check_sh_detected(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "check.sh").write_text("#!/usr/bin/env bash\n")
        cmds = detect_composite_commands(tmp_path)
        names = [c.name for c in cmds]
        assert "check.sh" in names

    def test_no_check_sh_returns_empty(self, tmp_path: Path) -> None:
        cmds = detect_composite_commands(tmp_path)
        assert cmds == []

    def test_detection_is_deterministic(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "check.sh").write_text("#!/usr/bin/env bash\n")
        r1 = detect_composite_commands(tmp_path)
        r2 = detect_composite_commands(tmp_path)
        assert [c.name for c in r1] == [c.name for c in r2]
