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

# Install BOTH the dispatcher and the script it delegates to: the
# dispatcher resolves prevent-trunk-commit relative to its own directory,
# so copying pre-merge-commit alone would fail on the missing file rather
# than exercising trunk protection.
install_hooks() {
    cp "$HOOK" .git/hooks/pre-merge-commit
    cp "$PREVENT_TRUNK_HOOK" .git/hooks/prevent-trunk-commit
    chmod +x .git/hooks/pre-merge-commit .git/hooks/prevent-trunk-commit
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

@test "git merge --no-ff onto main is blocked end-to-end via .git/hooks" {
    init_repo main
    touch base.txt
    git add base.txt
    git commit -q -m "base" --no-verify
    git checkout -q -b feature/test
    touch feat.txt
    git add feat.txt
    git commit -q -m "feature"
    git checkout -q main
    install_hooks
    run git merge --no-ff -m "merge feature" feature/test
    [ "$status" -ne 0 ]
    [[ "$output" == *"CANNOT COMMIT DIRECTLY TO TRUNK BRANCH"* ]]
    # The merge commit must not have been created
    [ "$(git rev-list --count HEAD)" -eq 1 ]
}

@test "git merge --no-ff between feature branches is allowed end-to-end" {
    init_repo feature/branch1
    touch base.txt
    git add base.txt
    git commit -q -m "base"
    git checkout -q -b feature/branch2
    touch feat.txt
    git add feat.txt
    git commit -q -m "feature"
    git checkout -q feature/branch1
    install_hooks
    run git merge --no-ff -m "merge branch2" feature/branch2
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
