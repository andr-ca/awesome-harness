#!/usr/bin/env bats
#
# Tests for the lifecycle subcommands (init/plan/status/doctor/audit/update/
# uninstall) added to tools/setup/harness-link.sh for P1-04. The pre-existing
# legacy-invocation behavior (harness-link.sh <target> [options]) is covered
# by tools/tests/harness-link.bats and is unchanged by this file.
#
# The submodule-mode tests clone this repo's real 'origin' remote (a public
# GitHub repo) and therefore need outbound network access — consistent with
# this repo's existing CI, which already clones bats-core from GitHub and
# pip-installs packages.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT"
}

@test "lifecycle: init writes a state file with mode, source, and skills" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching

    [ -f "$TEST_PROJECT/.agentharness-state.json" ]
    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
print(d['mode'])
print(sorted(d['skills']))
print(d['with_hook'])
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "link" ]]
    [[ "$output" =~ "branching" ]]
    [[ "$output" =~ "committing" ]]
    [[ "$output" =~ "False" ]]
}

@test "lifecycle: legacy invocation (no subcommand) also writes a state file" {
    bash "$SCRIPT" "$TEST_PROJECT" --skills committing
    [ -f "$TEST_PROJECT/.agentharness-state.json" ]
}

@test "lifecycle: plan makes no filesystem changes" {
    run bash "$SCRIPT" plan "$TEST_PROJECT" --skills committing
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dry run" ]]
    [ -z "$(ls -A "$TEST_PROJECT")" ]
}

@test "lifecycle: init --dry-run is equivalent to plan" {
    run bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dry run" ]]
    [ -z "$(ls -A "$TEST_PROJECT")" ]
}

@test "lifecycle: status reports mode, skills, and hook state" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mode:          link" ]]
    [[ "$output" =~ "skills:        committing" ]]
    [[ "$output" =~ "with_hook:     true" ]]
}

@test "lifecycle: status fails clearly when never initialized" {
    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no .agentharness-state.json found" ]]
}

@test "lifecycle: doctor passes for a healthy install" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,agentic-loops

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all checks passed" ]]
}

@test "lifecycle: doctor fails when a bundled resource link is broken" {
    # --mode copy, deliberately: in --mode link, .claude/skills/<name> in
    # $TEST_PROJECT is itself a symlink to *this actual repo's* skill
    # directory — rm/ln through that path would mutate this repo's own
    # tracked files, not a disposable copy. copy mode gives us a real,
    # independent file to safely break.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills agentic-loops
    rm "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py"
    ln -s /nonexistent/agent_loop.py "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "broken bundled-resource link" ]]
}

@test "lifecycle: doctor fails when a skill directory is deleted out from under it" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    rm -rf "$TEST_PROJECT/.claude/skills/committing"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "SKILL.md not found" ]]
}

@test "lifecycle: audit reports skills available upstream but not installed" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "available upstream, not installed: branching" ]]
}

@test "lifecycle: update adds newly-in-scope skills and refreshes the state file" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    # Simulate "install was set to track all skills, and a new one has since
    # been added upstream" by widening the recorded filter to null (no filter).
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = None
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "+ add: branching" ]]
    [ -e "$TEST_PROJECT/.claude/skills/branching" ]
}

@test "lifecycle: update removes skills no longer in scope" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = 'committing'
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "- remove: branching" ]]
    [ ! -e "$TEST_PROJECT/.claude/skills/branching" ]
    [ -e "$TEST_PROJECT/.claude/skills/committing" ]
}

@test "lifecycle: update declines to apply without confirmation" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = None
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" <<< "n"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Aborted" ]]
    [ ! -e "$TEST_PROJECT/.claude/skills/branching" ]
}

@test "lifecycle: update reports nothing-to-do when scope is unchanged" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "nothing to do" ]]
}

@test "lifecycle: uninstall reverses everything init recorded" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching --with-hook --profile internal

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Uninstalled" ]]

    [ ! -e "$TEST_PROJECT/.claude/skills/committing" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/branching" ]
    [ ! -f "$TEST_PROJECT/.agentharness-profile" ]
    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]
    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "lifecycle: uninstall declines without confirmation" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" <<< "n"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Aborted" ]]
    [ -e "$TEST_PROJECT/.claude/skills/committing" ]
}

@test "lifecycle: uninstall fails clearly when never initialized" {
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no .agentharness-state.json found" ]]
}

