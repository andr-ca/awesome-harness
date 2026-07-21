---
date: 2026-07-16
status: archived
topic: planning
purpose: Archival record of the Fable-vs-GPT-5.6 disagreements from the initial public-launch plan review round, with Fable's feedback and recommendation per item
related-harness: docs/operational/planning/public-launch-readiness-2026-07-16-status.md
---

# Public-Launch Plan — Review Disagreement Register (2026-07-16, archival)

**This is a historical record from the initial 2026-07-16 review round**,
recovered from an abandoned branch that forked the plan doc immediately
after this content was written. It was never merged, and the plan
document it originally accompanied has since continued evolving
directly on `main` through several follow-up PRs — see
[public-launch-readiness-2026-07-16-status.md](./public-launch-readiness-2026-07-16-status.md)
for current progress. Kept for the review context and rationale it
captures, not as a live companion to the current plan.

Two reviews shaped the launch plan: Fable's original
(`public-launch-readiness-2026-07-16.md`, first revision) and a GPT-5.6
addendum (full text in the appendix below; originally appended to the
plan, moved here to keep the plan executable). Where the two disagree,
this file records both positions, Fable's feedback, and a
recommendation. The clean plan carries only resolved decisions; where a
decision is the owner's, the plan states the recommended default as an
explicit assumption.

## Resolved by verification (no longer disagreements)

| Item | Outcome |
|---|---|
| F-01 recurrence automation | GPT-5.6 was right, Fable's plan was wrong: `tools/verify-content-quality.py:343-362` + CI already guard adapter drift. Corrected in the plan. |
| "Bootstrap command is marketed" | Overstated by GPT-5.6: `bootstrap` appears in no public-facing doc except `MANIFEST.md`. The product-boundary decision (D3) still stands on its own. |
| All Workstream E factual claims | Confirmed against the tree (versions 0.2.0 vs 0.1.0; `check.sh` omits the core pytest suite; production tier 80% vs core gate 65%; duplicate differing verifiers; SECURITY.md gaps; setuptools 80.9.0 / CVE-2026-59890 fixed in 83.0.0; markdown scan descends into `.worktrees`). Full evidence table in the appendix. |

## Disagreement register

### D1 — Sequencing: docs before or after dogfood

- **Fable:** A → C → B → D (fixes, then docs, then front door, dogfood
  on the weekend last).
- **GPT-5.6:** 0 → A → E → D → C → B → verify → review → publish —
  dogfood before docs/front door freeze, because real integration
  findings should change STATUS, KNOWN_LIMITATIONS, and the README.
- **Feedback:** GPT-5.6 is right on the substance — running C/B before
  D invites a second docs pass, and the first dogfood of a real
  multi-stack repo *will* surface things the docs should say. Fable's
  order was optimizing calendar (weekend dogfood), not evidence flow.
- **Recommendation:** Adopt GPT-5.6's order. One practical carve-out:
  purely mechanical B items (repo description, topics — ~10 minutes,
  unaffected by dogfood findings) can be done at any point.

### D2 — Hour estimates vs adversarial-acceptance gating

- **Fable:** Per-item hour estimates; A "doable in a day."
- **GPT-5.6:** Estimates are optimistic for safety-boundary work
  (F-03–F-05 change destructive behavior, ownership, state
  restoration); completion should be gated by adversarial acceptance
  tests, not elapsed time.
- **Feedback:** These answer different questions — estimates schedule,
  gates define done — so it's a false conflict, but GPT-5.6's implicit
  "this will take longer than you think" is probably correct for
  F-03/F-04 (installer ownership semantics have edge cases the
  disposition doc already enumerates).
- **Recommendation:** Keep estimates as scheduling hints only; the
  completion criterion per item is its acceptance-test list passing.
  If an item runs past ~2× its estimate, stop and reassess scope
  rather than pushing through a safety boundary tired.

### D3 — Definition-of-done breadth / product boundary (the big one)

- **Fable:** Narrow DoD — P0s closed, docs re-verified, metadata set,
  one dogfood row. The Python-core integration questions were not
  launch-gating.
- **GPT-5.6:** Expanded DoD including all of Workstream E: wire the
  core into the CLI or label it experimental, reconcile versions and
  acceptance ledgers, make `check.sh` match CI, refresh SECURITY.md,
  bump setuptools, secret scan, RC smoke test.
- **Feedback:** Every E fact verified, so the launch-truth concern is
  real. But the breadth is driven by one root cause: an experimental
  core that the public launcher doesn't expose. Resolve that with a
  **label**, and E-3 (ledger reconciliation) and the 80%-vs-65% tier
  question shrink from engineering work to labeling/scoping decisions.
  Wiring the core into the CLI under deadline pressure, days before
  invited public scrutiny, is exactly how the next safety finding gets
  created.
- **Recommendation:** Decide E-1 as **"label the Python core
  experimental/unreleased for this launch"**; adopt the slimmed E that
  falls out (versions, SECURITY.md, setuptools, secret scan, RC smoke
  test, scan pruning stay; ledger dedupe stays but as cleanup;
  tier-vs-gate resolved by scoping the core out of the production-tier
  claim until it ships). Revisit wiring post-launch. The clean plan
  assumes this default; the owner can override.

### D4 — Repo homepage target

- **Fable:** Set homepage to the owner's site (andr.ca — deliberate,
  since the identity link is the point of the launch).
- **GPT-5.6:** A generic personal landing page is worse than no
  homepage; set one only if it leads somewhere relevant.
