# GEMINI.md

Generated from this repo's own `CLAUDE.md` by `tools/generate-gemini-md.sh`
— do not hand-edit; regenerate instead
(`tools/generate-gemini-md.sh --output GEMINI.md`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.agents/skills/` — Gemini CLI's real skill mechanism (the
Agent Skills open standard, shared with Claude Code) injects every
enabled skill's `name`/`description` metadata into the system prompt at
session start, then loads a skill's full body only once its description
matches the task at hand (via its `activate_skill` tool). Google
Antigravity reads this same filename and gives it precedence over
`AGENTS.md` when both exist. The index below exists so that
metadata-scan step has something to match against; it is not a
substitute for reading the matched `SKILL.md` itself.

Gemini CLI also supports `/memory show` (inspect the concatenated
context) and `/memory refresh` (force a re-scan) if this file changes
mid-session.

---

## agentharness – Agent Router

This file is loaded into every session that touches this repo. Keep it
short — everything else is one link away. Full index: [MANIFEST.md](MANIFEST.md).
Planned-but-not-built: [ROADMAP.md](ROADMAP.md).

### 🤖 Agent Workflow Completion

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

**Never merge a PR on CI status alone — wait for review comments, then
address them, before merging.** A green CI run says nothing about
feedback left on the diff itself (human or automated, e.g. GitHub
Copilot's code review). Before merging:
1. Give automated review time to post (its own check, separate from CI,
   e.g. "Copilot Code Review") — don't merge the instant CI turns green.
2. Fetch *both* comment types — issue-level (`gh pr view <n> --json
   comments`) and inline review comments (`gh api
   repos/<owner>/<repo>/pulls/<n>/comments`); the first call alone misses
   inline findings entirely.
3. Verify each finding against current code before acting on it — an
   automated reviewer's claim can be stale (already fixed by a later
   commit) or simply wrong; confirm the premise, don't implement a "fix"
   on faith.
4. Fix what's real and in scope per the Recommendation Assessment
   mandate below (scoped/low-risk directly; larger findings get scoped
   and confirmed like any other recommendation); note explicitly why
   anything is skipped rather than silently ignoring it.
5. Reply on the PR to each review comment you fetched — issue-level and
   inline alike — with a short assessment and the action taken: the
   commit that addressed it, "already correct — no change (why)", or
   "skipped/deferred because …". This puts step 4's "don't silently
   ignore" on the thread where the reviewer left the finding, not only in
   a commit message or status file, so every decision is auditable next
   to the comment it answers. Use `gh pr comment <n>` for issue-level
   replies and `gh api --method POST repos/<owner>/<repo>/pulls/<n>/comments/<id>/replies -f body=…`
   for inline ones.

**Never report a push/merge as done while CI is still running or red —
watch it through to an actual, current green before moving on or telling
the user it's finished.** "I pushed" and "CI passed" are different
claims; only the second one means the work is safe. This applies to
every CI-triggering push this mandate covers: opening a PR, pushing more
commits to one, and merging into `main`.
1. After any such push, poll the run (`gh run watch --exit-status`, or an
   equivalent poll loop) until it reaches a terminal state — `queued` and
   `in_progress` are not outcomes, and reporting either as "done" is the
   exact mistake this rule exists to prevent.
2. On failure, read the actual log for the failed job(s)
   (`gh run view <run-id> --log-failed`) before deciding what to do next
   — don't guess from the job name.
3. If the failure is transient infrastructure (runner provisioning,
   `Service Unavailable`/network errors resolving actions, a flaky step
   unrelated to this diff — not a real test/lint/type failure), rerun
   the failed jobs (`gh run rerun <run-id> --failed`) and re-poll. Retry
   up to 5 times; if it's still failing after that, stop and surface it
   to the user rather than silently retrying forever.
4. If the failure reflects the actual change (a real test/lint/build
   failure), fix it like any other bug per the Recommendation Assessment
   mandate below, push the fix, and re-verify CI from a clean state —
   don't rerun a failing job hoping it passes the second time.
5. A merge to `main` is not finished until `main`'s own resulting CI run
   (the run the merge commit itself triggers, not just the PR's
   pre-merge run) is confirmed green — a PR's checks passing before
   merge doesn't guarantee the post-merge run on `main` will, and only
   the post-merge run reflects what's actually deployed/tagged from.

#### Publish authority

`touch .agentharness-publish-mode` at this repo's root grants standing
push/PR/auto-implement authority for every session that reads this file,
until the flag is removed. It's gitignored (never committed) because
it's a per-operator/per-machine authorization, not a repo-wide policy —
see `docs/DECISIONS.md` for why this replaced the old always-on default,
and `docs/INTEGRATION.md` for how to create/remove it.

### 🔍 Agent Recommendation Assessment

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

### What This Repo Is

A single source of truth for git conventions, coding guidelines, testing
standards, and (eventually) on-demand skills, so they're written once and
referenced everywhere instead of drifting across projects. Full rationale:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Where To Look

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

### Rules That Apply Regardless of What You're Working On

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

### Operational Documents

Temporary/working docs (research notes, agent logs, planning) go in
`docs/operational/`, tracked in git like everything else. See
`docs/operational/README.md` for the promote/archive/delete workflow.

---

## Skills (loaded on demand from `.agents/skills/`)

- `.agents/skills/agentic-loops/SKILL.md` — Use when building multi-turn agents, tool-calling systems, agent orchestration, or autonomous workflows — covers loops, tool calling, branching, reflection patterns.
- `.agents/skills/audit-review-followup/SKILL.md` — Use when asked to check whether review/audit recommendations were actually implemented, whether gaps were closed, or to re-score the repo — verifies claims against repo state instead of trusting status reports.
- `.agents/skills/branching/SKILL.md` — Use when creating a branch, naming it, deciding whether to use a worktree, or handling secrets accidentally committed to history — branch naming convention, trunk protection, and secrets-removal procedure.
- `.agents/skills/committing/SKILL.md` — Use when creating a git commit — atomic commits, message format, what never to commit, and the agent workflow-completion requirement (commit → push → PR).
- `.agents/skills/error-handling/SKILL.md` — Use when building error recovery, handling exceptions, designing error flows, or implementing logging for errors — covers retry, circuit-breaker, error wrapping, structured logging.
- `.agents/skills/port-agent-config/SKILL.md` — Use when asked to port, migrate, or add equivalent agent instructions, skills, or custom sub-agents for a different coding tool than the one already configured — e.g. "add Cursor support from our CLAUDE.md", "we're switching from Cursor to Codex, port our rules", "make this work for Copilot too", "port our review subagent to Codex". Covers both agentharness-linked projects (use the real generators, don't hand-write) and plain projects with hand-authored config (port by hand, same principles).
- `.agents/skills/python-conventions/SKILL.md` — Use when writing or reviewing Python code — naming conventions, type hints, common pitfalls (mutable defaults, bare except, is-vs-==), and testing structure.
