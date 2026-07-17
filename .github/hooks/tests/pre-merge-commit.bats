#!/usr/bin/env bats
# Tests for .github/hooks/pre-merge-commit
#
# Run locally:  bats .github/hooks/tests/pre-merge-commit.bats
# Requires: bats-core (https://github.com/bats-core/bats-core)

HOOK="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/pre-merge-commit"
PREVENT_TRUNK_HOOK="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/prevent-trunk-commit"

setup() {
    TEST_REPO="$(mktemp -d)"
    cd "$TEST_REPO" || exit 1
}

teardown() {
    cd /tmp || exit 1
    rm -rf "$TEST_REPO"
}

# git init + a throwaway local identity. CI runners have no default git
# identity configured, and any commit (blocked or not) needs one before
# git will even invoke the pre-merge-commit hook, so every test needs this
# instead of relying on the environment already having one.
init_repo() {
    git init -q -b "$1"
    git config user.email "test@example.com"
    git config user.name "Test"
}

install_hook() {
    cp "$HOOK" .git/hooks/pre-merge-commit
    chmod +x .git/hooks/pre-merge-commit
}

@test "pre-merge-commit hook file exists and is executable" {
    [ -x "$HOOK" ]
}

@test "pre-merge-commit hook delegates to prevent-trunk-commit" {
    # Verify the hook calls prevent-trunk-commit
    grep -q "prevent-trunk-commit" "$HOOK"
}

@test "pre-merge-commit hook blocks merge onto main by manual invocation" {
    init_repo main
    # Directly invoke the hook script (simulates git calling it)
    run "$HOOK"
    [ "$status" -ne 0 ]
    [[ "$output" == *"CANNOT COMMIT DIRECTLY TO TRUNK BRANCH"* ]]
}

@test "pre-merge-commit hook blocks merge onto release/* by manual invocation" {
    init_repo release/1.2
    # Directly invoke the hook script
    run "$HOOK"
    [ "$status" -ne 0 ]
    [[ "$output" == *"CANNOT COMMIT DIRECTLY TO TRUNK BRANCH"* ]]
}

@test "pre-merge-commit hook allows merge onto feature branch by manual invocation" {
    init_repo feature/test
    # Directly invoke the hook script
    run "$HOOK"
    [ "$status" -eq 0 ]
}

@test "prevent-trunk-commit (delegated script) blocks the first commit on an unborn main branch" {
    init_repo main
    cp "$PREVENT_TRUNK_HOOK" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    touch file.txt
    git add file.txt
    run git commit -m "test"
    [ "$status" -ne 0 ]
    [[ "$output" == *"CANNOT COMMIT DIRECTLY TO TRUNK BRANCH"* ]]
}
