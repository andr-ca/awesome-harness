#!/usr/bin/env bats
#
# Tests for tools/setup/harness-link.sh — verifies integration script works
#

setup() {
    # Resolve the script under test relative to this test file, not a
    # hardcoded developer path, so this runs in CI and on any machine.
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"

    # Create a temporary directory for test projects
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    # Clean up test directory
    cd /
    rm -rf "$TEST_PROJECT"
}

@test "harness-link.sh: help message shows usage" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Usage" ]]
}

@test "harness-link.sh: requires target project path argument" {
    run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "target project directory is required" ]]
}

@test "harness-link.sh: symlinks individual skills into .claude/skills/" {
    bash "$SCRIPT" "$TEST_PROJECT"

    # The script symlinks each skill individually into .claude/skills/,
    # it does not symlink .claude/skills/ itself.
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills/committing")
    [[ "$target" == *"/.claude/skills/committing" ]]
}

@test "harness-link.sh: --skills filters which skills are linked" {
    bash "$SCRIPT" "$TEST_PROJECT" --skills committing,branching

    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    [ -L "$TEST_PROJECT/.claude/skills/branching" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/python-conventions" ]
}

@test "harness-link.sh: merges .gitignore.template into .gitignore" {
    # Pre-create a .gitignore with some content
    echo "node_modules/" > "$TEST_PROJECT/.gitignore"

    bash "$SCRIPT" "$TEST_PROJECT"

    # Check that .gitignore exists and contains content from both original and template
    [ -f "$TEST_PROJECT/.gitignore" ]
    grep -q "node_modules" "$TEST_PROJECT/.gitignore"
    grep -q "\.env" "$TEST_PROJECT/.gitignore"  # From template
}

@test "harness-link.sh: --with-hook sets core.hooksPath in an existing git repo" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --with-hook

    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]
}

@test "harness-link.sh: --with-hook is a no-op (with warning) when target isn't a git repo yet" {
    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook

    [ "$status" -eq 0 ]
    [[ "$output" =~ "not a git repo" ]]
    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "harness-link.sh: without --with-hook, core.hooksPath is left untouched" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT"

    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "harness-link.sh: is idempotent (run twice safely, same resulting state)" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook
    [ "$status" -eq 0 ]
    initial_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    initial_gitignore=$(sha256sum "$TEST_PROJECT/.gitignore" | cut -d' ' -f1)
    initial_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    # Run again
    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook
    [ "$status" -eq 0 ]
    final_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    final_gitignore=$(sha256sum "$TEST_PROJECT/.gitignore" | cut -d' ' -f1)
    final_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    [ "$initial_links" = "$final_links" ]
    [ "$initial_gitignore" = "$final_gitignore" ]
    [ "$initial_hooks_path" = "$final_hooks_path" ]
}
