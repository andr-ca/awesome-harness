#!/usr/bin/env python3
"""Generates MANIFEST.md from manifest.yaml (B2).

Mirrors tools/generate-agents-md.sh's pattern (a structured source
rendered into committed markdown, drift-checked in CI via
check_manifest_md_sync() in verify-content-quality.py) but for the asset
manifest instead of the Codex adapter. Edit manifest.yaml, not
MANIFEST.md — MANIFEST.md is generated, committed output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_YAML = REPO_ROOT / "manifest.yaml"

# Maps each table's column header text to the YAML key holding that
# column's value per asset. "Path" values get wrapped in backticks on
# render; every other column is used verbatim.
_COLUMN_TO_KEY = {
    "Asset": "asset",
    "Path": "path",
    "Type": "type",
    "When to use": "when_to_use",
    "Purpose": "purpose",
}


def render_table(columns: list[str], assets: list[dict[str, str]]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join("---" for _ in columns) + "|"
    rows = []
    for asset in assets:
        cells = []
        for col in columns:
            key = _COLUMN_TO_KEY[col]
            value = asset[key]
            if key == "path":
                value = f"`{value}`"
            cells.append(value)
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows])


def generate(data: dict) -> str:
    parts = ["# Manifest", "", data["intro"], "", data["regeneration_note"], ""]
    for section in data["sections"]:
        parts.append(f"## {section['name']}")
        parts.append("")
        parts.append(render_table(section["columns"], section["assets"]))
        parts.append("")
    return "\n".join(parts).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Write to this path instead of stdout")
    args = parser.parse_args()

    data = yaml.safe_load(MANIFEST_YAML.read_text())
    output = generate(data)

    if args.output:
        Path(args.output).write_text(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
