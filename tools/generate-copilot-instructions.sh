#!/usr/bin/env bash
# ============================================================================
# generate-copilot-instructions.sh — build GitHub Copilot's instruction
# files from the same CLAUDE.md + languages/*/CONVENTIONS.md this repo's
# own agents read.
# ============================================================================
#
# GitHub Copilot (VS Code, github.com, Copilot coding agent) reads
# .github/copilot-instructions.md as a repo-wide, always-applied file,
# plus optional path-scoped .github/instructions/*.instructions.md files
# — each carrying an `applyTo` glob frontmatter field that Copilot uses
# to decide whether the file applies to the path currently being edited.
# See https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
# and https://code.visualstudio.com/docs/agent-customization/custom-instructions.
#
# This repo's languages/*/CONVENTIONS.md files already carry their own
# `applyTo` frontmatter (e.g. languages/python/CONVENTIONS.md's
# `applyTo: "*.py"`) — written for exactly this purpose but never
# actually wired into a real .github/instructions/ file until now. This
# generator reuses that existing frontmatter as the source of truth
# rather than hardcoding glob patterns a second time.
#
# Copilot also supports the Agent Skills open standard (added to VS
# Code's agent mode, April 2026) and recognizes .agents/skills/ as a
# compatibility path — already populated for every consumer by
# harness-link.sh, so this generator (like generate-agents-md.sh and
# generate-gemini-md.sh) only needs routing rules + a skill index, never
# full skill bodies, in copilot-instructions.md itself.
#
# Usage:
#   tools/generate-copilot-instructions.sh [harness-dir] [--output-dir <dir>]
#
# Writes:
#   <output-dir>/.github/copilot-instructions.md
#   <output-dir>/.github/instructions/<lang>.instructions.md  (one per
#     languages/<lang>/CONVENTIONS.md this repo ships)
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
languages_dir="$harness_dir/languages"

if [ ! -f "$claude_md" ]; then
    echo "Error: $claude_md not found." >&2
    exit 1
fi

generate_repo_wide() {
    cat <<'HEADER'
# GitHub Copilot Instructions

Generated from this repo's own `CLAUDE.md` by
`tools/generate-copilot-instructions.sh` — do not hand-edit; regenerate
instead (`tools/generate-copilot-instructions.sh --output-dir .`). A CI
check keeps this file in sync with its source (see
`.github/workflows/ci.yml`'s `content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.agents/skills/` — Copilot's real skill mechanism (the
Agent Skills open standard, shared with Claude Code, added to VS Code's
agent mode in April 2026) reads each `SKILL.md`'s `name`/`description`
metadata up front and loads a skill's full body only once its
description matches the task at hand. The index below exists so that
metadata-scan step has something to match against; it is not a
substitute for reading the matched `SKILL.md` itself.

Path-specific conventions live in `.github/instructions/*.instructions.md`
instead of here — each one only applies when a matching file is open,
via its own `applyTo` frontmatter.

---

HEADER

    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    render_skill_index "$harness_dir" "$skills_dir"
}

# One .github/instructions/<lang>.instructions.md per languages/<lang>/
# CONVENTIONS.md this repo ships, reusing that file's own `applyTo` and
# `description` frontmatter instead of restating the glob pattern here —
# the same "one source of truth" principle applied everywhere else in
# this repo's generators.
generate_language_instructions() {
    local conventions_md="$1" lang_name="$2"
    local apply_to description
    apply_to="$(frontmatter_field "$conventions_md" applyTo)"
    description="$(frontmatter_field "$conventions_md" description)"

    cat <<EOF
---
applyTo: "$apply_to"
description: "$description"
---

EOF
    cat <<HEADER
Generated from \`languages/$lang_name/CONVENTIONS.md\` by
\`tools/generate-copilot-instructions.sh\` — do not hand-edit; regenerate
instead. Only applied by Copilot when editing a file matching
\`$apply_to\`.

---

HEADER

    strip_frontmatter "$conventions_md" | demote_headings
}

mkdir -p "$output_dir/.github/instructions"

generate_repo_wide | squeeze_blank_lines > "$output_dir/.github/copilot-instructions.md"

for lang_dir in "$languages_dir"/*/; do
    lang_name="$(basename "$lang_dir")"
    conventions_md="$lang_dir/CONVENTIONS.md"
    [ -f "$conventions_md" ] || continue
    generate_language_instructions "$conventions_md" "$lang_name" \
        | squeeze_blank_lines > "$output_dir/.github/instructions/$lang_name.instructions.md"
done
