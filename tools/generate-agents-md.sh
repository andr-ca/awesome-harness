#!/usr/bin/env bash
# ============================================================================
# generate-agents-md.sh — build an AGENTS.md (Codex CLI's instruction file)
# from the same CLAUDE.md this repo's own agents read.
# ============================================================================
#
# P0-06: Codex CLI's real skill mechanism (the Agent Skills open standard,
# shared with Claude Code since Dec 2025) discovers skills by scanning
# .agents/skills/ up from the working directory to the repo root, reading
# only each SKILL.md's name+description metadata up front, and loading a
# skill's full body only once its description matches the task at hand —
# see https://developers.openai.com/codex/skills. It is NOT true that
# Codex has no on-demand loading; it uses the same progressive-disclosure
# model Claude Code does. harness-link.sh installs every skill under
# .agents/skills/ alongside .claude/skills/ (same source, same SKILL.md)
# specifically so this works for a consumer project too.
#
# AGENTS.md therefore only needs repo-wide routing rules (from CLAUDE.md)
# plus a lightweight skill index — name + description, not full bodies —
# so Codex's own metadata-scan step has something to match against even
# before it lists .agents/skills/ itself. Concatenating every skill body
# here would defeat the point: it would front-load unrelated Python,
# error-handling, and agent-loop material into every task regardless of
# relevance, the exact problem this redesign fixes (previously an 880-line
# adapter; see docs/INTEGRATION.md's Codex section for the measured
# before/after).
#
# Usage:
#   tools/generate-agents-md.sh [harness-dir] [--output <path>]
#
# harness-dir defaults to this script's own repo root. Without --output,
# writes to stdout.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sourced (not executed) so its dispatch never runs — see the
# BASH_SOURCE-vs-$0 guard at the bottom of harness-link.sh. Reuses
# list_available_skills and its own HARNESS_DIR computation instead of
# reimplementing skill discovery here.
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
# AGENTS.md

Generated from this repo's own `CLAUDE.md` by `tools/generate-agents-md.sh`
— do not hand-edit; regenerate instead
(`tools/generate-agents-md.sh --output AGENTS.md`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.agents/skills/` — Codex CLI's real skill mechanism (the
Agent Skills open standard, shared with Claude Code) scans that
directory from the working directory up to the repo root, reads each
`SKILL.md`'s `name`/`description` metadata up front, and loads a skill's
full body only once its description matches the task at hand. The index
below exists so that metadata-scan step has something to match against;
it is not a substitute for reading the matched `SKILL.md` itself.

---

HEADER

    # Reproduced content: CLAUDE.md doesn't itself claim a specific
    # skill-loading mechanism (that's client-specific behavior, not
    # something asserted in this file's text). Headings demoted (see
    # above) so its own "# agentharness – Agent Router" H1 doesn't
    # collide with this file's H1.
    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    render_skill_index "$harness_dir" "$skills_dir"
}

generate | write_generated_content
