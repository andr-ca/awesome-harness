#!/usr/bin/env python3
"""Analyze a project's top-level directory structure and generate a
.agentharness-guarded-paths.json file listing paths where new files/
directories must not be created without explicit permission.

Usage:
    python3 tools/analyze_structure.py <project-root> [--output <path>]
    python3 tools/analyze_structure.py <project-root> --recommend

The analyzer examines the root directory for:
1. Established top-level directories (docs/, src/, tests/, logs/, conf/, etc.)
2. Established root-level config files (.gitignore, package.json, etc.)
3. Whether the project is "early stage" (< 3 meaningful files/dirs)

For established projects it generates guarded-paths rules.
For new/early-stage projects it outputs recommendations for the user to accept.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Config files that, when present, signal an established project
_CONFIG_SIGNALS = frozenset({
    "package.json",
    "pyproject.toml",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "composer.json",
    "Gemfile",
    ".gitignore",
    "Makefile",
    "CMakeLists.txt",
    "build.gradle",
    "pom.xml",
})

# Directories that are common in established projects
_STRUCTURAL_DIRS = frozenset({
    "src",
    "lib",
    "app",
    "pkg",
    "cmd",
    "internal",
    "docs",
    "doc",
    "documentation",
    "tests",
    "test",
    "spec",
    "e2e",
    "integration",
    "logs",
    "log",
    "conf",
    "config",
    "configs",
    "scripts",
    "tools",
    "bin",
    "dist",
    "build",
    "out",
    "tmp",
    "temp",
    "data",
    "assets",
    "static",
    "public",
    "examples",
    "sample",
    "demo",
})

# Items that should always be guarded in any project
_ALWAYS_GUARDED = (
    "docs",
    "src",
    "lib",
    "tests",
    "test",
    "conf",
    "config",
    "logs",
    "scripts",
)

# Items that are root-level config files (should require permission to add new ones)
_ROOT_CONFIG_PATTERNS = (
    ".gitignore",
    ".gitattributes",
    "package.json",
    "pyproject.toml",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.sample",
    ".env.example",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
)

# Recommendations for new projects
_RECOMMENDED_STRUCTURE = {
    "dirs": ["src", "tests", "docs"],
    "files": [".gitignore", "README.md"],
    "rationale": (
        "A standard minimal structure keeps the root clean and "
        "makes it clear where new code, tests, and documentation belong."
    ),
}


def analyze(project_root: Path) -> dict:
    """Analyze *project_root* and return a structure report."""
    if not project_root.exists():
        raise FileNotFoundError(f"Project root not found: {project_root}")

    root_items = list(project_root.iterdir())
    root_dirs = {p.name for p in root_items if p.is_dir() and not p.name.startswith(".")}
    root_files = {p.name for p in root_items if p.is_file()}
    root_hidden = {
        p.name
        for p in root_items
        if p.name.startswith(".")
    }

    config_signals = root_files & _CONFIG_SIGNALS
    established_dirs = root_dirs & _STRUCTURAL_DIRS
    meaningful_count = len(root_dirs) + len(config_signals)

    is_established = meaningful_count >= 3 or bool(config_signals & {
        "package.json", "pyproject.toml", "setup.py", "Cargo.toml", "go.mod",
    })

    return {
        "project_root": str(project_root.resolve()),
        "is_established": is_established,
        "meaningful_item_count": meaningful_count,
        "config_signals": sorted(config_signals),
        "established_dirs": sorted(established_dirs),
        "all_root_dirs": sorted(root_dirs),
        "all_root_files": sorted(root_files | root_hidden),
    }


def generate_guarded_paths(report: dict) -> dict:
    """Generate a guarded-paths configuration from an analysis report."""
    guarded_dirs: list[str] = []
    guarded_patterns: list[str] = []

    # Guard all established structural directories
    for d in report["established_dirs"]:
        guarded_dirs.append(d + "/")

    # Guard any always-guarded dirs that exist
    for d in _ALWAYS_GUARDED:
        if d in report["all_root_dirs"] and d + "/" not in guarded_dirs:
            guarded_dirs.append(d + "/")

    # Guard root-level config files that are already present
    for name in _ROOT_CONFIG_PATTERNS:
        if name in report["all_root_files"]:
            guarded_patterns.append(name)

    # Always: new root-level items require permission
    guard_root_level = report["is_established"]

    return {
        "schema_version": 1,
        "guard_root_level_new_items": guard_root_level,
        "guarded_dirs": sorted(set(guarded_dirs)),
        "guarded_root_files": sorted(set(guarded_patterns)),
        "message": (
            "New files in guarded paths require explicit user permission. "
            "Add the path to .agentharness-allowed-additions.txt or ask the "
            "user before creating files in these locations."
            if guard_root_level
            else "Project structure not yet established — fewer restrictions apply."
        ),
        "generated_from": report["project_root"],
    }


def recommend_structure(report: dict) -> dict:
    """Return structure recommendations for an early-stage project."""
    existing_dirs = set(report["all_root_dirs"])
    existing_files = set(report["all_root_files"])

    missing_dirs = [d for d in _RECOMMENDED_STRUCTURE["dirs"] if d not in existing_dirs]
    missing_files = [f for f in _RECOMMENDED_STRUCTURE["files"] if f not in existing_files]

    return {
        "is_early_stage": not report["is_established"],
        "existing_dirs": report["all_root_dirs"],
        "recommended_dirs_to_create": missing_dirs,
        "recommended_files_to_create": missing_files,
        "rationale": _RECOMMENDED_STRUCTURE["rationale"],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_root", type=Path, help="Project root directory")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Write guarded-paths JSON to this path")
    parser.add_argument("--recommend", action="store_true",
                        help="Output structure recommendations for new projects")
    args = parser.parse_args(argv)

    report = analyze(args.project_root)

    if args.recommend:
        rec = recommend_structure(report)
        print(json.dumps(rec, indent=2))
        return 0

    config = generate_guarded_paths(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"Guarded-paths config written to {args.output}")
    else:
        print(json.dumps(config, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
