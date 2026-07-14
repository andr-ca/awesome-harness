---
title: "agentharness fourth-pass repository review"
reviewed_at: "2026-07-14T02:10:52Z"
reviewer: "GPT-5.6 Codex"
repository_commit: "4f3e94b"
previous_review: "docs/operational/reviews/gpt-5.6-sol-3rdpass-2026-07-13T134419Z.md"
---

## Executive verdict

**Overall: 7.4/10 — a strong engineering prototype and useful Claude-first
policy kit, but not yet a proven multi-client product or a safe general-purpose
installer.**

The repository improved substantially since the third pass. The npm install is
now durable, profiles enforce real Python/Go/Node/Vitest coverage, consumer
coverage hooks exist, releases have a real ancestry/CI gate, invalid skill
selection is atomic, Codex no longer receives every skill body up front, and
the test surface is much broader.

However, the repository also expanded from 152 to 216 tracked files and added
roughly 9,000 net lines across 73 commits in less than a day, before any
non-Claude client was live-tested and before one real external project was
dogfooded. That breadth created new safety and consistency failures:

1. `generate-clients` silently overwrites consumer-owned instruction files.
2. Forced hook installation does not restore the pre-existing hook path.
3. Explicit npm mode from a checkout copies untracked files, including `.env`.
4. The repository's own offline verification is currently red.
5. Three generated client adapters already drift from the source policy.
6. Status, limitation, integration, roadmap, and compatibility documents
   disagree with the current implementation.

The core idea remains good. The next move should be **proof and contraction,
not more platform breadth**: make installation non-destructive, restore a green
release gate, live-test Claude and Codex end to end, dogfood one external repo,
and turn the compatibility matrix into measured evidence.

## Review scope and method

I reviewed the repository at commit `4f3e94b`, including the product idea,
README/onboarding, architecture and integration documents, operational status,
client compatibility claims, shell lifecycle implementation, generators,
release workflow, profiles, eval scaffolding, skills, custom-agent ports, and
tests.

I compared the current tree with the third-pass baseline (`69ab106`), read the
third-pass status report, ran deterministic source checks, executed the offline
verification in a disposable clone, ran all `tools/tests/*.bats` directly, and
performed three focused destructive-behavior reproductions only in `/tmp`.

I attempted to refresh the time-sensitive Codex claims against official OpenAI
documentation, but the documentation endpoint was unavailable from this
environment due DNS/network restrictions. Therefore, Codex-specific conclusions
below are based on the current repository, the capabilities visible in this
Codex session, and bounded uncertainty. Exact config/path claims still require a
real supported-version compatibility test.

## What changed since the third pass

The change set is unusually large:

| Measure | Third pass | Fourth pass | Change |
|---|---:|---:|---:|
| Tracked files | 152 | 216 | +42% |
| Tracked lines | ~18,700 | 26,551 | ~+42% |
| Commits since baseline | — | 73 | one-day expansion |
| Client instruction targets | Claude + best-effort Codex | 8 named tools | materially broader claim |
| Custom-agent ports | none | 6 generated targets | structurally tested only |
| Language guides | 3 | 4 | Rust added |
| Pattern areas | 5 | 6 | accessibility added |

The strongest improvements are real rather than cosmetic:

- npm/npx initialization now creates a durable `.agentharness-pkg` rather than
  leaving links into an ephemeral npx cache.
- `enforce-profile` now gates Python, Go, Node's test runner, and Vitest, with a
  strict mode for unsupported project types.
- `--with-coverage-hook` creates a consumer-owned pre-push hook and has a real
  push acceptance test.
- Invalid or traversal-like skill names fail before mutation; `none` is the
  explicit zero-skill selection.
- Release publication now checks tag/version agreement, ancestry, and a
  successful CI run for the exact commit.
- Codex skills are installed under `.agents/skills`, while `AGENTS.md` is a
  router/index rather than an 880-line concatenation of all skill bodies.
- Generator outputs are parsed for TOML/YAML validity and checked for drift.
- Lifecycle/state-transition and hermeticity coverage is much better.

These changes move implementation maturity forward. They do not yet establish
that the expanded multi-client product works for users.

## Reassessment of the third-pass P0 items