- **Feedback:** "Unrelated personal page" overstates it — andr.ca is a
  deliberate identity anchor. But GPT-5.6 is right about visitor
  intent: someone clicking a repo's homepage wants product context,
  not a resume.
- **Recommendation:** Homepage → the article URL once it's live
  (docs/DEMO.md link until then). The andr.ca link belongs on the
  GitHub *profile*, which is where identity-seekers actually look.

### D5 — Evidence wording in the article

- **Fable:** Post-dogfood, "earned their keep"-strength wording is
  acceptable.
- **GPT-5.6:** Without a pre-launch real-task evidence bundle, wording
  must be "mechanisms I am testing"; no effectiveness claims.
- **Feedback:** GPT-5.6's bar is the safer public posture and costs
  almost nothing, since the dogfood bundle is planned pre-publication
  anyway — at which point stronger wording is licensed by *linkable*
  evidence instead of vibes.
- **Recommendation:** Adopted already (draft softened to "the ones I
  keep leaning on"). Re-strengthen only with the Recalium evidence
  bundle linked from the article, and keep the "cross-repository
  self-dogfood, not independent adoption" framing permanently.

### D6 — Formality of employer/outside-activity clearance

- **Fable/owner:** Policy confirmed 2026-07-16 — no approvals required
  for open-source pet projects or public speaking.
- **GPT-5.6:** Log the repo, article, and speaking through the
  applicable outside-activity/MCOI process; document that no employer
  resources were used.
- **Feedback:** GPT-5.6 can't see the owner's actual policy, so it
  demanded the generic maximum. But its underlying point survives the
  confirmation: a dated personal record of *what was checked and
  concluded* converts "I confirmed it" into evidence if anyone ever
  asks.
- **Recommendation:** One dated note, kept outside this public repo,
  recording the policy consulted and the determination. Five minutes;
  not blocking anything else.

### D7 — How prescriptive the dogfood run should be

- **Fable:** Any real project; public preferred; owner picks the task.
- **GPT-5.6:** Recalium specifically, two named bounded tasks (the
  cross-suite fact-leakage flake; a Playwright accessibility scenario),
  two sessions across two tools, pre-install hash inventory, full
  evidence bundle.
- **Feedback:** The rigor (bundle, hashes, two tools, negative findings
  kept) is a clear improvement and costs little. The specific task
  selection is a reviewer guessing the owner's backlog priorities from
  the outside — reasonable suggestions, not requirements.
- **Recommendation:** Adopt the evidence-bundle checklist and
  two-session/two-tool shape wholesale; treat the two named Recalium
  tasks as defaults the owner may swap for equivalent bounded real
  work. Recalium primary / private consumer app secondary / Breqy and
  TeleCLI deferred stands as agreed.

---

## Appendix A — GPT-5.6 addendum (verbatim, moved from the plan)

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

## Appendix B — Fable's tree-verification of the addendum (moved from the plan)

| Addendum claim | Verdict | Evidence |
|---|---|---|
| Python core not wired through npm launcher | ✅ Confirmed | `bin/cli.js` only wraps `tools/setup/harness-link.sh` (`spawnSync('bash', [SCRIPT…])`); `src/agentharness` is unreachable from the npm bin. Nuance: no public doc *markets* a bootstrap command — `bootstrap` appears only in `MANIFEST.md` among public-facing docs, not README/INTEGRATION/STATUS/DEMO. |
| npm/Python versions differ | ✅ Confirmed | `package.json` 0.2.0 vs `pyproject.toml` 0.1.0. |
| Local “all checks” omits core suite | ✅ Confirmed | `tools/check.sh` runs mypy on `src/` but its pytest steps target runtime/seed/config_loader/agent_loop/eval only — no `src/agentharness` test suite; `tools/check-completion.sh` does run it (≥65% branch). |
| Production tier vs core coverage bar disagree | ✅ Confirmed | `.agentharness-profile` = `production` (80% bar per `patterns/testing/COVERAGE_REQUIREMENTS.md`); completion gate enforces ≥65% branch on `src/agentharness`. |
| Acceptance ledgers/verifiers duplicated | ✅ Confirmed (duplication) | Both `…acceptance-matrix.md` and `…acceptance.yaml` exist; `tools/acceptance/verify-matrix.py` and `verify_matrix.py` are two differing ~100-line implementations (`diff -q` differs). Content-level disagreement to be reconciled during Workstream E. |
| F-01 recurrence guard already exists | ✅ Confirmed | `tools/verify-content-quality.py:343-362` + adapter-parity checks; plan corrected accordingly. |
| Content-quality traversal descends into `.worktrees`/nested `node_modules` | ✅ Confirmed | Markdown scan uses unpruned `scan_root.rglob("*.md")` (`verify-content-quality.py:321`); the YAML scan already prunes via `os.walk` (`:126-136`). Matches the false local failures observed 2026-07-16 (all in `.worktrees/`). |
| `SECURITY.md` threat-model gaps | ✅ Confirmed | Zero mentions of npm distribution, git-config mutation, or hooksPath in `SECURITY.md`. |
| setuptools 80.9.0 affected by CVE-2026-59890 | ✅ Confirmed | Pin present in `pyproject.toml:2` and `requirements-dev.txt:8`; advisory confirmed externally — MANIFEST.in exclusion bypass via Unicode normalization (NFD filenames evade NFC exclusion rules on macOS sdist builds), fixed in setuptools 83.0.0 (2026-07-04). |
| Recalium repo specifics (existing agent surfaces, gap register) | ⏸ Not re-verified here | External repo; owner-confirmed. Verify starting state per the evidence bundle at install time. |
