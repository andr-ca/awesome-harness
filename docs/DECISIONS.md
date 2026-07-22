# Decisions

A compact, retroactive architecture-decision log. Each entry is a real
choice this repo made, why, and whether it's still considered settled.
Not every decision in the repo's history is here — only ones a future
contributor is likely to second-guess without the context. New entries
go at the top.

Format: **Decision** / **Status** / **Context** / **Consequences**.

## Scoped authority contracts: declarative, expiring, revocable grants

**Status:** Implemented (MVP, 2026-07-22). Enforcement is advisory by
default; consumers can wire hard-block via an optional hook snippet.

**Context:** The binary `.agentharness-publish-mode` flag grants all-or-nothing
authority: an operator creates it and gets full commit/push/PR/auto-implement
permission for every session, or deletes it and gets none. That binary model
conflates orthogonal concerns — an operator might want to grant push authority
to `fix/*` branches only, or grant it for 48 hours while a feature ships,
or revoke it mid-session. The harness-engineering project's authority model
(https://github.com/lopopolo/harness-engineering/blob/226c8d35fb6ea3ed55467753dba6dea2b5fd5778/docs/authority/README.md)
separates capability (how to cause an effect) from authority (which effects
an identity may cause), using scoped, expiring, revocable grants as the
fundamental primitive. This decision adapts that principle into a declarative,
portable format this harness can enforce without requiring a remote
authorization server.

**Consequences:** Operators can now place a `.agentharness-authority.json`
(gitignored, per-operator, like the binary flag) at the repo root. The file
contains: `schema_version: 1`, a `grants` array of objects with `operations`
(required), `target` (optional glob pattern, e.g. `fix/*`), `expires` (optional
ISO 8601 UTC timestamp), and `granted_by` (optional provenance), and a `revoked`
list of operation names withdrawn even if a grant lists them. Operation
vocabulary: `commit`, `push`, `pr-create`, `pr-merge`, `issue-create`,
`fs-write-outside-repo`, `external-message`, `destructive-fs`. Precedence:
explicit in-session instruction (always wins) > `.agentharness-authority.json`
> bare `.agentharness-publish-mode` flag (treated as a full grant of all 8
operations) > default (verify-and-stage-only). A present contract overrides
the bare flag.

CLI: `agentharness authority` (human preflight listing granted ops for
context), `agentharness authority --json --target-dir DIR` (machine-readable
for CI/scripting), `agentharness authority check --operation OP [--target T]`
(exit 0 granted / non-0 refused — the portable, optional hard-block primitive).
`audit` and `audit --json` now surface `effective_authority` alongside
`publish_mode_active`.

**Enforcement model:** Advisory by default — the MVP ships the portable Python
gate + CLI + an optional `pre-push` hook snippet (a consumer invokes
`agentharness authority check --operation push` and blocks on non-zero exit).
The harness's own pre-push hook is NOT auto-wired this pass — enforcement is
opt-in for consumers. **Permanent non-goals:** no credential/token storage, no
token brokering, no remote authorization server, no invented cross-client
enforcement guarantees.

## Consumer-local completion gate: a generated wrapper, not a shipped script

**Status:** Settled.

**Context:** [#110](https://github.com/andr-ca/agentharness/issues/110)
reported that `committing/SKILL.md` unconditionally instructs agents to
run `tools/check-completion.sh`, but that script only exists in the
agentharness repo itself — never shipped to a consumer project in any
install mode — and exits 127 everywhere else. Worse, even where a copy
physically exists on disk (`--mode submodule` clones the whole harness
repo, `check-completion.sh` included), invoking it directly still
validates the *harness's own* code: the script resolves its root via
`dirname "${BASH_SOURCE[0]}"`, not the caller's working directory, so
there was no shortcut — a real consumer-side tool was needed, not just a
documentation fix.

**Consequences:** `init`/`update` now generate a small wrapper at
`<project>/.agentharness-bin/check` for `link`/`submodule`/`npm` modes,
which `exec`s the resolved harness checkout's own `enforce-profile`
subcommand with an explicit consumer-project argument — reusing
`enforce-profile`'s existing language-aware test+coverage logic rather
than duplicating `check-completion.sh`'s harness-specific gate set
(ruff/mypy/content-quality) into a new subsystem. `--mode copy` gets no
wrapper: no live harness checkout stays reachable from inside a copy
install, so there is nothing for a wrapper to delegate to; `doctor`
soft-warns (never hard-fails — a pre-#110 install just needs one `update`
run) when a non-`copy` install is missing its wrapper, and `audit --json`
exposes a `can_mechanically_enforce` boolean plus `hooks`/
`helper_commands` fields so an agent (or CI) can check this *before*
starting work instead of discovering it mid-task. Explicitly out of
scope: expanding the gate itself to cover lint/typecheck beyond
`enforce-profile`'s existing test+coverage scope — a separate, future
decision, not bundled into closing this gap.

## Relative symlinks for submodule/npm install modes

**Status:** Settled.

**Context:** [#106](https://github.com/andr-ca/agentharness/issues/106)
fixed `--mode link`'s absolute-path symlinks by changing the *default*
mode to `copy`, but [#109](https://github.com/andr-ca/agentharness/issues/109)
(a Copilot review comment on #106's own PR) pointed out the same failure
class survives one layer down in `--mode submodule` and `--mode npm`:
both already made the *source* portable (a submodule/durable copy
travels with a `git clone`), but the skill symlinks pointing at that
source were still created via a plain `ln -s "$src" "$dst"`, where
`$src` is built from `$target` — resolved to an absolute path via
`cd "$target" && pwd` at install time. Install with `--mode submodule`
or `--mode npm`, commit the result, clone the whole project onto a
different machine or a different absolute path on the same machine —
the symlinks still point at the old absolute location and resolve to
nothing, identical to #106's failure mode.

**Consequences:** `tools/setup/harness-link.sh`'s new `relative_symlink()`
helper computes a path relative to the symlink's own parent directory
(via `python3 -c 'import os; os.path.relpath(...)'`, already a hard
dependency of this script — no new one added) before calling `ln -s`,
used for both `submodule` and `npm` modes, in both `cmd_init`'s and
`cmd_update`'s skill-linking loops. `--mode link` deliberately keeps
absolute symlinks: it's documented (per #106's fix) as the
same-machine, same-checkout, not-for-committing case, so a relative
path adds nothing there and adds one more thing that could go stale if
the *project* moves relative to the harness checkout instead of the
reverse. Verified by installing with each mode, moving the installed
project to a different absolute path, and confirming `doctor` still
passes — this reproduces the exact scenario #106/#109 were filed
against, not just a symlink-format check.

Live-testing this fix also surfaced a related-but-separate bug:
`cmd_update` and part of `cmd_doctor` read the recorded `source.path`
from `.agentharness-state.json` verbatim for `submodule`/`npm` modes,
which is *also* a stale absolute path after the whole project moves —
`cmd_update` hard-fails on it rather than recomputing
`$target/.agentharness` or `$target/.agentharness-pkg` fresh the way
`cmd_init` does. Filed separately as
[#124](https://github.com/andr-ca/agentharness/issues/124) rather than
folded into this fix, since it's a different code path (state-recorded
source location, not symlink target format) with its own scope.

## Label-gated, unverified-by-default automated issue analysis

**Status:** Settled — narrowed scope, this repo only, not a harness
feature for consumers.

**Context:** [#107](https://github.com/andr-ca/agentharness/issues/107)
proposed a general-purpose harness feature: a GitHub Actions workflow
that auto-triages every opened issue via an unattended opencode agent.
This repo already ships `github-issue-triage`, an on-demand skill doing
the same verify-claims-and-recommend analysis with a human reviewing
before anything gets posted; the workflow's only real gain over that is
not having to invoke the skill by hand. Weighed against that small
convenience: this repo has never run an LLM agent unattended in CI
before, `issues: opened` is attacker-controlled content from untrusted
external accounts, and granting an agent `issues: write` to post public
comments off that content under the repo's identity is a new trust
surface, not a scoped fix. Declined as a general harness feature for
consumers for those reasons.

**Consequences:** built narrower, for this repo's own issue volume
only, not distributed via `harness-link.sh` to consumers.
`.github/workflows/issue-analysis.yml` triggers on `issues: opened`
(filed already labeled) and `issues: labeled` (labeled afterward),
gated in both cases on the `needs-analysis` label specifically — since
only accounts with triage/write access can apply a label to someone
else's issue at all, a random external opener can't self-trigger it
either way; a maintainer choosing to label an issue, at creation or
later, is what starts the process. The agent
(`.opencode/agents/issue-analyzer.md`) is read-only (`edit: deny`,
`bash` allowlisted to read-only commands) and its skill
(`.opencode/skills/issue-analysis/SKILL.md`) requires every output to
open with a disclaimer banner stating the analysis is unverified and
not authorized to be auto-implemented. The workflow relabels to
`auto-analyzed`, never `analyzed` — `analyzed` is reserved for a human
maintainer to apply after actually reading the output, so the bot never
gets to vouch for its own work. `.opencode/agents/` is otherwise this
repo's generated Claude-agent-porting output
(`tools/generate-opencode-agents.sh`); `issue-analyzer.md` is a hand-
authored exception there (opencode's custom-agent location is fixed,
not configurable) — `tools/verify-content-quality.py`'s
`check_opencode_agents_sync()` explicitly ignores it rather than
flagging it as drift.

**2026-07-20 update (live-caught race, issue #112):** filing an issue
already carrying `needs-analysis` in one API/CLI call fired both an
`opened` event and a separate `labeled` event as distinct webhook
deliveries, racing two concurrent runs — two duplicate comments got
posted, and the second run's `removeLabel` call 404'd. Fixed with a
`concurrency: group: issue-analysis-${{ github.event.issue.number }}`
block to serialize runs per issue, plus a dedupe gate that re-fetches
the issue's current labels and no-ops if `needs-analysis` was already
consumed by an earlier run in the same group, instead of trusting the
triggering event's label snapshot.

**2026-07-20 update (live-caught hang, issue #115):** re-testing the
dedupe fix above surfaced a second, unrelated problem — the third-party
`anomalyco/opencode/github` action itself hung for over 1h45m with no
progress or error on one live run, and because runs are now serialized
per issue, that also blocked the queued second run behind it. Root
cause unconfirmed (no step-log visibility into a still-running action;
cancelling it to unblock testing lost the evidence) — flagged as an
open question in #115 in case it recurs and points at the free-tier
model backend's reliability. Mitigated with a job-level
`timeout-minutes: 15`, generous against the one successful run's actual
~1-minute runtime, so a future hang fails fast instead of running for
hours.

**2026-07-20 update (auto-retry, issue #115):** a timeout alone just
fails fast, it doesn't recover — since the hang's root cause is
unconfirmed and plausibly transient, added
`.github/workflows/issue-analysis-retry.yml`, a **separate** workflow
triggered by `workflow_run: types: [completed]` that reruns the whole
issue-analysis run via `gh run rerun` (not `--failed`, which only
reruns `failure`-conclusion jobs and would silently skip the
`timed_out`/`cancelled` case this exists for — caught by Copilot
review on the pull request that introduced this file; the workflow has
a single job, so rerunning the whole run is equivalent on success and
correct for every failure mode), up to 2 retries (bounded by
`github.event.workflow_run.run_attempt < 3`,
so a persistent failure still surfaces after 3 total attempts instead
of looping forever). Has to be a separate workflow rather than a step
inside issue-analysis.yml's own job: the rerun API only accepts a run
that has reached a completed/terminal state, so a still-running job
can't rerun itself. Composes safely with the dedupe fix above — a
rerun re-executes the job from scratch, including the dedupe gate,
which correctly finds `needs-analysis` still present (a failed attempt
never reached the relabel step) and proceeds normally.

## Copy as the default install mode, reversing symlink-as-default

**Status:** Settled — reverses "Symlink as the default install mode, not
copy or submodule" below, which is kept for history and marked
superseded rather than deleted.

**Context:** [#106](https://github.com/andr-ca/agentharness/issues/106)
reported a real failure this default caused: `--mode link` symlinks are
*absolute paths* anchored to the harness checkout's exact location on
the machine that ran `init`. A project installed that way, committed,
and cloned onto a different machine (or even the same machine under a
different checkout path) gets skill symlinks that resolve to nothing —
silently, since nothing prompts a fresh clone to run `doctor`, which is
the only thing that currently notices. The original decision weighed
symlink/copy/submodule as a sync-freshness trade-off and picked the
"always current" option; it didn't fully weigh that the *default* is
what everyone gets who doesn't stop to read the trade-off, and for a
tool whose entire purpose is being installed into *other people's*
repos, "works only on the machine that ran init" is a bad property for
a default to have. It's also inconsistent with this repo's own npm/npx
distribution path (`bin/cli.js`), which already defaults to `--mode
npm` — a durable copy, not a symlink — for exactly this class of
portability reason (see "npm as the low-friction distribution channel"
below).

**Consequences:** `harness-link.sh init`'s default (`--mode` omitted)
is now `copy`, matching what `--mode npm` already effectively
preferred. `--mode link` remains fully supported and is still the right
choice for one specific case — actively co-developing the harness
itself alongside a project on the same machine — and is documented as
such in `docs/INTEGRATION.md`'s "Method 2: Symlinks" section, not
removed or discouraged outright. Existing installs aren't silently
migrated (their recorded `mode` in `.agentharness-state.json` is
unaffected by this change); `docs/INTEGRATION.md`'s "Migrating from
link mode" subsection documents the one-command fix (`init --mode
copy` re-run against the same target). The rendered core-instructions
block installed into every consumer's `CLAUDE.md`/`AGENTS.md` also now
carries a `doctor` hint for the "skill looks empty/unreadable" symptom,
and inline git-conventions text that doesn't depend on the `branching`/
`committing` skills being readable at all.

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

**Status:** Settled and shipped — published to npm as `agentharness-toolkit`
(first release `v0.2.0`); see Consequences for the two one-time manual
resolutions the first publish needed.

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

**2026-07-13 update (P0-06):** the original `AGENTS.md` adapter's
foundational premise was wrong — Codex CLI has a real on-demand skill
mechanism (the Agent Skills open standard, shared with Claude Code since
December 2025), not "no on-demand loading." Redesigned: every skill now
installs into `.agents/skills/<name>` alongside `.claude/skills/<name>`
(same source), and `AGENTS.md` shrank from concatenating every skill's
full body (880 lines/33.7KB) to routing rules plus a name+description
index (201 lines/11.6KB). Still not verified against a live Codex CLI
session end-to-end — the "don't claim what you haven't tested" caveat
stands, now against the corrected mechanism instead of the wrong one.

**2026-07-14 update (cross-platform parity):** research across the
remaining major agentic coding tools (OpenCode, Gemini CLI, Cursor,
GitHub Copilot, Antigravity, Zed, Kilo Code — full findings in
`docs/CLIENT_COMPATIBILITY.md`) found that the Codex exception above
generalizes further than expected. The Agent Skills open standard
(published December 2025, adopted within 48 hours by OpenAI and
Microsoft, 32+ tools by March 2026) means `.agents/skills/` — already
populated for every consumer by `harness-link.sh` — is a recognized
compatibility path for OpenCode, Gemini CLI, GitHub Copilot, Antigravity,
Zed, and Kilo Code too, not just Codex. Separately, always-on
project-instructions have converged around `AGENTS.md` as a de facto
cross-tool standard (OpenCode's and Zed's primary file, Antigravity's
fallback), so this repo's existing `AGENTS.md` was likely already doing
more work than its "Codex-only" framing gave it credit for.

Given that, this repo now builds and dogfoods the same
generated-routing-file-plus-skill-index adapter for `GEMINI.md`
(Gemini CLI/Antigravity), `.github/copilot-instructions.md` +
`.github/instructions/*.instructions.md` (GitHub Copilot's own
`applyTo`-glob mechanism, reusing frontmatter this repo's
`languages/*/CONVENTIONS.md` files already carried), and
`.kilo/rules/agentharness.md` (Kilo Code) — plus a structurally
different adapter for Cursor (`.cursor/rules/*.mdc`), the one platform
researched with no confirmed Agent Skills support.

This *broadens the structural coverage claim, not the tested-claim*:
"Claude-first" as a statement about what's actually been dogfooded in a
live session is unchanged — every new generated file carries the same
"not verified against a live session" caveat already established for
Codex. What changed is that "Claude-first, with one Codex exception" was
too narrow a description of what the `.agents/skills/` design already
made possible; it's now described accurately as "Claude-first, tested;
structurally covers 8 of 9 researched platforms via generated adapters,
none of them live-verified but all of them honestly labeled."

## Symlink as the default install mode, not copy or submodule

**Status:** Superseded — see "Copy as the default install mode,
reversing symlink-as-default" at the top of this file
([#106](https://github.com/andr-ca/agentharness/issues/106)). Kept here
for history, not applied.

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