| Prior item | Fourth-pass status | Assessment |
|---|---|---|
| P0-01 hook ownership | **Partial** | Refusal, ownership recording, doctor checks, and "leave changed values alone" are fixed. The requested previous-value restoration is still absent under `--force`. |
| P0-02 durable npm/npx install | **Mostly fixed** | Published-package behavior is durably copied and tested. Explicit `--mode npm` against a checkout has an unsafe whole-tree copy boundary. |
| P0-03 consumer profile enforcement | **Fixed with scope caveat** | The opt-in coverage hook enforces supported runners. Unsupported runners remain non-blocking unless strict mode is selected. |
| P0-04 atomic invalid skill selection | **Verified fixed** | Bad names and traversal fail before mutation; explicit `none` is tested. |
| P0-05 release gate | **Verified structurally fixed** | The workflow has a credible exact-commit CI/ancestry gate and package smoke check. Current source drift means the tree itself is not release-ready. |
| P0-06 Codex adapter | **Architecture fixed; compatibility unverified** | Progressive skill discovery and a compact router are the right shape. No live supported-version session proves all claimed paths, agents, or precedence. |

### P0-01 acceptance remains incomplete

The state records only the installed hook path
(`tools/setup/harness-link.sh:151-189`). Under `--force`, the previous path is
read and overwritten (`tools/setup/harness-link.sh:676-735`) but never persisted.
Uninstall then unsets the installed value (`tools/setup/harness-link.sh:1596-1633`)
instead of restoring the prior value.

Reproduction:

```text
before init:      core.hooksPath=.preexisting-hooks
after --force:    core.hooksPath=<agentharness hooks>
after uninstall:  core.hooksPath=<unset>
```

This is less destructive than the third-pass defect, but it still violates the
expected reversible lifecycle.

## Scorecard

| Dimension | Third pass | Fourth pass | Why |
|---|---:|---:|---|
| Idea / product thesis | 8.5 | **8.5** | A portable, versioned engineering-policy kit remains valuable. |
| Product focus | 7.2 | **6.6** | Eight-client breadth, six agent ports, Rust, and accessibility arrived before live proof or external dogfood. |
| Documentation structure | 8.0 | **8.1** | STATUS, KNOWN_LIMITATIONS, compatibility, decisions, and operational docs improve navigation. |
| Documentation correctness | 7.0 | **6.2** | Multiple current contradictions and unsupported time-sensitive platform claims now exist. |
| Implementation maturity | 7.2 | **7.8** | Lifecycle, release, enforcement, and generator mechanics improved materially. |
| Tests and CI | 8.5 | **8.4** | Test breadth is excellent, but the committed tree is red and package tests contaminate later tests on failure. |
| Safety / reversibility | 7.0 | **6.5** | Three reproducible destructive/secret-copy boundaries are release blockers. |
| Usefulness today | 7.2 | **7.6** | Useful now for a careful Claude-first adopter; multi-client usefulness is still asserted, not demonstrated. |
| Release readiness | 6.8 | **6.6** | The workflow is stronger, but generated drift and a failing local gate make the current commit unreleasable. |
| GPT-5 / Codex fit | 4.5 | **6.5** | Correct progressive-disclosure shape and native skill path; live behavior and custom agents remain unverified. |

**Weighted overall: 7.4/10.** The codebase gained capability faster than the
score because evidence, safety, and product focus did not keep pace.

## What is working especially well

### 1. The product is becoming operational, not merely documentary

The lifecycle CLI, state file, doctor/audit commands, install modes, release
workflow, generators, profile enforcement, and tests now form a real system.
This is the largest positive change from the original review.

### 2. Honest limitation documents exist

`docs/STATUS.md` and `docs/KNOWN_LIMITATIONS.md` explicitly admit that
non-Claude clients are not live-tested, real dogfood does not exist, and evals
are infrastructure rather than evidence. That honesty should remain the tone of
all top-level claims.

### 3. Codex context usage is much healthier

Moving skill bodies out of always-on `AGENTS.md` and installing them under
`.agents/skills` is a substantial improvement. The current 211-line adapter is
far better than the prior 880-line version. The repository is now aligned with
the progressive-disclosure behavior visible in this Codex environment.

### 4. Tests target behavior and regression classes

The repository now tests real push rejection, invalid input atomicity,
worktrees, hook conflicts, state transitions, generator syntax, committed-output
drift, npm cache disappearance, strict enforcement, and consumer fixtures. This
is unusually good for a policy/tooling repository.

### 5. Release controls are now credible

The release workflow no longer treats a matching version as sufficient proof.
Exact-commit CI and ancestry checks directly address the earlier publication
risk.

