# Manifest

Machine-readable-ish index of every real asset in this repo. One line per
item: what it is, where it lives, when to read it. If it's not listed here,
it doesn't exist yet — check [ROADMAP.md](ROADMAP.md) for planned work.

Generated from `manifest.yaml` by `tools/generate-manifest.py` — edit
that file, not this one, and run the generator to regenerate. CI fails if
they drift (`check_manifest_md_sync()` in `tools/verify-content-quality.py`).

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
| Bubblewrap AppArmor profile | `.github/apparmor/agentharness-bwrap` | CI sandbox policy | Allows only the trusted system bubblewrap launcher to create the user namespace used by mandatory Ubuntu runtime-upgrade isolation tests |

## Language Conventions

| Asset | Path | Type | When to use |
|---|---|---|---|
| Python conventions | `languages/python/CONVENTIONS.md` | guide | Naming, structure, idioms for `.py` files |
| Python agent instructions | `languages/python/COPILOT_INSTRUCTIONS.md` | guide | General-purpose agent operating principles for Python repos |
| TypeScript conventions | `languages/typescript/CONVENTIONS.md` | guide | Naming, type safety for `.ts` / `.tsx` files (React specifics are a separate framework add-on) |
| Go conventions | `languages/go/CONVENTIONS.md` | guide | Naming, concurrency, interfaces, testing for `.go` files |
| Rust conventions | `languages/rust/CONVENTIONS.md` | guide | Naming, unwrap/expect by rigor tier, error-crate choice, unsafe policy, testing for `.rs` files |
| React conventions | `frameworks/react/CONVENTIONS.md` | guide | Component naming, props typing — layered on top of the TypeScript guide |

## Testing & Quality Patterns

| Asset | Path | Type | When to use |
|---|---|---|---|
| Rigor tiers | `.github/CODING_GUIDELINES.md#rigor-tiers` | policy | **Read first** — decides which mandates below actually apply to the code you're writing |
| Rigor-tier profiles | `patterns/profiles/README.md` | guide | Selecting a tier via `.agentharness-profile`, precedence order, current enforcement state (Python, Go, and JS/TS `node --test`/Vitest via `enforce-profile`, advisory for other project types/runners) |
| Prototype profile | `patterns/profiles/prototype.yaml` | config | Machine-readable form of the Rigor Tiers table's Prototype column |
| Internal profile | `patterns/profiles/internal.yaml` | config | Machine-readable form of the Rigor Tiers table's Internal Tool column |
| Production profile | `patterns/profiles/production.yaml` | config | Machine-readable form of the Rigor Tiers table's Production Service column |
| TDD | `patterns/testing/TDD.md` | guide | Where this repo's TDD guidance departs from standard practice (one worked mistake) |
| Coverage requirements | `patterns/testing/COVERAGE_REQUIREMENTS.md` | policy | Single source of truth for the 80% coverage tiers — other docs link here, don't restate |
| Completion checklist | `patterns/testing/COMPLETION_CHECKLIST.md` | checklist | Before marking any task done |
| Playwright UI testing | `patterns/testing/PLAYWRIGHT_UI_TESTING.md` | guide | Web UI work at Production tier only |
| Accessibility patterns | `patterns/accessibility/README.md` | guide | Cross-framework WCAG 2.2 AA / ARIA baseline — semantic HTML, keyboard, contrast, custom-widget roles, testing |
| Mutation testing overview | `patterns/mutation-testing/README.md` | guide | Entry point for mutation testing — routes to MUTATION_TESTING.md |
| Mutation testing guide | `patterns/mutation-testing/MUTATION_TESTING.md` | guide | Mutation operators, mutation score thresholds, mutmut/Stryker/gremlins tooling, surviving mutant triage |
| File placement policy overview | `patterns/file-placement-policy/README.md` | guide | Entry point for the file placement protocol |
| File placement policy | `patterns/file-placement-policy/POLICY.md` | guide | Guarded paths, allowed-additions escape hatch, init-time analysis, pre-commit enforcement |
| Multi-agent coordination overview | `patterns/multi-agent-coordination/README.md` | guide | Entry point for multi-agent lock protocol |
| Multi-agent coordination guide | `patterns/multi-agent-coordination/COORDINATION.md` | guide | Lock-file protocol, stale detection, worktree isolation, and conflict resolution for concurrent agents |

