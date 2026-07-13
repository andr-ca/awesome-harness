#!/usr/bin/env python3
"""Content-quality gate (P1-08): catches structural doc/content bugs that
markdown-links and markdownlint don't — bad YAML, malformed skill
frontmatter, syntax errors in docs whose Python or bash examples are
explicitly maintained as tested, runnable reference implementations (not
every illustrative snippet in the repo — most are deliberately partial
pseudocode, and syntax-checking those would just be noise);
duplicate-policy detection (B7): the same numeric mandate restated with a
*different* number somewhere outside its source of truth; and
generated-file drift for AGENTS.md (P2-02), MANIFEST.md (B2), the
cross-platform-parity adapters (GEMINI.md, .kilo/rules/agentharness.md,
.github/copilot-instructions.md + .github/instructions/*, and
.cursor/rules/*.mdc), and the custom-agent-porting generators
(.codex/agents/*.toml, .opencode/agents/*.md, .cursor/agents/*.md,
.kilo/agents/*.md, .github/agents/*.agent.md, and .gemini/agents/*.md)
against their structured sources.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

import yaml


class PolicyRegistryEntry(TypedDict):
    name: str
    source_rel: str
    topic_word: re.Pattern[str]

REPO_ROOT = Path(__file__).resolve().parent.parent

# Docs whose fenced ```python blocks are meant to be complete, runnable
# examples — not every doc with a python fence qualifies (see module
# docstring). Add a file here only when its example is verified to run
# end-to-end, the same way these two were.
PYTHON_SNIPPET_SOURCES = [
    REPO_ROOT / "patterns/agentic-loops/README.md",
    REPO_ROOT / "patterns/logging/LOGGING_STANDARDS.md",
]

# B3: same allowlist principle as PYTHON_SNIPPET_SOURCES, extended to the
# docs whose ```bash fences are complete, runnable recipes rather than
# illustrative fragments — docs/INTEGRATION.md's harness-link.sh
# invocations and COVERAGE_REQUIREMENTS.md's bc-based coverage
# comparison. Deliberately NOT languages/*/CONVENTIONS.md,
# patterns/testing/TDD.md, or patterns/error-handling/README.md — those
# are intentional pseudocode/pattern illustrations (variable names like
# `<command>`, partial control flow), and syntax-checking them would be
# exactly the noise this module's docstring already warns against.
BASH_SNIPPET_SOURCES = [
    REPO_ROOT / "docs/INTEGRATION.md",
    REPO_ROOT / "patterns/testing/COVERAGE_REQUIREMENTS.md",
]

# B3: docs/DEMO.md's ```console blocks interleave prompts ("$ cmd"),
# commands' own output, and box-drawing decoration in the same fence —
# not raw bash. Only the "$ "-prefixed lines are commands; extracting
# just those and syntax-checking them is what actually protects this
# doc, since every command in it was hand-verified by running it for
# real when the doc was written (see its own intro paragraph).
CONSOLE_SNIPPET_SOURCES = [
    REPO_ROOT / "docs/DEMO.md",
]

FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)
PYTHON_FENCE_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)
BASH_FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)
CONSOLE_FENCE_RE = re.compile(r"```console\n(.*?)```", re.DOTALL)
ANY_FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)

# B7: duplicate-policy detection. Registry of (name, source-of-truth file,
# topic word) triples for numeric mandates this repo has *actually*
# drifted on before (the coverage floor was independently reconciled from
# a 79%/75%/80% three-way conflict — see CHANGELOG.md's v0.1.0 entry).
#
# Deliberately NOT "flag any percentage near the topic word" — a first
# pass at that flagged .claude/skills/agentic-loops/SKILL.md's "(100%
# coverage)" as a mandate conflict, when it's actually describing that
# one file's *measured* test result, not restating what the mandate
# requires. And a stricter "flag any restatement without a nearby
# cross-reference" design was rejected too:
# patterns/testing/COMPLETION_CHECKLIST.md alone legitimately repeats
# "80%" a dozen times as checklist shorthand, none of it wrong, and
# flagging every occurrence would be almost pure noise (the
# ~15-false-positive risk ROADMAP.md's prior analysis already named).
#
# What's left, cheap to get right, and unambiguous: a number near the
# topic word AND near a *mandate-signal* word/symbol (minimum, required,
# floor, at least, below, >=, <) — "80% coverage minimum" and "coverage
# drops below 80%" both count; "(100% coverage)" describing a measured
# result does not, because nothing near it signals a requirement.
DUPLICATE_POLICY_REGISTRY: list[PolicyRegistryEntry] = [
    {
        "name": "test coverage percentage mandate",
        "source_rel": "patterns/testing/COVERAGE_REQUIREMENTS.md",
        "topic_word": re.compile(r"coverage", re.IGNORECASE),
    },
]

_PERCENT_RE = re.compile(r"\b(\d{1,3})%")
_MANDATE_SIGNAL_RE = re.compile(
    r"minimum|floor|required?|requirement|mandatory|at least|no less than"
    r"|>=|<=?|below|must\s+(?:have|be|reach)",
    re.IGNORECASE,
)

# Historical/generated/fixture content isn't live policy prose — scanning
# it would just surface old snapshots and illustrative examples as if they
# were current, contradictory policy.
DUPLICATE_POLICY_EXCLUDED_DIR_PREFIXES = ("docs/operational/", "examples/")
DUPLICATE_POLICY_EXCLUDED_FILENAMES = {"MANIFEST.md", "AGENTS.md", "CHANGELOG.md"}


# Generated/dependency/venv trees a developer might have on disk locally
# (gitignored, so not tracked content) but that rglob() would still walk
# into — scanning them is pure noise at best and a slow/broken run at
# worst (e.g. node_modules can contain thousands of unrelated YAML files).
_YAML_SCAN_EXCLUDED_DIR_NAMES = {".git", "node_modules", "venv", ".venv", "__pycache__"}


def find_yaml_files() -> list[Path]:
    # os.walk() with in-place dirnames pruning, not Path.rglob() filtered
    # afterward — rglob() has no way to skip descending into an excluded
    # directory once it's found one, so a post-hoc filter still pays the
    # full traversal cost of walking into node_modules/venv/etc, which is
    # exactly the slow/noisy case this exists to avoid.
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _YAML_SCAN_EXCLUDED_DIR_NAMES]
        for name in filenames:
            if name.endswith((".yaml", ".yml")):
                files.append(Path(dirpath) / name)
    return files


def check_yaml_files() -> list[str]:
    errors = []
    for path in find_yaml_files():
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid YAML — {exc}")
    return errors


def check_skill_frontmatter() -> list[str]:
    errors: list[str] = []
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


def _display_path(path: Path) -> str:
    # check_bash_snippets()/check_console_snippets() accept an overridable
    # `sources` list (so tests can point them at tmp_path fixtures instead
    # of the real repo) — relative_to(REPO_ROOT) raises ValueError for a
    # path outside it, unlike the other checkers here that only ever see
    # real repo paths.
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _bash_syntax_error(script: str) -> str | None:
    # -n is syntax-check-only — never executes the script (the recipes
    # here do real things like `git submodule add` or `touch`, which must
    # never run as a side effect of linting docs). BASH_ENV is explicitly
    # cleared: a non-interactive bash normally sources it on startup
    # (verified this build's `bash -n` doesn't actually execute it, but
    # that's an implementation detail of one bash version, not a
    # documented guarantee) — this checker shouldn't depend on whatever
    # happens to be in the invoking environment's BASH_ENV.
    env = {**os.environ, "BASH_ENV": ""}
    result = subprocess.run(
        ["bash", "-n"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        return result.stderr.strip()
    return None


def check_bash_snippets(sources: list[Path] = BASH_SNIPPET_SOURCES) -> list[str]:
    errors = []
    for path in sources:
        if not path.is_file():
            errors.append(f"{_display_path(path)}: expected file not found")
            continue
        text = path.read_text()
        for i, block in enumerate(BASH_FENCE_RE.findall(text), start=1):
            error = _bash_syntax_error(block)
            if error:
                errors.append(
                    f"{_display_path(path)}: bash snippet #{i} has a syntax error — {error}"
                )
    return errors


def check_console_snippets(sources: list[Path] = CONSOLE_SNIPPET_SOURCES) -> list[str]:
    errors = []
    for path in sources:
        if not path.is_file():
            errors.append(f"{_display_path(path)}: expected file not found")
            continue
        text = path.read_text()
        for i, block in enumerate(CONSOLE_FENCE_RE.findall(text), start=1):
            commands = "\n".join(
                line[len("$ "):] for line in block.split("\n") if line.startswith("$ ")
            )
            if not commands:
                continue
            error = _bash_syntax_error(commands)
            if error:
                errors.append(
                    f"{_display_path(path)}: console snippet #{i} has a syntax error — {error}"
                )
    return errors


def _strip_fences(text: str) -> str:
    # Fenced code blocks (```...``` / ~~~...~~~) can legitimately contain
    # illustrative "wrong" numbers — e.g. README.md's before/after example
    # of two projects' drifted CLAUDE.md snippets — that aren't this
    # repo's actual live policy and shouldn't be scanned as if they were.
    return ANY_FENCE_RE.sub("", text)


def _extract_mandate_numbers(text: str, topic_word: re.Pattern[str]) -> set[str]:
    # A percentage counts as a mandate statement only if BOTH the topic
    # word (e.g. "coverage") and a mandate-signal word/symbol (minimum,
    # required, below, >=, ...) appear on the SAME line as it — see the
    # registry comment above for why a bare "N% <topic>" isn't enough on
    # its own. Scoped to a single line rather than a character window
    # around the match: a character window bled across adjacent list
    # items in testing, e.g. COMPLETION_CHECKLIST.md's "- [ ] Coverage >=
    # 80% (minimum requirement)" immediately followed by "- [ ] Strive for
    # 90%+ coverage" — a window wide enough to reach "minimum requirement"
    # from the 90% line would have wrongly flagged the aspirational
    # "strive for" stretch goal as a conflicting mandate. Scoping to
    # single lines trades a few missed same-file legitimate mentions that
    # happen to wrap across lines (never counted, never flagged either —
    # safe failure mode) for zero false conflicts from a neighboring line.
    numbers = set()
    for line in text.split("\n"):
        if not (topic_word.search(line) and _MANDATE_SIGNAL_RE.search(line)):
            continue
        for match in _PERCENT_RE.finditer(line):
            numbers.add(match.group(1))
    return numbers


def check_duplicate_policy_numbers(scan_root: Path = REPO_ROOT) -> list[str]:
    errors = []
    for entry in DUPLICATE_POLICY_REGISTRY:
        source_path = scan_root / entry["source_rel"]
        if not source_path.is_file():
            errors.append(f"{entry['source_rel']}: expected source-of-truth file not found")
            continue
        source_numbers = _extract_mandate_numbers(_strip_fences(source_path.read_text()), entry["topic_word"])

        for md_file in sorted(scan_root.rglob("*.md")):
            if ".git" in md_file.parts or md_file == source_path:
                continue
            rel = md_file.relative_to(scan_root)
            rel_str = str(rel)
            if rel_str.startswith(DUPLICATE_POLICY_EXCLUDED_DIR_PREFIXES):
                continue
            if md_file.name in DUPLICATE_POLICY_EXCLUDED_FILENAMES:
                continue

            found_numbers = _extract_mandate_numbers(_strip_fences(md_file.read_text()), entry["topic_word"])
            conflicting = found_numbers - source_numbers
            if conflicting:
                errors.append(
                    f"{rel_str}: states {entry['name']} as {sorted(conflicting)}, "
                    f"but {entry['source_rel']} (source of truth) says "
                    f"{sorted(source_numbers)} — fix the restatement or update the source"
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


def check_manifest_md_sync() -> list[str]:
    # B2: MANIFEST.md is generated from manifest.yaml by
    # tools/generate-manifest.py, not hand-maintained — exact mirror of
    # check_agents_md_sync() above, same drift class, same fix.
    committed = REPO_ROOT / "MANIFEST.md"
    generator = REPO_ROOT / "tools/generate-manifest.py"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        [sys.executable, str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-manifest.py --output MANIFEST.md' and commit the result"
        ]
    return []


def check_gemini_md_sync() -> list[str]:
    # Cross-platform parity: GEMINI.md is generated from CLAUDE.md +
    # .claude/skills/ by tools/generate-gemini-md.sh, exact mirror of
    # check_agents_md_sync() above — same drift class, same fix.
    committed = REPO_ROOT / "GEMINI.md"
    generator = REPO_ROOT / "tools/generate-gemini-md.sh"
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
            f"run 'tools/generate-gemini-md.sh --output GEMINI.md' and commit the result"
        ]
    return []


def check_kilo_rules_sync() -> list[str]:
    # Cross-platform parity: .kilo/rules/agentharness.md is generated by
    # tools/generate-kilo-rules.sh, exact mirror of check_agents_md_sync().
    committed = REPO_ROOT / ".kilo/rules/agentharness.md"
    generator = REPO_ROOT / "tools/generate-kilo-rules.sh"
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
            f"run 'tools/generate-kilo-rules.sh --output .kilo/rules/agentharness.md' and commit the result"
        ]
    return []


def _diff_generated_subdir(tmp_root: Path, subdir_rel: str, regen_hint: str) -> list[str]:
    # Shared by check_copilot_instructions_sync and check_cursor_rules_sync:
    # both own an entire directory of generated files (a variable set —
    # one per language or per skill — not a single fixed path), so drift
    # means comparing the whole subdirectory in both directions: a file
    # the generator produces that isn't committed (drift), and a
    # committed file the generator no longer produces (a stale leftover
    # from a removed language/skill).
    generated_root = tmp_root / subdir_rel
    committed_root = REPO_ROOT / subdir_rel
    generated_files = (
        {p.relative_to(generated_root) for p in generated_root.rglob("*") if p.is_file()}
        if generated_root.is_dir() else set()
    )
    committed_files = (
        {p.relative_to(committed_root) for p in committed_root.rglob("*") if p.is_file()}
        if committed_root.is_dir() else set()
    )
    errors = []
    for rel in sorted(generated_files - committed_files):
        errors.append(f"{subdir_rel}/{rel}: generated but missing from the committed tree — {regen_hint}")
    for rel in sorted(committed_files - generated_files):
        errors.append(f"{subdir_rel}/{rel}: committed but no longer generated — {regen_hint}")
    for rel in sorted(generated_files & committed_files):
        if (generated_root / rel).read_text() != (committed_root / rel).read_text():
            errors.append(f"{subdir_rel}/{rel}: out of sync with its source — {regen_hint}")
    return errors


def check_copilot_instructions_sync() -> list[str]:
    # Cross-platform parity: .github/copilot-instructions.md +
    # .github/instructions/*.instructions.md are generated by
    # tools/generate-copilot-instructions.sh, not hand-maintained.
    generator = REPO_ROOT / "tools/generate-copilot-instructions.sh"
    regen_hint = "run 'tools/generate-copilot-instructions.sh --output-dir .' and commit the result"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["bash", str(generator), str(REPO_ROOT), "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]

        errors = []
        committed_main = REPO_ROOT / ".github/copilot-instructions.md"
        generated_main = tmp_path / ".github/copilot-instructions.md"
        if not committed_main.is_file():
            errors.append(f"{committed_main.relative_to(REPO_ROOT)}: expected file not found")
        elif generated_main.read_text() != committed_main.read_text():
            errors.append(f"{committed_main.relative_to(REPO_ROOT)}: out of sync with its source — {regen_hint}")

        errors += _diff_generated_subdir(tmp_path, ".github/instructions", regen_hint)
        return errors


def check_cursor_rules_sync() -> list[str]:
    # Cross-platform parity: .cursor/rules/*.mdc are generated by
    # tools/generate-cursor-rules.sh — the whole directory is exclusively
    # generator output, so a plain subdirectory diff suffices.
    generator = REPO_ROOT / "tools/generate-cursor-rules.sh"
    regen_hint = "run 'tools/generate-cursor-rules.sh --output-dir .' and commit the result"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["bash", str(generator), str(REPO_ROOT), "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
        return _diff_generated_subdir(tmp_path, ".cursor/rules", regen_hint)


def _check_agent_generator_sync(
    generator_rel: str, output_subdir_rel: str
) -> list[str]:
    # Shared by the four custom-agent-porting generators
    # (Codex/OpenCode/Cursor/Kilo) below — each owns a whole directory
    # of variable-length output (one file per .claude/agents/*.md), the
    # same shape check_cursor_rules_sync() already handles via
    # _diff_generated_subdir().
    generator = REPO_ROOT / generator_rel
    regen_hint = f"run '{generator_rel} --output-dir .' and commit the result"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["bash", str(generator), str(REPO_ROOT), "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"{generator_rel}: failed to run — {result.stderr.strip()}"]
        return _diff_generated_subdir(tmp_path, output_subdir_rel, regen_hint)


def check_codex_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-codex-agents.sh", ".codex/agents"
    )


def check_opencode_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-opencode-agents.sh", ".opencode/agents"
    )


def check_cursor_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-cursor-agents.sh", ".cursor/agents"
    )


def check_kilo_agents_sync() -> list[str]:
    return _check_agent_generator_sync("tools/generate-kilo-agents.sh", ".kilo/agents")


def check_copilot_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-copilot-agents.sh", ".github/agents"
    )


def check_gemini_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-gemini-agents.sh", ".gemini/agents"
    )


def main() -> int:
    errors = []
    errors += check_yaml_files()
    errors += check_skill_frontmatter()
    errors += check_python_snippets()
    errors += check_bash_snippets()
    errors += check_console_snippets()
    errors += check_duplicate_policy_numbers()
    errors += check_agents_md_sync()
    errors += check_manifest_md_sync()
    errors += check_gemini_md_sync()
    errors += check_kilo_rules_sync()
    errors += check_copilot_instructions_sync()
    errors += check_cursor_rules_sync()
    errors += check_codex_agents_sync()
    errors += check_opencode_agents_sync()
    errors += check_cursor_agents_sync()
    errors += check_kilo_agents_sync()
    errors += check_copilot_agents_sync()
    errors += check_gemini_agents_sync()

    if errors:
        print("Content-quality check failed:\n")
        for err in errors:
            print(f"  ✗ {err}")
        print(f"\n{len(errors)} issue(s) found.")
        return 1

    print("Content-quality check passed: YAML parses, skill frontmatter valid, "
          "tested Python/bash/console snippets parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
