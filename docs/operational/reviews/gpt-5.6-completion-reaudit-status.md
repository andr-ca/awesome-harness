# GPT-5.6 Completion Re-audit — Response

**Timestamp:** 2026-07-13T03:04:34Z
**Source:** `docs/operational/reviews/gpt-5.6-completion-reaudit.md`
  (re-audit at merged `main` commit `d4d2541`, recorded 2026-07-13T02:55:42Z)
**Assessment method:** per `CLAUDE.md`'s Agent Recommendation Assessment
  mandate — every item below is triaged as a scoped/low-risk fix
  (implemented directly, no permission needed) or a larger/product-direction
  item (scoped and put to the user for explicit confirmation before any
  change).

## Summary

The re-audit is accurate. It checked the merged repository directly
rather than trusting prior status-report checkmarks, and every gap it
found is real. This response:

- **Fixes 6 items directly** — all scoped, low-risk, no external
  dependency, no product-direction call: a missing `ROADMAP.md` tracking
  entry, two documentation-precision corrections the audit specifically
  flagged as misleading, a compact ADR log, a scripted demo (built from
  commands actually executed against this repo, not written blind), and
  a before/after positioning example.
- **Confirms 3 items need no new action** — P2-02, P2-03, P2-04 were
  already correctly caveated as foundations with a named external
  boundary (untested client, publish credentials, API spend); the only
  gap was that a section *header* elsewhere overstated them, which is
  now fixed.
- **Scopes 7 items as larger/product-direction work** and does **not**
  implement any of them without confirmation — this includes the one
  P0-level miss (P0-03, the self-authorized remote-write default) and
  every "new subsystem" item (generated manifest, operational profile
  enforcement, expanded audit scope, comprehensive snippet execution,
  duplicate-policy detection, a real release cut). See "Larger items —
  pending your confirmation" below.
- **Leaves 2 items exactly where they are** — P2-05 (real dogfooding)
  and the live-eval half of P2-04 both require your own action (pinning
  the harness in real projects; spending your API budget), not code this
  session can write.

No code, test, or CI behavior changed — every fix here is documentation
(status-doc precision, `ROADMAP.md` tracking, two new doc files, one
README section). `tools/verify-content-quality.py` and
`tools/verify-manifest.sh` both pass against the new state;
`markdownlint-cli2` and `git diff --check` were run before commit.

## Per-item disposition

### P0 — restore trust before merging or releasing

| Item | Re-audit verdict | Response |
|---|---|---|
| P0-01 | ✅ Verified | Confirmed. No action. |
| P0-02 | ✅ Verified | Confirmed. No action. |
| P0-03 Remove self-authorized remote workflow | ❌ Missed | **Correct catch.** `CLAUDE.md` still grants every agent standing commit/push/PR authority by default with no opt-in-only profile. This is a change to the harness's own default trust model — exactly the "product-direction decision" class `CLAUDE.md`'s own Recommendation Assessment section says requires confirmation, not unilateral action (including from the mandate that would be the one changing). Documented in `docs/DECISIONS.md`; tracked in `ROADMAP.md`; scoped below for your decision. |
| P0-04 | ✅ Verified | Confirmed. No action. |
| P0-05 Generated bidirectional inventory | ⚠️ Partial | **Correct catch.** `tools/verify-manifest.sh` verifies a hand-written `MANIFEST.md` against the filesystem; it doesn't generate the file from a structured source. Building an actual generator (schema design + rewiring the verifier) is a new subsystem, not a fix to the existing script. Documented in `docs/DECISIONS.md`; scoped below. |
| P0-06 Validate runnable examples | ⚠️ Partial | **Correct catch.** The content-quality checker validates exactly two explicitly-listed files' Python snippets, not every claimed-runnable snippet repo-wide. Widening this needs a design call (which fenced blocks count as "claimed runnable" vs. deliberate partial pseudocode) — scoped below, bundled with the duplicate-policy-detection item since both touch the same checker. |
| P0-07 | ✅ Verified | Confirmed. No action. |
| P0-08 | ✅ Verified | Confirmed. No action. |

### P1 — turn the alpha into a dependable product

