#!/usr/bin/env bats
# Tests for tools/agent-lock.sh

setup() {
    # Create a temp dir as the project root with locks dir
    TEST_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_ROOT/.agentharness-locks"
    # Make agent-lock.sh use TEST_ROOT as the project root
    export TEST_ROOT
    export AGENTHARNESS_ROOT="$TEST_ROOT"
    # Use the test's own PID as AGENT_LOCK_PID so locks appear alive
    export AGENT_LOCK_PID="$$"
}

teardown() {
    rm -rf "$TEST_ROOT"
}

LOCK_SCRIPT="$BATS_TEST_DIRNAME/../../tools/agent-lock.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_acquire() {
    local feature="$1"
    local branch="${2:-feat/test}"
    # Run with project root override via subshell env
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "$feature" "$branch" 2>&1) | tail -1
}

_check() {
    local feature="$1"
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" check "$feature" 2>&1) | head -1
}

_release() {
    local feature="$1"
    local agent_id="$2"
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" release "$feature" "$agent_id" 2>&1) | head -1
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@test "acquire: creates a lock file" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "my-feature" "feat/my-feature")
    local slug
    slug="$(echo "my-feature" | tr '[:upper:]' '[:lower:]' | tr ' /' '-')"
    # Check that at least one .json file was created
    local count
    count="$(find "$TEST_ROOT/.agentharness-locks" -name '*.json' | wc -l)"
    [[ $count -ge 1 ]]
}

@test "acquire: returns an agent_id" {
    local id
    id="$(_acquire "my-feature")"
    # UUID-shaped output: 36 chars with dashes
    [[ ${#id} -ge 30 ]]
}

@test "check: FREE when no lock" {
    local result
    result="$(_check "no-such-feature")"
    [[ "$result" == *"FREE"* ]]
}

@test "check: LOCKED after acquire" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "locked-feature" "feat/locked")
    local result
    result="$(_check "locked-feature")"
    [[ "$result" == *"LOCKED"* ]]
}

@test "release: removes lock when agent_id matches" {
    local agent_id
    agent_id="$(_acquire "releaseable-feature")"
    local result
    result="$(_release "releaseable-feature" "$agent_id")"
    [[ "$result" == *"RELEASED"* ]]
    local check_result
    check_result="$(_check "releaseable-feature")"
    [[ "$check_result" == *"FREE"* ]]
}

@test "release: fails when agent_id does not match" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "mine" "feat/mine")
    local result
    result="$(_release "mine" "wrong-agent-id")"
    [[ "$result" == *"FORBIDDEN"* ]] || [[ "$result" == *"NOT FOUND"* ]]
}

@test "acquire: blocked when active lock exists" {
    local first_id
    first_id="$(_acquire "contested" "feat/contested")"
    local rc=0
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "contested" "feat/other") || rc=$?
    [[ $rc -ne 0 ]]
}

@test "suggest-branch: returns a branch name" {
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" suggest-branch "my-feature" 2>&1)"
    [[ "$result" == feat/* ]]
}

@test "list: shows no locks when none exist" {
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" list 2>&1)"
    [[ "$result" == *"No active locks"* ]]
}

@test "clean: removes stale locks" {
    # Write a lock with a non-existent PID (99999999)
    cat > "$TEST_ROOT/.agentharness-locks/stale-abc12345.json" << 'EOF'
{
  "agent_id": "stale-agent",
  "feature": "stale-feature",
  "branch": "feat/stale",
  "worktree": null,
  "started_at": "2000-01-01T00:00:00Z",
  "pid": 99999999
}
EOF
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" clean)
    local count
    count="$(find "$TEST_ROOT/.agentharness-locks" -name 'stale-*.json' | wc -l)"
    [[ $count -eq 0 ]]
}

# ---------------------------------------------------------------------------
# check-branch (branch is the unit of exclusion for pushes)
# ---------------------------------------------------------------------------

_write_foreign_lock() {
    # A lock held by a live process that is NOT an ancestor of this test.
    local branch="$1"
    local pid="$2"
    cat > "$TEST_ROOT/.agentharness-locks/foreign-feature-deadbeef.json" <<JSON
{
  "agent_id": "11111111-2222-3333-4444-555555555555",
  "branch": "$branch",
  "feature": "foreign-feature",
  "pid": $pid,
  "started_at": "2026-07-16T00:00:00Z",
  "worktree": null
}
JSON
}

@test "check-branch: FREE when no locks exist" {
    run bash "$LOCK_SCRIPT" check-branch "feat/anything"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
}

@test "check-branch: blocks when another live session holds the branch" {
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/contested" "$other_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/contested"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
    [[ "$output" =~ "foreign-feature" ]]
}

@test "check-branch: a lock on a different branch does not block" {
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/other-branch" "$other_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/mine"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
}

@test "check-branch: OWNED via AGENTHARNESS_AGENT_ID match" {
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/contested" "$other_pid"
    run env AGENTHARNESS_AGENT_ID="11111111-2222-3333-4444-555555555555" \
        bash "$LOCK_SCRIPT" check-branch "feat/contested"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OWNED" ]]
}

@test "check-branch: OWNED via ancestor pid without env var" {
    # AGENT_LOCK_PID=$$ (the bats process) is an ancestor of the check
    # subshell, so a lock this test acquires is recognized as its own.
    _acquire "my-own-feature" "feat/my-own"
    run bash "$LOCK_SCRIPT" check-branch "feat/my-own"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OWNED" ]]
}

@test "check-branch: stale lock (dead pid) is removed and branch is FREE" {
    # A guaranteed-nonexistent pid (above the kernel's pid_max) instead of
    # a reaped process's pid, which could be recycled on a busy host.
    local dead_pid=$(( $(cat /proc/sys/kernel/pid_max 2>/dev/null || echo 4194304) + 1 ))
    _write_foreign_lock "feat/contested" "$dead_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/contested"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
    [ ! -f "$TEST_ROOT/.agentharness-locks/foreign-feature-deadbeef.json" ]
}

@test "check-branch: owned lock does not mask a foreign live lock on the same branch" {
    _acquire "my-own-feature" "feat/shared"
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/shared" "$other_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/shared"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}
