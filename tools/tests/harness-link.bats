#!/usr/bin/env bats
#
# Tests for tools/setup/harness-link.sh — verifies integration script works
#

setup() {
    # Resolve the script under test relative to this test file, not a
    # hardcoded developer path, so this runs in CI and on any machine.
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"

    # Create a temporary directory for test projects
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    # Clean up test directory
    cd /
    rm -rf "$TEST_PROJECT"
}

# sha256sum isn't available by default on macOS (it uses `shasum` instead)
# — python3 is already a hard requirement for harness-link.sh itself, so
# it's a portable hash implementation both linux and macOS actually have.
file_hash() {
    python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1"
}

@test "harness-link.sh: help message shows usage" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Usage" ]]
}

@test "harness-link.sh: requires target project path argument" {
    run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "target project directory is required" ]]
}

@test "harness-link.sh: symlinks individual skills into .claude/skills/" {
    bash "$SCRIPT" "$TEST_PROJECT" --mode link

    # The script symlinks each skill individually into .claude/skills/,
    # it does not symlink .claude/skills/ itself.
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills/committing")
    [[ "$target" == *"/.claude/skills/committing" ]]
}

@test "harness-link.sh: also symlinks each skill into .agents/skills/ for Codex's real on-demand discovery (P0-06)" {
    bash "$SCRIPT" "$TEST_PROJECT" --mode link

    [ -d "$TEST_PROJECT/.agents/skills" ]
    [ ! -L "$TEST_PROJECT/.agents/skills" ]
    [ -L "$TEST_PROJECT/.agents/skills/committing" ]
    target=$(readlink "$TEST_PROJECT/.agents/skills/committing")
    [[ "$target" == *"/.claude/skills/committing" ]]
    # Same source as .claude/skills/committing — not two independent copies.
    [ -e "$TEST_PROJECT/.agents/skills/committing/SKILL.md" ]
    diff -q "$TEST_PROJECT/.agents/skills/committing/SKILL.md" "$TEST_PROJECT/.claude/skills/committing/SKILL.md"
}

@test "harness-link.sh: --skills filters which skills are linked" {
    bash "$SCRIPT" "$TEST_PROJECT" --mode link --skills committing,branching

    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    [ -L "$TEST_PROJECT/.claude/skills/branching" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/python-conventions" ]
}

@test "harness-link.sh: agentic-loops skill is importable standalone (only that skill linked)" {
    # Regression test for P1-03: a skill's own bundled code must resolve
    # in a consumer that only linked *this one* skill, not the whole
    # patterns/ tree (which harness-link.sh never symlinks). Previously
    # agentic-loops/SKILL.md referenced "patterns/agentic-loops/agent_loop.py"
    # — a path that doesn't exist anywhere in a consumer project, symlink
    # depth or not. Fixed by bundling agent_loop.py/test_agent_loop.py as
    # relative symlinks inside the skill's own directory.
    bash "$SCRIPT" "$TEST_PROJECT" --skills agentic-loops

    [ -e "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py" ]
    [ -e "$TEST_PROJECT/.claude/skills/agentic-loops/test_agent_loop.py" ]

    run python3 -c "
import sys
sys.path.insert(0, '$TEST_PROJECT/.claude/skills/agentic-loops')
from agent_loop import Budget, ToolSpec, run_agent_loop
print('importable')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "importable" ]]
}

@test "harness-link.sh: --skills rejects path traversal atomically instead of installing a partial set (P0-04)" {
    # Regression test: "../../patterns" (or an absolute path) used to
    # resolve straight through to SRC="$SKILLS_SRC/../../patterns",
    # symlinking an arbitrary harness path into the target project's
    # .claude/skills/. See docs/operational/reviews/gpt-5.6-review-status.md.
    #
    # Originally fixed by silently skipping the bad name (exit 0, partial
    # install) — the gpt-5.6 third-pass review correctly flagged that as its
    # own problem: automation can't distinguish "everything requested was
    # installed" from "one bad name got silently dropped." Now the whole
    # command aborts before touching the filesystem, and nothing traversal-
    # shaped should exist anywhere.
    run bash "$SCRIPT" "$TEST_PROJECT" --skills "../../patterns,committing"

    [ "$status" -ne 0 ]
    [[ "$output" =~ "invalid skill name: '../../patterns'" ]]
    [ ! -e "$TEST_PROJECT/.claude/skills" ]
}

@test "harness-link.sh: --skills with a typo fails atomically instead of producing an empty 'successful' install (P0-04)" {
    run bash "$SCRIPT" "$TEST_PROJECT" --skills "definitely-not-a-skill"

    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown skill: 'definitely-not-a-skill'" ]]
    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]
    [ ! -e "$TEST_PROJECT/.claude" ]
}

@test "harness-link.sh: --skills none is the sanctioned way to install zero skills (P0-04)" {
    run bash "$SCRIPT" "$TEST_PROJECT" --skills none
    [ "$status" -eq 0 ]

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
print(len(d['skills']))
"
    [ "$output" = "0" ]
}

@test "harness-link.sh: plan (--dry-run) reports the same invalid-skill failure init would, before mutating anything" {
    run bash "$SCRIPT" plan "$TEST_PROJECT" --skills "definitely-not-a-skill"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown skill: 'definitely-not-a-skill'" ]]
    [ ! -e "$TEST_PROJECT/.claude" ]
}

@test "harness-link.sh: merges .gitignore.template into .gitignore" {
    # Pre-create a .gitignore with some content
    echo "node_modules/" > "$TEST_PROJECT/.gitignore"

    bash "$SCRIPT" "$TEST_PROJECT"

    # Check that .gitignore exists and contains content from both original and template
    [ -f "$TEST_PROJECT/.gitignore" ]
    grep -q "node_modules" "$TEST_PROJECT/.gitignore"
    grep -q "\.env" "$TEST_PROJECT/.gitignore"  # From template
}