@test "lifecycle: --mode copy physically copies skill files, not symlinks" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing

    [ -f "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]
    [ ! -L "$TEST_PROJECT/.claude/skills/committing" ]
    [ ! -L "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]
}

@test "lifecycle: --mode copy dereferences a skill's bundled-resource symlinks instead of copying them literally" {
    # Regression test: agentic-loops bundles agent_loop.py/test_agent_loop.py
    # as *relative* symlinks back to patterns/agentic-loops/ (see P1-03),
    # which only resolve from inside this checkout. A plain `cp -r` copied
    # those links literally into the target, where they pointed at a
    # patterns/ directory --mode copy never creates — found by running the
    # examples/{python,typescript,go}-project fixtures through every mode.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills agentic-loops

    [ ! -L "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py" ]
    [ -f "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py" ]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    run python3 -c "
import sys
sys.path.insert(0, '$TEST_PROJECT/.claude/skills/agentic-loops')
from agent_loop import Budget, ToolSpec, run_agent_loop
print('importable')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "importable" ]]
}

@test "lifecycle: --mode copy update reports no drift when content is unchanged" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "nothing to do" ]]
}

@test "lifecycle: --mode copy update detects when the copied content has diverged from source" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    # 'update' diffs the copy against the current source regardless of
    # which side actually changed — editing the consumer's copy is the
    # simplest way to produce a real divergence without touching this
    # repo's own tracked files.
    echo "local edit" >> "$TEST_PROJECT/.claude/skills/committing/SKILL.md"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "content changed upstream: committing" ]]
    # --yes applied the refresh, so the local edit is gone (overwritten from source).
    ! grep -q "local edit" "$TEST_PROJECT/.claude/skills/committing/SKILL.md"
}

@test "lifecycle: --mode submodule adds this harness as a real submodule and symlinks from it" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"

    run bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Added agentharness as a submodule" ]]

    [ -e "$TEST_PROJECT/.agentharness/.git" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills/committing")
    [[ "$target" == *".agentharness/.claude/skills/committing" ]]
    [ -f "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]

    # Regression test: source.path/revision/remote must describe the
    # submodule *inside TEST_PROJECT*, not this harness dev checkout
    # (HARNESS_DIR). A real submodule-mode consumer never has HARNESS_DIR's
    # path on their machine — only their own submodule clone — and
    # recording HARNESS_DIR here previously made 'update'/'audit' compare
    # against the wrong tree (see gpt-5.6-review-status.md P1-06/07 CI
    # fixes: this caused 'update' to report phantom drift for skills that
    # exist in the live HARNESS_DIR checkout but not in whatever commit the
    # submodule actually cloned).
    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f: print(json.load(f)['source']['path'])
"
    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_PROJECT/.agentharness" ]
}

@test "lifecycle: --mode submodule with all skills reports no drift on immediate update" {
    # Regression test for the exact failure this repo's own CI hit
    # (fixture-matrix, submodule mode): init with the full default skill
    # set, then update right after — must be a no-op. It wasn't, because
    # 'update' used to recompute "available skills" from HARNESS_DIR
    # instead of the submodule it actually just installed from, so it saw
    # skills HARNESS_DIR has that the (possibly different-commit) submodule
    # didn't, and reported phantom drift.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"

    run bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule
    [ "$status" -eq 0 ]

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "(nothing to do)" ]]
}

@test "lifecycle: --mode submodule uninstall removes the submodule cleanly" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/.agentharness" ]
    run git -C "$TEST_PROJECT" submodule status
    [ -z "$output" ]
}

@test "lifecycle: --mode submodule supports pin, rollback, and re-upgrade against real history" {
    # P1-12: demonstrates the pin/upgrade/rollback story the submodule mode
    # promises (docs/INTEGRATION.md: "pinned via the submodule's own commit,
    # not a mutable external path") against this repo's actual git history,
    # not a simulated one. 'committing' has existed since v0.1.0, so it
    # resolves at any ancestor commit we roll back to.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"

    bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing
    submodule="$TEST_PROJECT/.agentharness"
    pinned_commit=$(git -C "$submodule" rev-parse HEAD)

    # Pin: doctor is healthy at the commit init recorded.
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    # Rollback: move the submodule to an ancestor commit by hand (the
    # documented, deliberately-manual way — see "Keeping Projects Updated"
    # in docs/INTEGRATION.md). The skill symlink still resolves because it
    # points into the submodule's working tree, not a specific blob. Roll
    # back to the v0.1.0 tag specifically (a real prior release, guaranteed
    # to carry the 'committing' skill per CHANGELOG.md) rather than an
    # arbitrary N-commits-back offset — this repo's history is full of
    # merge commits, so "~N" can land before a skill existed at all
    # instead of at an actual past release.
    rollback_commit=$(git -C "$submodule" rev-parse v0.1.0)
    git -C "$submodule" checkout --quiet "$rollback_commit"
    [ -f "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    # Re-upgrade: move back to the tip commit, same mechanism.
    git -C "$submodule" checkout --quiet "$pinned_commit"
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ "$(git -C "$submodule" rev-parse HEAD)" = "$pinned_commit" ]
}
