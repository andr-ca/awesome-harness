#!/usr/bin/env bats
#
# Tests for the .agentharness-publish-mode flag (B1): CLAUDE.md is prose
# an agent reads, not executable, so this can't test agent *behavior* —
# it tests the two things that ARE mechanically checkable: the flag is
# actually gitignored (not just documented as gitignored), and the docs
# that reference it stay internally consistent (same filename everywhere).

setup() {
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "publish-authority: .agentharness-publish-mode is ignored by this repo's own .gitignore" {
    cd "$HARNESS_ROOT"
    run git check-ignore .agentharness-publish-mode
    [ "$status" -eq 0 ]
}

@test "publish-authority: .agentharness-publish-mode is ignored by the consumer .gitignore.template" {
    scratch="$BATS_TEST_TMPDIR/scratch-project"
    mkdir -p "$scratch"
    cd "$scratch"
    git init -q
    cp "$HARNESS_ROOT/.github/.gitignore.template" .gitignore
    touch .agentharness-publish-mode
    run git check-ignore .agentharness-publish-mode
    [ "$status" -eq 0 ]
}

@test "publish-authority: CLAUDE.md documents the exact flag filename used in .gitignore" {
    grep -q '\.agentharness-publish-mode' "$HARNESS_ROOT/CLAUDE.md"
    grep -q '\.agentharness-publish-mode' "$HARNESS_ROOT/.gitignore"
    grep -q '\.agentharness-publish-mode' "$HARNESS_ROOT/.github/.gitignore.template"
    grep -q '\.agentharness-publish-mode' "$HARNESS_ROOT/docs/INTEGRATION.md"
}

@test "publish-authority: CLAUDE.md's default is stated as verify-and-stage, not always-push" {
    run grep -c "Stop before pushing, opening a PR, or auto-implementing recommendations" "$HARNESS_ROOT/CLAUDE.md"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "publish-authority: CLAUDE.md requires checking PR review comments before merging, not just CI" {
    grep -q "Never merge a PR on CI status alone" "$HARNESS_ROOT/CLAUDE.md"
    grep -q "pulls/<n>/comments" "$HARNESS_ROOT/CLAUDE.md"
}

@test "publish-authority: CLAUDE.md requires watching CI to a real terminal state, not reporting in-progress as done" {
    grep -q "Never report a push/merge as done while CI is still running or red" "$HARNESS_ROOT/CLAUDE.md"
    grep -q "gh run rerun <run-id> --failed" "$HARNESS_ROOT/CLAUDE.md"
    grep -q "own resulting CI run" "$HARNESS_ROOT/CLAUDE.md"
}

@test "publish-authority: creating the flag file is a real, working git-ignore round trip" {
    scratch="$BATS_TEST_TMPDIR/scratch-roundtrip"
    mkdir -p "$scratch"
    cd "$scratch"
    git init -q
    git config user.email "test@example.com"
    git config user.name "Test"
    cp "$HARNESS_ROOT/.github/.gitignore.template" .gitignore
    git add .gitignore
    git commit -q -m "init"
    touch .agentharness-publish-mode
    run git status --short --porcelain
    [ "$status" -eq 0 ]
    # An ignored file must not show up as an untracked candidate for commit
    [[ "$output" != *".agentharness-publish-mode"* ]]
}
