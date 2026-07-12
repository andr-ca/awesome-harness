# agentharness – Agent Router

This file is loaded into every session that touches this repo. Keep it
short — everything else is one link away. Full index: [MANIFEST.md](MANIFEST.md).
Planned-but-not-built: [ROADMAP.md](ROADMAP.md).

## 🤖 Agent Workflow Completion (MANDATORY)

**When an agent finishes work on a task, it MUST always complete the workflow:**

1. ✅ **Verify all work is done** — tests pass, coverage meets the applicable rigor tier (see `.github/CODING_GUIDELINES.md#rigor-tiers`), lint passes, no TODOs
2. ✅ **Create atomic commits** — one logical unit per commit, clear message explaining WHY
3. ✅ **Push to remote** — push branch to origin with tracking (`git push -u origin branch-name`)
4. ✅ **Create pull request** — use `gh pr create` with title, body summary, and checklist
5. ✅ **Never leave work uncommitted** — work in progress that isn't pushed is work that doesn't exist

**An agent claiming work is "complete" without a PR/commit is incomplete.** Always finish the workflow.

## 🔍 Agent Recommendation Assessment (MANDATORY)

**When an agent is asked to address/review/look into recommendations:**

1. **Assess each item** — evaluate positive vs. negative impact (complexity, effort, risk, benefit)
2. **Scoped, low-risk fixes** — a bug fix, a correctness/security fix with one
   clear resolution, closing a gap in something already built:
   - ✅ Implement directly, regardless of effort. Follow the normal
     commit/push/PR workflow above. Don't ask permission for these —
     assessing and then fixing a clear bug *is* the job.
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
never actually signed off on.

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
