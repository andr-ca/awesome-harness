# Manifest

Machine-readable-ish index of every real asset in this repo. One line per
item: what it is, where it lives, when to read it. If it's not listed here,
it doesn't exist yet — check [ROADMAP.md](ROADMAP.md) for planned work.

Regenerate mentally whenever you add/remove a top-level doc; there's no
generator script yet (see ROADMAP.md).

## Git / Workflow

| Asset | Path | Type | When to use |
|---|---|---|---|
| Branching strategy | `.github/BRANCHING_STRATEGY.md` | guide | Before creating a branch; naming, worktrees, gitignore, secrets cleanup |
| Committing guidelines | `.github/COMMITTING_GUIDELINES.md` | guide | Before every commit; message format, atomic commits, agent workflow-completion rule |
| Coding guidelines | `.github/CODING_GUIDELINES.md` | guide | Before writing code in any language; naming, comments, testing mandate, definition of done |
| PR template | `.github/pull_request_template.md` | template | Auto-populated on PR creation |
| gitignore template | `.github/.gitignore.template` | template | `cp` into a new project as `.gitignore` |
| prevent-trunk-commit hook | `.github/hooks/prevent-trunk-commit` | git hook | Installed via `git config core.hooksPath .github/hooks` (done in this repo) |

## Language Conventions

| Asset | Path | Type | When to use |
|---|---|---|---|
| Python conventions | `languages/python/CONVENTIONS.md` | guide | Naming, structure, idioms for `.py` files |
| Python agent instructions | `languages/python/COPILOT_INSTRUCTIONS.md` | guide | General-purpose agent operating principles for Python repos |
| TypeScript conventions | `languages/typescript/CONVENTIONS.md` | guide | Naming, type safety, React patterns for `.ts` / `.tsx` files |
| Go conventions | `languages/go/CONVENTIONS.md` | guide | Naming, concurrency, interfaces, testing for `.go` files |

## Testing & Quality Patterns

| Asset | Path | Type | When to use |
|---|---|---|---|
| Rigor tiers | `.github/CODING_GUIDELINES.md#rigor-tiers` | policy | **Read first** — decides which mandates below actually apply to the code you're writing |
| TDD | `patterns/testing/TDD.md` | guide | Red-green-refactor workflow, one-time-only exceptions |
| Coverage requirements | `patterns/testing/COVERAGE_REQUIREMENTS.md` | policy | Single source of truth for the 80% coverage tiers — other docs link here, don't restate |
| Completion checklist | `patterns/testing/COMPLETION_CHECKLIST.md` | checklist | Before marking any task done |
| Playwright UI testing | `patterns/testing/PLAYWRIGHT_UI_TESTING.md` | guide | Web UI work at Production tier only |

## Error Handling & Reliability

| Asset | Path | Type | When to use |
|---|---|---|---|
| Error handling patterns | `patterns/error-handling/README.md` | guide | Explicit errors, wrapping, retry/circuit-breaker, structured logging |

## Agentic & Autonomous Systems

| Asset | Path | Type | When to use |
|---|---|---|---|
| Agentic loops | `patterns/agentic-loops/README.md` | guide | Building multi-turn agents, tool calling, tool chaining, branching |

## Logging

| Asset | Path | Type | When to use |
|---|---|---|---|
| Logging standards | `patterns/logging/LOGGING_STANDARDS.md` | guide | Structured logging design, levels, what to log/redact, centralized config |
| logging.yaml example | `patterns/logging/logging.yaml.example` | template | Copy and adapt for your service; includes OTEL, cloud, file, console backends |
| Config loader | `patterns/logging/config_loader.py` | utility | Python: load YAML config with `${VAR:-default}` env var interpolation |
| Config loader tests | `patterns/logging/test_config_loader.py` | tests | Tests for config_loader.py; run with pytest

## Claude Code Skills

| Asset | Path | Type | When to use |
|---|---|---|---|
| Committing | `.claude/skills/committing/SKILL.md` | skill | Loads on demand for commit-related work |
| Branching | `.claude/skills/branching/SKILL.md` | skill | Loads on demand for branch/worktree work |
| Python conventions | `.claude/skills/python-conventions/SKILL.md` | skill | Loads on demand when writing Python |
| Error handling | `.claude/skills/error-handling/SKILL.md` | skill | Loads on demand for error recovery, resilience patterns |
| Agentic loops | `.claude/skills/agentic-loops/SKILL.md` | skill | Loads on demand for multi-turn agents, tool calling |

## Setup & Examples

| Asset | Path | Type | When to use |
|---|---|---|---|
| Harness link script | `tools/setup/harness-link.sh` | script | One-command integration into a consuming project |
| Sample project | `examples/sample-project/` | project | Demonstrates harness integration; validates INTEGRATION.md commands work |
| Integration verification | `examples/sample-project/verify.sh` | script | Checks that skills, hooks, and guidelines are properly integrated |

## GitHub Configuration

| Asset | Path | Type | Purpose |
|---|---|---|---|
| Dependency updates | `.github/dependabot.yml` | config | Automated dependency version checking (Go, GitHub Actions) |
| Code ownership | `.github/CODEOWNERS` | config | Review routing and ownership for framework components |

## Meta

| Asset | Path | Type |
|---|---|---|
| Repo overview | `README.md` | doc |
| Agent-facing router + mandatory rules | `CLAUDE.md` | doc (loaded every session — kept short on purpose) |
| Architecture / design philosophy | `docs/ARCHITECTURE.md` | doc |
| Integration instructions | `docs/INTEGRATION.md` | doc |
| Planned-but-not-built components | `ROADMAP.md` | doc |
| Release history | `CHANGELOG.md` | doc |
| Security / secrets procedure | `SECURITY.md` | doc |
| Prior full repo review | `docs/operational/reviews/fable-review.md` | historical record — dated 2026-07-11, describes the repo as `awesome-harness` before the rename |
| Review recommendations status | `docs/operational/reviews/fable-review-status.md` | disposition of all 30 backlog items from the review above |
