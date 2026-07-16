#!/usr/bin/env bats
# Tests for tools/check-completion.sh — the agent completion gate.
#
# Uses minimal stub projects to avoid running the full 70s pytest suite.

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$REPO_ROOT/tools/check-completion.sh"
}

_make_minimal_project() {
    # Create a minimal committed git project with stubs that pass ruff.
    # Uses a two-line verify-content-quality stub to avoid E702 (multiple
    # statements on one line). No src/, tests/, or pyproject.toml.
    local dir
    dir="$(mktemp -d)"
    git -C "$dir" init -q
    git -C "$dir" config user.email "test@example.com"
    git -C "$dir" config user.name "Test"
    mkdir -p "$dir/tools"
    cp "$SCRIPT" "$dir/tools/check-completion.sh"
    printf 'import sys\nsys.exit(0)\n' > "$dir/tools/verify-content-quality.py"
    git -C "$dir" add .
    git -C "$dir" commit -m "initial" -q
    echo "$dir"
}

@test "check-completion: stdout is valid JSON" {
    proj="$(_make_minimal_project)"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 -c "import json; json.loads('$output')"
}

@test "check-completion: JSON has required keys" {
    proj="$(_make_minimal_project)"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
assert "can_declare_complete" in d
assert "gates_passed" in d
assert "gates_failed" in d
assert isinstance(d["can_declare_complete"], bool)
PYEOF
}

@test "check-completion: stdout is a single JSON line" {
    proj="$(_make_minimal_project)"
    lines=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null | wc -l || true)
    rm -rf "$proj"
    [ "$lines" -eq 1 ]
}

@test "check-completion: exits 0 on clean project" {
    proj="$(_make_minimal_project)"
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 0 ]
}

@test "check-completion: exits 1 when a gate fails" {
    proj="$(_make_minimal_project)"
    # Override stub to fail
    printf 'import sys\nsys.exit(1)\n' > "$proj/tools/verify-content-quality.py"
    git -C "$proj" add . && git -C "$proj" commit -m "break" -q
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 1 ]
}

@test "check-completion: failing gate in gates_failed JSON" {
    proj="$(_make_minimal_project)"
    printf 'import sys\nsys.exit(1)\n' > "$proj/tools/verify-content-quality.py"
    git -C "$proj" add . && git -C "$proj" commit -m "break" -q
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
assert d["can_declare_complete"] is False
assert any("content-quality" in f for f in d["gates_failed"]), d
PYEOF
}

@test "check-completion: unborn HEAD handled gracefully" {
    fresh="$(mktemp -d)"
    git -C "$fresh" init -q
    mkdir -p "$fresh/tools"
    cp "$SCRIPT" "$fresh/tools/check-completion.sh"
    printf 'import sys\nsys.exit(0)\n' > "$fresh/tools/verify-content-quality.py"
    run bash -c "cd '$fresh' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$fresh"
    [ "$status" -le 1 ]
}

@test "check-completion: missing shellcheck in gates_failed" {
    proj="$(_make_minimal_project)"
    stripped=""
    IFS=':' read -ra entries <<< "$PATH"
    for e in "${entries[@]}"; do
        [ -x "$e/shellcheck" ] && continue
        stripped="${stripped:+$stripped:}$e"
    done
    output=$(cd "$proj" && env PATH="$stripped" bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
assert any("shellcheck" in f for f in d.get("gates_failed", [])), d
PYEOF
}

# ---------------------------------------------------------------------------
# JS/TS gate
# ---------------------------------------------------------------------------

@test "check-completion: JS project with passing lint script passes" {
    proj="$(_make_minimal_project)"
    # Add a package.json with a lint script that exits 0
    cat > "$proj/package.json" << 'EOF'
{
  "name": "test",
  "version": "1.0.0",
  "scripts": { "lint": "node -e 'process.exit(0)'" }
}
EOF
    git -C "$proj" add . && git -C "$proj" commit -m "add pkg" -q
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 0 ]
}

@test "check-completion: JS project with failing lint script fails the gate" {
    proj="$(_make_minimal_project)"
    cat > "$proj/package.json" << 'EOF'
{
  "name": "test",
  "version": "1.0.0",
  "scripts": { "lint": "node -e 'process.exit(1)'" }
}
EOF
    git -C "$proj" add . && git -C "$proj" commit -m "add pkg" -q
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 1 ]
}

@test "check-completion: project without package.json skips JS gate" {
    # Verify that the JS gate doesn't run in a Python-only project
    proj="$(_make_minimal_project)"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
# No JS gates should appear in passed or failed
js_gates = [g for g in d["gates_passed"] + d["gates_failed"]
            if "tsc" in g or "npm-lint" in g]
assert len(js_gates) == 0, f"Unexpected JS gates: {js_gates}"
PYEOF
}
