#!/usr/bin/env bats
# Tests for tools/check-file-placement.sh

setup() {
    TEST_ROOT="$(mktemp -d)"
    export TEST_ROOT
    export AGENTHARNESS_ROOT="$TEST_ROOT"
    # Create a fake git repo so git diff --cached works
    (cd "$TEST_ROOT" && git init -q && git config user.email "test@test.com" && git config user.name "Test")
}

teardown() {
    rm -rf "$TEST_ROOT"
}

CHECK_SCRIPT="$BATS_TEST_DIRNAME/../../tools/check-file-placement.sh"

_run_check() {
    bash "$CHECK_SCRIPT" "$TEST_ROOT" 2>&1
    return $?
}

# ---------------------------------------------------------------------------
# No config file
# ---------------------------------------------------------------------------

@test "check: exits 0 when no config file exists" {
    # Stage a new file
    echo "content" > "$TEST_ROOT/newfile.txt"
    (cd "$TEST_ROOT" && git add newfile.txt)
    run bash "$CHECK_SCRIPT" "$TEST_ROOT"
    [[ $status -eq 0 ]]
}

# ---------------------------------------------------------------------------
# Root not guarded
# ---------------------------------------------------------------------------

@test "check: exits 0 when root not guarded and file added to root" {
    cat > "$TEST_ROOT/.agentharness-guarded-paths.json" << 'EOF'
{
  "schema_version": 1,
  "guard_root_level_new_items": false,
  "guarded_dirs": ["src/", "docs/"],
  "guarded_root_files": [],
  "message": "test"
}
EOF
    echo "content" > "$TEST_ROOT/newfile.txt"
    (cd "$TEST_ROOT" && git add newfile.txt)
    run bash "$CHECK_SCRIPT" "$TEST_ROOT"
    [[ $status -eq 0 ]]
}

# ---------------------------------------------------------------------------
# Root guarded — new root file blocked
# ---------------------------------------------------------------------------

@test "check: exits 1 when root guarded and new root file staged" {
    cat > "$TEST_ROOT/.agentharness-guarded-paths.json" << 'EOF'
{
  "schema_version": 1,
  "guard_root_level_new_items": true,
  "guarded_dirs": [],
  "guarded_root_files": [".gitignore"],
  "message": "test"
}
EOF
    echo "content" > "$TEST_ROOT/newfile.txt"
    (cd "$TEST_ROOT" && git add newfile.txt)
    local rc=0
    bash "$CHECK_SCRIPT" "$TEST_ROOT" 2>/dev/null || rc=$?
    [[ $rc -ne 0 ]]
}

# ---------------------------------------------------------------------------
# Guarded directory — file blocked
# ---------------------------------------------------------------------------

@test "check: exits 1 when file added to guarded directory" {
    cat > "$TEST_ROOT/.agentharness-guarded-paths.json" << 'EOF'
{
  "schema_version": 1,
  "guard_root_level_new_items": false,
  "guarded_dirs": ["docs/"],
  "guarded_root_files": [],
  "message": "test"
}
EOF
    mkdir -p "$TEST_ROOT/docs"
    echo "content" > "$TEST_ROOT/docs/newfile.md"
    (cd "$TEST_ROOT" && git add docs/newfile.md)
    local rc=0
    bash "$CHECK_SCRIPT" "$TEST_ROOT" 2>/dev/null || rc=$?
    [[ $rc -ne 0 ]]
}

# ---------------------------------------------------------------------------
# Non-guarded directory — file allowed
# ---------------------------------------------------------------------------

@test "check: exits 0 when file added to non-guarded directory" {
    cat > "$TEST_ROOT/.agentharness-guarded-paths.json" << 'EOF'
{
  "schema_version": 1,
  "guard_root_level_new_items": false,
  "guarded_dirs": ["docs/"],
  "guarded_root_files": [],
  "message": "test"
}
EOF
    mkdir -p "$TEST_ROOT/tmp"
    echo "content" > "$TEST_ROOT/tmp/workfile.txt"
    (cd "$TEST_ROOT" && git add tmp/workfile.txt)
    run bash "$CHECK_SCRIPT" "$TEST_ROOT"
    [[ $status -eq 0 ]]
}

# ---------------------------------------------------------------------------
# Error message content
# ---------------------------------------------------------------------------

@test "check: error message mentions FILE PLACEMENT POLICY" {
    cat > "$TEST_ROOT/.agentharness-guarded-paths.json" << 'EOF'
{
  "schema_version": 1,
  "guard_root_level_new_items": true,
  "guarded_dirs": [],
  "guarded_root_files": [],
  "message": "test"
}
EOF
    echo "content" > "$TEST_ROOT/blocked.txt"
    (cd "$TEST_ROOT" && git add blocked.txt)
    local output
    output="$(bash "$CHECK_SCRIPT" "$TEST_ROOT" 2>&1 || true)"
    [[ "$output" == *"FILE PLACEMENT POLICY"* ]]
}

@test "check: exits 0 when guarded file is in allowed-additions" {
    cat > "$TEST_ROOT/.agentharness-guarded-paths.json" << 'EOF'
{
  "schema_version": 1,
  "guard_root_level_new_items": false,
  "guarded_dirs": ["src"],
  "guarded_root_files": [],
  "message": "test"
}
EOF
    echo "src/newfile.ts" > "$TEST_ROOT/.agentharness-allowed-additions.txt"
    mkdir -p "$TEST_ROOT/src"
    echo "content" > "$TEST_ROOT/src/newfile.ts"
    (cd "$TEST_ROOT" && git add src/newfile.ts)
    local rc
    bash "$CHECK_SCRIPT" "$TEST_ROOT"
    rc=$?
    [[ $rc -eq 0 ]]
}

@test "check: exits 1 when json is invalid (fail-closed)" {
    echo "{ not valid json }" > "$TEST_ROOT/.agentharness-guarded-paths.json"
    echo "content" > "$TEST_ROOT/test.txt"
    (cd "$TEST_ROOT" && git add test.txt)
    run bash "$CHECK_SCRIPT" "$TEST_ROOT"
    [[ "$status" -ne 0 ]]
}
