#!/usr/bin/env bats
#
# Tests for `harness-link.sh generate-clients` (P1-01, first increment) —
# runs this repo's client-adapter generators into a consumer project so a
# single command produces the router/instruction files, instead of the
# per-generator manual steps in docs/INTEGRATION.md.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"
    TARGET=$(mktemp -d)
}

teardown() {
    rm -rf "$TARGET"
}

@test "generate-clients: --client all writes every adapter" {
    run bash "$SCRIPT" generate-clients "$TARGET"
    [ "$status" -eq 0 ]
    [ -f "$TARGET/AGENTS.md" ]
    [ -f "$TARGET/GEMINI.md" ]
    [ -f "$TARGET/.github/copilot-instructions.md" ]
    [ -f "$TARGET/.github/instructions/python.instructions.md" ]
    [ -f "$TARGET/.cursor/rules/agentharness-router.mdc" ]
    [ -f "$TARGET/.kilo/rules/agentharness.md" ]
}

@test "generate-clients: a comma-separated subset writes only those clients" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client copilot,cursor
    [ "$status" -eq 0 ]
    [ -f "$TARGET/.github/copilot-instructions.md" ]
    [ -f "$TARGET/.cursor/rules/agentharness-router.mdc" ]
    [ ! -f "$TARGET/AGENTS.md" ]
    [ ! -f "$TARGET/GEMINI.md" ]
    [ ! -e "$TARGET/.kilo" ]
}

@test "generate-clients: single --client codex writes AGENTS.md only" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client codex
    [ "$status" -eq 0 ]
    [ -f "$TARGET/AGENTS.md" ]
    [ ! -f "$TARGET/GEMINI.md" ]
}

@test "generate-clients: generated AGENTS.md is non-empty and names the router" {
    bash "$SCRIPT" generate-clients "$TARGET" --client codex
    [ -s "$TARGET/AGENTS.md" ]
    grep -q "agentharness" "$TARGET/AGENTS.md"
}

@test "generate-clients: an unknown client is a clear error" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client bogus
    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown client 'bogus'" ]]
}

@test "generate-clients: a non-directory target is a clear error" {
    run bash "$SCRIPT" generate-clients "$TARGET/does-not-exist"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "not a directory" ]]
}

@test "generate-clients: is idempotent — a second run reproduces identical files" {
    bash "$SCRIPT" generate-clients "$TARGET" --client copilot,cursor
    first="$(find "$TARGET" -type f -exec sha256sum {} + | sort -k2)"
    bash "$SCRIPT" generate-clients "$TARGET" --client copilot,cursor
    second="$(find "$TARGET" -type f -exec sha256sum {} + | sort -k2)"
    [ "$first" = "$second" ]
}