## Release-blocking findings (P0)

### P0-01 — Make client generation non-destructive

`cmd_generate_clients` writes directly to `AGENTS.md`, `GEMINI.md`, Copilot,
Cursor, and Kilo locations (`tools/setup/harness-link.sh:1668-1725`). It does
not detect existing consumer content, preview a merge, create a backup, require
`--force`, use managed blocks, or record ownership for uninstall.

Verified reproduction:

```text
input first line:  # Consumer-owned AGENTS instructions
command:           generate-clients <target> --client codex
output first line: # AGENTS.md
result:            original file silently replaced
```

**Action:** default to refusal when a target exists and is not an exact
agentharness-managed output. Add `--force` only for explicit replacement, plus
`--dry-run`/diff. Prefer managed blocks where the target format permits them.
Record generated paths and hashes in state so doctor/update/uninstall can
distinguish harness content from user content.

**Acceptance tests:** preserve a sentinel file; refuse atomically across
multi-client generation; do not leave earlier clients written when a later
client conflicts; update only a managed block; uninstall preserves user edits.

### P0-02 — Restore the previous hook value after forced ownership

**Action:** add `previous_hooks_path` (including an explicit "previously
unset" representation) to managed state. On uninstall, if the current value is
still the harness-owned value, restore the previous value. If it changed after
install, leave it untouched and warn.

**Acceptance tests:** unset→install→uninstall, foreign→refuse, foreign→force→
restore, relative foreign path→force→restore exact original string, and
post-install user change→preserve.

### P0-03 — Restrict npm durable copying to a package allowlist

`copy_npm_durable_source` copies all of `HARNESS_DIR` except `.git` and its own
destination (`tools/setup/harness-link.sh:319-343`). The comment assumes npm
has already pruned the source, but the shell CLI publicly accepts
`--mode npm`, so that invariant is not enforced.

Verified from a disposable checkout:

```text
source contained untracked .env
init --mode npm completed
consumer/.agentharness-pkg/.env existed
```

The normal published-npm path is safer because `package.json`'s `files`
allowlist prunes the package first. The direct shell path still duplicates
secrets and potentially huge directories into another project.

**Action:** copy an explicit manifest/allowlist, or reject npm mode unless the
source is recognizably a packed npm artifact. Always exclude secret/env files,
VCS metadata, dependency/build caches, and the target subtree. Never rely on a
commented caller assumption for a security boundary.

**Acceptance tests:** untracked `.env`, `.env.local`, `node_modules`, nested
target, symlinks, spaces, and a packed-tarball golden manifest.

### P0-04 — Restore a green self-verification gate before the next release

`bash tools/check.sh --offline` failed in a disposable clone. A direct run of
all `tools/tests/*.bats` produced **177 passes and 5 failures out of 182**:

- deterministic generated-output drift: `AGENTS.md`, `GEMINI.md`, and
  `.kilo/rules/agentharness.md` do not match their generators after the latest
  `CLAUDE.md` policy change;
- the npm cache-disappearance test failed during the pack/materialization path;
- a later materialization test found its expected symlinks already replaced,
  showing failed package setup can contaminate subsequent tests.

The full check stops in the pre-push Bats suite because that suite recursively
invokes the repository checks and observes these failures.

**Action:** regenerate every affected adapter, then make package
materialization transactional with a trap/finally-style restoration path.
Isolate package tests in their own clone rather than modifying the suite's repo
root. Ensure each test independently establishes and cleans its preconditions.

**Acceptance:** two consecutive offline runs from clean clones pass; after an
intentionally interrupted `npm pack`, tracked symlinks and `git status` are
unchanged; test order randomization does not alter results.

## High-priority improvements (P1)

### P1-01 — Freeze new client breadth and establish a compatibility contract

Treat Claude as supported, Codex as beta, and every other adapter as
experimental until tested. Define a versioned matrix with:

- client name and exact tested version;
- instruction discovery and precedence;
- skill discovery and activation;
- custom-agent invocation/delegation;
- workspace/user-scope behavior;
- fixture, command, expected trace, result, and last-tested date.

Do not count "a valid generated file" as client compatibility.

### P1-02 — Run a real Claude + Codex dogfood loop

Install a pinned release into one independent Python or TypeScript repository.
For each client, run at least five representative tasks: policy lookup, Python
review, branch/commit guidance, error-handling change, and a task that must not
load an irrelevant skill. Capture instruction/skill activation evidence,
failures, context cost, and user friction.

This is more valuable than adding another language, framework, pattern, or
adapter.

### P1-03 — Turn eval scaffolding into product evidence

Create a small versioned corpus with blind baseline versus harness conditions.
Score rule adherence, correctness, unnecessary context, destructive actions,
and task completion. Publish seeds, prompts, model/client versions, raw
redacted traces, scorer rubric, and confidence intervals. The current runner's
coverage proves its code works; it does not prove the harness improves agents.

### P1-04 — Repair documentation drift with generated facts

Concrete current contradictions include:

- `docs/STATUS.md:74` reports 6 skills; 7 are installed, including
  `port-agent-config`.
- `docs/STATUS.md:82-83` and `docs/KNOWN_LIMITATIONS.md:31-35` say profile
  enforcement is not wired into pre-push; `--with-coverage-hook` now does so.
- `docs/INTEGRATION.md:28` omits supported Go and Vitest enforcement.
- `docs/INTEGRATION.md:29` says update shows a diff; it lists changed skill
  names but does not show content diffs.
- `ROADMAP.md:117-134` still says Go/Vitest and pre-push wiring are not built.
- `docs/CLIENT_COMPATIBILITY.md:14-16` defines ✅ as "built and dogfooded" while
  rows use ✅ for implementations explicitly marked not live-tested.

**Action:** generate simple counts and capability tables from the manifest/test
matrix; add a vocabulary with separate `built`, `structurally tested`,
`live-tested`, and `supported` states; fail CI on stale generated status blocks.

### P1-05 — Remove fragile or unsourced platform marketing claims

`docs/CLIENT_COMPATIBILITY.md` contains highly time-sensitive assertions about
tool paths, delegation semantics, default parallelism, launch timing, and
adoption. Some may be correct, but a repository-local generator test cannot
verify them.

**Action:** attach official source links and `verified_at` dates to each claim,
or rewrite it as an explicit hypothesis awaiting a live compatibility test.
Avoid ephemeral market/adoption commentary in a durable technical contract.

### P1-06 — Make strict enforcement selectable at install time

`--with-coverage-hook` invokes enforcement, but unsupported runners exit zero
unless `--strict` is used manually. Add an explicit policy such as
`--coverage-unsupported fail|warn|skip`, record it in state, show it in status,
and generate the hook accordingly. Production profiles should default to
`fail`; prototype profiles can warn or skip.

### P1-07 — Make update previews truthful and exact

Implement a bounded content diff or rename the documentation to "change
summary." Confirmation must apply exactly the previewed plan and detect both
upstream changes and consumer-local modifications. Add a source revision/hash
precondition to avoid time-of-check/time-of-use drift.

### P1-08 — Decouple package materialization from mutable Git state

The current restore operation uses `git checkout`; this fails in read-only Git
metadata, non-Git source distributions, and interrupted package workflows.
Build the package in a temporary staging tree. Never mutate the developer's
tracked source as part of packing.

### P1-09 — Define state migrations before version 2 exists

Add a state parser with supported-version bounds, a v1→v2 migration fixture,
unknown-new-version refusal, corrupt/partial-state recovery guidance, and
round-trip tests. The newly needed previous hook value and generated-file
ownership are good reasons to design this now.

### P1-10 — Reduce always-on instruction weight further

`AGENTS.md` is improved but still 211 lines/~12.8 KB. Test whether Codex's own
`.agents/skills` metadata scan makes the repeated skill index unnecessary. Move
GitHub-specific publishing details out of universal client routers where the
target client may not have `gh` or remote-write authority. Keep always-on policy
to routing, safety invariants, and repository-specific facts.

### P1-11 — Split universal invariants from language/style preferences

Keep universal policy to security, correctness, testing proportionality,
ownership, reversibility, and verification. Move naming, casing, UI wording,
arrow-function style, and framework-specific choices into scoped guides that
yield to the consumer's formatter, linter, and design system.

## Useful follow-ups (P2)

1. Archive completed review cycles and keep one active status/backlog view.
2. Add moved-source, package-upgrade, downgrade, corrupt-state, interrupted
   update, and partial multi-client generation transitions.
3. Add install/uninstall property tests: unrelated consumer files/config must
   remain byte-identical.
4. Add size/context budgets for all always-on adapters, measured in tokens as
   well as lines/bytes.
5. Add a machine-readable support matrix and generate the README summary from
   it.
6. Add Windows and macOS validation before claiming general portability;
   current shell/tar/readlink assumptions are Unix-oriented.
7. Add a threat model covering untrusted repository instructions, generator
   source injection, symlink traversal, secret copying, shell command creation,
   and remote-write authority.
8. Make `doctor --json` return stable reason codes so consumers and CI do not
   parse prose.
9. Measure install/update time, generated context size, and disk footprint.
10. Add a minimal "choose your path" onboarding: consume policies, author a
    skill, or maintain the harness.

## Specific guidance for GPT-5 / Codex

### What is now right

- `.agents/skills/<name>/SKILL.md` is the correct progressive-disclosure shape
  for the behavior visible in this Codex session.
- The always-on adapter no longer embeds all skill bodies.
- Skill descriptions provide a routing surface, and bundled resources remain
  adjacent to their skill.
- Generated Codex custom-agent TOML is syntax-tested rather than treated as
  arbitrary text.

### What still needs proof or refinement

1. **Test activation, not file presence.** Demonstrate that a fresh Codex
   session discovers the intended skill and reads its complete `SKILL.md` only
   when relevant.
2. **Test precedence.** Verify root/nested `AGENTS.md`, user-level instructions,
   and consumer-owned content with exact supported Codex versions.
3. **Test custom-agent semantics.** Confirm `.codex/agents/*.toml` path,
   supported keys, model behavior, delegation, permissions, and failure modes
   in a real session.
4. **Avoid duplicate routing context.** If Codex already scans skill metadata,
   remove the repeated AGENTS skill index unless an experiment proves it helps.
5. **Use concise descriptions.** Descriptions should state the trigger and
   outcome, not encode entire procedures; this improves tool/skill selection.
6. **Add negative-routing evals.** Measure irrelevant skill activation and
   instruction collisions, not only whether the desired skill can be found.
7. **Port capabilities semantically.** A TOML file produced from Claude
   frontmatter is not equivalent until tool permissions and isolation behavior
   are explicitly mapped or deliberately omitted with a visible warning.
8. **Version the compatibility claim.** Say "tested with Codex X on date Y"
   rather than "Codex supports" without a bound.

## Recommended execution sequence

### Phase 1 — regain safety and green status

1. Regenerate drifted adapters and restore a clean offline check.
2. Make package creation staging-tree based and interruption-safe.
3. Refuse consumer-file overwrites by default.
4. Restore prior hooks after forced installs.
5. Constrain npm durable-copy inputs with an explicit allowlist.

### Phase 2 — prove the narrow product

6. Declare Claude supported and Codex beta; mark all others experimental.
7. Dogfood one external project with Claude and Codex.
8. Run a small baseline/treatment eval and publish the evidence.
9. Correct status/roadmap/compatibility terminology from generated facts.

### Phase 3 — expand only from evidence

10. Promote one additional client only after passing the compatibility contract.
11. Add languages/frameworks only when a dogfood consumer or measured demand
    requires them.
12. Introduce state v2 with hook restoration and generated-file ownership.

## Release recommendation

**Do not publish another release from this commit.** First close P0-01 through
P0-04 and obtain two consecutive green clean-clone checks. The existing v0.2.0
can remain an early/experimental release if its documentation clearly limits
support to the verified path.

After those fixes, the repository would be a credible **8/10 Claude-first,
Codex-beta harness**. Reaching a credible multi-client 8.5+ requires live
compatibility evidence and external dogfood, not additional generated files.

## Verification record

- Repository commit reviewed: `4f3e94b`
- Working tree before report: clean
- `tools/check.sh --offline` in disposable clone: **failed**
- Direct `bats tools/tests/*.bats`: **177/182 passed; 5 failed**
- Deterministic generator comparison: **AGENTS.md drift confirmed**; the Bats
  suite also confirmed GEMINI and Kilo router drift
- Hook ownership reproduction: previous path became unset after forced install
  and uninstall
- Client-generation reproduction: existing `AGENTS.md` was silently replaced
- npm-copy reproduction: untracked `.env` was copied into
  `.agentharness-pkg`
- Python component results observed inside the check: logging **37 passed,
  99.45%**; agent loop **9 passed, 100%**; eval tools **15 passed, 87.5%**

This is an assessment only. No implementation finding was fixed as part of this
review.
