---
name: multi-agent-coordination
description: Protocol, lock-file format, and worktree isolation rules for coordinating concurrent agent sessions on the same repository. Use when two or more agents may work on the same codebase simultaneously.
complexity: low
scope: [all]
---

# Multi-Agent Coordination

## The problem

Two agent sessions running concurrently in the same repository will fight
over the same working tree, `git stash`, index, and branch HEAD. The result
is corrupted state and lost work.

## The solution: per-feature lock files + worktrees

Each agent **locks** the feature it's working on by writing a small JSON file
to `.agentharness-locks/`. A second agent that wants to work on the same
feature reads the lock, detects the conflict, and either:

- **Waits** — if the first agent will finish soon.
- **Creates its own worktree** on a fresh branch — if parallel work is
  acceptable or expected.

---

## Lock file format

`.agentharness-locks/<feature-slug>.json`:

```json
{
  "agent_id":   "3f2a1c8d-...",
  "feature":    "add-user-auth",
  "branch":     "feat/user-auth",
  "worktree":   ".worktrees/feat-user-auth",
  "started_at": "2026-07-14T10:00:00Z",
  "pid":        12345
}
```

| Field | Purpose |
|---|---|
| `agent_id` | Random UUID — uniquely identifies the agent session |
| `feature` | Human-readable description (becomes the lock file name slug) |
| `branch` | The branch this agent is using |
| `worktree` | Path to the worktree, or `null` if using the main checkout |
| `started_at` | ISO 8601 UTC timestamp |
| `pid` | OS process ID — used for stale-lock detection |

---

## Stale lock detection

A lock is **stale** if `pid` no longer refers to a running process:

```bash
kill -0 "$pid" 2>/dev/null && echo "alive" || echo "stale"
```

When a stale lock is detected, it must be deleted before a new one is
created — do not skip detection and overwrite silently.

---

## Acquiring a lock

```bash
# agent-lock.sh acquire <feature> <branch> [worktree]
tools/agent-lock.sh acquire "add-user-auth" "feat/user-auth"
```

Steps:
1. Compute `feature-slug` = lowercase, hyphens, max 40 chars + 8-char hash suffix.
2. Check `.agentharness-locks/<slug>.json` — if it exists and is not stale:
   - Print the existing lock (feature, branch, worktree).
   - Exit non-zero with: `LOCKED: feature already being worked on`.
3. Write the lock file atomically (`mktemp` + `mv`).
4. Exit 0.

---

## Releasing a lock

```bash
tools/agent-lock.sh release "add-user-auth" "$AGENT_ID"
```

Steps:
1. Find `.agentharness-locks/<slug>.json`.
2. Verify `agent_id` matches `$AGENT_ID` — don't release someone else's lock.
3. Delete the file.
4. Exit 0.

---

## What to do when a lock exists

```
LOCKED: 'add-user-auth' is being worked on by agent 3f2a1c8d on branch feat/user-auth.

Options:
  1. Wait for that agent to finish and release the lock.
  2. Create your own branch and worktree:
       git worktree add -b feat/user-auth-agent-2 .worktrees/user-auth-2 main
```

The suggested branch name: `feat/<slug>-agent-<timestamp>`.

---

## Worktree isolation rules

When running parallel agents, each agent **must** have its own worktree:

```bash
# Agent 1 — primary branch
git worktree add -b feat/user-auth .worktrees/user-auth main

# Agent 2 — parallel branch
git worktree add -b feat/user-auth-2 .worktrees/user-auth-2 main
```

**Never** share a worktree between agents. Git's index, `ORIG_HEAD`, and
`MERGE_HEAD` files are per-worktree — two agents in the same worktree will
corrupt each other's state.

---

## `.agentharness-locks/` in `.gitignore`

Lock files are operational state, not committed history. Add to `.gitignore`:

```gitignore
.agentharness-locks/
```

---

## Cleanup

Stale locks are auto-removed on `acquire` and `list` commands. To manually
clean all stale locks:

```bash
tools/agent-lock.sh clean
```

---

## Integration with the branching skill

See `.agents/skills/branching/SKILL.md` for the full branch and worktree
naming conventions. Multi-agent lock naming follows the same `feat/<slug>`
pattern.
