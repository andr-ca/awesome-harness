#!/usr/bin/env bats
# Tests for tools/verify-skill-symlinks.sh — guards the 1:1 invariant
# between .claude/skills/ (real skill dirs) and .agents/skills/ (the
# relative symlinks every Agent-Skills-standard tool — Codex, Copilot,
# Gemini, Kilo, OpenCode — reads from). Failure modes below are the exact
# drifts that would silently hide a skill from those tools.

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$REPO_ROOT/tools/verify-skill-symlinks.sh"
    FIXTURE="$(mktemp -d)"
    mkdir -p "$FIXTURE/.claude/skills" "$FIXTURE/.agents/skills"
}

teardown() {
    rm -rf "$FIXTURE"
}

# Create a real skill dir (.claude side) named $1 in the fixture.
make_skill_dir() {
    local name="$1"
    mkdir -p "$FIXTURE/.claude/skills/$name"
    printf -- '---\nname: %s\ndescription: test skill\n---\nbody\n' \
        "$name" > "$FIXTURE/.claude/skills/$name/SKILL.md"
}

# Create a real skill plus its correct .agents/skills relative symlink.
make_skill() {
    make_skill_dir "$1"
    ln -s "../../.claude/skills/$1" "$FIXTURE/.agents/skills/$1"
}

@test "verify-skill-symlinks: passes on this repo's real tree" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "verify-skill-symlinks: passes on a well-formed fixture" {
    make_skill alpha
    make_skill beta
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -eq 0 ]
}

@test "verify-skill-symlinks: fails when a skill has no .agents symlink" {
    make_skill alpha
    make_skill_dir beta   # real skill, but no .agents/skills/beta symlink
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"no .agents/skills/beta symlink"* ]]
}

@test "verify-skill-symlinks: fails on a dangling symlink for an existing skill" {
    make_skill_dir beta
    ln -s "../../.claude/skills/nonexistent" "$FIXTURE/.agents/skills/beta"
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"dangling"* ]]
}

@test "verify-skill-symlinks: fails on an orphan symlink (no skill behind it)" {
    make_skill alpha
    mkdir -p "$FIXTURE/elsewhere"
    ln -s "../../elsewhere" "$FIXTURE/.agents/skills/weird"
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"orphan"* ]]
}

@test "verify-skill-symlinks: fails when the .agents entry is a real dir, not a symlink" {
    make_skill_dir beta
    mkdir -p "$FIXTURE/.agents/skills/beta"   # real dir instead of a symlink
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"not a symlink"* ]]
}

@test "verify-skill-symlinks: fails on a broken bundled-resource symlink inside a skill" {
    make_skill alpha
    ln -s "../../../patterns/gone/thing.py" \
        "$FIXTURE/.claude/skills/alpha/thing.py"
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"bundled resource"* ]]
}

@test "verify-skill-symlinks: fails when .agents/skills is missing entirely" {
    make_skill_dir alpha
    rm -rf "$FIXTURE/.agents/skills"
    run bash "$SCRIPT" "$FIXTURE"
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing entirely"* ]]
}
