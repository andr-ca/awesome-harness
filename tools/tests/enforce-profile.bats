#!/usr/bin/env bats
#
# Tests for `harness-link.sh enforce-profile` (B4) — the Python-only v1 of
# operational profile enforcement. Builds a minimal, throwaway Python
# fixture per test via mktemp rather than reusing/mutating the shared
# examples/python-project/ fixture, which other CI jobs (fixture-matrix)
# depend on staying exactly as it is.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"
    TEST_PROJECT=$(mktemp -d)
}

teardown() {
    rm -rf "$TEST_PROJECT"
}

write_covered_python_project() {
    # Fully covered — should pass at production tier's 80% floor.
    cat > "$TEST_PROJECT/requirements.txt" <<'EOF'
# fixture, no real deps
EOF
    cat > "$TEST_PROJECT/mod.py" <<'EOF'
def add(a, b):
    return a + b
EOF
    cat > "$TEST_PROJECT/test_mod.py" <<'EOF'
from mod import add


def test_add():
    assert add(2, 3) == 5
EOF
}

write_undercovered_python_project() {
    # add() is tested; subtract() is not — coverage lands well under 80%.
    cat > "$TEST_PROJECT/requirements.txt" <<'EOF'
# fixture, no real deps
EOF
    cat > "$TEST_PROJECT/mod.py" <<'EOF'
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b
EOF
    cat > "$TEST_PROJECT/test_mod.py" <<'EOF'
from mod import add


def test_add():
    assert add(2, 3) == 5
EOF
}

@test "enforce-profile: prototype tier skips the test run entirely" {
    write_undercovered_python_project
    echo "prototype" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "tests.required: false" ]]
    [[ "$output" =~ "skipping" ]]
}

@test "enforce-profile: production tier gates for real — passes a fully covered project" {
    write_covered_python_project
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "coverage_min: 80" ]]
}

@test "enforce-profile: production tier gates for real — fails an undercovered project" {
    write_undercovered_python_project
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
}

@test "enforce-profile: defaults to production (fail-safe) when no .agentharness-profile exists" {
    write_undercovered_python_project
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "selected profile: production" ]]
}

@test "enforce-profile: unrecognized profile value falls back to production with a warning" {
    write_covered_python_project
    echo "not-a-real-tier" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [[ "$output" =~ "unrecognized profile" ]] || [[ "$stderr" =~ "unrecognized profile" ]]
    [[ "$output" =~ "selected profile: production" ]]
}

@test "enforce-profile: non-Python project reports 'not implemented yet' and exits 0" {
    echo "some content" > "$TEST_PROJECT/README.md"
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "implemented yet" ]]
}

@test "enforce-profile: internal tier requires tests but has no coverage floor" {
    write_undercovered_python_project
    echo "internal" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "coverage_min: none" ]]
}
