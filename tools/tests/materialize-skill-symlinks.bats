#!/usr/bin/env bats
# Tests for tools/release/materialize-skill-symlinks.py — the npm
# prepack/postpack hook that dereferences .claude/skills/ bundled-resource
# symlinks (npm tarballs don't preserve symlinks) and restores them
# afterward via `git checkout`.

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$REPO_ROOT/tools/release/materialize-skill-symlinks.py"
}

teardown() {
    # Always leave the real repo's skill symlinks exactly as git tracks them,
    # even if a test fails partway through.
    git -C "$REPO_ROOT" checkout -- .claude/skills >/dev/null 2>&1 || true
}

@test "materialize-skill-symlinks: agentic-loops bundled symlinks exist before the test" {
    [ -L "$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py" ]
}

@test "materialize-skill-symlinks: materialize replaces symlinks with real files of identical content" {
    local link="$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py"
    local expected
    expected="$(cat "$link")"

    python3 "$SCRIPT" materialize

    [ -f "$link" ]
    [ ! -L "$link" ]
    [ "$(cat "$link")" = "$expected" ]
}

@test "materialize-skill-symlinks: restore puts the symlinks back via git checkout" {
    python3 "$SCRIPT" materialize
    [ ! -L "$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py" ]

    python3 "$SCRIPT" restore

    [ -L "$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py" ]
    run git -C "$REPO_ROOT" status --short .claude/skills
    [ -z "$output" ]
}

@test "materialize-skill-symlinks: rejects an unknown action" {
    run python3 "$SCRIPT" bogus
    [ "$status" -ne 0 ]
    [[ "$output" == *"usage:"* ]]
}
