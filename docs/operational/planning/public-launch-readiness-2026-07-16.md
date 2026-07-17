---
date: 2026-07-16
last_updated: 2026-07-17
status: in-progress
topic: planning
purpose: Sequenced readiness plan for the repo's first deliberate public-attention moment — an external article and social post will link here
related-harness: docs/operational/reviews/fable-gpt5-sol-disposition-2026-07-14.md
---

# Public-Launch Readiness Plan (2026-07-16)

## Overview

An external article on why coding agents need a harness, with an
accompanying social post, will link to this repository. That is a
different bar than merely being public (this repo has been public since
2026-07-11): readers will arrive cold, skim the README for under a
minute, and the skeptical minority will check whether the repo's own
audit trail contradicts its pitch. This plan sequences the work needed
before that link goes out.

Every status below was **re-verified against the tree on 2026-07-16**
(branch `docs/public-launch-readiness`, base `2d9fd41`) — not copied
from prior status documents.

## Verified current state

Findings labeled F-xx come from
[fable-gpt5-sol-disposition-2026-07-14.md](../reviews/fable-gpt5-sol-disposition-2026-07-14.md).

| Finding | Status at HEAD | Evidence (2026-07-16) |
|---|---|---|
| F-01 adapter drift | ✅ Closed (manually) | `CLAUDE.md` last edited 2026-07-15; `AGENTS.md`/`GEMINI.md` regenerated 2026-07-16 — currently in sync. No automation guarding recurrence. |
| F-02 committing-skill contradiction | ❌ Open | `.claude/skills/committing/SKILL.md` (lines 46–52) still mandates "commit → push → PR. Don't stop at the commit," contradicting the opt-in publish-authority model. Safety-relevant; ships to every consumer. |
| F-03 destructive `generate-clients` | ❌ Open | `cmd_generate_clients` (`tools/setup/harness-link.sh`) still has no existence check, `--force`, backup, or state record. |
| F-04 npm durable copy over-broad | ❌ Open | `copy_npm_durable_source` still tars everything except `.git` and the durable dir — untracked `.env*` would be copied into a consumer. |
| F-05 hooks path not restored on uninstall | ❌ Open | Zero occurrences of `previous_hooks_path` in `harness-link.sh`. |
| F-06 stale hand-written status | ⚠️ Stale | `docs/STATUS.md` says "last verified 2026-07-13" — that predates the Tier-2/3 skill batches, the bootstrap-policy core, and the completion gate. |
| F-07 review-loop archive | ❌ Open | `docs/operational/reviews/` is flat — 15 files, no dated archive dirs. |
| F-08 external evidence | ❌ Open | `docs/KNOWN_LIMITATIONS.md` remains accurate: no real-world dogfood, no live non-Claude session, no eval run. |

**Also fixed while verifying** (dev environment, not repo content): this
checkout's local git config carried leaked test state — `core.bare=true`,
`core.hooksPath=someone/else/changed/this`, and a stale
`submodule..agentharness.url` pointing into a deleted `/tmp` directory —
which had left the working tree frozen at a pre-PR-#55 state while
`main`'s ref advanced underneath it. Restored with `core.bare=false`,
`core.hooksPath=.github/hooks`, removing the stale submodule section,
and `git checkout -- .`. This is the F-05 failure class manifesting in
the dev checkout itself; treat it as live evidence for Workstream A, and
consider a test-infrastructure guard asserting the bats suites never
mutate the enclosing repo's config.

## Workstream A — close the open P0s (blocking)

The repo's own filed reviews call F-02–F-05 release blockers, one of
them safety-relevant. A reader who follows the audit trail will find
them; "fixed, or honestly re-dispositioned with rationale" is the bar.

| Item | Action | Est. |
|---|---|---|
| F-02 | Rewrite committing skill to the verify-and-stage default + publish-authority reference; regenerate `.cursor/rules/committing.mdc` and `.agents/skills/committing/` | 30 min |
| F-03 | `generate-clients`: refuse when target exists and isn't harness-generated; add `--force` / `--dry-run`; record outputs in state | 2 h |
| F-04 | npm durable copy: allowlist-based copy (or reject unrecognized sources); always exclude `.env*`, VCS metadata, caches; tests | 1 h |
| F-05 | Persist `previous_hooks_path` in state; restore on uninstall; warn on post-install user change; tests | 1 h |
| Follow-up | Update the 2026-07-14 disposition doc's per-item statuses to match | 15 min |

