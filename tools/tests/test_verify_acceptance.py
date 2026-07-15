"""Tests for the acceptance matrix verifier."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.acceptance.verify_matrix import verify


class TestVerifyMatrix:
    def test_clean_ledger_has_no_errors(self) -> None:
        errors = verify(release_mode=False)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_release_mode_fails_on_planned(self) -> None:
        errors = verify(release_mode=True)
        # At least some rows are still 'planned', so release mode should fail
        assert any("planned" in e for e in errors)

    def test_release_mode_fails_on_partial(self) -> None:
        errors = verify(release_mode=True)
        # 'partial' means a required part is unproven — never releasable
        assert any("partial" in e for e in errors)

    def test_all_31_ac_ids_present(self) -> None:
        import yaml

        from tools.acceptance.verify_matrix import LEDGER, REQUIRED_IDS
        data = yaml.safe_load(open(LEDGER, encoding="utf-8"))
        ids = {row["id"] for row in data["criteria"]}
        missing = REQUIRED_IDS - ids
        assert not missing, f"Missing: {sorted(missing)}"
