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

# --- Go (P1-02) ------------------------------------------------------------
#
# `go test -coverprofile` + `go tool cover -func` total is stable across Go
# versions and needs no third-party tooling — the Go analog of the Python
# pytest-cov path. GOCACHE is pinned into the throwaway project so the run
# never depends on (or pollutes) a shared cache.

write_covered_go_project() {
    cat > "$TEST_PROJECT/go.mod" <<'EOF'
module fixture

go 1.21
EOF
    cat > "$TEST_PROJECT/mod.go" <<'EOF'
package fixture

func Add(a, b int) int { return a + b }
EOF
    cat > "$TEST_PROJECT/mod_test.go" <<'EOF'
package fixture

import "testing"

func TestAdd(t *testing.T) {
	if Add(2, 3) != 5 {
		t.Fatal("bad")
	}
}
EOF
}

write_undercovered_go_project() {
    # Add is tested; Sub/Mul/Div are not — 1 of 4 functions, well under 80%.
    cat > "$TEST_PROJECT/go.mod" <<'EOF'
module fixture

go 1.21
EOF
    cat > "$TEST_PROJECT/mod.go" <<'EOF'
package fixture

func Add(a, b int) int { return a + b }
func Sub(a, b int) int { return a - b }
func Mul(a, b int) int { return a * b }
func Div(a, b int) int { return a / b }
EOF
    cat > "$TEST_PROJECT/mod_test.go" <<'EOF'
package fixture

import "testing"

func TestAdd(t *testing.T) {
	if Add(2, 3) != 5 {
		t.Fatal("bad")
	}
}
EOF
}

@test "enforce-profile (Go): production tier passes a fully covered module" {
    command -v go >/dev/null || skip "go not installed"
    export GOCACHE="$TEST_PROJECT/.gocache"
    write_covered_go_project
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Go project detected" ]]
    [[ "$output" =~ "meets the 'production' tier's minimum" ]]
}

@test "enforce-profile (Go): production tier fails an undercovered module" {
    command -v go >/dev/null || skip "go not installed"
    export GOCACHE="$TEST_PROJECT/.gocache"
    write_undercovered_go_project
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "is below the 'production' tier's minimum" ]]
}

@test "enforce-profile (Go): internal tier requires tests but has no coverage floor" {
    command -v go >/dev/null || skip "go not installed"
    export GOCACHE="$TEST_PROJECT/.gocache"
    write_undercovered_go_project
    echo "internal" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "coverage_min: none" ]]
}

# --- Vitest (P1-02) --------------------------------------------------------
#
# Vitest's `--coverage.reporter=json-summary` writes
# coverage/coverage-summary.json with a stable `total.lines.pct`. These
# tests stub the local `node_modules/.bin/vitest` binary so the real
# invoke->parse->gate path is exercised hermetically — no Vitest install,
# no network (the point of P1-05's hermeticity goal).

write_vitest_project() {
    local pct="$1" exit_code="${2:-0}"
    cat > "$TEST_PROJECT/package.json" <<'EOF'
{"name": "fixture", "scripts": {"test": "vitest run"}}
EOF
    mkdir -p "$TEST_PROJECT/node_modules/.bin"
    cat > "$TEST_PROJECT/node_modules/.bin/vitest" <<EOF
#!/usr/bin/env bash
mkdir -p coverage
printf '%s' '{"total":{"lines":{"total":10,"covered":$pct,"skipped":0,"pct":$pct}}}' > coverage/coverage-summary.json
exit $exit_code
EOF
    chmod +x "$TEST_PROJECT/node_modules/.bin/vitest"
}

@test "enforce-profile (Vitest): production tier passes a fully covered project" {
    command -v node >/dev/null || skip "node not installed"
    write_vitest_project 100
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Vitest" ]]
    [[ "$output" =~ "meets the 'production' tier's minimum" ]]
}

@test "enforce-profile (Vitest): production tier fails an undercovered project" {
    command -v node >/dev/null || skip "node not installed"
    write_vitest_project 50
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "is below the 'production' tier's minimum" ]]
}

@test "enforce-profile (Vitest): a failing test run fails enforcement" {
    command -v node >/dev/null || skip "node not installed"
    write_vitest_project 100 1
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT"
    [ "$status" -ne 0 ]
}

# --- --strict (P1-02) ------------------------------------------------------

@test "enforce-profile --strict: unrecognized project type fails instead of exit 0" {
    echo "some content" > "$TEST_PROJECT/README.md"
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT" --strict
    [ "$status" -ne 0 ]
    [[ "$output" =~ "strict" ]]
}

@test "enforce-profile --strict: an unsupported JS runner (Jest) fails instead of exit 0" {
    cat > "$TEST_PROJECT/package.json" <<'EOF'
{"name": "fixture", "scripts": {"test": "jest"}}
EOF
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT" --strict
    [ "$status" -ne 0 ]
    [[ "$output" =~ "strict" ]]
}

@test "enforce-profile --strict: still passes a supported, compliant project" {
    command -v node >/dev/null || skip "node not installed"
    write_vitest_project 100
    echo "production" > "$TEST_PROJECT/.agentharness-profile"
    run bash "$SCRIPT" enforce-profile "$TEST_PROJECT" --strict
    [ "$status" -eq 0 ]
}
