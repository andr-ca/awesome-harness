#!/usr/bin/env bash
# ============================================================================
# generate-codex-agents.sh — port .claude/agents/*.md subagent definitions
# to Codex CLI's own subagent config format.
# ============================================================================
#
# Codex CLI supports real sub-agent delegation (a primary agent
# dispatching a task to a separate, specialized agent instance with its
# own model/prompt) via TOML files under .codex/agents/ (or
# ~/.codex/agents/ for global agents) — see
# https://learn.chatgpt.com/docs/agent-configuration/subagents. This is
# a genuinely different mechanism from Codex's routing-only AGENTS.md
# (generate-agents-md.sh) and skill index (.agents/skills/): those cover
# always-on instructions and on-demand skill content the CURRENT agent
# reads; this covers task delegation to a SEPARATE agent instance.
#
# Cross-tool tool-name/permission-scoping is explicitly NOT translated —
# Codex's own tool-name vocabulary is unverified against a live session,
# so asserting a mapping here would be exactly the kind of claim this
# repo's "not verified" caveat exists to avoid (see
# docs/CLIENT_COMPATIBILITY.md's custom-agent section). Ported files
# carry name/description/model and the body verbatim; anyone adopting a
# ported agent needs to re-specify its tool/permission scope for Codex
# by hand.
#
# Usage:
#   tools/generate-codex-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.codex/agents/<name>.toml per
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

# TOML basic-string escaping (backslash, then double quote) is the same
# rule yaml_dquote_escape() already implements for YAML — reused as-is
# rather than duplicated. developer_instructions uses a TOML literal
# multi-line string ('''...''') instead, so the Markdown body embeds
# verbatim with no escaping at all (TOML also trims the one newline
# immediately after the opening ''' automatically, per spec).
generate_agent_toml() {
    local agent_md="$1"
    local name description model body
    name="$(yaml_dquote_escape "$(agent_field "$agent_md" name)")"
    description="$(yaml_dquote_escape "$(agent_field "$agent_md" description)")"
    model="$(yaml_dquote_escape "$(agent_field "$agent_md" model)")"
    body="$(strip_frontmatter "$agent_md")"

    cat <<EOF
# Generated from \`.claude/agents/$(basename "$agent_md")\` by
# tools/generate-codex-agents.sh (https://github.com/andr-ca/agentharness)
# — do not hand-edit; regenerate instead
# (tools/generate-codex-agents.sh --output-dir .). Codex's own
# tool/permission scoping is NOT ported (unverified against a live
# session) — re-specify it here by hand if this agent needs restricted
# tool access.
name = "$name"
description = "$description"
model = "$model"
developer_instructions = '''
$body
'''
EOF
}

mkdir -p "$output_dir/.codex/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_toml "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.codex/agents/$agent.toml"
done < <(list_available_agents "$harness_dir" | sort)
