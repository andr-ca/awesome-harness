#!/usr/bin/env bash
# ============================================================================
# generate-gemini-md.sh — build a GEMINI.md (Gemini CLI's and Antigravity's
# instruction file) from the same CLAUDE.md this repo's own agents read.
# ============================================================================
#
# Gemini CLI reads GEMINI.md (its default context filename, concatenated
# hierarchically from the working directory up to .git, plus a global
# ~/.gemini/GEMINI.md) and supports the same Agent Skills open standard
# progressive-disclosure model as Claude Code and Codex: it injects every
# enabled skill's name+description into the system prompt at session
# start, then calls an `activate_skill` tool to load a skill's full body
# only once it matches the task at hand — see
# https://geminicli.com/docs/cli/skills/. Google Antigravity reads the
# same GEMINI.md filename and gives it precedence over AGENTS.md when
# both exist (see docs/CLIENT_COMPATIBILITY.md).
#
# GEMINI.md therefore follows the exact same shape as AGENTS.md
# (tools/generate-agents-md.sh, P0-06): CLAUDE.md's routing prose plus a
# name+description skill index pointing at .agents/skills/ (already
# populated for every consumer by harness-link.sh) — never full skill
# bodies, which would defeat the point of on-demand loading.
#
# Usage:
#   tools/generate-gemini-md.sh [harness-dir] [--output <path>]
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
# GEMINI.md

Generated from this repo's own `CLAUDE.md` by `tools/generate-gemini-md.sh`
(https://github.com/andr-ca/agentharness) — do not hand-edit; regenerate instead
(`tools/generate-gemini-md.sh --output GEMINI.md`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.agents/skills/` — Gemini CLI's real skill mechanism (the
Agent Skills open standard, shared with Claude Code) injects every
enabled skill's `name`/`description` metadata into the system prompt at
session start, then loads a skill's full body only once its description
matches the task at hand (via its `activate_skill` tool). Google
Antigravity reads this same filename and gives it precedence over
`AGENTS.md` when both exist. The index below exists so that
metadata-scan step has something to match against; it is not a
substitute for reading the matched `SKILL.md` itself.

Gemini CLI also supports `/memory show` (inspect the concatenated
context) and `/memory refresh` (force a re-scan) if this file changes
mid-session.

---

HEADER

    # Reproduced content: CLAUDE.md doesn't itself claim a specific
    # skill-loading mechanism (that's client-specific behavior, not
    # something asserted in this file's text). Headings demoted so its
    # own "# agentharness – Agent Router" H1 doesn't collide with this
    # file's H1.
    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    render_skill_index "$harness_dir" "$skills_dir"
}

generate | write_generated_content
