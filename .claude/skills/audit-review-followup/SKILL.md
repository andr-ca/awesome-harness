---
name: audit-review-followup
description: Use when asked to check whether review/audit recommendations were actually implemented, whether gaps were closed, or to re-score the repo — verifies claims against repo state instead of trusting status reports.
metadata:
  type: skills
  when: "User asks: 'did we address the review feedback?', 'did it close the gaps?', 'what's the overall score now?'"
---

# Audit Review Follow-up

Assess whether a past review's recommendations were genuinely implemented — not
just marked done — and re-score the repo. **This is an assessment task: report
findings, do not fix anything unless asked.**

## The Prompt (canonical form)

> Check the review and its status report in `docs/operational/reviews/`, then
> verify what was *actually* implemented against the current repo state — do
> not trust the status report's checkmarks. Did it close all the gaps? What
> gaps did the status report itself miss? What would you add next? Re-score
> using the original review's dimensions.

## Procedure

### 1. Locate the documents
- Reviews live in `docs/operational/reviews/` as `<name>-review.md` (findings +
  scored verdict) and `<name>-review-status.md` (per-item disposition).
- If several review cycles exist, use the frontmatter datestamps (required per
  `docs/operational/README.md`) to pick the cycle in question — usually the
  newest.

### 2. Read both documents fully
Extract: the item list (usually a numbered backlog), the claimed status of each
item, and the original scoring rubric/dimensions.

### 3. Verify claims — never trust checkmarks
For each item marked done, check the repo itself. Typical checks:
- **Files claimed created/deleted**: `ls`, `test -e`, read key sections.
- **CI claimed added/passing**: `gh run list` — confirm green on the default branch, not just "workflow file exists".
- **Repo settings claimed changed** (branch protection, rename, tags): `gh api`, `git remote -v`, `git tag`, `git config core.hooksPath`.
- **"Removed everywhere" claims** (a phrase, a bad pattern): `grep -rn` across the repo — the sweep that was run may have missed non-link prose.
- **Fixed scripts**: read the fix and, where cheap, execute it.

Spot-check breadth over depth: every category of claim, not every single item.

### 4. Hunt the missed instances (the highest-value step)
Status reports fail in *classes*, not one-offs. When you find one leftover, ask
what verification method produced it and where else that method is blind.
Example: a markdown *link* checker validates `[text](path)` but not prose
asserting a file exists — so grep for the claim text, not just dead links.

### 5. Classify every item

| Bucket | Meaning |
|---|---|
| ✅ Verified done | Claimed done, confirmed against repo state |
| ⚠️ Partial (admitted) | Status report itself flags it incomplete |
| ❌ Missed gap | Marked done but you found a surviving instance |
| ⏸ Deferred | Explicitly deferred — check it's recorded in `ROADMAP.md`, not only in the status report |

### 6. Suggest additions
Ideas the review didn't cover, ranked by leverage-per-effort. Prefer
*self-verifying* fixes (a CI check that prevents the failure class) over
one-time cleanups.

### 7. Re-score
Use the **same dimensions and scale as the original review** so scores are
comparable. Present a before/after table with a one-line rationale per
dimension, then an overall score and what separates it from the next tier.

## Output shape

1. **TL;DR first**: closed or not, count of missed gaps, new score.
2. Verified-implemented (with how you verified).
3. Gaps: admitted vs. newly found (file:line for each).
4. Suggested additions, ranked.
5. Score table (was → now → why).
6. Offer to fix — but don't fix unprompted.

## Rules

- New review/status documents you write must carry ISO 8601 datestamps in
  frontmatter (see `docs/operational/README.md`).
- If asked to *implement* the findings afterwards, the repo's
  recommendation-assessment mandate in `CLAUDE.md` takes over (implement
  net-positive items, escalate high-risk ones).