## Error Handling & Reliability

| Asset | Path | Type | When to use |
|---|---|---|---|
| Error handling patterns | `patterns/error-handling/README.md` | guide | Explicit errors, wrapping, retry/circuit-breaker, structured logging |
| API design overview | `patterns/api-design/README.md` | guide | Entry point for HTTP API design — routes to REST_CONVENTIONS.md |
| REST API conventions | `patterns/api-design/REST_CONVENTIONS.md` | guide | Resource naming, HTTP methods/status codes, RFC 9457 errors, versioning, pagination, auth |

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

## Skills (installed under both .claude/skills/ and .agents/skills/ — Claude Code and Codex)

| Asset | Path | Type | When to use |
|---|---|---|---|
| Committing | `.claude/skills/committing/SKILL.md` | skill | Loads on demand for commit-related work |
| Branching | `.claude/skills/branching/SKILL.md` | skill | Loads on demand for branch/worktree work |
| Python conventions | `.claude/skills/python-conventions/SKILL.md` | skill | Loads on demand when writing Python |
| Error handling | `.claude/skills/error-handling/SKILL.md` | skill | Loads on demand for error recovery, resilience patterns |
| Agentic loops | `.claude/skills/agentic-loops/SKILL.md` | skill | Loads on demand for multi-turn agents, tool calling |
| Audit review follow-up | `.claude/skills/audit-review-followup/SKILL.md` | skill | Verifying that review recommendations were actually implemented; re-scoring |
| Port agent config | `.claude/skills/port-agent-config/SKILL.md` | skill | Porting/migrating agent instructions, skills, and custom subagents to a different coding tool — uses this repo's own generators when linked, hand-ports the same principles when not |
| TypeScript conventions | `.claude/skills/typescript-conventions/SKILL.md` | skill | Loads on demand when writing or reviewing TypeScript/JavaScript |
| Go conventions | `.claude/skills/go-conventions/SKILL.md` | skill | Loads on demand when writing or reviewing Go |
| Testing | `.claude/skills/testing/SKILL.md` | skill | Loads on demand when writing tests, choosing coverage strategy, or applying TDD |
| Logging | `.claude/skills/logging/SKILL.md` | skill | Loads on demand when adding or reviewing logging |
| Accessibility | `.claude/skills/accessibility/SKILL.md` | skill | Loads on demand when building or reviewing web UIs for accessibility |
| Security review | `.claude/skills/security-review/SKILL.md` | skill | Loads on demand for security audits, OWASP Top 10 checks, code review for vulnerabilities |
| Planning with files | `.claude/skills/planning-with-files/SKILL.md` | skill | Loads on demand when starting complex multi-step tasks requiring persistent state across context resets |
| Requirements clarification | `.claude/skills/requirements-clarification/SKILL.md` | skill | Loads on demand before implementing ambiguous or underspecified features |
| Code review | `.claude/skills/code-review/SKILL.md` | skill | Loads on demand when reviewing a diff or pull request |
| API design | `.claude/skills/api-design/SKILL.md` | skill | Loads on demand when designing or reviewing REST or GraphQL APIs |
| React best practices | `.claude/skills/react-best-practices/SKILL.md` | skill | Loads on demand when writing or reviewing React or Next.js code |
| Database conventions | `.claude/skills/database-conventions/SKILL.md` | skill | Loads on demand when designing schemas, writing migrations, or reviewing SQL queries |
| Docker conventions | `.claude/skills/docker-conventions/SKILL.md` | skill | Loads on demand when writing Dockerfiles or docker-compose files |
| Dependency audit | `.claude/skills/dependency-audit/SKILL.md` | skill | Loads on demand when checking dependencies for vulnerabilities or updating packages |
| Performance profiling | `.claude/skills/performance-profiling/SKILL.md` | skill | Loads on demand when diagnosing slow code, high memory, or CPU spikes |
| Mutation testing | `.claude/skills/mutation-testing/SKILL.md` | skill | Loads on demand when auditing test suite quality beyond line coverage or interpreting surviving mutants |
| Multi-agent coordination | `.claude/skills/multi-agent-coordination/SKILL.md` | skill | Loads on demand when two or more agents may work on the same repository concurrently |
| File placement policy | `.claude/skills/file-placement-policy/SKILL.md` | skill | Loads at session start in projects with .agentharness-guarded-paths.json; checks before any new file creation |
| Dependency injection | `.claude/skills/dependency-injection/SKILL.md` | skill | Constructor injection, DI containers, testability; load when reviewing tightly-coupled code or designing services |
| SOLID principles | `.claude/skills/solid-principles/SKILL.md` | skill | SRP, OCP, LSP, ISP, DIP; load during design review or when a class feels too large |
| Design patterns | `.claude/skills/design-patterns/SKILL.md` | skill | Factory, Strategy, Observer, Repository, Decorator, Command, Builder; load when recognizing a recurring design problem |
| Clean architecture | `.claude/skills/clean-architecture/SKILL.md` | skill | Hexagonal/ports-and-adapters, domain isolation; load when business logic is tangled with infrastructure |
| Code review | `.claude/skills/code-review/SKILL.md` | skill | Systematic review checklist; load when reviewing a PR or assessing a code change |

