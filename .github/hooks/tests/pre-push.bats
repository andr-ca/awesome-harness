#!/usr/bin/env bats
# Tests for .github/hooks/pre-push
#
# Run locally:  bats .github/hooks/tests/pre-push.bats
# Requires: bats-core, pytest, pytest-cov, pyyaml

HOOK="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/pre-push"

setup() {
    # The hook's own bats sweep runs this exact file (it lives in
    # .github/hooks/tests/, right alongside prevent-trunk-commit.bats).
    # Every test here invokes the hook itself, so without this guard a
    # pre-push run would recurse into itself forever. AGENTHARNESS_PRE_PUSH_RUNNING
    # is set by the hook (never by a person running `bats` directly), so
    # this only skips when we're already inside a hook-triggered run.
    if [ -n "${AGENTHARNESS_PRE_PUSH_RUNNING:-}" ]; then
        skip "avoiding recursive pre-push invocation (already inside a pre-push run)"
    fi
}

@test "pre-push: passes cleanly against the repo's current state" {
    run bash "$HOOK"
    # bats doesn't print $output on a bare `[ "$status" -eq 0 ]` failure —
    # print it explicitly so a CI failure here is diagnosable from the log
    # instead of just "status 1, good luck".
    if [ "$status" -ne 0 ]; then
        echo "--- pre-push output (exit $status) ---" >&2
        echo "$output" >&2
    fi
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All pre-push checks passed" ]]
}

@test "pre-push: no-ops for a consumer repo that merely borrows core.hooksPath" {
    # Regression test: this hook must never run agentharness's own test
    # suite against a *different* repo's push just because that repo's
    # core.hooksPath happens to point at .github/hooks here (exactly what
    # tools/setup/harness-link.sh --with-hook does for every consumer).
    # See docs/operational/reviews/gpt-5.6-review-status.md, finding 1,
    # for the original reproduction of this as a live bug.
    consumer_repo="$(mktemp -d)"
    git -C "$consumer_repo" init --quiet

    run bash -c "cd '$consumer_repo' && bash '$HOOK'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "not to agentharness itself" ]]
    [[ "$output" != *"pytest:"* ]]

    rm -rf "$consumer_repo"
}

@test "pre-push: treats a linked worktree as the agentharness repository" {
    primary_repo="$(mktemp -d)"
    linked_worktree="$(mktemp -d)"
    stub_dir="$(mktemp -d)"
    rmdir "$linked_worktree"

    git -C "$primary_repo" init --quiet
    git -C "$primary_repo" config user.email "test@example.com"
    git -C "$primary_repo" config user.name "Test"
    git -C "$primary_repo" commit --quiet --allow-empty -m "initial"
    mkdir -p "$primary_repo/.github/hooks"
    cp "$HOOK" "$primary_repo/.github/hooks/pre-push"
    git -C "$primary_repo" worktree add --quiet -b feature/worktree "$linked_worktree"

    cat > "$stub_dir/bats" <<'STUB'
#!/bin/bash
exit 0
STUB
    cat > "$stub_dir/python3" <<'STUB'
#!/bin/bash
exit 0
STUB
    chmod +x "$stub_dir/bats" "$stub_dir/python3"

    run bash -c "cd '$linked_worktree' && PATH='$stub_dir:$PATH' bash '$primary_repo/.github/hooks/pre-push'"

    git -C "$primary_repo" worktree remove --force "$linked_worktree"
    rm -rf "$primary_repo" "$stub_dir"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All pre-push checks passed" ]]
    [[ "$output" != *"not to agentharness itself"* ]]
}

