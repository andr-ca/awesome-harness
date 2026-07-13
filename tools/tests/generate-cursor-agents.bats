#!/usr/bin/env bats
#
# Tests for tools/generate-cursor-agents.sh: ports .claude/agents/*.md
# subagent definitions to Cursor's own subagent format (.cursor/agents/
# — distinct from the existing generate-cursor-rules.sh's
# .cursor/rules/*.mdc, which ports SKILLS, not custom agents). Tool and
# readonly/is_background scoping are deliberately not translated (see
# the generator's own header comment).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-cursor-agents.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-cursor-agents: produces one .md per .claude/agents/*.md, in .cursor/agents/ not .cursor/rules/" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        [ -f "$BATS_TEST_TMPDIR/.cursor/agents/$agent.md" ]
    done
}

@test "generate-cursor-agents: every generated file's frontmatter is valid YAML with name/description/model matching the source" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        run python3 -c "
import yaml
src_fm = yaml.safe_load(open('$agent_md').read().split('---')[1])
out_fm = yaml.safe_load(open('$BATS_TEST_TMPDIR/.cursor/agents/$agent.md').read().split('---')[1])
assert out_fm['name'] == src_fm['name']
assert out_fm['description'] == src_fm['description']
assert out_fm['model'] == src_fm['model']
"
        [ "$status" -eq 0 ]
    done
}

@test "generate-cursor-agents: does not port tools/readonly/is_background" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$BATS_TEST_TMPDIR"/.cursor/agents/*.md; do
        ! grep -q "^tools\|^readonly\|^is_background" "$agent_md"
    done
}

@test "generate-cursor-agents: committed .cursor/agents/*.md match the generator's current output" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.cursor/agents" "$HARNESS_ROOT/.cursor/agents"
}
