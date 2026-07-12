# awesome-harness — Full Repository Review

**Reviewer:** Claude (Fable 5) · **Date:** 2026-07-11 · **Scope:** concept, documentation, implementation, consistency, usability

---

## Executive Summary

The idea is strong and increasingly relevant: a single versioned repository of agent instructions, skills, hooks, conventions, and patterns, reused across all projects ("dotfiles for AI-assisted development"). The execution today is mostly **scaffolding that describes a repository that doesn't exist yet**. Of the seven component categories the docs promise (skills, agents, hooks, frameworks, languages, patterns, tools), roughly one and a half have any real content. The repo also visibly violates several of its own mandatory rules, contains broken shell snippets presented as copy-paste-ready, and duplicates its core mandates across four files with mutually contradictory numbers — which is exactly the failure mode a harness repo exists to prevent.

**Overall score: 4.5 / 10** — excellent concept, well-written prose, but currently a promise rather than a product.

| Dimension | Score | One-line rationale |
|---|---|---|
| Concept / idea | 8/10 | Right problem, right shape; DRY for agent context is genuinely valuable |
| Documentation quality | 6/10 | Fluent and thorough, but inflated, duplicative, and describes phantom content |
| Implementation completeness | 2/10 | 1 hook script + guideline docs; no skills, agents, tools, frameworks, or CI |
| Internal consistency | 3/10 | Repo breaks its own rules; numbers conflict between files |
| Practical usability today | 4/10 | The git/testing/logging guides are usable; integration instructions are not |

---

## 1. The Idea (8/10)

Centralizing agent harness assets is a sound and forward-looking concept:

- **Real pain point.** Every project accumulates its own CLAUDE.md, conventions, hooks, and CI rituals; drift between projects is real and costly.
- **Right primitives.** Skills with frontmatter, symlink-vs-copy-vs-submodule integration tiers, an operational-docs quarantine (`docs/operational/`), and a feedback loop ("improve in project → contribute back") are all the correct building blocks.
- **Layered model is coherent.** The ARCHITECTURE.md layering (universal → tools → patterns → language → framework → project) is a good mental model.

Weaknesses at the concept level:

- **Name collision.** The `awesome-*` prefix conventionally means "curated link list" on GitHub. This is a toolkit, not a list; the name sets wrong expectations.
- **No consumption story for agents.** The docs explain how a *human* copies files around, but the primary consumer is an agent. There is no manifest, no machine-readable index, and the main index (CLAUDE.md) is ~450 lines of prose loaded into every session of every consuming project — expensive and mostly irrelevant to any single task.
- **No versioning in practice.** ARCHITECTURE.md promises tags, CHANGELOG, and pinning; none exist.

---

## 2. Documentation vs. Reality Gap (the biggest finding)

The README, CLAUDE.md, ARCHITECTURE.md, and INTEGRATION.md all describe directories and assets that **do not exist**:

| Promised | Reality |
|---|---|
| `.claude/skills/`, `.claude/agents/`, `.claude/hooks/` | Only `.claude/README.md` exists |
| `.codex/` configs | Absent (and README.md:31 calls Codex "Anthropic Codex" — Codex is an OpenAI product) |
| `frameworks/react|vue|angular|django|express|go/` | Only `frameworks/README.md` |
| `languages/typescript/`, `languages/go/`, … | Only `languages/python/` exists |
| `patterns/agentic-loops/`, `error-handling/`, `api-design/` | Only `testing/` and `logging/` exist |
| `tools/lint/`, `tools/build/`, `tools/deploy/` | Only `tools/README.md` |
| Top-level `hooks/pre-commit/`, `hooks/post-merge/` | Absent; the one real hook lives in `.github/hooks/` instead |
| `.github/workflows/` (reusable CI) | Absent |
| `dependabot.yml`, `CODEOWNERS` (listed in `.github/README.md` as present) | Absent |
| `docs/operational/{research,experiments,agent-logs,planning,archives}/` | Absent; INDEX.md is all "(none yet)" |
| CHANGELOG, version tags | Absent |
| Skills like `/code-review-advanced`, `/testing-strategy` used as examples | Don't exist |

