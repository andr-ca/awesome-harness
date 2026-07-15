"""Integration tests for profile CLI sub-commands (AC-10).

AC-10: Profile operations support preview, apply, validate, and explain.

These tests exercise the four profile sub-commands end-to-end through
the CLI main() entry point, verifying both human-readable and JSON output.
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pytest

from agentharness.cli import main

# ---------------------------------------------------------------------------
# Shared profile fixture
# ---------------------------------------------------------------------------

VALID_PROFILE = textwrap.dedent(
    """\
    schema_version: 1
    runtime:
      lock: .agentharness-policy/runtime.lock
    project:
      name: example
      rigor: production
    bootstrap:
      mode: strict
      confirmed_at: 2026-07-14T00:00:00Z
      existing_checks_are_required: true
    plugins:
      python:
        enabled: true
        version: 1.0.0
        config: {}
    requirements:
      unit_testing:
        provider: python
        enabled: true
        command: [pytest]
        minimum_coverage: 80
        scope:
          include: [src/**]
          exclude: []
        gates: [push, ci, completion]
    workflow:
      reviews:
        expected_signals: []
        timeout_seconds: 900
        stabilization_seconds: 60
      completion:
        require_clean_tree: true
        require_committed_changes: true
        publication: follow_publish_authority
        require_current_ci: true
        require_resolved_reviews: true
    protection:
      provider: github
      default_branch: main
      requirement_reductions:
        codeowners: ['@maintainers']
        require_codeowner_approval: true
        minimum_total_approvals: 1
      waivers:
        require_expiry: true
        require_reason: true
    """
)

INVALID_PROFILE = "schema_version: 1\nproject:\n  name: bad\n"


@pytest.fixture()
def valid_profile_file(tmp_path: Path) -> Path:
    f = tmp_path / "profile.yaml"
    f.write_text(VALID_PROFILE, encoding="utf-8")
    return f


@pytest.fixture()
def invalid_profile_file(tmp_path: Path) -> Path:
    f = tmp_path / "invalid.yaml"
    f.write_text(INVALID_PROFILE, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# profile validate
# ---------------------------------------------------------------------------


class TestProfileValidate:
    def test_valid_profile_exits_0(self, valid_profile_file: Path) -> None:
        out = io.StringIO()
        rc = main(["profile", "validate", str(valid_profile_file)], output=out)
        assert rc == 0

    def test_valid_profile_reports_valid(self, valid_profile_file: Path) -> None:
        out = io.StringIO()
        main(["profile", "validate", str(valid_profile_file)], output=out)
        assert "valid" in out.getvalue().lower()

    def test_invalid_profile_exits_nonzero(self, invalid_profile_file: Path) -> None:
        out = io.StringIO()
        rc = main(["profile", "validate", str(invalid_profile_file)], output=out)
        assert rc != 0

    def test_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        out = io.StringIO()
        rc = main(["profile", "validate", str(tmp_path / "missing.yaml")], output=out)
        assert rc != 0

    def test_json_output_has_schema_version(self, valid_profile_file: Path) -> None:
        import json
        out = io.StringIO()
        main(["profile", "validate", str(valid_profile_file), "--json"], output=out)
        data = json.loads(out.getvalue())
        assert data.get("details", {}).get("schema_version") == 1


# ---------------------------------------------------------------------------
# profile explain
# ---------------------------------------------------------------------------


class TestProfileExplain:
    def test_valid_profile_exits_0(self, valid_profile_file: Path) -> None:
        out = io.StringIO()
        rc = main(["profile", "explain", str(valid_profile_file)], output=out)
        assert rc == 0

    def test_explains_requirement_count(self, valid_profile_file: Path) -> None:
        import json
        out = io.StringIO()
        main(["profile", "explain", str(valid_profile_file), "--json"], output=out)
        data = json.loads(out.getvalue())
        reqs = data.get("details", {}).get("requirements", [])
        assert len(reqs) == 1
        assert reqs[0]["id"] == "unit_testing"

    def test_invalid_profile_exits_nonzero(self, invalid_profile_file: Path) -> None:
        out = io.StringIO()
        rc = main(["profile", "explain", str(invalid_profile_file)], output=out)
        assert rc != 0


# ---------------------------------------------------------------------------
# profile preview
# ---------------------------------------------------------------------------


class TestProfilePreview:
    def test_no_current_reports_new_file(self, valid_profile_file: Path, tmp_path: Path) -> None:  # noqa: E501
        import json
        out = io.StringIO()
        # Point --current at a path that doesn't exist
        rc = main(
            [
                "profile", "preview", str(valid_profile_file),
                "--current", str(tmp_path / "nonexistent.yaml"),
                "--json",
            ],
            output=out,
        )
        assert rc == 0
        data = json.loads(out.getvalue())
        assert data["details"]["diff"] == "new_file"

    def test_identical_current_reports_no_change(
        self, valid_profile_file: Path, tmp_path: Path
    ) -> None:
        import json
        current = tmp_path / "current.yaml"
        current.write_text(VALID_PROFILE, encoding="utf-8")
        out = io.StringIO()
        rc = main(
            [
                "profile", "preview", str(valid_profile_file),
                "--current", str(current),
                "--json",
                "--json",
            ],
            output=out,
        )
        assert rc == 0
        data = json.loads(out.getvalue())
        assert data["details"]["diff"] == "no_change"

    def test_changed_profile_reports_diff_lines(
        self, valid_profile_file: Path, tmp_path: Path
    ) -> None:
        import json
        current = tmp_path / "current.yaml"
        current.write_text(VALID_PROFILE.replace("rigor: production", "rigor: internal"), encoding="utf-8")  # noqa: E501
        out = io.StringIO()
        rc = main(
            [
                "profile", "preview", str(valid_profile_file),
                "--current", str(current),
                "--json",
            ],
            output=out,
        )
        assert rc == 0
        data = json.loads(out.getvalue())
        assert data["details"]["diff"] == "changed"
        assert len(data["details"]["diff_lines"]) > 0


# ---------------------------------------------------------------------------
# profile apply
# ---------------------------------------------------------------------------


class TestProfileApply:
    def test_applies_valid_profile(self, valid_profile_file: Path, tmp_path: Path) -> None:  # noqa: E501
        target = tmp_path / "applied.yaml"
        out = io.StringIO()
        rc = main(
            ["profile", "apply", str(valid_profile_file), "--target", str(target)],
            output=out,
        )
        assert rc == 0
        assert target.exists()
        assert target.read_text(encoding="utf-8") == VALID_PROFILE

    def test_apply_reports_target_path(self, valid_profile_file: Path, tmp_path: Path) -> None:  # noqa: E501
        import json
        target = tmp_path / "applied.yaml"
        out = io.StringIO()
        main(
            ["profile", "apply", str(valid_profile_file), "--target", str(target), "--json"],  # noqa: E501
            output=out,
        )
        data = json.loads(out.getvalue())
        assert str(target) in data["details"]["target"]

    def test_invalid_profile_not_applied(self, invalid_profile_file: Path, tmp_path: Path) -> None:  # noqa: E501
        target = tmp_path / "should-not-exist.yaml"
        out = io.StringIO()
        rc = main(
            ["profile", "apply", str(invalid_profile_file), "--target", str(target)],
            output=out,
        )
        assert rc != 0
        assert not target.exists()
