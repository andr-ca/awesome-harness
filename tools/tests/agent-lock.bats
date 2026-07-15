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
    result="$((cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" suggest-branch "my-feature") 2>&1)"
    [[ "$result" == feat/* ]]
}

@test "list: shows no locks when none exist" {
    local result
    result="$((cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" list) 2>&1)"
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
