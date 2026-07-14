---
name: fable-gpt5-sol-disposition-2026-07-14
description: Disposition of merged Fable + GPT-5.6 fourth-pass reviews (both at commit 4f3e94b)
metadata:
  type: status
  timestamp: "2026-07-14T03:15:00Z"
---

# Fable + GPT-5.6 Fourth-Pass Review Disposition

**Reviews merged:** [PR #32](https://github.com/andr-ca/agentharness/pull/32) (GPT-5.6 at 46b820d) + [PR #34](https://github.com/andr-ca/agentharness/pull/34) (Fable at 4f3e94b)

**Filed:** 2026-07-14T03:04:33Z (main commits [`e1d1f3b`](https://github.com/andr-ca/agentharness/commit/e1d1f3b), [`8f6c90e`](https://github.com/andr-ca/agentharness/commit/8f6c90e))

**Scope of this document:** Merges both reviews' findings (Fable F-01–F-13 + GPT P0s) into a single action list per CLAUDE.md Recommendation Assessment mandate. Neither review has been acted upon yet.

---

## P0 Release Blockers (5 items)

All five require implementation before next release. No additional scoping needed — these are small, scoped, correctness/safety fixes.

### ✅ F-01 / GPT P0-04 — Regenerate drifted adapters

**Status:** DONE (merged in PR #31 before it was closed)

**What:** Commit `4f3e94b` edited CLAUDE.md without regenerating consuming `AGENTS.md`, `GEMINI.md`, `.kilo/rules/agentharness.md`.

**Action taken:** Regenerated all three adapters. Commit [`1cad158`](https://github.com/andr-ca/agentharness/commit/1cad158) (in closed PR #31, never reached main).

**Status:** This was done but not merged. **Action required:** Cherry-pick or reapply the regeneration to main to restore green CI gate. Recommend automating this — pre-commit hook or build step — so CLAUDE.md edits trigger adapter regeneration automatically.

### 🛑 F-02 / GPT P0-06 — Fix committing skill contradiction

**Status:** NOT STARTED — safety-relevant, high priority

**What:** `.claude/skills/committing/SKILL.md` frontmatter + body still say "commit → push → PR. Don't stop at the commit" and "work is not done until the PR exists." This contradicts CLAUDE.md's current verify-and-stage default + opt-in publish authority (settled as B1 decision in DECISIONS.md). The skill installs into every consumer on all 8 platforms, instructing agents to take publish actions they may not be authorized for.

**Why critical:** Safety issue — the skill is telling consumers to do the opposite of what the trust model mandates.

**Action needed:**
1. Update `.claude/skills/committing/SKILL.md` body to reflect verify-and-stage default
2. Update frontmatter description (currently republished to all platforms, contradicts mandate)
3. Regenerate `.cursor/rules/committing.mdc`, `.agents/skills/committing/SKILL.md`
4. Test on all platforms (at least Claude Code + one other)

**Estimate:** 30 min, low complexity, high impact.

### F-03 / GPT P0-01 — Make generate-clients non-destructive

**Status:** NOT STARTED

**What:** `harness-link.sh cmd_generate_clients` (line 1668) writes `AGENTS.md`, `GEMINI.md`, Copilot/Cursor/Kilo files directly into the target with no existence check, no backup, no `--force`, no state record.

**Reproduction:** Create a file `docs/gpt-5.6-sol-4th-...md`, run `generate-clients <target>`, file is silently replaced.

**Action needed:**
1. Refuse when target exists and is not harness-generated
2. Add `--force` for explicit replacement, `--dry-run` for preview
3. Record generated paths+hashes in state for doctor/uninstall
4. Add acceptance tests: preserve sentinel file, refuse atomically, uninstall preserves user edits

**Estimate:** 2 hours, medium complexity.

### F-04 / GPT P0-03 — Restrict npm durable copying to allowlist

**Status:** NOT STARTED

**What:** `copy_npm_durable_source` (line 323) tars **all** of HARNESS_DIR except `.git` and destination. Comment assumes npm pruned it, but CLI accepts `--mode npm` from any checkout, so safety assumption isn't enforced. Verified: `--mode npm` from a git checkout copies untracked `.env`, `.env.local` into consumer's `.agentharness-pkg`.

**Action needed:**
1. Copy from explicit manifest/allowlist, or reject `--mode npm` unless source is recognized packed npm artifact
2. Always exclude `.env*`, VCS metadata, caches, build artifacts
3. Add acceptance tests: untracked `.env`, `node_modules`, symlinks, spaces, packed-tarball golden manifest

**Estimate:** 1 hour, medium complexity, critical security boundary.

### F-05 / GPT P0-02 — Persist and restore pre-existing hooks path

**Status:** NOT STARTED

**What:** `harness-link.sh` state records only installed `hooks_path`; pre-existing value is never persisted. Uninstall unsets rather than restores. Reproduction:
```
before init:      core.hooksPath=.preexisting-hooks
after --force:    core.hooksPath=<agentharness>
after uninstall:  core.hooksPath=<unset>   ❌ should be .preexisting-hooks
```

**Action needed:**
1. Add `previous_hooks_path` to state (with "previously unset" representation)
2. On uninstall, restore previous value if current is still harness-owned
3. If user changed it after install, leave untouched + warn
4. Add acceptance tests: unset→install→uninstall, foreign→refuse, foreign→force→restore, post-install user change→preserve

**Estimate:** 1 hour, low complexity.

---

## P1 High-Priority Improvements (11 items)

These are larger, need explicit scoping confirmation before work starts. Listed by impact.

### F-06 — Fix documented contradictions with generated facts

**Scope:** Hand fixes + extended `manifest.yaml` pattern
- Update STATUS.md (6 skills → 7)
- Fix KNOWN_LIMITATIONS + INTEGRATION + ROADMAP + CLIENT_COMPATIBILITY contradictions
- Extend manifest.yaml to render counts (skills, languages, patterns) + capability tables
- Add semantic-contradiction CI checks (numeric detector can't catch "skill still says push PR" type errors)

**Why:** Multiple docs contradicted at the third-pass review; this was supposed to be fixed (P1-03) but drifted again. Root cause: hand-written summaries of machine-checkable facts.

**Estimate:** 4-6 hours. Blocks: F-07 (you can't rate progress without accurate status).

### F-07 — Cap the review loop

**Scope:** Archive + consolidate + standing rule
- Archive completed review cycles under dated directories (immutable)
- Keep ONE live backlog with globally unique IDs (date-prefixed)
- Adopt standing rule: no new full review until previous P0s closed + one external-evidence item landed

**Why:** This is the fifth full review in three days (Fable-1, Fable-2, GPT-1, GPT-2, GPT-3, GPT-4). ROADMAP has three colliding P-numbering schemes. Marginal information is now in the field, not the tree.

**Estimate:** 2 hours. Prerequisite: F-06 (need accurate status first).

### F-08 — Produce external evidence (HIGHEST VALUE)

**Scope:** Dogfood + live session + eval run (in order of information/hour)
1. Run `docs/operational/planning/DOGFOODING.md` plan against one real non-fixture repo
2. One live Codex CLI session validating `.agents/skills/` design
3. One funded baseline/treatment eval run through `tools/eval/` infrastructure

**Why:** Until at least one exists, every feature addition is speculative. The repo has reached the point where proving usefulness requires leaving the tree.

**Estimate:** Dogfood plan: 4-8 hours (depends on friction). Live session: 2-3 hours. Eval: 3-4 hours (+ API spend).

**Decision required:** Which one first, and is the user willing to fund eval?

### F-09 — Put always-on context on a budget

**Scope:** CLAUDE.md review + skill migration
- `CLAUDE.md` has 181 lines, 60+ of which are procedural git/CI mechanics (`gh pr comment`, retry counts, CI polling)
- These belong in an on-demand skill (loaded when reviewing PRs), not always-on
- Keep always-on to routing, invariants, authority rules only
- Add token-budget CI check

**Estimate:** 2-3 hours. Blocks: nothing (can do in parallel).

### F-10 — Rewrite ARCHITECTURE.md to reality

**Scope:** Delete aspirational, link DECISIONS.md
- Keep layering diagram + actual principles
- Delete component templates + metrics sections (never implemented)
- Link DECISIONS.md for "why" rather than restating it

**Estimate:** 1 hour. Prerequisite: none.

### F-11 — Already done

GPT review already filed; PR #31 closed with explanation.

### P1-02–P1-05 (from GPT)

Live-test Codex, define compatibility contract, run evals, turn scaffolding into evidence — same as F-08 above, just different source.

---

## P2 Useful Follow-ups (4 items)

These add value but don't block anything. Prioritize F-08 first.

- **F-12:** State-schema migration before v2 fields land (F-05's `previous_hooks_path` triggers this)
- **F-13:** Composable presets vs. one global opinion set (not requested by either review; mentioned in ROADMAP as P2-05)
- **Compare/migration story (ROADMAP P2-08):** After dogfood exists, write "when to use agentharness vs. X"
- **Property tests + threat model (from GPT):** Install/uninstall byte-identity; untrusted instruction content

---

## Recommendation Assessment Summary

| Category | Count | Status |
|----------|-------|--------|
| P0 (release blockers) | 5 | 1 done (F-01, not merged); 4 not started |
| P1 (coherence/proof) | 11 | All not started |
| P2 (useful follow-ups) | 4 | All not started |

**Total:** 20 actionable findings across two reviews.

**User decision required:**
1. Confirm scope for P1 items (especially F-08: which external-evidence item first, eval funding?)
2. Pick sequence for P0 fixes (recommend: F-02, F-03, F-04, F-05 in parallel after F-01 cherry-pick)
3. Re-apply F-01 to main (currently in closed PR #31)

---

## Notes

- Both reviews scored 7.2–7.6/10 at the same commit; they overlap significantly
- Fable's two unique findings (F-02 trust-model contradiction, F-07 review-loop caps) are both high-impact
- Neither review has scoped the bigger product questions (composable presets, multi-client evidence) — treating those as P2 until proof exists
- This disposition follows the Recommendation Assessment mandate: scoped/low-risk items are ready to implement (P0), larger items need user confirmation on scope (P1+)