## Custom Agents (task delegation to a separate agent instance — a different mechanism from skills, ported to Codex/OpenCode/Cursor/Kilo Code/Copilot/Gemini CLI)

| Asset | Path | Type | When to use |
|---|---|---|---|
| Coding guidelines reviewer | `.claude/agents/coding-guidelines-reviewer.md` | subagent | Dispatch after finishing a change to check it against CODING_GUIDELINES.md's rigor tiers and COMPLETION_CHECKLIST.md — read-only, reports gaps, does not fix them |

## Setup & Examples

| Asset | Path | Type | When to use |
|---|---|---|---|
| Harness lifecycle CLI | `tools/setup/harness-link.sh` | script | init/plan/status/doctor/audit/enforce-profile/generate-clients/update/uninstall; link/copy/submodule modes; state tracked in `<project>/.agentharness-state.json` |
| Local check entrypoint | `tools/check.sh` | script | Runs every check CI runs (shellcheck, bats, ruff, mypy, pytest+coverage, manifest verify, skill-symlink integrity) in one command (P1-06) |
| Agent lock manager | `tools/agent-lock.sh` | script | Per-feature lock files for concurrent agent sessions — acquire/release/check/list/clean/suggest-branch |
| Structure analyzer | `tools/analyze_structure.py` | script | Analyze project structure and generate .agentharness-guarded-paths.json; also --recommend for early-stage projects |
| File placement check | `tools/check-file-placement.sh` | script | Pre-commit hook check — blocks staged files in guarded paths; wired into .github/hooks/pre-commit alongside trunk protection |
| Completion gate script | `tools/check-completion.sh` | script | Run before declaring work done — verifies lint, types, tests, coverage, content quality. Exit 0 = complete; exit 1 = incomplete |
| Completion gate hook (Copilot) | `.github/hooks/completion-gate.json` | hook | Copilot Stop hook — prevents agents from stopping until check-completion.sh passes |
| Completion gate hook (Claude Code) | `.claude/settings.json` | hook | Claude Code Stop hook — same enforcement as the Copilot hook |
| Skill-symlink verifier | `tools/verify-skill-symlinks.sh` | script | Verifies `.agents/skills/` stays 1:1 with `.claude/skills/` — every Agent-Skills-standard tool (Codex, Copilot, Gemini, ...) reads the symlinks, so drift silently hides a skill from them while Claude still sees it |
| Pinned dev/CI toolchain | `requirements-dev.txt` | config | Exact pinned versions of pytest/ruff/mypy/etc. — install after the separate hash-locked runtime requirements (P1-06) |
| Wheel-only CI runtime lock | `requirements-ci-runtime.lock` | config | Hash-closed PyYAML and fastjsonschema wheel installation for Python 3.12/3.14 CI jobs; versions must match requirements-runtime.lock |
| Minimal content-quality runtime lock | `requirements-ci-content.lock` | config | Hash-closed PyYAML-only wheel installation for the content-quality CI job |
| Runtime artifact cache seeder | `tools/runtime/seed-runtime-artifacts.sh` | script | Portable shell entrypoint before building or packaging the Python runtime zipapp in a clean checkout |
| Authenticated runtime artifact acquisition | `tools/runtime/seed-runtime-artifacts.py` | script | Downloads fixed official artifacts as inert bytes, strictly parses requirements-runtime.lock, promotes each file atomically under a cache lock, and fails closed if a mixed generation remains |
| Canonical runtime requirements parser | `src/agentharness/runtime_requirements.py` | utility | Shared strict parser used by runtime zipapp building and authenticated artifact seeding; rejects duplicate, extra, malformed, or version-drifted lock declarations |
| Sample project | `examples/sample-project/` | project | Blank/generic fixture; demonstrates harness integration, validates INTEGRATION.md commands work |
| Integration verification | `examples/sample-project/verify.sh` | script | Checks that skills, hooks, and guidelines are properly integrated |
| Python fixture | `examples/python-project/` | project | Realistic Python consumer (pre-existing `.gitignore`); CI-verified across all install modes |
| TypeScript fixture | `examples/typescript-project/` | project | Realistic TypeScript consumer (pre-existing `.gitignore`); CI-verified across all install modes |
| Go fixture | `examples/go-project/` | project | Realistic Go consumer (pre-existing `.gitignore`); CI-verified across all install modes |
| npm package manifest | `package.json` | config | `files` allowlist for `npm publish`; `bin.agentharness` entry point; see `docs/RELEASING.md#npm-distribution` for what's built vs. not-yet-published |
| npm CLI shim | `bin/cli.js` | script | Execs `tools/setup/harness-link.sh` from an npm/npx install; fails clearly if `bash`/`python3` are missing |
| Symlink materializer | `tools/release/materialize-skill-symlinks.py` | script | `prepack`/`postpack` hook — npm tarballs don't preserve symlinks, so bundled-resource symlinks (e.g. `agentic-loops`'s) are copied to real files before packing, then restored via `git checkout` |
| Manifest source of truth | `manifest.yaml` | config | Structured source MANIFEST.md is generated from (B2) — edit this, not MANIFEST.md directly |
| MANIFEST.md generator | `tools/generate-manifest.py` | script | Renders MANIFEST.md from manifest.yaml; drift-checked in CI the same way tools/generate-agents-md.sh is (B2) |

