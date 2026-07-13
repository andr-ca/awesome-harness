#!/usr/bin/env bats
#
# Tests for tools/generate-copilot-instructions.sh: repo-wide routing
# rules in .github/copilot-instructions.md (skill index, not skill
# bodies — same shape as AGENTS.md/GEMINI.md/Kilo's rules file), plus
# path-scoped .github/instructions/<lang>.instructions.md files carrying
# an `applyTo` glob copied verbatim from each languages/<lang>/CONVENTIONS.md.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-copilot-instructions.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-copilot-instructions: repo-wide file's skill index lists every skill's name and description, not its body" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    main="$BATS_TEST_TMPDIR/.github/copilot-instructions.md"
    [ -f "$main" ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        grep -q ".agents/skills/$skill/SKILL.md" "$main"
    done
    ! grep -q "Before you commit" "$main"
    grep -q "atomic commits, message format" "$main"
}

@test "generate-copilot-instructions: one .instructions.md per languages/<lang>/CONVENTIONS.md, applyTo copied verbatim" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for lang_dir in "$HARNESS_ROOT"/languages/*/; do
        lang="$(basename "$lang_dir")"
        conventions_md="$lang_dir/CONVENTIONS.md"
        [ -f "$conventions_md" ] || continue
        instructions_md="$BATS_TEST_TMPDIR/.github/instructions/$lang.instructions.md"
        [ -f "$instructions_md" ]
        expected_apply_to="$(grep -m1 '^applyTo: ' "$conventions_md" | sed -E 's/^applyTo: "?//; s/"?$//')"
        actual_apply_to="$(grep -m1 '^applyTo: ' "$instructions_md" | sed -E 's/^applyTo: "?//; s/"?$//')"
        [ "$actual_apply_to" = "$expected_apply_to" ]
    done
}

@test "generate-copilot-instructions: committed files match the generator's current output" {
    # Regression guard duplicating check_copilot_instructions_sync() in
    # tools/verify-content-quality.py so a local 'bats' run alone catches
    # a stale commit too.
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.github/instructions" "$HARNESS_ROOT/.github/instructions"
    diff "$BATS_TEST_TMPDIR/.github/copilot-instructions.md" "$HARNESS_ROOT/.github/copilot-instructions.md"
}
