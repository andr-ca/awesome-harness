#!/usr/bin/env bats
#
# Tests for tools/generate-agents-md.sh (P2-02, redesigned P0-06): AGENTS.md
# is routing rules only, from CLAUDE.md — skill bodies are NOT concatenated
# in. Codex CLI discovers skills on demand from .agents/skills/, the same
# progressive-disclosure mechanism (the Agent Skills open standard) Claude
# Code uses for .claude/skills/. These tests replace the old "every skill's
# full body is always included" assertions (the premise P0-06 found false)
# with behavioral tests: discovery, trigger-matching metadata, path
# resolution, and context size.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-agents-md.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-agents-md: skill index lists every installed skill's name and description, not its body" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [[ "$output" =~ ".agents/skills/$skill/SKILL.md" ]]
    done
    # committing/SKILL.md's own body has a "## Before you commit" heading —
    # that must NOT leak into AGENTS.md; only the frontmatter description does.
    [[ "$output" != *"Before you commit"* ]]
    [[ "$output" =~ "atomic commits, message format" ]]
}

@test "generate-agents-md: documents the real Codex on-demand skill mechanism, not the old always-included claim" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"loaded on demand from"*".agents/skills/"* ]]
    [[ "$output" != *"Codex has no on-demand skill-loading mechanism"* ]]
    [[ "$output" == *"loads a skill's"* ]]
    [[ "$output" == *"full body only once its description matches"* ]]
}

@test "generate-agents-md: path resolution — every referenced .agents/skills/*/SKILL.md path exists on disk" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [ -e "$HARNESS_ROOT/.agents/skills/$skill/SKILL.md" ]
    done
}

@test "generate-agents-md: context size — output is a small fraction of concatenating every skill's full body" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    output_bytes="${#output}"
    full_body_bytes=0
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill_md="$skill_dir/SKILL.md"
        [ -f "$skill_md" ] || continue
        bytes="$(wc -c < "$skill_md")"
        full_body_bytes=$((full_body_bytes + bytes))
    done
    # The old design concatenated every skill body in full (880 lines /
    # 33.7KB at the time P0-06 was filed); the redesigned index alone must
    # stay well under half of what just the skill bodies weigh on their own.
    [ "$output_bytes" -lt $((full_body_bytes / 2)) ]
}

@test "generate-agents-md: --output writes to a file instead of stdout" {
    out="$BATS_TEST_TMPDIR/AGENTS.md"
    run bash "$SCRIPT" --output "$out"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$out" ]
    grep -q "committing/SKILL.md" "$out"
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
