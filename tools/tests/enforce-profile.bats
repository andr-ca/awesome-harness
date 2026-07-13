#!/usr/bin/env bats
#
# Tests for `harness-link.sh enforce-profile` — operational profile
# enforcement (B4: Python v1; extended here for JS/TS). Builds a minimal,
# throwaway fixture per test via mktemp rather than reusing/mutating the
# shared examples/{python,typescript}-project/ fixtures, which other CI
# jobs (fixture-matrix) depend on staying exactly as they are.

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

# --- JS/TS (extends B4's Python-only v1) -----------------------------------
#
# Scope: only projects whose package.json "test" script already invokes
# Node's built-in `node --test` get real enforcement (zero-dependency,
# stable output format) — this repo has no reliable way to invoke and
# parse coverage from Jest/Vitest/Mocha without guessing at a specific
# version's output shape, so those get an honest "not implemented for
# this test runner yet" instead of a guessed-at, possibly-wrong result.

write_covered_js_project() {
    cat > "$TEST_PROJECT/package.json" <<'EOF'
{"name": "fixture", "scripts": {"test": "node --test --experimental-test-coverage"}}
EOF
    cat > "$TEST_PROJECT/mod.js" <<'EOF'
function add(a, b) { return a + b; }
module.exports = { add };
EOF
    cat > "$TEST_PROJECT/mod.test.js" <<'EOF'
const test = require('node:test');
const assert = require('node:assert');
const { add } = require('./mod.js');
test('add works', () => { assert.strictEqual(add(2, 3), 5); });
EOF
}

write_undercovered_js_project() {
    # add() is tested; subtract/multiply/divide are not — Node's exact
    # per-version coverage-counting methodology (V8 internals) shifts the
    # precise percentage a couple of points either way, so this needs a
    # wide margin below 80%, not just barely under it (a 1-of-2-function
    # fixture measured 66.67% on Node 24 locally but landed >=80% on the
    # CI runner's pinned Node 20 — same lesson as the Python fixture's
    # 1-of-4 ratio above).
    cat > "$TEST_PROJECT/package.json" <<'EOF'
{"name": "fixture", "scripts": {"test": "node --test --experimental-test-coverage"}}
EOF
    cat > "$TEST_PROJECT/mod.js" <<'EOF'
function add(a, b) { return a + b; }
function subtract(a, b) { return a - b; }
function multiply(a, b) { return a * b; }
function divide(a, b) { return a / b; }
module.exports = { add, subtract, multiply, divide };
EOF
    cat > "$TEST_PROJECT/mod.test.js" <<'EOF'
const test = require('node:test');
const assert = require('node:assert');
const { add } = require('./mod.js');
test('add works', () => { assert.strictEqual(add(2, 3), 5); });
EOF
}

@test "enforce-profile (JS/TS): production tier gates for real — passes a fully covered project" {
    write_covered_js_project
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Node built-in test runner" ]]
    [[ "$output" =~ "meets the 'production' tier's minimum" ]]
}

@test "enforce-profile (JS/TS): production tier gates for real — fails an undercovered project" {
    write_undercovered_js_project
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "is below the 'production' tier's minimum" ]]
}

@test "enforce-profile (JS/TS): internal tier requires tests but has no coverage floor" {
    write_undercovered_js_project
    echo "internal" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "coverage_min: none" ]]
}

@test "enforce-profile (JS/TS): a non-node-test runner (e.g. Jest) reports 'not implemented' and exits 0" {
    cat > "$TEST_PROJECT/package.json" <<'EOF'
{"name": "fixture", "scripts": {"test": "jest"}}
EOF
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "isn't Node's built-in test runner" ]]
}

@test "enforce-profile (JS/TS): missing 'test' script is a hard error, not a silent pass" {
    cat > "$TEST_PROJECT/package.json" <<'EOF'
{"name": "fixture"}
EOF
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no 'test' script defined" ]]
}
