---
name: playwright-ui-testing
description: Mandatory Playwright testing for all web UI work with screenshot verification
complexity: medium
frameworks: web, react, vue, angular, next, nuxt, svelte
languages: typescript, javascript
---

# Playwright UI Testing

This applies at the **Production** rigor tier — see
`.github/CODING_GUIDELINES.md#rigor-tiers`. Internal tools and prototypes
can skip this; manual verification is fine there.

Playwright's own setup, config, browser/device projects, selectors, and
CI wiring are covered thoroughly by
[Playwright's docs](https://playwright.dev/docs/intro) and its
[best practices guide](https://playwright.dev/docs/best-practices) — this
file only covers the one thing this repo requires that Playwright itself
doesn't enforce: screenshots actually being looked at.

## The mandate (Production tier)

All Production-tier web UI work requires Playwright tests, and every
test that touches rendered UI must include screenshot verification.
Screenshots that were generated but never reviewed don't count. Work
without this **will not merge** at Production tier.

## What "screenshot approval" actually means

"Agent MUST review and approve screenshots" is meaningless without a
concrete mechanism. Here's the mechanism:

1. Playwright writes screenshots to `test-results/screenshots/` (or your
   configured path) as part of the normal test run.
2. Before marking the task complete, the agent (or human) opens each new
   or changed screenshot and states, in the PR description or commit
   message, what was checked and what was seen — e.g. "Reviewed
   `login-success.png`: form renders correctly, no layout shift, matches
   the design spec." A screenshot that was generated but never looked at
   does not count as reviewed.
3. If comparing against a baseline (`--update-snapshots` workflow), the
   diff output itself (pass/fail per snapshot) is the evidence — link or
   paste it.
4. CI enforces the mechanical part: the Playwright test suite (including
   snapshot comparison) must pass. CI cannot enforce that a human actually
   looked at a screenshot; that's why step 2's written statement exists —
   it's the audit trail for the part CI can't check.

If you can't produce that written statement, the screenshots weren't
reviewed — go review them.

## Testing checklist for UI work

- [ ] Playwright set up, with a screenshot on every test that touches
      rendered UI
- [ ] Happy path, error states, edge cases, responsive sizes, and
      accessibility all covered
- [ ] All tests pass; all screenshots reviewed and approved (see above)
- [ ] No visual regressions; baseline screenshots committed
- [ ] Test coverage >= 80% (see `COVERAGE_REQUIREMENTS.md`)

Prototype/Internal-tier UI work can use manual verification instead — see
`.github/CODING_GUIDELINES.md#rigor-tiers`.

---

**See Also:** `TDD.md`, `COVERAGE_REQUIREMENTS.md`, `COMPLETION_CHECKLIST.md`
