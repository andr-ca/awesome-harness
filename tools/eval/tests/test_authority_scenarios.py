"""Wires the deterministic authority eval scenarios into the test suite.

`authority_scenarios.py` defines fixed allow/refuse/expire/revoke/precedence
cases and scores each against `agentharness.authority.decide`. These make no
API calls, so — like `test_score.py` — they are ordinary deterministic tests,
run here so CI actually exercises the scenarios rather than leaving them as a
never-invoked module.
"""

from __future__ import annotations

import sys
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_ROOT))

from authority_scenarios import AUTHORITY_SCENARIOS, score_scenarios  # noqa: E402


def test_scenarios_are_defined() -> None:
    """The scenario battery is non-empty and covers the key decision paths."""
    assert len(AUTHORITY_SCENARIOS) >= 5
    names = {s.name for s in AUTHORITY_SCENARIOS}
    # At least one of each decision path we care about.
    assert any("expir" in n for n in names)
    assert any("revok" in n for n in names)


def test_all_scenarios_pass() -> None:
    """Every scenario's actual decision matches its expected outcome."""
    results = score_scenarios()
    failed = [name for name, passed in results.items() if not passed]
    assert not failed, f"authority eval scenarios failed: {failed}"
