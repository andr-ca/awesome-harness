# agentharness – Agent Router

This file is loaded into every session that touches this repo. Keep it
short — everything else is one link away. Full index: [MANIFEST.md](MANIFEST.md).
Planned-but-not-built: [ROADMAP.md](ROADMAP.md).

## 🤖 Agent Workflow Completion

**Default (no publish authority): verify and stage, then stop.**

1. ✅ **Verify all work is done** — tests pass, coverage meets the applicable rigor tier (see `.github/CODING_GUIDELINES.md#rigor-tiers`), lint passes, no TODOs
2. ✅ **Create atomic commits locally** — one logical unit per commit, clear message explaining WHY
3. 🛑 **Stop before pushing, opening a PR, or auto-implementing recommendations.** Present a summary of what's staged and ask the user to confirm before publishing anything.

**Full publish authority (commit → push → PR, same as before) applies only when either is true:**
- `.agentharness-publish-mode` exists at this repo's root (a local,
  gitignored, per-operator flag — see "Publish authority" below), **or**
- The user has explicitly granted standing authorization for this session
  or task in the current conversation. This always overrides the flag in
  either direction — explicit instructions in the request outrank a
  standing file the same way rigor-tier precedence already works (see
  `patterns/profiles/README.md#precedence-order`).

Under full publish authority, the original mandate applies as written:
push to remote with tracking, create a PR with `gh pr create`, and never
leave verified work uncommitted-and-unpushed — an agent claiming work is
"complete" while it's only staged locally is incomplete.

### Publish authority

`touch .agentharness-publish-mode` at this repo's root grants standing
push/PR/auto-implement authority for every session that reads this file,
until the flag is removed. It's gitignored (never committed) because
it's a per-operator/per-machine authorization, not a repo-wide policy —
see `docs/DECISIONS.md` for why this replaced the old always-on default,
and `docs/INTEGRATION.md` for how to create/remove it.

## 🔍 Agent Recommendation Assessment

**When an agent is asked to address/review/look into recommendations:**

1. **Assess each item** — evaluate positive vs. negative impact (complexity, effort, risk, benefit)
2. **Scoped, low-risk fixes** — a bug fix, a correctness/security fix with one
   clear resolution, closing a gap in something already built:
   - ✅ Implement directly, regardless of effort — don't ask permission to
     *fix* it. Whether the fix gets **published** still follows the
     Agent Workflow Completion default above (verify + stage, or full
     publish if authorized).
3. **Anything larger** — a new subsystem, a product-direction decision
   (target users, supported clients, distribution model), an architecture
   change, or a recommendation batch that amounts to a roadmap rather than
   a fix:
   - 🛑 **Present a scoped summary and get explicit confirmation on scope
     before implementing.** A review file recommending something is not
     the same as the user authorizing a multi-session build-out. Once
     scope is confirmed, that confirmation covers the agreed batch — don't
     re-ask item-by-item within it, but do re-check before expanding past
     what was agreed.
4. **If potential outcome is NEGATIVE or HIGH-RISK regardless of size:**
   - 🚨 **Escalate to user immediately** — do not implement
   - Include: specific concern, risk analysis, request guidance
5. **Report status in `<recommendations>-status.md`** with:
   - Timestamp (ISO 8601: `2026-07-11T14:30:00Z`)
   - Summary of what was implemented (and, for a confirmed larger batch,
     what scope was agreed)
   - Rationale for positive/negative aspects of each recommendation
   - Link to PR(s)

**This applies to:**
- Recommendations from reviews, audits, or assessments
- All work on this repository (agentharness)
- All harnesses and projects consuming this harness

**Rationale:** Recommendations only improve systems when they're acted on
deliberately. Complexity is not a reason to decline a scoped fix — but
silently treating an unbounded backlog as blanket authorization turns
"assess recommendations" into unrequested product decisions the user
never actually signed off on. The same logic applies one level up: a
mandate that grants an agent standing remote-write authority by default
is itself a product-direction decision the user should make explicitly,
not inherit silently from a template — see "Publish authority" above.

---

## What This Repo Is

A single source of truth for git conventions, coding guidelines, testing
standards, and (eventually) on-demand skills, so they're written once and
referenced everywhere instead of drifting across projects. Full rationale:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Where To Look

| Need | Read |
|---|---|
| Full asset index | [MANIFEST.md](MANIFEST.md) |
| Git workflow (branches, commits, secrets) | `.github/BRANCHING_STRATEGY.md`, `.github/COMMITTING_GUIDELINES.md` |
| Coding standards + rigor tiers | `.github/CODING_GUIDELINES.md` |
| Testing (TDD, coverage, Playwright) | `patterns/testing/` |
| Logging | `patterns/logging/` |
| Python conventions | `languages/python/` |
| Integrating this repo into a project | `docs/INTEGRATION.md`, or just run `tools/setup/harness-link.sh` |
| What's planned but not built | [ROADMAP.md](ROADMAP.md) |

## Rules That Apply Regardless of What You're Working On

- **Rigor tiers.** Not all mandates apply to all code — see
  `.github/CODING_GUIDELINES.md#rigor-tiers` before assuming 80% coverage
  or full Playwright suites apply to a prototype or one-off script.
- **One source of truth per rule.** If you find the same number/rule
  stated differently in two files, that's a bug — fix the duplicate, don't
  add a third version.
- **`.env.sample` not `.env.example`.** Never hardcode secrets; always
  provide a sanitized sample file.
- **Never commit to `main` directly.** Branch protection enforces this for
  everyone except repo admins; agents should never rely on the admin
  bypass.

## Operational Documents

Temporary/working docs (research notes, agent logs, planning) go in
`docs/operational/`, tracked in git like everything else. See
`docs/operational/README.md` for the promote/archive/delete workflow.