@test "harness-link.sh: --with-hook sets core.hooksPath in an existing git repo" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --with-hook

    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]
}

@test "harness-link.sh: --with-hook works against a linked worktree, not just the main checkout" {
    # Regression test: a worktree's .git is a *file* (gitdir: ...), not a
    # directory, so `[ -d "$TARGET/.git" ]` used to treat every worktree
    # as "not a git repo" and silently skip hook installation.
    main_repo=$(mktemp -d)
    git -C "$main_repo" init --quiet
    git -C "$main_repo" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    worktree_dir="$TEST_PROJECT/worktree"
    git -C "$main_repo" worktree add --quiet "$worktree_dir" --detach >/dev/null

    [ -f "$worktree_dir/.git" ]
    [ ! -d "$worktree_dir/.git" ]

    run bash "$SCRIPT" "$worktree_dir" --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Installed" ]]
    hooks_path=$(git -C "$worktree_dir" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]

    git -C "$main_repo" worktree remove --force "$worktree_dir" 2>/dev/null || true
    rm -rf "$main_repo"
}

@test "harness-link.sh: --with-hook refuses to overwrite a different existing core.hooksPath" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "some/other/hooks" ]
}

@test "harness-link.sh: --mode copy --with-hook does not treat an equivalent relative core.hooksPath as a conflict" {
    # Copilot review on PR #21: core.hooksPath can be recorded as a
    # relative path (git resolves it relative to the work tree at run
    # time), but the conflict check compared it as a raw string against
    # our always-absolute intended hooks_path — an equivalent, correct
    # relative value was wrongly treated as a conflicting hooksPath.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath ".github/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --mode copy --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"already has a different core.hooksPath"* ]]
    [[ "$output" =~ "Installed trunk-protection hook" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "$TEST_PROJECT/.github/hooks" ]
}

@test "harness-link.sh: --mode copy --with-hook normalizes a './'-prefixed, trailing-slash hooksPath before comparing (Copilot review round 4)" {
    # Plain string concatenation isn't enough: "./.github/hooks/" and
    # "$TEST_PROJECT/.github/hooks" are the same directory to git but
    # different strings — normalize both sides before comparing.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "./.github/hooks/"

    run bash "$SCRIPT" "$TEST_PROJECT" --mode copy --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"already has a different core.hooksPath"* ]]
    [[ "$output" =~ "Installed trunk-protection hook" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "$TEST_PROJECT/.github/hooks" ]
}

@test "harness-link.sh: --with-hook still detects a genuinely different relative core.hooksPath as a conflict" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --mode copy --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "some/other/hooks" ]
}

@test "harness-link.sh: generated coverage hook's harness-link.sh path is shell-escaped against injection" {
    # Copilot review on PR #21: the generated pre-push script's
    # HARNESS_LINK=... assignment embeds this path %q-quoted but
    # otherwise unquoted-on-the-left — an unescaped path containing
    # shell metacharacters would be evaluated as a command when the
    # generated hook later runs.
    git -C "$TEST_PROJECT" init --quiet
    local evil_dir="$TEST_PROJECT/../evil-\$(touch $TEST_PROJECT/PWNED)-dir"
    mkdir -p "$evil_dir"

    (
        source "$SCRIPT" 2>/dev/null || true
        mkdir -p "$TEST_PROJECT/.github/hooks"
        generate_coverage_pre_push "$TEST_PROJECT" "$evil_dir/harness-link.sh"
    )

    bash -n "$TEST_PROJECT/.github/hooks/pre-push"
    run bash "$TEST_PROJECT/.github/hooks/pre-push"
    [ ! -e "$TEST_PROJECT/PWNED" ]

    rm -rf "$evil_dir"
}

@test "harness-link.sh: --with-coverage-hook refusing a conflicting core.hooksPath leaves no generated hook files behind" {
    # Copilot review on PR #21: the generated/copied hook files used to be
    # written to $target/.github/hooks BEFORE the core.hooksPath conflict
    # check ran, so a declined install (with_hook=false recorded) could
    # still leave real files behind as a side effect. Verify the decline
    # path is now genuinely a no-op on the filesystem, not just on state.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --with-coverage-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    [ ! -e "$TEST_PROJECT/.github/hooks" ]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "some/other/hooks" ]
}

@test "harness-link.sh: --with-hook --force overwrites a different existing core.hooksPath" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook --force
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Overwrote existing core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]
}

@test "harness-link.sh: --with-hook is a no-op (with warning) when target isn't a git repo yet" {
    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook

    [ "$status" -eq 0 ]
    [[ "$output" =~ "not a git repo" ]]
    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "harness-link.sh: without --with-hook, core.hooksPath is left untouched" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT"

    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "harness-link.sh: is idempotent (run twice safely, same resulting state)" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --mode link --with-hook
    [ "$status" -eq 0 ]
    initial_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    initial_gitignore=$(file_hash "$TEST_PROJECT/.gitignore")
    initial_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    # Run again
    run bash "$SCRIPT" "$TEST_PROJECT" --mode link --with-hook
    [ "$status" -eq 0 ]
    final_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    final_gitignore=$(file_hash "$TEST_PROJECT/.gitignore")
    final_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    [ "$initial_links" = "$final_links" ]
    [ "$initial_gitignore" = "$final_gitignore" ]
    [ "$initial_hooks_path" = "$final_hooks_path" ]
}
