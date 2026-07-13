#!/usr/bin/env bash
# ============================================================================
# verify-skill-symlinks.sh — verify the .agents/skills/ compatibility
# symlinks stay 1:1 with .claude/skills/ (the real skill directories).
# ============================================================================
#
# .claude/skills/<name>/ holds the real skill (SKILL.md plus any bundled
# resources). Every non-Claude tool that speaks the Agent Skills standard
# (Codex CLI, GitHub Copilot, Gemini CLI, Kilo Code, OpenCode, ...) reads
# instead from .agents/skills/<name>, which this repo populates as a
# relative symlink back to ../../.claude/skills/<name>.
#
# Why this needs its own check: if a skill is added under .claude/skills/
# without its matching .agents/skills/ symlink (or a symlink is left
# dangling, points somewhere unexpected, or a bundled-resource symlink
# inside a skill breaks), every one of those tools silently stops seeing
# that skill while Claude Code still does. Worse, the generated skill
# index in AGENTS.md / .github/copilot-instructions.md / GEMINI.md is
# built from .claude/skills/, so it would still list the skill — making
# the drift invisible without a dedicated invariant check.
#
# Verifies, for a given repo root (default: this script's own repo):
#   1. every .claude/skills/<name>/ containing a SKILL.md has a matching
#      .agents/skills/<name> that is a symlink resolving to it;
#   2. every .agents/skills/<name> is a symlink, resolves (not dangling),
#      and maps back to a real .claude/skills/<name> (no orphan/foreign
#      targets);
#   3. every bundled-resource symlink inside .claude/skills/** resolves
#      (e.g. agentic-loops/agent_loop.py -> ../../../patterns/...).
#
# Usage: bash tools/verify-skill-symlinks.sh [repo-root]
# Exit codes: 0 = all good, 1 = a mismatch / dangling / orphan symlink.
# ============================================================================
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
claude_skills="$REPO_ROOT/.claude/skills"
agents_skills="$REPO_ROOT/.agents/skills"

fail=0
note_fail() {
    echo "  ✗ $1" >&2
    fail=1
}

# Canonicalize a directory path (resolve symlinks) portably — macOS
# readlink has no -f, so use a cd + pwd -P subshell instead.
canonical_dir() { (cd "$1" 2>/dev/null && pwd -P); }

if [ ! -d "$claude_skills" ]; then
    echo "ERROR: $claude_skills not found" >&2
    exit 1
fi
if [ ! -d "$agents_skills" ]; then
    echo "  ✗ .agents/skills/ is missing entirely — no skill is visible to" >&2
    echo "    Agent-Skills-standard tools (Codex, Copilot, Gemini, ...)." >&2
    exit 1
fi

echo "Verifying .claude/skills/ <-> .agents/skills/ symlinks..."

# 1. Every real skill has a resolving symlink pointing at it.
for skill_md in "$claude_skills"/*/SKILL.md; do
    [ -e "$skill_md" ] || continue   # skip the literal glob when no matches
    name="$(basename "$(dirname "$skill_md")")"
    link="$agents_skills/$name"

    if [ ! -L "$link" ]; then
        if [ -e "$link" ]; then
            note_fail "$name: .agents/skills/$name exists but is not a symlink"
        else
            note_fail "$name: .claude/skills/$name/SKILL.md has no .agents/skills/$name symlink"
        fi
        continue
    fi
    if [ ! -e "$link" ]; then
        note_fail "$name: .agents/skills/$name is a dangling symlink (target '$(readlink "$link")' does not resolve)"
        continue
    fi
    if [ "$(canonical_dir "$link")" != "$(canonical_dir "$claude_skills/$name")" ]; then
        note_fail "$name: .agents/skills/$name resolves to '$(canonical_dir "$link")', expected '$(canonical_dir "$claude_skills/$name")'"
        continue
    fi
    echo "  ✓ $name"
done

# 2. No orphan symlinks: every .agents/skills/<name> maps back to a real skill.
for link in "$agents_skills"/*; do
    [ -e "$link" ] || [ -L "$link" ] || continue   # skip literal glob / nothing there
    name="$(basename "$link")"
    if [ ! -L "$link" ]; then
        note_fail "$name: .agents/skills/$name is not a symlink (should point at ../../.claude/skills/$name)"
        continue
    fi
    if [ ! -e "$claude_skills/$name/SKILL.md" ]; then
        note_fail "$name: .agents/skills/$name is an orphan — no .claude/skills/$name/SKILL.md behind it"
    fi
done

# 3. Every bundled-resource symlink inside a real skill resolves.
while IFS= read -r -d '' l; do
    if [ ! -e "$l" ]; then
        note_fail "bundled resource ${l#"$REPO_ROOT"/} is a dangling symlink (target '$(readlink "$l")')"
    fi
done < <(find "$claude_skills" -type l -print0)

if [ "$fail" -ne 0 ]; then
    echo "Skill symlink verification FAILED." >&2
    exit 1
fi
echo "All skill symlinks resolve 1:1 with .claude/skills/."