Why this matters more than usual: **the consumers are agents.** An agent that reads "symlink `.claude/skills` from the harness" or "use `/code-review-advanced`" will attempt it, fail, or worse, fabricate. Documentation describing a fictional repo is actively harmful in an agent-context repo, not just untidy.

---

## 3. The Repo Violates Its Own Rules

This is the credibility problem. The harness mandates discipline it does not practice:

1. **All 9 commits are direct to `main`** — BRANCHING_STRATEGY.md's core rule is "You must NEVER directly commit to trunk branches," with an explicit FAQ answer "Can I commit directly to main in emergencies? **No.**"
2. **Its own `prevent-trunk-commit` hook is not installed** in this repo's `.git/hooks/`.
3. **Commit messages break COMMITTING_GUIDELINES.md**: "Add comprehensive mandatory logging and telemetry standards" is 59 chars (limit: 50); `first commit` is exactly the style the guide lists under "Bad ❌".
4. **No branch protection, no PRs, no reviews** — all mandated for consuming projects.
5. **Zero tests and zero CI** in a repo that declares 80% coverage "MANDATORY, NON-NEGOTIABLE" for "ALL production code … ALL agents and orchestrators." The one executable artifact (the hook script) has no tests and no shellcheck run.
6. **No LICENSE file** — "maintained for personal use" in the README is not a license and blocks any sharing/reuse.

A harness earns adoption by demonstrating its rules. Right now it demonstrates the opposite.

---

## 4. Broken or Incorrect Commands in Docs

All of these are presented as copy-paste-ready:

