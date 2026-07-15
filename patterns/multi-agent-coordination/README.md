# Multi-Agent Coordination

Index for this directory. The docs below cover coordination between
concurrent agent sessions working on the same repository.

| Doc | Covers |
|---|---|
| [COORDINATION.md](./COORDINATION.md) | The lock-file protocol, worktree isolation, discovery, and stale-lock handling |

The on-demand skill at `.claude/skills/multi-agent-coordination/SKILL.md`
is the condensed reference. This directory is the canonical source.

## When to use this

Use multi-agent coordination when:

- Two agent sessions may work on the **same repository** simultaneously.
- You run agents in parallel on different features (parallel worktrees).
- You want to prevent an agent from accidentally overwriting another
  agent's in-progress work.

The lock-file approach is **local only** — it protects concurrent writes
on the same machine. For multi-machine coordination, use branch protection
and PR workflows.
