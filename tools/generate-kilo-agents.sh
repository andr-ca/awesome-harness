#!/usr/bin/env bash
# ============================================================================
# generate-kilo-agents.sh — port .claude/agents/*.md subagent
# definitions to Kilo Code's own custom-subagent format.
# ============================================================================
#
# Kilo Code supports real sub-agent delegation — a primary agent
# auto-invokes a subagent via its own Task tool when the subagent's
# description matches, or a user manually invokes one with
# `@agent-name` — through Markdown files with YAML frontmatter under
# .kilo/agents/ (or ~/.config/kilo/agents/ for global agents; the
# filename becomes the agent name). See
# https://kilo.ai/docs/customize/custom-subagents.
#
# NOT to be confused with this repo's existing generate-kilo-rules.sh /
# .kilo/rules/agentharness.md: that generator covers Kilo's always-on
# routing rules plus a skill index (content the CURRENT agent reads).
# This generator covers delegation to a SEPARATE agent instance, a
# different Kilo mechanism and a different directory.
#
# Kilo's own `permission`/`permission.task` fields (which scope which
# tools/subagents an agent may use) are NOT ported here — that
# vocabulary is unverified against a live session, and guessing values
# risks asserting behavior this repo can't back up (see
# docs/CLIENT_COMPATIBILITY.md's custom-agent section). Ported files
# carry name/description/model and the body verbatim.
#
# Usage:
#   tools/generate-kilo-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.kilo/agents/<name>.md per
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
\`tools/generate-kilo-agents.sh\` (https://github.com/andr-ca/agentharness)
— do not hand-edit; regenerate
instead. Kilo's own \`permission\`/\`permission.task\` fields are NOT
ported (unverified against a live session) — re-specify them here by
hand if this agent needs restricted tool/subagent access.

---

HEADER
    strip_frontmatter "$agent_md"
}

mkdir -p "$output_dir/.kilo/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_md "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.kilo/agents/$agent.md"
done < <(list_available_agents "$harness_dir" | sort)
