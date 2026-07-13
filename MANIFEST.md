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
| prevent-trunk-commit hook | `.github/hooks/prevent-trunk-commit` | git hook | The enforcement logic. Installed via `git config core.hooksPath .github/hooks` (done in this repo) |
| pre-commit dispatcher | `.github/hooks/pre-commit` | git hook | Required alongside the hook above — `core.hooksPath` only invokes a file literally named `pre-commit`; this execs `prevent-trunk-commit` |
| pre-push test/coverage hook | `.github/hooks/pre-push` | git hook | Runs bats + pytest suites and blocks the push if anything fails or Python coverage drops below 80%. Installed the same way as the hooks above (git only needs a file literally named `pre-push`) |

## Language Conventions

| Asset | Path | Type | When to use |
|---|---|---|---|
| Python conventions | `languages/python/CONVENTIONS.md` | guide | Naming, structure, idioms for `.py` files |
| Python agent instructions | `languages/python/COPILOT_INSTRUCTIONS.md` | guide | General-purpose agent operating principles for Python repos |
| TypeScript conventions | `languages/typescript/CONVENTIONS.md` | guide | Naming, type safety for `.ts` / `.tsx` files (React specifics are a separate framework add-on) |
| Go conventions | `languages/go/CONVENTIONS.md` | guide | Naming, concurrency, interfaces, testing for `.go` files |
| React conventions | `frameworks/react/CONVENTIONS.md` | guide | Component naming, props typing — layered on top of the TypeScript guide |

## Testing & Quality Patterns

| Asset | Path | Type | When to use |
|---|---|---|---|
| Rigor tiers | `.github/CODING_GUIDELINES.md#rigor-tiers` | policy | **Read first** — decides which mandates below actually apply to the code you're writing |
| Rigor-tier profiles | `patterns/profiles/README.md` | guide | Selecting a tier via `.agentharness-profile`, precedence order, current state of enforcement (advisory only) |
| Prototype profile | `patterns/profiles/prototype.yaml` | config | Machine-readable form of the Rigor Tiers table's Prototype column |
| Internal profile | `patterns/profiles/internal.yaml` | config | Machine-readable form of the Rigor Tiers table's Internal Tool column |
| Production profile | `patterns/profiles/production.yaml` | config | Machine-readable form of the Rigor Tiers table's Production Service column |
| TDD | `patterns/testing/TDD.md` | guide | Where this repo's TDD guidance departs from standard practice (one worked mistake) |
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
| Agent loop implementation | `patterns/agentic-loops/agent_loop.py` | utility | Python: tested, provider-neutral single-tool-call agent loop with schema validation, budget, approval hook, audit trace |
| Agent loop tests | `patterns/agentic-loops/test_agent_loop.py` | tests | Tests for agent_loop.py; run with pytest |

## Eval Suite

| Asset | Path | Type | When to use |
|---|---|---|---|
| Overview | `tools/eval/README.md` | guide | What the suite measures, task format, how to score a candidate, what running a real eval requires (P2-04) |
| Task definitions | `tools/eval/tasks/` | fixtures | 3 task specs (2 Python, 1 Go): prompt, starter code, hidden grading tests |
| Deterministic scorer | `tools/eval/score.py` | script | Runs a task's hidden tests against a candidate dir; no LLM calls (P2-04) |
| Orchestrator | `tools/eval/run.py` | script | Baseline/treatment condition setup + ledger writing; the live-agent call is unimplemented by design — see the README's "Running a real eval" (P2-04) |
| Scorer/orchestrator fixtures | `tools/eval/fixtures/` | fixtures | Hand-written correct/broken implementations per task, used by `tests/test_score.py` |
| Results ledger | `tools/eval/results/README.md` | doc | JSON-lines format for tracked score history |

## Logging

| Asset | Path | Type | When to use |
|---|---|---|---|
| Logging standards | `patterns/logging/LOGGING_STANDARDS.md` | guide | Structured logging design, levels, what to log/redact, centralized config |
| logging.yaml example | `patterns/logging/logging.yaml.example` | template | Copy and adapt for your service; includes OTEL, cloud, file, console backends |
| Config loader | `patterns/logging/config_loader.py` | utility | Python: load YAML config with `${VAR:-default}` env var interpolation |
| Config loader tests | `patterns/logging/test_config_loader.py` | tests | Tests for config_loader.py; run with pytest |

## Claude Code Skills

| Asset | Path | Type | When to use |
|---|---|---|---|
| Committing | `.claude/skills/committing/SKILL.md` | skill | Loads on demand for commit-related work |
| Branching | `.claude/skills/branching/SKILL.md` | skill | Loads on demand for branch/worktree work |
| Python conventions | `.claude/skills/python-conventions/SKILL.md` | skill | Loads on demand when writing Python |
| Error handling | `.claude/skills/error-handling/SKILL.md` | skill | Loads on demand for error recovery, resilience patterns |
| Agentic loops | `.claude/skills/agentic-loops/SKILL.md` | skill | Loads on demand for multi-turn agents, tool calling |
| Audit review follow-up | `.claude/skills/audit-review-followup/SKILL.md` | skill | Verifying that review recommendations were actually implemented; re-scoring |

## Setup & Examples