## GitHub Configuration

| Asset | Path | Type | Purpose |
|---|---|---|---|
| Dependency updates | `.github/dependabot.yml` | config | Automated dependency version checking (Go, GitHub Actions) |
| Code ownership | `.github/CODEOWNERS` | config | Review routing and ownership for framework components |
| Scheduled link check | `.github/workflows/link-check-scheduled.yml` | workflow | Weekly online external-link validation, separate from the offline PR gate (P1-08) |
| Release workflow | `.github/workflows/release.yml` | workflow | Runs `npm publish` on a `v*` tag push; inert until `NPM_TOKEN` secret exists (P2-03) |
| Markdownlint config | `.markdownlint-cli2.yaml` | config | Rules enforced in CI's content-quality job; documents why purely-stylistic rules are off (P1-08) |
| Content-quality checker | `tools/verify-content-quality.py` | script | YAML validity, skill frontmatter schema, tested Python/bash/console-snippet syntax (P1-08, B3); `AGENTS.md` sync (P2-02); duplicate-policy number detection (B7); `MANIFEST.md` sync (B2) |
| Content-quality checker tests | `tools/tests/test_verify_content_quality.py` | tests | Tests for `check_duplicate_policy_numbers()` (real conflicts vs. measured-result/cross-reference/fenced-example false positives, B7) and `check_bash_snippets()`/`check_console_snippets()` (real syntax errors caught, B3) |
| AGENTS.md generator | `tools/generate-agents-md.sh` | script | Builds Codex's routing-only `AGENTS.md` from `CLAUDE.md` plus a name+description skill index (P2-02, redesigned P0-06 — full skill bodies load on demand from `.agents/skills/` instead) |
| Shared adapter-generator library | `tools/lib/adapter-common.sh` | script | Common helpers (heading demotion, frontmatter extraction, skill-index rendering, CLI-arg parsing) shared by every client-adapter generator instead of duplicated five times (cross-platform parity) |
| GEMINI.md generator | `tools/generate-gemini-md.sh` | script | Builds Gemini CLI's/Antigravity's routing-only `GEMINI.md` from `CLAUDE.md` plus a name+description skill index, same shape as `AGENTS.md` (cross-platform parity) |
| GitHub Copilot instructions generator | `tools/generate-copilot-instructions.sh` | script | Builds `.github/copilot-instructions.md` (routing rules + skill index) plus one `.github/instructions/<lang>.instructions.md` per `languages/<lang>/CONVENTIONS.md`, reusing that file's own `applyTo`/`description` frontmatter (cross-platform parity) |
| Kilo Code rules generator | `tools/generate-kilo-rules.sh` | script | Builds Kilo Code's auto-discovered `.kilo/rules/agentharness.md` from `CLAUDE.md` plus a name+description skill index, same shape as `AGENTS.md` (cross-platform parity) |
| Cursor rules generator | `tools/generate-cursor-rules.sh` | script | Builds Cursor's `.cursor/rules/agentharness-router.mdc` (always-on) plus one `.cursor/rules/<skill-name>.mdc` per skill (full body, no Agent Skills support to delegate to) — the one structurally different adapter (cross-platform parity) |
| Codex custom-agent generator | `tools/generate-codex-agents.sh` | script | Ports `.claude/agents/*.md` subagent definitions to Codex's TOML sub-agent-delegation format (`.codex/agents/*.toml`) — a different mechanism from `generate-agents-md.sh`'s routing/skill-index file; tool/permission scoping deliberately not translated (unverified per-platform) |
| OpenCode custom-agent generator | `tools/generate-opencode-agents.sh` | script | Ports `.claude/agents/*.md` subagent definitions to OpenCode's Markdown+YAML custom-agent format (`.opencode/agents/*.md`) |
| Cursor custom-agent generator | `tools/generate-cursor-agents.sh` | script | Ports `.claude/agents/*.md` subagent definitions to Cursor's own subagent format (`.cursor/agents/*.md`) — distinct from `generate-cursor-rules.sh`'s `.cursor/rules/*.mdc` (that ports skills, not custom agents) |
| Kilo Code custom-agent generator | `tools/generate-kilo-agents.sh` | script | Ports `.claude/agents/*.md` subagent definitions to Kilo Code's custom-subagent format (`.kilo/agents/*.md`) — distinct from `generate-kilo-rules.sh`'s routing rules file |
| GitHub Copilot custom-agent generator | `tools/generate-copilot-agents.sh` | script | Ports `.claude/agents/*.md` subagent definitions to Copilot's own custom-agent format (`.github/agents/*.agent.md`) — genuine isolated-context sub-agent delegation, distinct from `generate-copilot-instructions.sh`'s routing/skill mechanism; an earlier research pass wrongly classified Copilot as persona-only, corrected the same day (see docs/CLIENT_COMPATIBILITY.md) |
| Gemini CLI custom-agent generator | `tools/generate-gemini-agents.sh` | script | Ports `.claude/agents/*.md` subagent definitions to Gemini CLI's own custom-subagent format (`.gemini/agents/*.md`) — genuine isolated-context sub-agent delegation, distinct from `generate-gemini-md.sh`'s routing/skill mechanism; an earlier research pass wrongly classified Gemini CLI as having no delegation at all, corrected the same day (see docs/CLIENT_COMPATIBILITY.md) |

