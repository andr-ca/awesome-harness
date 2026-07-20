---
name: multi-agent-coordination
description: "Use when two or more agent sessions may work on the same repository concurrently — covers the per-feature lock-file protocol, stale-lock detection, worktree isolation rules, and what to do when a feature is already locked."
metadata:
  type: skills
  complexity: low
  scope: [all]
---

# Multi-Agent Coordination

Use this skill when you start work on a feature and another agent session
might be working on the same repository, or when you detect that a lock
exists for the feature you want to work on.

**`tools/agent-lock.sh` is agentharness's own dogfooding tool — it is
not currently installed into consumer projects by `harness-link.sh`.**
If this skill file is symlinked/copied into a consumer repo (the
normal case for every install mode) and `tools/agent-lock.sh` doesn't
exist there, every command below will fail with "No such file or
directory" (issue #110). Check `[ -f tools/agent-lock.sh ]` before
relying on this skill's commands; if it's missing, this protocol
doesn't apply to this repo yet — fall back to plain git branch
discipline (check `git branch -a` / `git log` for other in-progress
work before starting) rather than assuming the lock file exists.

Deeper reference: `patterns/multi-agent-coordination/COORDINATION.md`
(full protocol, lock format, stale detection, worktree rules).

---

## Before starting work: check for a lock

```bash
tools/agent-lock.sh check "add-user-auth"
```

- **FREE** — no lock exists. Proceed normally.
- **LOCKED** — another agent is working on this feature.

---

## Acquiring a lock

```bash
AGENT_ID=$(tools/agent-lock.sh acquire "add-user-auth" "feat/user-auth")
```

`AGENT_ID` is a UUID printed on the last line. Keep it — you need it to release.

With a worktree:

```bash
git worktree add -b feat/user-auth .worktrees/user-auth main
AGENT_ID=$(tools/agent-lock.sh acquire "add-user-auth" "feat/user-auth" ".worktrees/user-auth")
```

---

## When a lock exists — what to do

```
LOCKED: 'add-user-auth' is being worked on.
  agent_id : 3f2a1c8d-...
  branch   : feat/user-auth
  worktree : .worktrees/user-auth
  since    : 2026-07-14T10:00:00Z
```

**Option A — Wait:** If the agent will finish soon, wait and retry.

**Option B — New branch + worktree:**

```bash
# Get a suggested branch name
NEW_BRANCH=$(tools/agent-lock.sh suggest-branch "add-user-auth")

# Create an isolated worktree
git worktree add -b "$NEW_BRANCH" ".worktrees/$(echo $NEW_BRANCH | tr '/' '-')" main

# Acquire a lock for your sub-task
AGENT_ID=$(tools/agent-lock.sh acquire "add-user-auth-review" "$NEW_BRANCH")
```

---

## Releasing a lock

Always release when done — don't leave locks for the next agent to clean up:

```bash
tools/agent-lock.sh release "add-user-auth" "$AGENT_ID"
```

---

## Stale lock cleanup

Locks are auto-cleaned on `acquire` and `check`. To manually clean all:

```bash
tools/agent-lock.sh clean
```

A lock is stale when its `pid` is no longer a running process.

---

## Worktree isolation rules

- **One branch per worktree.** Never check out the same branch in two worktrees at once.
- **Keep them in `.worktrees/<branch-name>/`** — gitignored.
- **Remove with git:** `git worktree remove <dir>` (not `rm -rf`).

---

## Lock files should be gitignored

`.agentharness-locks/` should be in `.gitignore` — lock files are
operational state, not committed history. The harness adds this entry
automatically when you run `agentharness init`.

---

## Enforcement — locks are checked at push time

This protocol is no longer purely advisory:

- Acquire a lock **before your first commit on any branch** (CLAUDE.md
  mandate) and `export AGENTHARNESS_AGENT_ID=<the printed id>`.
- The `pre-push` hook runs `tools/agent-lock.sh check-branch <branch>`
  for every branch you push: a live lock held by a *different* session
  blocks the push. Your own locks pass (agent-id or ancestor-pid match).
- A repo-wide GitHub ruleset rejects force pushes on all branches — if
  your push is rejected as non-fast-forward, fetch and rebase; never
  force.

Full details: `patterns/multi-agent-coordination/COORDINATION.md`
("Enforcement").
