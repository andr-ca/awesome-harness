# GPT-5.6 review follow-up — P1/P2 backlog completion status

**Timestamp:** 2026-07-12T19:24:10Z
**Source:** `gpt-5.6-review.md`, continuing from `gpt-5.6-review-status.md`
  (snapshot at `43604a7`, 1 of 30 items verified complete at that point)
**Snapshot:** `c6b1e6e597f1210b584c83924711b1ce8e023101` on
  `chore/add-remaining-components` (PR #4)
**Assessment method:** per `CLAUDE.md`'s Agent Recommendation Assessment
  mandate — scoped/low-risk items implemented directly; the P2 batch's
  product-direction items were scoped and confirmed with the user before
  implementation (see "P2 items not implemented" below).

## Summary

**Scope note (added 2026-07-13 per the independent re-audit below):** "the
entire P1 backlog" in this section's original title means specifically
the P1-06–P1-14 slice — it does not cover P1-01 through P1-05. P1-02
(selectable profiles and precedence) in particular remains **advisory
only**: `patterns/profiles/README.md` says outright that no script reads
`.agentharness-profile` yet. See
`docs/operational/reviews/gpt-5.6-completion-reaudit-status.md` for the
full current disposition of every backlog item, including P1-01–P1-05.

Since the `43604a7` snapshot, the P1-06–P1-14 slice of the P1 backlog
was implemented, verified locally, and confirmed green on hosted CI for
every push:

| Item | What shipped |
|---|---|
| P1-06/P1-07 | Pinned dev/CI toolchain (`requirements-dev.txt`), fixed submodule-mode `source.path` bug, CI supply-chain fixes (bats-core SHA, shellcheck-directive parsing) |
| P1-08 | `content-quality` CI job: `git diff --check`, `markdownlint-cli2`, `verify-content-quality.py` (YAML/frontmatter/tested-snippet validation) |
| P1-09 | TypeScript/Go convention guides technically corrected (compiled/verified examples); `frameworks/react/CONVENTIONS.md` split out |
| P1-10 | Rationalized testing/logging policy duplication — `patterns/testing/README.md` rewritten from a 464-line near-duplicate into a real index; 80%-coverage language scoped to Production tier everywhere it appeared |
| P1-11 | `README.md`/`docs/INTEGRATION.md` onboarding docs repaired against actually-executed commands — 3 real bugs found only by running the documented commands (stale per-skill symlink lists, `cp -r` reproducing a fixed dangling-symlink bug, a single-quoted heredoc silently discarding its own expansion) |
| P1-12 | `CHANGELOG.md` `Unreleased` section; new `docs/RELEASING.md` (versioning policy, release checklist, pin/upgrade/rollback table backed by a real bats test using this repo's actual git history) |
| P1-13 | Fixed contradictions: `BRANCHING_STRATEGY.md`'s naming-format heading vs. its own examples; `.github/README.md`'s stale hooks list and wrong GitHub owner in its example; `languages/`, `patterns/`, `frameworks/` category READMEs claiming categories that don't exist (rust/, api-design/, vue/, django/, …) while omitting ones that do (agentic-loops, error-handling, profiles); `ROADMAP.md` describing `tools/` as unbuilt when it's substantially built; `SECURITY.md`'s stale 2-executable inventory |
| P1-14 | `SECURITY.md` expanded with an "instruction attack surface" section (CLAUDE.md/SKILL.md are agent instructions, not just executable code — a materially different risk the prior version didn't name); explicit maintainer-responsibility statement; conditional triggers for a private disclosure channel and independent instruction-change review |

Plus the confirmed-scope half of the P2 batch (see below).

All of the above landed as five commits on PR #4
(`de867a1`, `4bb8158`/`ccf795a`, `38541e9`, `5c98934`, `c6b1e6e`), each
individually verified via the full local suite (`tools/check.sh`,
`git diff --check` against `origin/main`, the `pre-push` hook) and then
confirmed green on hosted CI via `gh run watch` before moving to the
next item — per the user's standing instruction to check actual CI
status after every push, not just local hooks.

## P2 batch — what was implemented

The user was asked to scope the 8-item P2 list before implementation
(several items are product-direction decisions, not scoped fixes — see
`CLAUDE.md`'s Recommendation Assessment mandate). Confirmed scope: do
the safe half now, write up the rest as options.

- **P2-01 (partial):** `harness-link.sh audit --json` — the review's
  specific complaint was "no machine-readable output" for this repo's
  one real audit capability. Now emits the same drift data as the text
  mode as a single JSON object. A full new top-level `agentharness audit`
  binary/command (implied by "signature capability" framing in the
  original review) was not built — `harness-link.sh audit` already *is*
  that capability; the gap was output format, which is now closed.
- **P2-07:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor
  Covenant), `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md`,
  a CI status badge on the README. Not done: a demo (would need an
  actual recording/hosting decision) and ADRs (would need retroactively
  documenting past decisions — real work, but additive and low-risk;
  listed below as small enough to just do on request rather than as a
  "needs a decision" item).
- **P2-08:** README gained a one-line positioning subtitle and a "Why
  not just CLAUDE.md?" section.

## P2 items — expanded scope, built to their respective boundaries

**Timestamp:** 2026-07-12T22:10:00Z
**Precision correction added:** 2026-07-13 (per the independent
re-audit) — "now implemented" below described the infrastructure, not
the outcome each recommendation actually asked for. Only P2-06 is a
fully closed outcome. P2-02, P2-03, and P2-04 are foundations built up
to an explicit, named external boundary this session cannot cross on its
own (an unverified real-client test, publish credentials, and API spend,
respectively) — not the completed capability (a verified Codex client, a
published package, real evaluation results) the original review asked
for. See
`docs/operational/reviews/gpt-5.6-completion-reaudit-status.md` for the
precise per-item verdicts.

After the options memo below was written, the user reviewed it and chose
the most ambitious option for all four remaining items. Given the size
and real external dependencies involved (npm registry credentials, live
API costs for evals), this was planned via `EnterPlanMode`/`ExitPlanMode`
before any code changed — see the approved plan for the full design and
sequencing rationale. The user approved that plan with no changes. All
four are now built, sequenced in the plan's order, each its own commit
group, verified locally and confirmed green on hosted CI before moving
to the next:

| Item | Commit(s) | What shipped |
|---|---|---|
| P2-02 | `ad8e4ea` | `tools/generate-agents-md.sh` builds `AGENTS.md` (Codex's equivalent of `CLAUDE.md`) from `CLAUDE.md` + every skill's `SKILL.md`, generated (not hand-maintained) so it can't drift; a CI drift-check regenerates and diffs against the committed copy; README/INTEGRATION.md state plainly this is untested against a real Codex session |
| P2-06 | `ea71715`, `0585922`, `086276b`, `907b466`, `72f6880`, `f294b6d` | Cut generic tutorial/reference material from `languages/{python,typescript,go}/CONVENTIONS.md`, `patterns/logging/{README,LOGGING_STANDARDS}.md`, `patterns/testing/{TDD,COVERAGE_REQUIREMENTS,PLAYWRIGHT_UI_TESTING}.md`, `patterns/error-handling/README.md`, `.github/BRANCHING_STRATEGY.md`, and one restated line in `.github/CODING_GUIDELINES.md` — kept every repo-specific decision, deduplicated the 80%-coverage mandate to one source of truth. Caught and preserved several genuine repo decisions in the TypeScript file that an initial automated inventory had mis-classified as "100% generic" (private-field guidance, null-vs-undefined framework, async/await rethrow rule) by reading the file in full before cutting |
| P2-03 | `88ae11a`, `9b86f4d` | `package.json`/`bin/cli.js` so `npx agentharness init` works as an alternative to `git clone`; `.github/workflows/release.yml` runs `npm publish` on a `v*` tag. Built up to the credential boundary only — publishing needs an `NPM_TOKEN` secret and confirming the package name, neither of which this session can do. Caught a real bug via end-to-end testing (pack → unpack → run), not just eyeballing the `files` list: the `agentic-loops` skill's bundled-resource symlinks don't survive `npm pack` (tarballs don't preserve symlinks the way git does), which would have shipped a silently-broken skill to every npm-installed consumer — fixed with a prepack/postpack materialize-then-restore step |
| P2-04 | `093acc0` | `tools/eval/`: 3 task specs (2 Python, 1 Go) with hidden grading tests; `score.py`, a fully deterministic scorer (no LLM calls) tested against hand-written correct/broken fixtures per task; `run.py`'s orchestration logic (condition setup, ledger writing) unit-tested with a fake, free agent — `invoke_agent_via_api`, the piece that would spend real API credits, is deliberately left unimplemented; results ledger format documented in `tools/eval/results/README.md` |

None of this expanded past what the user approved in the plan — P2-05
(real dogfooding) remains explicitly out of scope as a non-coding item,
unchanged from the original assessment below.

## P2 items — original options memo (superseded above, kept for the record)

### P2-02 — Cross-agent adapters (Codex/`AGENTS.md`, others)

**What it is:** generate or package tested adapters for Claude Code,
Codex/`AGENTS.md`, and other agent clients from one canonical policy
catalog, instead of the Claude-only scope stated in the README's Product
Contract today.

**Why it's not scoped-and-done:** this is a support-surface commitment,
not a fix. Claiming Codex support means testing discovery/reference
resolution against a real Codex checkout (which this environment may
not have access to validate the same way `.claude/skills/` is verified
here), and a wrong claim is worse than no claim — the README already
explicitly warns "don't assume Cursor, Copilot, or another harness picks
up `.claude/skills/` the same way." Widening that claim needs either a
real test fixture for the second client or an explicit "untested, best
effort" caveat, and the user should decide which stance to take before
work starts.

**Options:**
1. Do nothing — stay Claude-only, most honest given no way to test
   others here.
2. Add an `AGENTS.md` adapter for Codex specifically, generated from the
   same skill/convention source, with an explicit "untested against a
   real Codex session" caveat until someone verifies it.
3. Scope a fixture similar to `examples/*-project/` but for a second
   client, if one is available to test against.

### P2-03 — Low-friction distribution (marketplace, package, plugin)

**What it is:** something better than "clone plus mutable local
symlinks" as the default onboarding path — a Claude Code plugin, a
package registry entry, or similar.

**Why it's not scoped-and-done:** this is an infrastructure/hosting
commitment (a plugin marketplace listing, a package registry account)
that outlives this PR and this session, and picking one shapes how every
future consumer integrates — squarely the kind of call CLAUDE.md asks to
confirm before building.

**Options:**
1. Do nothing — `harness-link.sh init --mode submodule` already gives a
   version-pinned, non-mutable-path option today; that may be "good
   enough" until real adoption pressure exists (see P2-05).
2. Package as a Claude Code plugin (if the plugin format documented
   elsewhere in this environment fits) — moderate effort, one clear
   target.
3. Publish to a package registry (npm, PyPI-as-a-vendoring-shim, etc.)
   — more effort, ongoing maintenance (version bumps, registry account).

### P2-04 — Evaluations

**What it is:** a task set, baseline, method, and results/cost/adherence
measurements proving the harness actually changes agent behavior for the
better.

**Why it's not scoped-and-done:** this is a new subsystem requiring real
design work (what counts as a task, what's the baseline "no harness"
condition, how is adherence scored) — not something to improvise inside
an unrelated PR. It's also the kind of claim ("this measurably helps")
that's worse wrong than absent.

**Options:**
1. Skip for now — no eval harness exists in comparable single-maintainer
   tooling repos either; may not be worth the investment yet.
2. Small pilot: 3-5 concrete tasks (e.g. "add a Python module with
   tests," measured with/without the harness's CLAUDE.md/skills loaded),
   scored on a simple rubric (coverage achieved, convention violations,
   time/turns to green CI). Cheap enough to be a single follow-up PR.
3. Full eval suite with tracked baselines over time — real ongoing
   investment, only worth it once adoption (P2-05) is real.

### P2-06 — Reduce generic encyclopedia

**What it is:** cut the long-form, mostly-generic material in
`languages/`, `patterns/testing/`, `patterns/logging/`, and elsewhere —
content that reads as general programming-advice boilerplate rather than
this-repo-specific policy — replacing it with links to authoritative
external sources where a generic explanation adds no real value.

**Why it's not scoped-and-done:** this is a deletion call over content
someone (a past session) wrote deliberately, and "generic" is a judgment
this session can't make unilaterally without risking cutting something a
future reader actually needed. Note also: this same follow-up pass
already found and fixed several *factually wrong* generic-sounding
sections in `languages/README.md`, `patterns/README.md`, and
`frameworks/README.md` (P1-13) — those were corrected, not cut, because
the fix was "make it accurate," not "make it shorter." P2-06 is a
different, larger ask: is *accurate-but-generic* content itself the
problem.

**Options:**
1. Leave as-is — accurate generic content isn't wrong, just long; low
   urgency.
2. Targeted trim: identify the 2-3 most encyclopedia-like files (likely
   `languages/python/README.md`'s "Performance Tips"/"External
   References" sections, `patterns/logging/README.md`'s duplicated
   level-by-level walkthrough already mostly covered in
   `LOGGING_STANDARDS.md`) and cut just those, replacing with a link out.
3. Full pass across every doc — largest effort, real risk of cutting
   something valuable; should be its own reviewed PR, not folded into
   this one.

### P2-05 — Real dogfood

Not a coding task at all — it means this harness gets pinned and used in
one or more real (non-scratch-fixture) projects, ideally by someone other
than its own author, over enough time to surface real friction. Nothing
to implement here; noting it so it isn't silently dropped from the
backlog.

## Links

- PR: #4 (`chore/add-remaining-components` → `main`)
- Prior status: `gpt-5.6-review-status.md` (snapshot at `43604a7`),
  `pr4-comments-status.md` (PR #4 review-comment disposition)
