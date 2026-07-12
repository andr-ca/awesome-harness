#!/usr/bin/env bats
#
# Tests for tools/generate-agents-md.sh (P2-02): the Codex AGENTS.md
# adapter generated from CLAUDE.md + .claude/skills/, not hand-maintained.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-agents-md.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-agents-md: output contains every installed skill by name" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [[ "$output" =~ "### Skill: $skill" ]]
    done
}

@test "generate-agents-md: documents the on-demand-vs-always-included distinction for Codex" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Codex has no on-demand skill-loading mechanism" ]]
    [[ "$output" =~ "has not been verified against a real Codex CLI session" ]]
}

@test "generate-agents-md: strips SKILL.md frontmatter from the skill body" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    # The frontmatter's own 'name:' line shouldn't leak into the output —
    # only the '### Skill: <name>' heading this script generates itself.
    [[ "$output" != *"name: committing"* ]]
    [[ "$output" =~ "### Skill: committing" ]]
}

@test "generate-agents-md: --output writes to a file instead of stdout" {
    out="$BATS_TEST_TMPDIR/AGENTS.md"
    run bash "$SCRIPT" --output "$out"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$out" ]
    grep -q "### Skill: committing" "$out"
}

@test "generate-agents-md: committed AGENTS.md at repo root matches the generator's current output" {
    # Regression guard for the same drift class fixed for docs in P1-13 —
    # this is also asserted in CI via tools/verify-content-quality.py's
    # check_agents_md_sync(), duplicated here so a local 'bats' run alone
    # catches a stale commit too.
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    committed="$(cat "$HARNESS_ROOT/AGENTS.md")"
    [ "$output" = "$committed" ]
}