| Item | Re-audit verdict | Response |
|---|---|---|
| P1-01 | ✅ Verified | Confirmed. No action. |
| P1-02 Selectable profiles and precedence | ⚠️ Partial | **Correct catch.** `patterns/profiles/*.yaml` exist and are selectable by convention, but no script reads `.agentharness-profile` — selection doesn't gate anything yet. Wiring it into `tools/check.sh`/CI so prototype/internal/production produce measurably different results is a new subsystem. Scoped below. Also fixed the wording in `gpt-5.6-p1-p2-followup-status.md` that the re-audit flagged as capable of being misread as covering this item (it technically didn't — "P1-06 through P1-14" excludes P1-02 — but the ambiguity was real and worth closing). |
| P1-03 | ✅ Verified | Confirmed. No action. |
| P1-04 | ✅ Verified | Confirmed. No action. |
| P1-05 | ✅ Verified | Confirmed. No action. |
| P1-06 | ✅ Verified | Confirmed. No action. |
| P1-07 | ✅ Verified | Confirmed. No action. |
| P1-08 Content-quality gate | ⚠️ Partial | **Correct catch.** Duplicate-policy detection (the same rule restated with a different number across docs) remains unbuilt. The original blocking condition — waiting for P1-10 and P2-06 to consolidate the testing/logging/encyclopedia content first — is now resolved (both shipped), so `ROADMAP.md` is updated to say so, but the detector itself still needs a design call to avoid false-failing on legitimate cross-references. Scoped below. |
| P1-09 | ✅ Verified | Confirmed. No action. |
| P1-10 | ✅ Verified | Confirmed. No action. |
| P1-11 | ✅ Verified | Confirmed. No action. |
| P1-12 Release discipline | ⚠️ Partial | **Correct catch.** `v0.1.0` is six commits behind `main`; the documented release checklist has never been exercised end-to-end against real (not test-fixture) history. Cutting a tag is technically low-risk (green `main`, no credentials needed, `release.yml` is designed to fail cleanly at the `npm publish` step without a token), but it's a visible, public "this state is releasable" statement — scoped below rather than assumed. |
| P1-13 | ✅ Verified | Confirmed. No action. |
| P1-14 | ✅ Verified | Confirmed. No action. |

### P2 — differentiated usefulness and adoption

