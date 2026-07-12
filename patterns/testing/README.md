# Testing

Index for this directory — each doc below is the single source of truth
for its topic; this file doesn't restate their content, just routes to it.

All of it applies in full at the **Production** rigor tier — see
`.github/CODING_GUIDELINES.md#rigor-tiers` and `patterns/profiles/` for
what changes at Prototype/Internal tiers (short answer: tests become
optional or un-gated by a coverage number, not "the same rules apply
everywhere").

| Doc | Covers |
|---|---|
| [TDD.md](./TDD.md) | Where this repo's TDD guidance departs from Kent Beck's own (one mistake worth calling out) |
| [COVERAGE_REQUIREMENTS.md](./COVERAGE_REQUIREMENTS.md) | The 80% mandate: what counts, the one measurement gotcha, the review checklist |
| [COMPLETION_CHECKLIST.md](./COMPLETION_CHECKLIST.md) | The pre-PR checklist — don't mark work done without running through it |
| [PLAYWRIGHT_UI_TESTING.md](./PLAYWRIGHT_UI_TESTING.md) | The screenshot-approval mechanism this repo enforces on top of Playwright itself |

**Read COVERAGE_REQUIREMENTS.md first** if you're new to this repo's
testing expectations — it states the actual mandate; TDD.md and
PLAYWRIGHT_UI_TESTING.md are narrower notes on top of standard practice.
