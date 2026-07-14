# Operational Documents Index

Quick reference for active documents and their status.

## 📋 Active Documents

Currently being researched, developed, or planned:

| Document | Status | Purpose | Location |
|----------|--------|---------|----------|
| Dogfooding plan | Not started | Executable plan + tracking template to get real-world evidence (P2-05/P2-02) | `planning/DOGFOODING.md` |

## 🔄 In-Progress Work

Items currently under development:

- (none yet)

## ✅ Completed & Ready

Documents ready to be promoted to harness or archived:

- `reviews/fable-review.md` — full repo review, 2026-07-11. Findings
  consolidated into MANIFEST.md/ROADMAP.md/CHANGELOG.md and the P0/P1/P2
  fixes across the repo; kept here as the historical record rather than
  archived, since `reviews/fable-review-status.md` actively references it.
- `reviews/fable-review-status.md` — disposition of all 30 review
  recommendations. Its two originally-partial items are now done: a real
  logging config loader (`patterns/logging/config_loader.py`, further
  fixed per `reviews/pr4-comments-status.md` item 2) and the sample
  integration project (`examples/sample-project/`). The status doc's
  own per-item verdicts are a dated snapshot and are left as written;
  this note just tracks that both gaps have since closed.
- `reviews/gpt-5.6-review.md` — independent full-repository review dated
  2026-07-11; kept as the historical baseline for its completion audit.
- `reviews/gpt-5.6-review-status.md` — independent re-validation at
  `43604a7`, recorded 2026-07-12T15:47:00Z: 1 of 30 items verified
  complete at that snapshot. Superseded for current-state purposes by
  `reviews/gpt-5.6-p1-p2-followup-status.md` below; kept as the
  historical snapshot it's dated as.
- `reviews/pr4-comments-status.md` — disposition and verification record for
  PR #4's review-comment fixes and later coverage/pre-push work.
- `reviews/gpt-5.6-p1-p2-followup-status.md` — completion status for the
  P1-06–P1-14 slice of the P1 backlog, the confirmed-scope half of the P2
  batch, and (as of 2026-07-12T22:10:00Z) the remaining four P2
  product-direction items (P2-02, P2-03, P2-04, P2-06), which the user
  chose the most ambitious option for after reviewing the doc's original
  options memo (kept in the same file for the record). Only P2-06 fully
  closed its outcome — P2-02/03/04 are foundations built to a named
  external boundary; see the 2026-07-13 precision correction added
  inline and the re-audit below.
- `reviews/gpt-5.6-completion-reaudit.md` — evidence-based re-audit at merged
  `main` commit `d4d2541`, recorded 2026-07-13T02:55:42Z. Reclassifies the
  original 30 recommendations as 17 verified, 11 partial, 1 missed, and 1
  deferred; re-scores the repository from 4.5/10 to 7.0/10.
- `reviews/gpt-5.6-completion-reaudit-status.md` — this session's
  per-item response to the re-audit above: scoped/low-risk items fixed
  directly, larger product-direction items scoped and put to the user for
  confirmation before implementation.
- `reviews/pr9-16-comments-status.md` — disposition of review-comment
  findings that were missed on PRs #9–#15 (merged on CI status alone,
  before `CLAUDE.md` required checking comments too) plus the one Copilot
  found on PR #16 itself, which added that requirement.
- `reviews/gpt-5.6-sol-3rdpass-2026-07-13T134419Z.md` — third-pass
  independent review at `9d32ddc`, scoring the repo 7.3/10 (up from 7.0).
  6 P0, 10 P1, 8 P2 findings; disposition of all of them recorded in
  `reviews/gpt-5.6-sol-3rdpass-status.md` below.
- `reviews/gpt-5.6-sol-3rdpass-status.md` — disposition of the review
  above. All six P0 items fixed and merged (P0-01/04/05 directly;
  P0-02/03/06 were product-direction decisions, confirmed by the user,
  and shipped as PR #20, #21, #22). The 18 P1/P2 items are tracked,
  not implemented, in `ROADMAP.md`'s "Third-Pass Review Backlog" section
  (PR #23) — each still needs its own scoping decision before work
  starts.
- `reviews/gpt-5.6-sol-4th-2026-07-14T021052Z.md` — fourth-pass
  independent review at merged `main` commit `46b820d`, scoring the repo
  7.6/10. Revalidates the third-pass P0 work, records three remaining
  installer-safety blockers, and prioritizes live Claude/Codex evidence
  over further unverified client breadth.
- `reviews/fable-review-2026-07-13.md` — full Fable repository review,
  7.2/10. Independent concurrent assessment at commit `4f3e94b` (before
  4th-pass was filed). Confirms that review's four P0s and identifies two
  additional findings: the `committing` skill contradicts the trust model
  (safety-relevant), and the review-loop accumulation itself (5 cycles in
  3 days). 13 itemized findings (F-01–F-13); **disposition pending**.

- `reviews/fable-gpt5-sol-disposition-2026-07-14.md` — merged disposition
  of Fable (7.2/10) + GPT-5.6 fourth-pass (7.4/10 at different commits).
  Filed 2026-07-14. 5 P0 blockers (1 done, 4 not started), 11 P1
  improvements, 4 P2 follow-ups. **Requires user scoping for P1+ before implementation.**

- `reviews/fable-gpt5-sol-disposition-2026-07-14.md` — merged disposition
  of Fable (7.2/10) + GPT-5.6 fourth-pass (7.4/10 at different commits).
  Filed 2026-07-14. 5 P0 blockers (1 done, 4 not started), 11 P1
  improvements, 4 P2 follow-ups. **Requires user scoping for P1+ before implementation.**

## 📚 Archives

Historical documents kept for reference:

- (none yet)

## 📝 Adding to This Index

When creating a new operational document:

1. Create the document in appropriate subdirectory (`research/`, `planning/`, etc.)
2. Use format: `{DATE}-{TOPIC}.md` or `{TOPIC}/` directory
3. Add entry to this index with:
   - Document name/path
   - Current status (in-progress, pending-review, completed)
   - Brief purpose
   - When it will be archived or promoted

## 🗑️ Maintenance Schedule

- **Monthly review** – Update this index, archive completed items
- **Quarterly review** – Consolidate findings, promote to harness
- **Yearly archive** – Move old logs and obsolete docs to archives/