| Item | Re-audit verdict | Response |
|---|---|---|
| P2-01 Signature audit capability | ⚠️ Partial | **Correct catch.** `harness-link.sh audit --json` covers install-drift only, not the original policy-conflict/unsafe-authority/validation-command/profile-selection scope. Expanding it is a new subsystem, and the "unsafe-authority" half specifically depends on P0-03 being resolved first (can't audit against an authority model that's still an open question). Scoped below. |
| P2-02 Cross-agent adapters | ⚠️ Partial | **No code gap.** Already accurately caveated — README states plainly the `AGENTS.md` adapter is generated and CI drift-tested but not verified against a real Codex session. That boundary needs an actual Codex test session, which this environment can't supply. The only real issue was a status-doc section header implying more completeness than warranted, which the "missed gaps" fix below corrects. |
| P2-03 Low-friction distribution | ⚠️ Partial | **No code gap.** Already accurately caveated — `docs/RELEASING.md#npm-distribution` spells out exactly what's missing (npm account/org, name confirmation, `NPM_TOKEN` secret). Unchanged boundary; same header fix as P2-02. |
| P2-04 Evaluations | ⚠️ Partial | **No code gap.** `invoke_agent_via_api()` is deliberately `NotImplementedError` — documented explicitly in the new `docs/DECISIONS.md` entry. No baseline/treatment results exist because producing them costs real API credits, which needs your explicit go-ahead, not a unilateral spend. Same header fix as P2-02/03. |
| P2-05 Real dogfood | ⏸ Deferred | **Correct catch — fixed directly.** Wasn't tracked in `ROADMAP.md`; now is (see "Explicitly Deferred / Needs a Decision"). This remains a non-coding item: it needs the harness actually pinned and used in a real project, which is your action to take, not something to simulate. |
| P2-06 | ✅ Verified | Confirmed. No action. |
| P2-07 Public project hygiene | ⚠️ Partial | **Fixed directly.** Added `docs/DECISIONS.md` (compact ADR log, 6 retroactive entries) and `docs/DEMO.md` (5-minute scripted walkthrough — every command and its output was actually executed against a scratch project this session, not written from memory, per this repo's own P1-11 lesson about unverified snippets). Both were already flagged in the prior status doc as "small enough to just do on request" — this review request is that ask. |
| P2-08 Clarify positioning | ⚠️ Partial | **Fixed directly.** Added a concrete before/after example to README's "Why not just CLAUDE.md?" section — two drifted `CLAUDE.md` snippets vs. the single-source-of-truth version. |

## Missed gaps in the follow-up status — response

1. **P0-03 not carried into "remaining work" framing.** Fixed: added to
   `ROADMAP.md`'s "Explicitly Deferred / Needs a Decision" section;
   scoped below for your decision.
2. **"Entire P1 backlog" phrasing risked being misread as covering
   P1-02.** Fixed: added an explicit scope note to
   `gpt-5.6-p1-p2-followup-status.md`'s summary and tightened the same
   line in `docs/operational/INDEX.md`.
3. **P0-05 changed the verifier, not the requested source of truth.**
   Acknowledged — this was never claimed otherwise in any status doc
   (checked: `gpt-5.6-review-status.md` already marked P0-05 ❌ at the
   `43604a7` snapshot and it was never re-marked done since). Now
   documented with full context in `docs/DECISIONS.md`; the actual fix
   (a generator) is scoped below.
4. **P2-02/03/04 are foundations, not completed outcomes; "now
   implemented" obscured this.** Fixed: renamed the section header in
   `gpt-5.6-p1-p2-followup-status.md` from "expanded scope, now
   implemented" to "expanded scope, built to their respective
   boundaries," and added a precision-correction paragraph naming
   exactly which item (P2-06) is a closed outcome versus which three
   have a named external boundary still open.
5. **P2-05 not tracked in `ROADMAP.md`.** Fixed — see item 1 above (same
   edit covers both).

## Suggested additions — response

1. **Separate inspection/editing/commit/publication authority.** Same
   item as P0-03. Scoped below.
2. **Make profile selection operational.** Same item as P1-02. Scoped
   below.
3. **Generate the manifest from structured data.** Same item as P0-05.
   Scoped below.
4. **Complete one release proof.** Same item as P1-12. Scoped below.
5. **Run the smallest real evaluation and dogfood trial.** Not
   implemented — this needs your `ANTHROPIC_API_KEY` and explicit
   sign-off on real spend (evaluation), plus pinning the harness in at
   least two real, non-fixture projects (dogfooding). Both are
   consistent with the boundary already established and agreed in the
   P2 expansion plan: this session builds infrastructure, you trigger
   anything that spends money or requires real-world adoption. No change
   from current state; not re-litigated here.
6. **Close the self-verifying documentation gaps.** Split across two
   dispositions: the ADR, demo, and before/after example are done
   directly (P2-07/P2-08 above). Duplicate-policy detection and
   comprehensive executable-snippet fixtures are bundled into the
   scoped-below batch (same items as P0-06/P1-08).

## Larger items — pending your confirmation

None of the following were implemented. Each is either a product-direction
decision (changes what the harness does by default or what it claims) or
a new subsystem (meaningful design work, not a fix to something that
already exists) — per `CLAUDE.md`'s Recommendation Assessment mandate,
both classes need your explicit sign-off on scope before work starts,
the same way the P2 npm/eval/Codex/encyclopedia batch did earlier.

| # | Item | What it would mean | Why it's not scoped-and-done |
|---|---|---|---|
| B1 | P0-03 — remote-write authorization model | Split `CLAUDE.md`'s always-on commit/push/PR + auto-implement-recommendations mandate into an opt-in profile, with a default that leaves inspection/review-only agents able to stop short of publishing | Changes the harness's default trust model for every future session that loads this `CLAUDE.md`, including this one |
| B2 | P0-05 — generated manifest | Design a structured asset schema (e.g. per-directory metadata or a single manifest-source file) and rewire `verify-manifest.sh` to diff against generated output instead of a hand-written file | New subsystem; current hand-maintained-plus-verified approach already catches missing/unlisted files, so this is a completeness upgrade, not a bug fix |
| B3 | P0-06 / part of P1-08 — comprehensive runnable-snippet validation | Extend `verify-content-quality.py` beyond the current 2-file allowlist to every doc claiming a runnable example, plus executable fixtures where "parses" isn't enough proof | Needs a design call on what counts as "claimed runnable" vs. intentional partial pseudocode — get this wrong and it's noisy false failures, not a safety net |
| B4 | P1-02 — operational profile enforcement | Wire `.agentharness-profile` selection into `tools/check.sh`/CI so prototype/internal/production tiers actually gate different things (not just describe different things) | New subsystem; today's YAML profiles are lookup tables nothing reads yet |
| B5 | P2-01 — expanded audit scope | Extend `harness-link.sh audit` beyond install-drift to policy-conflict, unsafe-authority, validation-command, and selected-profile checks | New subsystem; the "unsafe-authority" half specifically can't be built meaningfully until B1 resolves what "unsafe" means |
| B6 | P1-12 — a real release proof | Bump `package.json`/tag `vX.Y.Z` from current green `main` per `docs/RELEASING.md`'s checklist, exercising the documented process for real (still without `npm publish`, which stays credential-blocked) | Technically low-risk, but a public, hard-to-cleanly-undo "this is releasable" statement — confirming first rather than assuming |
| B7 | P1-08 — duplicate-policy detection | Build a detector for the same rule restated with a different number across docs, without false-failing on ~15+ legitimate cross-references | Needs a design call on what counts as "restated" vs. "correctly links back to the source of truth" |

**Options for how to proceed** (mirrors the pattern used for the earlier
P2 batch): do all seven now, pick a subset, or leave the backlog as
scoped-but-not-started for a future session. Whichever is chosen, that
confirmation covers the agreed batch — no further per-item asks within
it, per `CLAUDE.md`.

## Verification

- `tools/verify-content-quality.py` — passed.
- `tools/verify-manifest.sh` — passed (this file plus `docs/DECISIONS.md`
  and `docs/DEMO.md` added to `MANIFEST.md` in the same change).
- `docs/DEMO.md`'s commands were executed against a real scratch git
  repository this session (init, `harness-link.sh init --with-hook`,
  `status`, a blocked trunk commit, a successful feature-branch commit)
  — the doc's console output is copied from that run, not invented.
- `markdownlint-cli2` and `git diff --check` run before commit.

## Links

- Source re-audit: `docs/operational/reviews/gpt-5.6-completion-reaudit.md`
- Prior status (now precision-corrected): `docs/operational/reviews/gpt-5.6-p1-p2-followup-status.md`
- New: `docs/DECISIONS.md`, `docs/DEMO.md`
- `ROADMAP.md` — three new "Explicitly Deferred / Needs a Decision" entries
- PR: pending (see workflow completion below)