@test "pre-push: strips repository-local Git environment before fixture suites" {
    repo_root="$(cd "$(dirname "$HOOK")/../.." && pwd)"
    git_dir="$(git -C "$repo_root" rev-parse --absolute-git-dir)"
    stub_dir="$(mktemp -d)"

    cat > "$stub_dir/bats" <<'STUB'
#!/bin/bash
for name in GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES; do
    if [ -n "${!name+x}" ]; then
        echo "repository-local Git variable leaked into bats: $name" >&2
        exit 1
    fi
done
exit 0
STUB
    cat > "$stub_dir/python3" <<'STUB'
#!/bin/bash
for name in GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES; do
    if [ -n "${!name+x}" ]; then
        echo "repository-local Git variable leaked into python: $name" >&2
        exit 1
    fi
done
exit 0
STUB
    chmod +x "$stub_dir/bats" "$stub_dir/python3"

    run env GIT_DIR="$git_dir" GIT_WORK_TREE="$repo_root" \
        PATH="$stub_dir:$PATH" bash "$HOOK"

    if [ "$status" -ne 0 ]; then
        echo "$output" >&2
    fi
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All pre-push checks passed" ]]

    rm -rf "$stub_dir"
}

@test "pre-push: fails clearly when bats is not on PATH" {
    # Exclude every PATH directory that actually contains a `bats`
    # executable — not just pattern-matching "bats" in the directory name
    # (bats-core installs to /usr/local/bin in CI, no "bats" in that
    # name), and not just the first hit from `command -v` (bats-core
    # itself prepends its own libexec/bats-core to PATH while running
    # tests, so there can be two real "bats" directories on PATH at once:
    # that prepended one and wherever it was actually installed).
    stripped_path=""
    IFS=':' read -ra path_entries <<< "$PATH"
    for entry in "${path_entries[@]}"; do
        [ -x "$entry/bats" ] && continue
        stripped_path="${stripped_path:+$stripped_path:}$entry"
    done

    run env PATH="$stripped_path" bash "$HOOK"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "bats not installed" ]]
}

@test "pre-push: fails clearly when pytest is not available" {
    # Shadow python3 earlier in PATH with a stub that fails "-m pytest
    # --version" the same way a real interpreter without pytest installed
    # would, without disturbing the real python3 or bats. Falls back to
    # the real python3's resolved path (not a hardcoded /usr/bin/python3,
    # which may not be the interpreter actions/setup-python put pytest
    # into) for anything else.
    real_python3="$(command -v python3)"
    stub_dir="$(mktemp -d)"
    cat > "$stub_dir/python3" <<STUB
#!/bin/bash
if [ "\$1" = "-m" ] && [ "\$2" = "pytest" ]; then
    exit 1
fi
exec "$real_python3" "\$@"
STUB
    chmod +x "$stub_dir/python3"

    run env PATH="$stub_dir:$PATH" bash "$HOOK"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "pytest not installed" ]]

    rm -rf "$stub_dir"
}

@test "pre-push: blocks a push to a branch locked by another live session" {
    # The branch-lock gate fires before any test suite runs, so this test
    # is fast: a foreign live lock on the pushed branch must exit 1 with
    # the block message. Locks live under AGENTHARNESS_ROOT so the real
    # repo's .agentharness-locks/ is never touched.
    lock_root="$(mktemp -d)"
    mkdir -p "$lock_root/.agentharness-locks"
    sleep 60 &
    other_pid=$!
    cat > "$lock_root/.agentharness-locks/foreign-feature-deadbeef.json" <<JSON
{
  "agent_id": "11111111-2222-3333-4444-555555555555",
  "branch": "feat/locked-elsewhere",
  "feature": "foreign-feature",
  "pid": $other_pid,
  "started_at": "2026-07-16T00:00:00Z",
  "worktree": null
}
JSON

    run bash -c "echo 'refs/heads/feat/locked-elsewhere 1111111 refs/heads/feat/locked-elsewhere 2222222' | AGENTHARNESS_ROOT='$lock_root' bash '$HOOK'"
    kill "$other_pid" 2>/dev/null || true
    rm -rf "$lock_root"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Push blocked" ]]
    [[ "$output" != *"pytest:"* ]]
}
