#!/usr/bin/env bash
# ============================================================================
# generate-kilo-rules.sh — build Kilo Code's rules file from the same
# CLAUDE.md this repo's own agents read.
# ============================================================================
#
# Kilo Code auto-discovers every file under .kilo/rules/ (no kilo.jsonc
# wiring needed — the directory itself is the mechanism) and treats their
# combined contents as always-on project instructions, the same role
# CLAUDE.md/AGENTS.md/GEMINI.md play for their respective tools. Kilo
# also recognizes .agents/skills/ as an Agent-Skills-standard-compliant
# path (already populated for every consumer by harness-link.sh), so
# this file — like AGENTS.md and GEMINI.md — only needs routing rules
# plus a name+description skill index, never full skill bodies.
#
# Usage:
#   tools/generate-kilo-rules.sh [harness-dir] [--output <path>]
#
# harness-dir defaults to this script's own repo root. Without --output,
# writes to stdout.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=./setup/harness-link.sh
source "$SCRIPT_DIR/setup/harness-link.sh"
# shellcheck source=./lib/adapter-common.sh
source "$SCRIPT_DIR/lib/adapter-common.sh"

harness_dir=""
# shellcheck disable=SC2034  # used by write_generated_content() in adapter-common.sh
output=""
parse_common_adapter_args "$@"

claude_md="$harness_dir/CLAUDE.md"
skills_dir="$harness_dir/.claude/skills"

if [ ! -f "$claude_md" ]; then
    echo "Error: $claude_md not found." >&2
    exit 1
fi

generate() {
    cat <<'HEADER'
# Kilo Code Rules

Generated from this repo's own `CLAUDE.md` by
`tools/generate-kilo-rules.sh` (https://github.com/andr-ca/agentharness)
— do not hand-edit; regenerate instead
(`tools/generate-kilo-rules.sh --output .kilo/rules/agentharness.md`). A
CI check keeps this file in sync with its source (see
`.github/workflows/ci.yml`'s `content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.agents/skills/` — Kilo Code's real skill mechanism (the
Agent Skills open standard, shared with Claude Code) reads each
`SKILL.md`'s `name`/`description` metadata up front and loads a skill's
full body only once its description matches the task at hand. The index
below exists so that metadata-scan step has something to match against;
it is not a substitute for reading the matched `SKILL.md` itself.

Kilo auto-discovers every file placed under `.kilo/rules/` — no
`kilo.jsonc` entry is required for this file to take effect.

---

HEADER

    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    render_skill_index "$harness_dir" "$skills_dir"
}

generate | write_generated_content
