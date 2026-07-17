#!/usr/bin/env bash
# ============================================================================
# generate-opencode-agents.sh — port .claude/agents/*.md subagent
# definitions to OpenCode's own custom-agent format.
# ============================================================================
#
# OpenCode supports real sub-agent delegation — auto-invoked by a
# primary agent when a subagent's description matches the task, manually
# via @mention, or via its own Task tool — through Markdown files with
# YAML frontmatter under .opencode/agents/ (or ~/.config/opencode/agents/
# for global agents), the closest structural match to Claude Code's own
# .claude/agents/*.md of any researched platform. See
# https://opencode.ai/docs/agents/. This is a different mechanism from
# OpenCode's routing-only AGENTS.md (already this repo's own AGENTS.md,
# since OpenCode reads that filename directly) and its Agent-Skills-standard
# skill discovery: those cover always-on instructions and on-demand skill
# content the CURRENT agent reads; this covers delegation to a SEPARATE
# agent instance.
#
# Cross-tool tool-name/permission-scoping is explicitly NOT translated —
# see docs/CLIENT_COMPATIBILITY.md's custom-agent section for why (same
# reasoning as every other agent-porting generator here). Ported files
# carry name/description/model and the body verbatim.
#
# Usage:
#   tools/generate-opencode-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.opencode/agents/<name>.md per
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
\`tools/generate-opencode-agents.sh\` (https://github.com/andr-ca/agentharness)
— do not hand-edit; regenerate
instead. OpenCode's own tool/permission scoping is NOT ported
(unverified against a live session) — re-specify it here by hand if
this agent needs restricted tool access.

---

HEADER
    strip_frontmatter "$agent_md"
}

mkdir -p "$output_dir/.opencode/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_md "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.opencode/agents/$agent.md"
done < <(list_available_agents "$harness_dir" | sort)
