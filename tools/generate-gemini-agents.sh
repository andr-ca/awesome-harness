#!/usr/bin/env bash
# ============================================================================
# generate-gemini-agents.sh — port .claude/agents/*.md subagent
# definitions to Gemini CLI's own custom-subagent format.
# ============================================================================
#
# Gemini CLI supports real sub-agent delegation: interactions with a
# subagent happen in a separate context loop of its own — invoked
# automatically (task description matched against the subagent's own
# description) or manually via `@subagent-name`. Config is Markdown with
# YAML frontmatter under .gemini/agents/ (or ~/.gemini/agents/ for
# global agents). See https://geminicli.com/docs/core/subagents/.
# Subagents cannot themselves call further subagents — a depth-1 nesting
# limit, the same shape as Codex CLI's own max_depth bound — which does
# not disqualify the mechanism from being real delegation.
#
# NOTE: an earlier pass of this repo's research (docs/CLIENT_COMPATIBILITY.md)
# wrongly classified Gemini CLI as having no delegation at all, having
# conflated the depth-1 nesting limit above with an absence of
# delegation. Corrected the same day it was found — see that doc's
# dated correction note.
#
# Cross-tool tool-name/permission-scoping is explicitly NOT translated,
# same reasoning as every other agent-porting generator here: Gemini's
# own `tools`/`temperature`/`max_turns` fields are real and documented,
# but mapping Claude Code's `tools:` allow-list into Gemini's own
# tool-name vocabulary is unverified against a live session (see
# docs/CLIENT_COMPATIBILITY.md's custom-agent section). Ported files
# carry name/description/model and the body verbatim.
#
# Usage:
#   tools/generate-gemini-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.gemini/agents/<name>.md per
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
\`tools/generate-gemini-agents.sh\` — do not hand-edit; regenerate
instead. Gemini's own \`tools\`/\`temperature\`/\`max_turns\` fields are
NOT ported (unverified against a live session) — re-specify them here
by hand if this agent needs restricted tool access or different
sampling behavior.

---

HEADER
    strip_frontmatter "$agent_md"
}

mkdir -p "$output_dir/.gemini/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_md "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.gemini/agents/$agent.md"
done < <(list_available_agents "$harness_dir" | sort)
