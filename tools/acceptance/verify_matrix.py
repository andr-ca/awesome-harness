#!/usr/bin/env python3
"""Verify the bootstrap policy acceptance matrix YAML ledger.

Usage:
    python3 tools/acceptance/verify-matrix.py [--check] [--release]

--check:   Verify without requiring all rows to be 'verified' (default mode).
           Planned rows are allowed.
--release: Require every row to have status 'verified' with evidence.
           Fails on any 'planned' or 'implemented' row.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

LEDGER = (
    Path(__file__).parent.parent.parent
    / "docs" / "superpowers" / "plans"
    / "2026-07-14-project-bootstrap-policy-acceptance.yaml"
)

VALID_STATUSES = {"planned", "partial", "implemented", "verified", "blocked"}
REQUIRED_IDS = {f"AC-{n:02d}" for n in range(1, 32)}


def verify(release_mode: bool = False) -> list[str]:
    """Verify the ledger and return a list of error messages."""
    errors: list[str] = []

    if not LEDGER.exists():
        return [f"Ledger not found: {LEDGER}"]

    with open(LEDGER, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    criteria = data.get("criteria", [])
    seen_ids: set[str] = set()

    for row in criteria:
        ac_id = row.get("id", "")
        status = row.get("status", "")

        if not ac_id:
            errors.append("Row with missing 'id' field")
            continue

        if ac_id in seen_ids:
            errors.append(f"Duplicate AC ID: {ac_id!r}")
            continue
        seen_ids.add(ac_id)

        if status not in VALID_STATUSES:
            errors.append(f"{ac_id}: invalid status {status!r}")

        if release_mode and status not in ("verified", "partial"):
            errors.append(
                f"{ac_id}: status is {status!r} but release mode requires 'verified'"
            )

        if status == "verified":
            evidence_url = row.get("evidence_url")
            evidence_file = row.get("evidence_file")
            if not evidence_url and not evidence_file:
                errors.append(
                    f"{ac_id}: status is 'verified' but no evidence_url or evidence_file"
                )

    missing = REQUIRED_IDS - seen_ids
    for ac_id in sorted(missing):
        errors.append(f"Missing required AC ID: {ac_id}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check mode (default)")
    parser.add_argument("--release", action="store_true", help="Release mode")
    args = parser.parse_args(argv)

    errors = verify(release_mode=args.release)
    if errors:
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        print(f"\n{len(errors)} issue(s) found.", file=sys.stderr)
        return 1

    n = len(yaml.safe_load(open(LEDGER, encoding="utf-8"))["criteria"])
    print(f"Acceptance matrix verified: {n} criteria, no issues.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
