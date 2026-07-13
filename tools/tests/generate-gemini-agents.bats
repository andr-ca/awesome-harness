#!/usr/bin/env bats
#
# Tests for tools/generate-gemini-agents.sh: ports .claude/agents/*.md
# subagent definitions to Gemini CLI's own custom-subagent format
# (.gemini/agents/*.md — genuine sub-agent delegation in a separate
# context loop, confirmed against geminicli.com/docs/core/subagents/
# after an earlier research pass wrongly classified Gemini CLI as
# having no delegation at all). Tool/temperature/max_turns scoping is
# deliberately not translated (see the generator's own header comment).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-gemini-agents.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-gemini-agents: produces one .md per .claude/agents/*.md" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        [ -f "$BATS_TEST_TMPDIR/.gemini/agents/$agent.md" ]
    done
}

@test "generate-gemini-agents: every generated file's frontmatter is valid YAML with name/description/model matching the source" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        run python3 -c "
import yaml
src_fm = yaml.safe_load(open('$agent_md').read().split('---')[1])
out_fm = yaml.safe_load(open('$BATS_TEST_TMPDIR/.gemini/agents/$agent.md').read().split('---')[1])
assert out_fm['name'] == src_fm['name']
assert out_fm['description'] == src_fm['description']
assert out_fm['model'] == src_fm['model']
"
        [ "$status" -eq 0 ]
    done
}

@test "generate-gemini-agents: does not port tools/temperature/max_turns" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$BATS_TEST_TMPDIR"/.gemini/agents/*.md; do
        ! grep -q "^tools\|^temperature\|^max_turns" "$agent_md"
    done
}

@test "generate-gemini-agents: committed .gemini/agents/*.md match the generator's current output" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.gemini/agents" "$HARNESS_ROOT/.gemini/agents"
}
