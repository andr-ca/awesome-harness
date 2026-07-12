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
    bash "$SCRIPT" "$TEST_PROJECT"

    # The script symlinks each skill individually into .claude/skills/,
    # it does not symlink .claude/skills/ itself.
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills/committing")
    [[ "$target" == *"/.claude/skills/committing" ]]
}

@test "harness-link.sh: --skills filters which skills are linked" {
    bash "$SCRIPT" "$TEST_PROJECT" --skills committing,branching

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

@test "harness-link.sh: --skills rejects path traversal instead of symlinking outside skills dir" {
    # Regression test: "../../patterns" (or an absolute path) used to
    # resolve straight through to SRC="$SKILLS_SRC/../../patterns",
    # symlinking an arbitrary harness path into the target project's
    # .claude/skills/. See docs/operational/reviews/gpt-5.6-review-status.md.
    run bash "$SCRIPT" "$TEST_PROJECT" --skills "../../patterns,committing"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "Skipping invalid skill name: ../../patterns" ]]
    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/patterns" ]
    # Nothing traversal-shaped should exist anywhere under .claude/skills/
    run find "$TEST_PROJECT/.claude/skills" -mindepth 1 -maxdepth 1 -name '..*'
    [ -z "$output" ]
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

    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook
    [ "$status" -eq 0 ]
    initial_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    initial_gitignore=$(sha256sum "$TEST_PROJECT/.gitignore" | cut -d' ' -f1)
    initial_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    # Run again
    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook
    [ "$status" -eq 0 ]
    final_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    final_gitignore=$(sha256sum "$TEST_PROJECT/.gitignore" | cut -d' ' -f1)
    final_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    [ "$initial_links" = "$final_links" ]
    [ "$initial_gitignore" = "$final_gitignore" ]
    [ "$initial_hooks_path" = "$final_hooks_path" ]
}