| Asset | Path | Type | When to use |
|---|---|---|---|
| Harness lifecycle CLI | `tools/setup/harness-link.sh` | script | init/plan/status/doctor/audit/update/uninstall; link/copy/submodule modes; state tracked in `<project>/.agentharness-state.json` |
| Local check entrypoint | `tools/check.sh` | script | Runs every check CI runs (shellcheck, bats, ruff, mypy, pytest+coverage, manifest verify) in one command (P1-06) |
| Pinned dev/CI toolchain | `requirements-dev.txt` | config | Exact pinned versions of pytest/ruff/mypy/etc. — `pip install -r requirements-dev.txt` (P1-06) |
| Sample project | `examples/sample-project/` | project | Blank/generic fixture; demonstrates harness integration, validates INTEGRATION.md commands work |
| Integration verification | `examples/sample-project/verify.sh` | script | Checks that skills, hooks, and guidelines are properly integrated |
| Python fixture | `examples/python-project/` | project | Realistic Python consumer (pre-existing `.gitignore`); CI-verified across all install modes |
| TypeScript fixture | `examples/typescript-project/` | project | Realistic TypeScript consumer (pre-existing `.gitignore`); CI-verified across all install modes |
| Go fixture | `examples/go-project/` | project | Realistic Go consumer (pre-existing `.gitignore`); CI-verified across all install modes |
| npm package manifest | `package.json` | config | `files` allowlist for `npm publish`; `bin.agentharness` entry point; see `docs/RELEASING.md#npm-distribution` for what's built vs. not-yet-published |
| npm CLI shim | `bin/cli.js` | script | Execs `tools/setup/harness-link.sh` from an npm/npx install; fails clearly if `bash`/`python3` are missing |
| Symlink materializer | `tools/release/materialize-skill-symlinks.py` | script | `prepack`/`postpack` hook — npm tarballs don't preserve symlinks, so bundled-resource symlinks (e.g. `agentic-loops`'s) are copied to real files before packing, then restored via `git checkout` |

## GitHub Configuration

| Asset | Path | Type | Purpose |
|---|---|---|---|
| Dependency updates | `.github/dependabot.yml` | config | Automated dependency version checking (Go, GitHub Actions) |
| Code ownership | `.github/CODEOWNERS` | config | Review routing and ownership for framework components |
| Scheduled link check | `.github/workflows/link-check-scheduled.yml` | workflow | Weekly online external-link validation, separate from the offline PR gate (P1-08) |
| Release workflow | `.github/workflows/release.yml` | workflow | Runs `npm publish` on a `v*` tag push; inert until `NPM_TOKEN` secret exists (P2-03) |
| Markdownlint config | `.markdownlint-cli2.yaml` | config | Rules enforced in CI's content-quality job; documents why purely-stylistic rules are off (P1-08) |
| Content-quality checker | `tools/verify-content-quality.py` | script | YAML validity, skill frontmatter schema, tested-snippet syntax (P1-08); also checks `AGENTS.md` sync (P2-02) |
| AGENTS.md generator | `tools/generate-agents-md.sh` | script | Builds the Codex adapter from `CLAUDE.md` + `.claude/skills/` (P2-02) |

## Meta

| Asset | Path | Type |
|---|---|---|
| Repo overview | `README.md` | doc |
| Agent-facing router + mandatory rules | `CLAUDE.md` | doc (loaded every session — kept short on purpose) |
| Codex adapter (generated, untested against real Codex) | `AGENTS.md` | doc (generated by `tools/generate-agents-md.sh`; do not hand-edit) |
| Architecture / design philosophy | `docs/ARCHITECTURE.md` | doc |
| Architecture decision log (compact, retroactive) | `docs/DECISIONS.md` | doc |
| Integration instructions | `docs/INTEGRATION.md` | doc |
| 5-minute scripted demo (real commands, real output) | `docs/DEMO.md` | doc |
| Planned-but-not-built components | `ROADMAP.md` | doc |
| Release history | `CHANGELOG.md` | doc |
| Release policy (versioning, checklist, pin/upgrade/rollback) | `docs/RELEASING.md` | doc |
| Security / secrets procedure | `SECURITY.md` | doc |
| Contribution workflow | `CONTRIBUTING.md` | doc |
| Code of Conduct | `CODE_OF_CONDUCT.md` | doc |
| Issue template: bug report | `.github/ISSUE_TEMPLATE/bug_report.md` | GitHub config |
| Issue template: feature request | `.github/ISSUE_TEMPLATE/feature_request.md` | GitHub config |
| Prior full repo review | `docs/operational/reviews/fable-review.md` | historical record — dated 2026-07-11, describes the repo as `awesome-harness` before the rename |
| Review recommendations status | `docs/operational/reviews/fable-review-status.md` | disposition of all 30 backlog items from the review above |
| Independent repo review (GPT-5.6) | `docs/operational/reviews/gpt-5.6-review.md` | second-opinion review, dated 2026-07-11; completion status is recorded separately below |
| GPT-5.6 review completion status | `docs/operational/reviews/gpt-5.6-review-status.md` | evidence-based re-validation of all 30 backlog items and 12 release gates at `43604a7` |
| GPT-5.6 completion re-audit | `docs/operational/reviews/gpt-5.6-completion-reaudit.md` | current-state validation at merged `main` commit `d4d2541`; 17 verified, 11 partial, 1 missed, 1 deferred |
| GPT-5.6 re-audit response | `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md` | per-item disposition: scoped fixes implemented directly, larger items scoped for user confirmation |
| PR #4 review-comment status | `docs/operational/reviews/pr4-comments-status.md` | disposition of Copilot's PR #4 comments and this session's own audit gaps |