## Meta

| Asset | Path | Type |
|---|---|---|
| Repo overview | `README.md` | doc |
| Agent-facing router + mandatory rules | `CLAUDE.md` | doc (loaded every session — kept short on purpose) |
| Codex routing rules (generated; skills load on demand from `.agents/skills/`) | `AGENTS.md` | doc (generated by `tools/generate-agents-md.sh`; do not hand-edit) |
| Gemini CLI/Antigravity routing rules (generated; skills load on demand from `.agents/skills/`) | `GEMINI.md` | doc (generated by `tools/generate-gemini-md.sh`; do not hand-edit) |
| GitHub Copilot repo-wide instructions (generated; skills load on demand from `.agents/skills/`) | `.github/copilot-instructions.md` | doc (generated by `tools/generate-copilot-instructions.sh`; do not hand-edit) |
| GitHub Copilot path-scoped instructions (generated; one per language guide, `applyTo`-scoped) | `.github/instructions/` | doc (generated by `tools/generate-copilot-instructions.sh`; do not hand-edit) |
| Kilo Code rules (generated; skills load on demand from `.agents/skills/`) | `.kilo/rules/agentharness.md` | doc (generated by `tools/generate-kilo-rules.sh`; do not hand-edit) |
| Cursor rules (generated; one always-on router plus one full-body rule per skill) | `.cursor/rules/` | doc (generated by `tools/generate-cursor-rules.sh`; do not hand-edit) |
| Codex custom agents (generated; ported from .claude/agents/, tool/permission scoping not translated) | `.codex/agents/` | doc (generated by `tools/generate-codex-agents.sh`; do not hand-edit) |
| OpenCode custom agents (generated; ported from .claude/agents/) | `.opencode/agents/` | doc (generated by `tools/generate-opencode-agents.sh`; do not hand-edit) |
| Cursor custom agents (generated; ported from .claude/agents/, distinct from .cursor/rules/) | `.cursor/agents/` | doc (generated by `tools/generate-cursor-agents.sh`; do not hand-edit) |
| Kilo Code custom agents (generated; ported from .claude/agents/, distinct from .kilo/rules/) | `.kilo/agents/` | doc (generated by `tools/generate-kilo-agents.sh`; do not hand-edit) |
| GitHub Copilot custom agents (generated; ported from .claude/agents/, distinct from .github/copilot-instructions.md) | `.github/agents/` | doc (generated by `tools/generate-copilot-agents.sh`; do not hand-edit) |
| Gemini CLI custom agents (generated; ported from .claude/agents/, distinct from GEMINI.md) | `.gemini/agents/` | doc (generated by `tools/generate-gemini-agents.sh`; do not hand-edit) |
| Architecture / design philosophy | `docs/ARCHITECTURE.md` | doc |
| Architecture decision log (compact, retroactive) | `docs/DECISIONS.md` | doc |
| Project bootstrap and deterministic policy design (approved; not implemented) | `docs/superpowers/specs/2026-07-14-project-bootstrap-policy-design.md` | design specification |
| Project bootstrap implementation master plan (planned; not implemented) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-master-plan.md` | implementation plan |
| Project bootstrap acceptance and evidence matrix | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md` | acceptance plan |
| Project bootstrap Slice 1 plan (core, schema, lifecycle, runtime) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-1-core.md` | implementation plan |
| Project bootstrap Slice 2 plan (plugin SDK and Python plugin) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-2-plugins.md` | implementation plan |
| Project bootstrap Slice 3 plan (policy compiler, gates, evidence) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-3-policy.md` | implementation plan |
| Project bootstrap Slice 4 plan (core quality modules and integrations) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-4-quality.md` | implementation plan |
| Project bootstrap Slice 5 plan (GitHub protection and completion) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-5-github.md` | implementation plan |
| Project bootstrap Slice 6 plan (dogfood and release proof) | `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-6-dogfood.md` | implementation plan |
| Integration instructions | `docs/INTEGRATION.md` | doc |
| Client compatibility matrix (always-on instructions + on-demand skills, per agentic tool) | `docs/CLIENT_COMPATIBILITY.md` | doc |
| 5-minute scripted demo (real commands, real output) | `docs/DEMO.md` | doc |
| Planned-but-not-built components | `ROADMAP.md` | doc |
| Current status (what works today, single snapshot) | `docs/STATUS.md` | doc |
| Known limitations (open gaps and caveats, single list) | `docs/KNOWN_LIMITATIONS.md` | doc |
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
