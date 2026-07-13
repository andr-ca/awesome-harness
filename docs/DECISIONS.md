# Decisions

A compact, retroactive architecture-decision log. Each entry is a real
choice this repo made, why, and whether it's still considered settled.
Not every decision in the repo's history is here — only ones a future
contributor is likely to second-guess without the context. New entries
go at the top.

Format: **Decision** / **Status** / **Context** / **Consequences**.

## Deterministic-only eval infrastructure; live agent invocation deliberately unimplemented

**Status:** Settled for now — revisit once a user explicitly funds a run.

**Context:** `tools/eval/` (P2-04) needed to prove the harness changes
agent behavior for the better, which requires actually running an agent
against real tasks and spending API credits to do it. Building the
task/scoring/orchestration infrastructure doesn't require that spend;
producing an actual baseline-vs-treatment number does.

**Consequences:** `tools/eval/run.py`'s `invoke_agent_via_api()` raises
`NotImplementedError` on purpose. The orchestration logic around it is
fully unit-tested with a free, deterministic fake. No eval results,
costs, or adherence numbers exist yet — the suite is a rubric and a
harness, not a completed measurement. See `tools/eval/README.md`.

## npm as the low-friction distribution channel, published as agentharness-toolkit

**Status:** Settled on the channel and package name; publish itself in progress.

**Context:** `harness-link.sh init --mode submodule` already gives a
pinned install path, but "clone this repo first" is friction compared to
`npx <package>`. Of the plausible options (do nothing, a Claude Code
plugin, a package registry), npm was chosen because `npx` is a
ubiquitous zero-install entry point regardless of the harness's own
Bash/Python tooling underneath.

**Consequences:** `package.json`, `bin/cli.js`, and
`.github/workflows/release.yml` are built and tested end-to-end
(`npm pack` → unpack → run), including a real bug caught this way: npm
tarballs don't preserve the `agentic-loops` skill's symlinked bundled
resources, fixed with a prepack/postpack materialize-then-restore step.
First publish needed two manual, one-time resolutions neither this
repo's tooling nor CI could complete unattended: the unscoped
`agentharness` name was rejected by npm's anti-squatting check as too
similar to an existing package (`agent-harness`), settled as
`agentharness-toolkit` instead (the CLI command itself stays
`agentharness` — `bin` is independent of the package name); and npm's
2FA-or-bypass-token publish requirement meant the actual first
`npm publish` had to be run interactively rather than from CI. See
`docs/RELEASING.md#npm-distribution`.

## Publish authority split from workflow completion, gated by an opt-in flag

**Status:** Settled (resolved 2026-07-13; previously open, see
`docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`).

**Context:** `CLAUDE.md`'s "Agent Workflow Completion (MANDATORY)"
section used to direct an agent to always finish a task by committing,
pushing, and opening a PR, and (per the Recommendation Assessment
section) implement scoped/low-risk recommendations without asking
first. This was written to stop "work in progress that isn't pushed is
work that doesn't exist" — silently-abandoned agent work — but it also
meant the harness's *default* posture granted an agent standing
write/publish authority, with no built-in opt-out for a reviewer who
wanted an agent to stop at inspection. The 2026-07-13 re-audit named
this the one unresolved P0-level trust-model gap in the repo; the user
confirmed splitting it into an opt-in profile.

**Consequences:** the default is now verify-and-stage-only — an agent
commits locally but stops before push/PR/auto-implement and asks first.
Full publish authority (the original always-on behavior) now requires
either a local, gitignored `.agentharness-publish-mode` flag file at the
repo root, or explicit standing authorization in the current
conversation (which always overrides the flag, matching the existing
rigor-tier precedence pattern). See `CLAUDE.md`'s "Agent Workflow
Completion" and "Publish authority" sections, and
`docs/INTEGRATION.md`'s "Publish Authority" section for how to grant or
revoke it in a given repo.

## MANIFEST.md generated from a structured manifest.yaml source

**Status:** Settled (resolved 2026-07-13; previously open, see
`docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`).

**Context:** The original review asked for a generated, bidirectionally
accurate inventory so `MANIFEST.md` couldn't silently drift from the
repo the way several other docs were found to have drifted (P1-13).
`tools/verify-manifest.sh` was already checking that every file
`MANIFEST.md` claims exists on disk, and flagging anything unlisted —
but it verified a hand-written file against reality; it didn't generate
the file from a structured source of truth, so `MANIFEST.md` could still
drift *in prose* (wrong one-line description, wrong "when to use"
guidance) even though missing/unlisted *files* were caught. The user
confirmed building an actual generator.

**Consequences:** `manifest.yaml` is now the structured source (one
entry per asset: `path`, `type`, `when_to_use`/`purpose`, grouped under
the same 11 section headers `MANIFEST.md` always used) —
`tools/generate-manifest.py` renders `MANIFEST.md` from it, mirroring
`tools/generate-agents-md.sh`'s existing generated-file pattern exactly,
including a CI drift-check (`check_manifest_md_sync()` in
`tools/verify-content-quality.py`) that fails the build if someone edits
`MANIFEST.md` by hand instead of `manifest.yaml`. The migration was
verified byte-for-byte: the generator's output against the pre-migration
`MANIFEST.md` differed only in the one paragraph that was deliberately
rewritten (the old "no generator script yet" line), across all 83
pre-existing rows. `tools/verify-manifest.sh` (the file-existence
checker) was left as-is — it still validates the rendered `MANIFEST.md`
against the filesystem, which remains exactly correct once `MANIFEST.md`
is generated-but-committed.

## Claude-first client scope, not multi-agent from day one

**Status:** Settled; Codex adapter added as an explicit exception with
its own caveat, not a scope change.

**Context:** The harness's actual, tested integration point (`.claude/skills/`
auto-loading, `CLAUDE.md` routing) only exists for Claude Code. Claiming
support for Cursor, Copilot, or another agent without a way to test
against a real session of it would be a worse-than-absent claim — a
reviewer or contributor could reasonably build on a claim this repo
can't back up.

**Consequences:** README's Product Contract states "Claude-first" and
explicitly warns "don't assume Cursor, Copilot, or another harness picks
up `.claude/skills/` the same way." The one exception is `AGENTS.md`
(Codex's equivalent of `CLAUDE.md`, generated from the same source by
`tools/generate-agents-md.sh`), which is *generated and CI drift-tested*
but explicitly labeled "not verified against a real Codex CLI session" —
the same "don't claim what you haven't tested" principle applied to a
best-effort exception instead of blocking it outright.

## Symlink as the default install mode, not copy or submodule

**Status:** Settled.

**Context:** `harness-link.sh init` needed a default among three real
trade-offs: symlink (always current, but mutates if the harness checkout
changes), copy (frozen, but drifts silently unless `update` is re-run),
submodule (pinned and reproducible, but reaches the network to add the
submodule and requires consumers to understand git submodules).

**Consequences:** `--mode link` is the default because most consumers of
a shared-policy repo want the latest conventions without manual syncing,
matching this repo's own core purpose (write once, don't let it drift).
Consumers who want a version-pinned install use `--mode submodule`
explicitly; `docs/RELEASING.md`'s Pin/Upgrade/Rollback table documents
all three modes' behavior so the trade-off is visible, not hidden in the
default choice.
