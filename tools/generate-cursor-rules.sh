#!/usr/bin/env bash
# ============================================================================
# generate-cursor-rules.sh — build Cursor's rules files from the same
# CLAUDE.md + skills this repo's own agents read.
# ============================================================================
#
# Cursor is the one platform researched with no confirmed Agent Skills
# (SKILL.md) support. Its native mechanism is structurally different:
# .cursor/rules/*.mdc files, each with `description`/`globs`/
# `alwaysApply` frontmatter and four activation modes (Always,
# Auto-Attached-by-glob, Agent-Requested-by-description, Manual). See
# https://docs.cursor.com/context/rules.
#
# This generator produces two kinds of .mdc file:
#   - agentharness-router.mdc: alwaysApply: true, CLAUDE.md's routing
#     prose as body — Cursor's closest analog to AGENTS.md/GEMINI.md's
#     always-on file.
#   - one <skill-name>.mdc per skill under .claude/skills/, with no
#     `globs` set so the rule activates in Agent-Requested mode: Cursor's
#     agent reads the `description` (copied verbatim from that skill's
#     own SKILL.md frontmatter) and decides whether to pull the full
#     rule body in — the closest native analog to SKILL.md's own
#     progressive disclosure, since Cursor has no metadata-then-body
#     loading step of its own to delegate to.
#
# Usage:
#   tools/generate-cursor-rules.sh [harness-dir] [--output-dir <dir>]
#
# Writes:
#   <output-dir>/.cursor/rules/agentharness-router.mdc
#   <output-dir>/.cursor/rules/<skill-name>.mdc  (one per .claude/skills/*)
#
# harness-dir and output-dir both default to this script's own repo
# root, so running with no arguments regenerates this repo's own
# dogfooded files in place.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=./setup/harness-link.sh
source "$SCRIPT_DIR/setup/harness-link.sh"
# shellcheck source=./lib/adapter-common.sh
source "$SCRIPT_DIR/lib/adapter-common.sh"

harness_dir=""
output_dir=""
parse_multi_file_adapter_args "$@"

claude_md="$harness_dir/CLAUDE.md"
skills_dir="$harness_dir/.claude/skills"

if [ ! -f "$claude_md" ]; then
    echo "Error: $claude_md not found." >&2
    exit 1
fi

generate_router() {
    cat <<'HEADER'
---
description: "agentharness repo-wide routing rules — always applied"
alwaysApply: true
---

HEADER
    cat <<'BODY'
Generated from this repo's own `CLAUDE.md` by
`tools/generate-cursor-rules.sh` (https://github.com/andr-ca/agentharness)
— do not hand-edit; regenerate instead
(`tools/generate-cursor-rules.sh --output-dir .`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

This file covers repo-wide routing rules only. Cursor has no confirmed
support for the Agent Skills open standard (SKILL.md) — each skill under
`.claude/skills/` is instead mirrored here as its own
`.cursor/rules/<skill-name>.mdc`, with that skill's own `description`
copied into the rule's frontmatter and no `globs` set. That makes each
rule Agent-Requested: Cursor's agent reads the description and decides
whether to pull the full rule body in, the closest native analog to
SKILL.md's own progressive disclosure.

---

BODY

    demote_headings < "$claude_md"
}

# One .cursor/rules/<skill-name>.mdc per .claude/skills/<skill-name>/,
# reusing that skill's own SKILL.md `description` frontmatter verbatim
# instead of restating it — the same "one source of truth" principle
# applied everywhere else in this repo's generators. No `globs` set:
# Agent-Requested activation, not Auto-Attached, since these skills are
# task-shaped, not file-extension-shaped.
generate_skill_rule() {
    local skill_md="$1"
    local description
    description="$(yaml_dquote_escape "$(skill_description "$skill_md")")"

    cat <<EOF
---
description: "$description"
---

EOF
    strip_frontmatter "$skill_md" | demote_headings
}

mkdir -p "$output_dir/.cursor/rules"

generate_router | squeeze_blank_lines > "$output_dir/.cursor/rules/agentharness-router.mdc"

while IFS= read -r skill; do
    [ -z "$skill" ] && continue
    skill_md="$skills_dir/$skill/SKILL.md"
    [ -f "$skill_md" ] || continue
    generate_skill_rule "$skill_md" \
        | squeeze_blank_lines > "$output_dir/.cursor/rules/$skill.mdc"
done < <(list_available_skills "$harness_dir" | sort)
