#!/usr/bin/env bash
# ============================================================================
# generate-copilot-agents.sh — port .claude/agents/*.md subagent
# definitions to GitHub Copilot's own custom-agent format.
# ============================================================================
#
# GitHub Copilot (CLI and VS Code) supports real sub-agent delegation:
# the runtime spins up an isolated-context subagent — its own context
# window, so it doesn't clutter the parent's — invoked automatically
# (task description matched against the agent's own description), via
# the `/agent` slash command, by naming the agent explicitly, or
# programmatically (`--agent`); it can run multiple agents in parallel.
# Config is Markdown with YAML frontmatter under .github/agents/ (or
# ~/.copilot/agents/ for global agents, which takes precedence on a name
# collision), file extension `.agent.md`. See
# https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli
# and https://docs.github.com/en/copilot/reference/custom-agents-configuration.
#
# NOTE: an earlier pass of this repo's research (docs/CLIENT_COMPATIBILITY.md)
# wrongly classified Copilot as persona-only, having found only the
# *cloud coding agent's* custom-agent docs (a different Copilot surface)
# without finding the CLI/VS Code mechanism above. Corrected the same
# day it was found — see that doc's dated correction note.
#
# Cross-tool tool-name/permission-scoping is explicitly NOT translated,
# same reasoning as every other agent-porting generator here: Copilot's
# own `tools`/`target`/`disable-model-invocation`/`user-invocable` fields
# are real and documented, but mapping Claude Code's `tools:` allow-list
# into Copilot's own tool-name vocabulary is unverified against a live
# session (see docs/CLIENT_COMPATIBILITY.md's custom-agent section).
# Ported files carry name/description/model and the body verbatim.
#
# Usage:
#   tools/generate-copilot-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.github/agents/<name>.agent.md per
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
\`tools/generate-copilot-agents.sh\` (https://github.com/andr-ca/agentharness)
— do not hand-edit; regenerate
instead. Copilot's own \`tools\`/\`target\`/\`disable-model-invocation\`/
\`user-invocable\` fields are NOT ported (unverified against a live
session) — re-specify them here by hand if this agent needs restricted
tool access or non-default invocation behavior.

---

HEADER
    strip_frontmatter "$agent_md"
}

mkdir -p "$output_dir/.github/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_md "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.github/agents/$agent.agent.md"
done < <(list_available_agents "$harness_dir" | sort)
