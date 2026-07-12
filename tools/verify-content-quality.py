#!/usr/bin/env python3
"""Content-quality gate (P1-08): catches structural doc/content bugs that
markdown-links and markdownlint don't — bad YAML, malformed skill
frontmatter, and syntax errors in the two docs whose Python examples are
explicitly maintained as tested, runnable reference implementations (not
every illustrative snippet in the repo — most are deliberately partial
pseudocode, and syntax-checking those would just be noise).
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Docs whose fenced ```python blocks are meant to be complete, runnable
# examples — not every doc with a python fence qualifies (see module
# docstring). Add a file here only when its example is verified to run
# end-to-end, the same way these two were.
PYTHON_SNIPPET_SOURCES = [
    REPO_ROOT / "patterns/agentic-loops/README.md",
    REPO_ROOT / "patterns/logging/LOGGING_STANDARDS.md",
]

FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)
PYTHON_FENCE_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def find_yaml_files() -> list[Path]:
    files = []
    for pattern in ("*.yaml", "*.yml"):
        files.extend(REPO_ROOT.rglob(pattern))
    return [f for f in files if ".git" not in f.parts]


def check_yaml_files() -> list[str]:
    errors = []
    for path in find_yaml_files():
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid YAML — {exc}")
    return errors


def check_skill_frontmatter() -> list[str]:
    errors = []
    skills_dir = REPO_ROOT / ".claude/skills"
    if not skills_dir.is_dir():
        return errors
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: missing")
            continue
        text = skill_md.read_text()
        match = FRONTMATTER_RE.match(text)
        if not match:
            errors.append(
                f"{skill_md.relative_to(REPO_ROOT)}: no --- frontmatter block found"
            )
            continue
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: invalid frontmatter YAML — {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: frontmatter is not a mapping")
            continue
        name = data.get("name")
        if name != skill_dir.name:
            errors.append(
                f"{skill_md.relative_to(REPO_ROOT)}: frontmatter name "
                f"{name!r} doesn't match directory name {skill_dir.name!r}"
            )
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: missing or empty description")
    return errors


def check_python_snippets() -> list[str]:
    errors = []
    for path in PYTHON_SNIPPET_SOURCES:
        if not path.is_file():
            errors.append(f"{path.relative_to(REPO_ROOT)}: expected file not found")
            continue
        text = path.read_text()
        for i, block in enumerate(PYTHON_FENCE_RE.findall(text), start=1):
            try:
                ast.parse(block)
            except SyntaxError as exc:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: python snippet #{i} has a syntax error — {exc}"
                )
    return errors


def check_agents_md_sync() -> list[str]:
    # P2-02: AGENTS.md is generated from CLAUDE.md + .claude/skills/ by
    # tools/generate-agents-md.sh, not hand-maintained — the same drift
    # class fixed for docs in P1-13, guarded against here the same way
    # verify-manifest.sh guards MANIFEST.md's bidirectional accuracy.
    committed = REPO_ROOT / "AGENTS.md"
    generator = REPO_ROOT / "tools/generate-agents-md.sh"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        ["bash", str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-agents-md.sh --output AGENTS.md' and commit the result"
        ]
    return []


def main() -> int:
    errors = []
    errors += check_yaml_files()
    errors += check_skill_frontmatter()
    errors += check_python_snippets()
    errors += check_agents_md_sync()

    if errors:
        print("Content-quality check failed:\n")
        for err in errors:
            print(f"  ✗ {err}")
        print(f"\n{len(errors)} issue(s) found.")
        return 1

    print("Content-quality check passed: YAML parses, skill frontmatter valid, "
          "tested Python snippets parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
