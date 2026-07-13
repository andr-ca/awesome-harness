#!/usr/bin/env bats
#
# Tests for tools/generate-manifest.py (B2): MANIFEST.md generated from
# manifest.yaml, not hand-maintained. Mirrors
# tools/tests/generate-agents-md.bats's pattern for the same drift class.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-manifest.py"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-manifest: output starts with the '# Manifest' heading" {
    run python3 "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == "# Manifest"* ]]
}

@test "generate-manifest: renders every section from manifest.yaml as a heading" {
    run python3 "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "## Testing & Quality Patterns" ]]
    [[ "$output" =~ "## Meta" ]]
    [[ "$output" =~ "## GitHub Configuration" ]]
}

@test "generate-manifest: Path column values are backtick-quoted" {
    run python3 "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *'`manifest.yaml`'* ]]
}

@test "generate-manifest: --output writes to a file instead of stdout" {
    out="$BATS_TEST_TMPDIR/MANIFEST.md"
    run python3 "$SCRIPT" --output "$out"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$out" ]
    grep -q "# Manifest" "$out"
}

@test "generate-manifest: committed MANIFEST.md at repo root matches the generator's current output" {
    # Regression guard for the same drift class fixed for AGENTS.md in
    # P2-02 — also asserted in CI via verify-content-quality.py's
    # check_manifest_md_sync(), duplicated here so a local 'bats' run
    # alone catches a stale commit too.
    run python3 "$SCRIPT"
    [ "$status" -eq 0 ]
    committed="$(cat "$HARNESS_ROOT/MANIFEST.md")"
    [ "$output" = "$committed" ]
}
