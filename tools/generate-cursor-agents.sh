#!/usr/bin/env bash
# ============================================================================
# generate-cursor-agents.sh — port .claude/agents/*.md subagent
# definitions to Cursor's own subagent format.
# ============================================================================
#
# Cursor supports real sub-agent delegation — a parent agent spawns a
# subagent in a separate thread, optionally in the background — through
# YAML-frontmatter Markdown files under .cursor/agents/. See
# https://cursor.com/docs/context/subagents.
#
# NOT to be confused with this repo's existing generate-cursor-rules.sh
# / .cursor/rules/*.mdc: that generator ports on-demand SKILLS (content
# the current agent loads inline, since Cursor has no Agent Skills
# support) into a completely different Cursor feature and directory.
# This generator ports CUSTOM AGENTS (delegation to a separate agent
# instance) into .cursor/agents/ instead — same source repo
# (.claude/skills/ vs. .claude/agents/), different Cursor mechanism,
# different output directory. Don't conflate the two.
#
# Cursor's own `readonly`/`is_background` fields are NOT set here —
# their default semantics are unverified against a live session, and
# guessing a value risks asserting behavior this repo can't back up
# (see docs/CLIENT_COMPATIBILITY.md's custom-agent section). Tool/model
# scoping beyond the source's own `model` field is likewise not
# translated. Ported files carry name/description/model and the body
# verbatim.
#
# Usage:
#   tools/generate-cursor-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.cursor/agents/<name>.md per
# .claude/agents/<name>.md this repo (or a consumer project) defines.
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

agents_dir="$harness_dir/.claude/agents"

generate_agent_md() {
    local agent_md="$1"
    local name description model
    name="$(agent_field "$agent_md" name)"
    description="$(yaml_dquote_escape "$(agent_field "$agent_md" description)")"
    model="$(agent_field "$agent_md" model)"

    cat <<EOF
---
name: $name
description: "$description"
model: $model
---

EOF
    cat <<HEADER
Generated from \`.claude/agents/$(basename "$agent_md")\` by
\`tools/generate-cursor-agents.sh\` — do not hand-edit; regenerate
instead. Cursor's own \`readonly\`/\`is_background\` fields and
tool/permission scoping are NOT ported (unverified against a live
session) — re-specify them here by hand if this agent needs them.

---

HEADER
    strip_frontmatter "$agent_md"
}

mkdir -p "$output_dir/.cursor/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_md "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.cursor/agents/$agent.md"
done < <(list_available_agents "$harness_dir" | sort)