1. **README.md:114** — `ln -s ~/coding-harness/hooks/pre-commit/.git/hooks/pre-commit .git/hooks/pre-commit` — malformed path (missing space); links a nonexistent path either way.
2. **INTEGRATION.md:261** — `ln -s ~/awesome-harness/languages . docs/language-guide` — three arguments; invalid.
3. **CLAUDE.md ("How to use")** — `ln -s ~/awesome-harness/.claude/skills ~/.claude/skills` is captioned "In a project, symlink skills from this harness" but targets the **home directory**, clobbering (or failing on) the user's global Claude config. `.claude/README.md` goes further: `ln -s ~/awesome-harness/.claude ~/.claude` would shadow the user's entire Claude configuration.
4. **CLAUDE.md / INTEGRATION.md** — `cp ~/awesome-harness/hooks/pre-commit/* .husky/pre-commit` copies *multiple files onto a single file path*; source dir also doesn't exist.
5. **prevent-trunk-commit hook** — on a freshly `git init`-ed repo (unborn branch), `git rev-parse --abbrev-ref HEAD` fails, `CURRENT_BRANCH` is empty, and the hook **blocks the very first commit of every new repository** with "Could not determine current branch." Also: the trunk list contains literal `release`, but the strategy doc says `release/*` — exact-match means `release/1.2` is *not* blocked.
6. **TDD.md:99–107** — the "refactored, still passes tests" example is invalid Python: a module-level `authenticate()` calls `self._validate_credentials(...)`, and `_validate_credentials` is defined at module level taking no `self`. The flagship TDD doc's example would fail its own tests.
7. **TDD.md Go coverage script** — `[ $(…) -lt 80 ]` performs integer comparison on a float ("87.5") → `integer expression expected`, script breaks. (COVERAGE_REQUIREMENTS.md has the correct `bc -l` version — same repo, two answers.)
8. **BRANCHING_STRATEGY.md:668–677** — the "check for large files" pipeline is garbled shell (a `sed -n` fed by a malformed `-e` list) that cannot run.
9. **BRANCHING_STRATEGY.md secrets removal** — `bfg --delete-files .env .git` is wrong syntax (BFG takes a repo path, and `--delete-files` takes a glob, not two args); `git filter-branch … HEAD` rewrites only the current branch, leaving the secret in all others.
10. **PLAYWRIGHT_UI_TESTING.md:69–77** — `npx playwright install` appears twice, the second labeled "Initialize Playwright config" (that's `npm init playwright@latest`). Also claims tests run in "real … Safari" — Playwright drives WebKit, not Safari.
11. **logging.yaml.example** — uses `${VAR:-default}` interpolation throughout, but no loader supporting that syntax is provided or referenced anywhere. The "centralized logging framework" is a config file for an implementation that doesn't exist.
12. **LOGGING_STANDARDS.md** — examples use `logger.trace(...)` and `logger.info("msg", {dict})`; Python's stdlib logging has no TRACE level and doesn't accept a structured dict as the second positional argument that way. The examples imply a specific (structlog-like) library that is never named or configured.

---

## 5. Internal Contradictions & Duplication

The repo's #1 stated principle is DRY. Meanwhile:

1. **The 80%-coverage mandate is restated in at least four files** (CODING_GUIDELINES.md, TDD.md, COVERAGE_REQUIREMENTS.md, COMPLETION_CHECKLIST.md) — with **conflicting tier tables**:
   - TDD.md: `<75% → must be rewritten`
   - COVERAGE_REQUIREMENTS.md: `50–74% → request significant testing; <50% → rewrite`
   - COMPLETION_CHECKLIST.md: `79% → below minimum; <79% → unacceptable` (an off-by-one split of the same number)
2. **Lock files**: the `.gitignore.template` ignores `package-lock.json` and `Gemfile.lock`; BRANCHING_STRATEGY.md's FAQ says "Should I commit lock files? **Yes (usually)**."
3. **Assertion style**: CODING_GUIDELINES.md says "Minimize assertions — prefer one comprehensive snapshot assertion"; TDD.md's examples split every field into its own single-assert test and call the combined version a mistake.
4. **Scope discipline vs. maximalism**: CODING_GUIDELINES.md wisely says "trust internal code," "don't add error handling for scenarios that can't happen," "three similar lines don't need an abstraction" — then mandates OTEL-grade structured multi-backend logging, multi-browser screenshot-verified Playwright suites, and 80% coverage for *all* code with "no exceptions." The two philosophies (minimalism vs. mandate-everything) are never reconciled, and there's no scale-down path for scripts, prototypes, or one-offs.
5. **"Everything must be logged" vs. "No sensitive data"** in LOGGING_STANDARDS.md — stated as co-equal absolutes with no guidance on the obvious conflict.
6. **`docs/operational/` is "not version-critical"** yet tracked in git in a repo whose principle #3 is "Version Control – track all harnesses in git."
7. **`.env.example` vs. your own global preference** — your user-level CLAUDE.md standardizes on `.env.sample`; the harness repeatedly instructs `.env.example`. The harness contradicts its owner.
8. **CLAUDE.md principle 5: "Testability – Harnesses are tested before being added to this repo."** Nothing in the repo is tested.

---

## 6. Content-Quality Findings

1. **Fabricated statistics presented as fact.** "10 bugs per 1000 lines → <1", "~95% of bugs prevented before production", "Ship with ~99% fewer critical bugs", "0 failed deployments" (TDD.md, COVERAGE_REQUIREMENTS.md, PLAYWRIGHT_UI_TESTING.md, LOGGING_STANDARDS.md all use the same invented before/after template). In an instruction corpus for agents, these become "facts" the agent repeats to users. Either cite sources or cut them.
2. **VS Code internals leaked into a "universal" harness.** `accessibility.instructions.md` is entirely VS Code-internal (AccessibleContentProvider, `CONTEXT_ACCESSIBILITY_MODE_ENABLED`, "PR #293163"), yet its frontmatter claims general applicability. CODING_GUIDELINES.md similarly carries VS Code-isms presented as universal: `DisposableStore`/`this._register()`, "correlated file watchers," arrow-function style rules. The commit message even admits the source ("generalized … from vscode project") — the generalization pass didn't happen.
3. **Questionable universal advice**: "Avoid `any` **or `unknown`**" — `unknown` is TypeScript's recommended safe alternative to `any`; banning both removes the correct tool. "For languages with explicit resource management (Rust, C++, or languages with GC)" describes every language.
4. **Mandate without mechanism.** "Agent MUST review and approve all screenshots (no approval = not done)" — no protocol for what approval means, where it's recorded, or how CI checks it. Same for "logging verification required before marking work complete."
5. **`.gitignore.template` hazards**: ignores `lib/` and `lib64/` globally (kills legitimate `lib/` source dirs — these belong under a venv path, not root); ignores `vendor/` for Go (vendored deps, when used, should be committed); ignores `.nvmrc` / `.python-version` / `.ruby-version` (version pins that are conventionally committed); triple-lists `.DS_Store`; duplicates `build/`/`dist/`/`out/`/`target/` across sections.
6. **Hand-maintained "Last Updated" dates** on every file will rot immediately; git already records this.
7. **CLAUDE.md is doing the wrong job.** It's a 450-line human onboarding doc loaded into every agent session. Agent-facing CLAUDE.md should be a lean router (what exists, where, when to read it), with human prose in README/docs.

---

## 7. What's Actually Good

Credit where due — these are genuinely useful today:

- **COMMITTING_GUIDELINES.md** is the best file in the repo: correct, scoped, actionable (never `--no-verify`, respect signing, atomic commits, good/bad examples).
- **BRANCHING_STRATEGY.md**'s naming conventions, worktree guidance, and lifecycle walkthrough are solid (modulo the broken snippets noted above).
- **COPILOT_INSTRUCTIONS.md** (Python) is excellent agent-instruction writing: "never claim a command passed unless it ran," "don't hide failures by weakening tests," repository-inspection-first. This is the tone the whole repo should have.
- **languages/python/CONVENTIONS.md** is accurate and appropriately scoped.
- **The `docs/operational/` concept** (quarantine for agent-generated ephemera, with promote/archive/delete workflow) is a genuinely good idea I'd keep.
- **The hook script**, initial-commit bug aside, is well-structured with helpful remediation output.

---

## 8. Improvement Backlog

### P0 — Make the repo honest (docs describe what exists)
1. Rewrite README/CLAUDE.md/ARCHITECTURE.md to document **only existing content**; move the aspirational directory tree to a ROADMAP.md.
2. Delete or clearly mark every reference to nonexistent skills (`/code-review-advanced`), directories (`.codex/`, `hooks/`, `frameworks/react/`…), and files (`dependabot.yml`, `CODEOWNERS`).
3. Fix the "Anthropic Codex" error (README.md:31).
4. Add a LICENSE file (even proprietary/personal — make it explicit).

### P0 — Practice what it preaches
5. Install `prevent-trunk-commit` into this repo (`core.hooksPath=.github/hooks` makes it automatic for every clone).
6. Adopt branch + PR flow for the harness itself; enable branch protection on GitHub.
7. Add CI: markdown link check, shellcheck on all hooks/scripts, and bats (or similar) tests for the hook script. The repo mandates CI for everyone else; it needs its own.
8. Bring commit subjects within the repo's own 50-char rule going forward.

### P1 — Fix the broken artifacts
9. Fix the hook's unborn-branch bug (treat rev-parse failure as "not on trunk", or detect via `git symbolic-ref`), and decide whether `release/*` should be pattern-matched.
10. Repair every broken shell snippet (§4: README:114, INTEGRATION:261, husky copy, BFG/filter-branch, large-file scan, Go coverage float comparison, duplicate `npx playwright install`).
11. Fix the invalid Python in TDD.md's refactor example.
12. Either ship a real config loader for `logging.yaml.example`'s `${VAR:-default}` syntax (a small Python module would do) or rewrite the example in a format something actually parses; name the logging library the examples assume (structlog/loguru) and make examples runnable.
13. Overhaul `.gitignore.template`: remove `lib/`, `vendor/` (Go), version-pin files; deduplicate; align lock-file policy with the FAQ.

### P1 — Deduplicate and reconcile
14. Make each rule live in exactly one file. Suggested: COVERAGE_REQUIREMENTS.md owns the tiers; TDD.md, CODING_GUIDELINES.md, and COMPLETION_CHECKLIST.md link to it. Resolve the three conflicting tier tables into one.
15. Reconcile the minimalism-vs-maximalism split: define **tiers of rigor** (prototype / internal tool / production service) and state which mandates apply at which tier. "80% coverage and OTEL for everything including throwaway scripts" is not a rule anyone will follow, and unfollowable rules teach agents to ignore all rules.
16. Resolve assertion-style contradiction (one-comprehensive-assert vs. one-assert-per-behavior) with a single stated policy.
17. Standardize on `.env.sample` (your global preference) everywhere, or consciously change the global preference — one or the other.
18. Remove or source the fabricated before/after statistics.

### P2 — Make it agent-native (the real payoff)
19. Slim CLAUDE.md to a ~50-line router: what exists, one line each, when to read it. Agents pay for every token of it in every session.
20. Add a machine-readable `manifest.json`/`INDEX.md` at root listing every asset with type/language/framework tags — the "discoverability by metadata" ARCHITECTURE.md promises but doesn't implement.
21. Convert the strongest docs into actual **Claude Code skills** with proper frontmatter under `.claude/skills/` (e.g., `committing`, `branching`, `python-conventions`) so they load on demand instead of via copy-paste. This single step would make the repo do what its name claims.
22. Generalize or relocate the VS Code-specific content (accessibility instructions → `frameworks/vscode-extensions/` or delete; strip `DisposableStore`/file-watcher/arrow-function items from the "universal" guidelines or label them TypeScript/VS Code).
23. Write one real end-to-end example: a tiny sample project that consumes the harness via each of the three integration methods, kept green by CI. This validates every integration command in INTEGRATION.md automatically.
24. Add the promised setup script (`tools/setup/harness-link.sh`) so integration is one tested command instead of a page of hand-typed symlinks — eliminating the class of bugs found in §4.

### P2 — Process & hygiene
25. Replace hand-written "Last Updated" lines with git history (or a pre-commit hook that stamps them).
26. Create CHANGELOG.md and tag `v0.1.0` now that the docs exist; ARCHITECTURE.md already promises this workflow.
27. Rename consideration: `dev-harness`, `agent-harness`, or `harness` — avoid the `awesome-list` convention collision.
28. Create the `docs/operational/` subdirectories with `.gitkeep` (or drop them from the docs), and decide whether operational docs are tracked or gitignored — currently both is claimed.
29. Define the screenshot-approval and logging-verification protocols concretely (where evidence is recorded, what CI checks), or soften the language from "MUST … WILL NOT MERGE" to guidance.
30. Add a `SECURITY.md`-style note for the secrets-in-history procedure once the broken commands are fixed — it's a good topic, currently a dangerous copy-paste.

---

## 9. Verdict

**4.5 / 10.** The concept deserves an 8; the current artifact is a well-written prospectus for a repository that hasn't been built, wrapped around four genuinely useful guideline docs and one hook script with an initial-commit bug. The highest-leverage fixes are cheap: make the docs match reality (P0), make the repo obey itself (P0), then convert the best content into on-demand skills with a machine-readable index (P2 #19–21). Do those and this becomes a 7+ that other people would actually clone.

The single most important insight for the roadmap: **the audience is agents, not humans.** Every design decision — index size, on-demand loading, no phantom references, runnable-not-illustrative snippets, one source of truth per rule — follows from that.