## Workstream B — front door (blocking, ~1 h)

- **GitHub repo description** — still the pre-product placeholder
  ("My handpicked harnesses…"); replace with the README's actual
  one-liner.
- **Topics** — currently none; add (e.g. `ai-agents`, `claude-code`,
  `coding-agents`, `agent-skills`, `developer-tools`).
- **Homepage** — set (owner's site).
- **README top restructure** — first screen should carry: the pitch
  paragraph, then the three distinctive governance mechanisms (opt-in
  publish authority, enforced completion gate, review/merge mandates),
  then the `docs/DEMO.md` link — before the compatibility matrices and
  caveat blocks that currently dominate the first scroll.
- **Naming** — one explicit line that the repo is `agentharness` and the
  npm package is `agentharness-toolkit`.

## Workstream C — doc-accuracy sweep (blocking, ~1–2 h)

- Re-verify `docs/STATUS.md` row by row; bump its "last verified" date.
- Re-verify `docs/KNOWN_LIMITATIONS.md` against the tree.
- Optional but recommended (F-07): archive completed review cycles under
  dated directories so `docs/operational/` reads as history rather than
  churn to a first-time visitor.

## Workstream D — external evidence (highest value, scheduled)

Execute [planning/DOGFOODING.md](./DOGFOODING.md) against at least one
real, non-fixture project (owner has candidates lined up; target:
before 2026-07-19 weekend is over).

- A **public** target is preferred for this launch: it produces
  linkable evidence (a real repo, a real commit installing the harness).
- A second, **private**, different-stack target adds signal per
  DOGFOODING.md's P2-02 note without needing a public link.
- Record findings in DOGFOODING.md's tracking table; update
  `KNOWN_LIMITATIONS.md`'s "no real-world dogfood" bullet accordingly.

## Sequencing and definition of done

A → C → B (all doable in a day, in that order — fixes first, then make
the docs describe the fixed state, then polish the surface) → D
(weekend) → article links in.

Done means: every ❌ row above is ✅ or re-dispositioned with written
rationale; STATUS/KNOWN_LIMITATIONS re-verified at a current commit;
repo metadata updated; at least one dogfood row recorded.

## Out of scope (deliberate)

- **F-09** (CLAUDE.md always-on token budget) and **F-10**
  (ARCHITECTURE.md rewrite) — real items, not launch-gating; they stay
  on the disposition backlog.
- **Funded eval runs** (P2) — post-launch.
- **The article itself** — external content, drafted and maintained
  outside the repo in the gitignored local `media/` workspace.

---

## GPT-5.6 review addendum (2026-07-16)

**Reviewer posture:** evidence-first assessment for a deliberate public
attention moment, with the expected audience including skeptical senior
engineers, financial-services executives, and readers who will inspect the
repo's own audit trail.

### Disagreements and corrections

1. **The current definition of done is too narrow.** Closing F-02–F-08,
   refreshing docs, setting metadata, and recording one dogfood row would not
   make the current product story internally consistent. The new deterministic
   Python core is not wired through the public npm launcher; the acceptance
   ledgers disagree; the local “all checks” command omits the core suite; the
   declared Production tier and the core's CI coverage threshold disagree; and
   npm/Python versions differ. These are launch-truth issues even if the
   article focuses on the governance thesis.

2. **A → C → B → D is the wrong evidence flow.** Workstream A must come
   first, but dogfood should happen before the final documentation and front
   door are frozen. Real integration findings should change `STATUS`,
   `KNOWN_LIMITATIONS`, the README, and possibly the product boundary. The
   safer sequence is clearance → safety fixes → release-integrity gate →
   dogfood → docs → front door → final release verification.

3. **“All doable in a day” and the itemized hour estimates are optimistic for
   safety-boundary work.** F-03–F-05 change destructive behavior, ownership,
   state restoration, and test infrastructure. Completion should be gated by
   adversarial acceptance tests, not elapsed-time estimates.

4. **Self-hosting is not external evidence, and author-owned project use is
   not independent adoption.** Installing into another author-owned public
   repo is valuable cross-repository self-dogfood. Describe it that way. Do
   not call it customer use, third-party validation, or proof of generalized
   productivity.

5. **The F-01 row understates the existing recurrence guard.**
   `tools/verify-content-quality.py` already regenerates and compares
   `AGENTS.md`, `GEMINI.md`, Kilo, Copilot, Cursor, and the custom-agent
   adapters, and CI runs that check. Re-verify it in a clean checkout and mark
   adapter drift automation closed if green. The public claim should still
   distinguish CI-checked harness adapters from consumer-local copies that
   require an explicit lifecycle update.

6. **F-07 should be curated, not merely hidden.** The honest review trail is
   part of the article's thesis. Keep a concise indexed summary and archive raw
   cycles by date; do not make important unresolved findings harder to locate.

7. **A generic owner homepage is not automatically useful metadata.** Set a
   homepage only if it leads to a relevant project page, documentation, or the
   article. An unrelated personal landing page is worse than no homepage.

8. **Full funded eval infrastructure can remain post-launch, but a minimal
   evidence bundle cannot.** If the article retains phrases such as “earned
   their keep,” pre-launch evidence must show what happened in a real task.
   Otherwise change the wording to “mechanisms I am testing” and make no
   effectiveness claim.

### Workstream 0 — employer, outside-activity, and IP clearance (blocking)

Before amplifying an already-public repo:

- log the repository, article, LinkedIn activity, and related speaking activity
  through the applicable outside-activity/MCOI process;
- document that no employer code, data, internal policies, confidential
  examples, accounts, devices, or work product entered the project;
- obtain guidance on using the current employer and title in the post or
  speaker biography; and
- use an accurate personal-capacity/non-endorsement disclaimer. “Built on
  personal time and equipment” is a factual assertion and must only be used if
  it is fully true.

This is a publication gate, not a README substitute.

### Workstream E — product and release integrity (blocking)

Add the following before Workstream D:

1. **Choose the launch product boundary.** Either wire the Python policy core
   into the public CLI and complete its command contract, or label it
   experimental/unreleased and launch the working policy/skills installer.
   Do not market a bootstrap command the public launcher cannot execute.
2. **Reconcile release truth.** Align or explicitly separate the npm package,
   Python package, tag, changelog, and documented version.
3. **Make acceptance machine-verifiable.** Reconcile the Markdown and YAML
   acceptance ledgers, remove/fix the duplicate verifier implementations, and
   require the release-mode verifier to pass.
4. **Make local verification match CI.** Add the core suite to
   `tools/check.sh`; either meet the Production-tier 80% line-plus-branch bar or
   explicitly reclassify/scoped-exclude experimental core code. Do not end with
   “All checks passed” while omitting a CI suite.
5. **Refresh the threat model.** `SECURITY.md` must describe runtime downloads,
   mutations to consumer repos and git config, GitHub protection changes, npm
   distribution, private reporting, and the supported security boundary.
6. **Update `setuptools`.** The pinned `80.9.0` build/dev dependency is affected
   by CVE-2026-59890; move to `83.0.0` or later while preserving the project's
   exact-pin policy, then re-run packaging checks.
7. **Run a dedicated secret/history scan** and record the tool/version/result.
   Basic pattern matching is not sufficient for a release that may copy source
   trees into consumer projects.
8. **Freeze and smoke-test a release candidate.** Install the exact packed npm
   artifact and any Python artifact into a clean repo, exercise
   init/generate/update/doctor/uninstall, and confirm current remote CI green.
9. **Make local content gates ignore local tooling state.** The current
   content-quality traversal descends into gitignored `.worktrees`, and the
   Markdown glob reaches nested `.kilo/node_modules` and
   `.opencode/node_modules`. This produces false local failures from historical
   worktree snapshots and third-party docs. Prune worktree/tool dependency
   directories while continuing to scan all tracked project Markdown.

### Workstream D target recommendation

#### Primary public target — Recalium

Use [Recalium](https://github.com/andr-ca/recalium) as the primary public
dogfood target after F-02–F-05 and Workstream E's product-boundary decision.

It is the best candidate because it is active, public, multi-stack
(FastAPI/PostgreSQL/React/MCP), has real release-readiness tasks, and already
contains project-specific Claude, Codex, Gemini, Cursor, and AGENTS surfaces.
That existing configuration makes it a meaningful test of ownership,
non-destructive generation, canonical-policy integration, and project-local
overrides.

Use a pinned release candidate in a dedicated branch/worktree. Hash and record
the existing agent files before installation. Recommended bounded tasks:

1. fix Recalium's documented cross-suite fact-leakage test flake; and
2. add one missing Playwright keyboard/accessibility evidence scenario or
   another bounded item from its
   [v1 gap register](https://github.com/andr-ca/recalium/blob/main/docs/operational/validations/recalium-v1-release-readiness-gap-register.md).

Run the harness across at least two genuine work sessions, preferably one with
Claude and one with Codex. Record install time, conflicts/overrides, context
cost, false positives, actual blocked actions, verification outcomes,
update/uninstall restoration, the pinned harness release, and the resulting
Recalium commit/PR. A negative finding is valid evidence and should not be
polished away.

The article must call this **cross-repository self-dogfood**, not independent
adoption, and must avoid causal productivity or quality claims.

#### Secondary private target — StarkyStar

[StarkyStar](https://starkystar.com/) is a useful second target because a
consumer family application provides product and stack distance from
developer tooling. Use it only after confirming ownership/IP provenance and
with no real child, family, customer, production, or secret data in prompts,
logs, traces, screenshots, or published evidence.

Because the source and change are not publicly inspectable, it cannot be the
article's primary proof point. Refer to it generically as “a private consumer
application” unless naming it is deliberate and cleared.

#### Defer Breqy and TeleCLI for this launch

- [Breqy](https://github.com/andr-ca/breqy) is a good later integration target,
  but using a multi-agent runtime as the first example blurs the distinction
  between model, agent runtime, and governance harness.
- [TeleCLI](https://github.com/andr-ca/telecli) is a valuable later
  least-privilege/security stress test because it controls terminal sessions
  through web, Telegram, and optional AI automation. It should first close its
  own public-facing security, licensing, and README-polish gaps so those do not
  distract from the harness evidence.

### Required dogfood evidence bundle

The tracking row in `DOGFOODING.md` should link to a dated status artifact that
contains:

- target repo and starting commit;
- harness release/artifact and integrity identifier;
- pre-existing agent configuration inventory and hashes;
- exact install/generate/update/uninstall commands and timings;
- real task description and resulting commit/PR;
- test/lint/type/coverage outcomes;
- conflicts, overrides, false positives, and abandoned features;
- observed authority/completion behavior, including failures to block;
- configuration restoration diff after uninstall; and
- a bounded verdict: keep, revise, or remove, with reasons.

Do not manufacture a baseline from incomparable tasks. For this launch, a
specific qualitative finding is enough if the article explicitly says no
effectiveness evaluation has been completed.

### Revised sequence and expanded definition of done

Recommended sequence:

```text
Workstream 0 clearance
  → Workstream A safety fixes
  → Workstream E product/release-integrity gate
  → Workstream D Recalium dogfood
  → Workstream C doc-accuracy sweep
  → Workstream B front door
  → clean-clone/package/current-CI verification
  → article factual/adversarial review
  → publish
```

In addition to the original criteria, “done” requires:

- outside-activity/IP clearance recorded outside the public repo as required;
- generated-adapter drift checks confirmed green in a clean checkout, with the
  consumer update boundary described accurately;
- public CLI and documented commands aligned;
- versions and acceptance ledgers reconciled;
- local checks matching CI and the rigor-tier decision documented;
- updated threat model, fixed build dependency, and recorded secret scan;
- exact release artifact successfully exercised in a clean clone;
- Recalium evidence linked and described as self-dogfood;
- every article use of “blocks,” “requires,” “cannot,” or “enforced” mapped to
  a mechanism verified at the linked release; and
- no unresolved placeholders, employer implication, or unmeasured efficacy
  claim in the article or companion post.

---

## Session 3 — Independent audit of the status report (2026-07-17)

**New session.** Every ✅ in
[public-launch-readiness-2026-07-16-status.md](./public-launch-readiness-2026-07-16-status.md)
was re-verified against the tree at `main` (`96ef3be`), not taken on
trust. Verdict: **16 of 17 claimed-complete items verified genuinely
done; 1 missed gap found; 1 in-progress item has since completed but the
status file wasn't updated.**

### Verified done (spot-checked against repo state)

- **F-02** — `.claude/skills/committing/SKILL.md` now carries the
  verify-and-stage default + publish-authority model (lines 44–60).
- **F-03** — `--force`/`--dry-run` flags and non-harness-file refusal
  present in `harness-link.sh`; `tools/tests/generate-clients.bats` has
  12 tests covering skip-without-force, force-overwrite-with-warning,
  and dry-run-writes-nothing.
- **F-04** — `copy_npm_durable_source` tar excludes `.env`, `.env.*`,
  `*.env`, `node_modules`, `.cache`, `__pycache__`, `*.pyc`,
  `.worktrees` (`harness-link.sh:329–355`).
- **F-05** — `previous_hooks_path` recorded in state and restored on
  uninstall (`harness-link.sh:1642–1647`).
- **E3** — `tools/acceptance/verify_matrix.py` gone; only
  `verify-matrix.py` remains.
- **E4** — `tools/check.sh:147–158` runs the core suite with
  `--cov=src/agentharness --cov-fail-under=65`.
- **E5** — `SECURITY.md` covers npm distribution, git-config mutations,
  GitHub protection boundary, and the supported boundary.
- **E6** — `setuptools==83.0.0` exact-pinned in both `pyproject.toml`
  and `requirements-dev.txt`.
- **E9** — `verify-content-quality.py:322` prunes `.worktrees` from the
  markdown scan.
- **F-07** — `docs/operational/reviews/README.md` exists;
  `INDEX.md:26` references it.
- **Workstream B (all 6)** — `gh repo view` confirms the description,
  5 topics, and homepage are live; README has the "What makes it
  different" section (line 11) and the repo/npm naming line (line 5);
  all 11 `tools/generate-*.sh` generators emit the GitHub provenance
  URL and generated outputs (e.g. `AGENTS.md:4`) carry it.

### ❌ Missed gap found by this audit

- **E1 is only half done.** The status file claims "MANIFEST.md and
  STATUS.md both label bootstrap policy core as ⚠ EXPERIMENTAL —
  unreleased." `docs/STATUS.md:29` does say "Python core is
  experimental/unreleased," but **MANIFEST.md has never contained the
  label** — PR #65 (the commit that marked E1 ✅) did not touch
  MANIFEST.md at all, and `git log -S EXPERIMENTAL -- MANIFEST.md`
  across all branches is empty. MANIFEST's bootstrap rows say
  "(approved; not implemented)"/"(planned; not implemented)", which
  describes the *plans*, not the shipped `src/agentharness/` core.
  **Action needed:** add the experimental/unreleased label to the
  relevant MANIFEST.md rows, then correct the E1 note in the status
  file.

### Status file stale in the other direction

- **C "STATUS.md re-verification" (🔄) is now done.** PR #74
  (`e212544`, merged 2026-07-17) performed the full row-by-row sweep;
  `docs/STATUS.md:20` reads "Last verified against the tree: 2026-07-17
  (commit `af36f2c`)." The status row should move to ✅.
- **E2 note is stale on facts:** versions have since moved to npm
  `v0.2.1` / pyproject `0.1.1` (not `0.1.0`); the deliberate
  deferral of full reconciliation stands.

### Still outstanding (confirmed, not just claimed)

| Item | Status | Evidence / blocker |
|---|---|---|
| Workstream 0 — clearance record | ⏸ owner | Recorded outside repo; nothing verifiable here |
| A — disposition wrap-up | ❌ | `fable-gpt5-sol-disposition-2026-07-14.md` F-02–F-05 sections still read as open; no per-item status updates |
| E1 — MANIFEST.md label | ❌ (new) | See missed gap above |
| E2 — version reconciliation | 🔄 deferred | Deliberate post-launch deferral; STATUS.md documents the split |
| E7 — secret/history scan | ⏸ owner | No recorded gitleaks/trufflehog result |
| E8 — RC smoke test | ⏸ owner | Needs clean environment |
| D — dogfood run + evidence bundle + KNOWN_LIMITATIONS | ⏸ owner | All three blocked on the Recalium run |
| C — KNOWN_LIMITATIONS re-verification | ❌ | File untouched since PR #47 (`e98335c`) — predates all launch work |

### Not tracked in the status file at all

The addendum's expanded definition of done has items with **no status
row anywhere**:

- clean-clone / packed-artifact / current-CI release verification;
- article factual/adversarial review (external, but the gate is listed
  here);
- F-01 follow-up from addendum item 5: re-verify the adapter-drift
  check green in a clean checkout and formally close F-01's automation
  caveat.

These should either get rows in the status file or an explicit
out-of-scope note, so the tracker and the definition of done agree.
