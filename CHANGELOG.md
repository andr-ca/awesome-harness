# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).
See [docs/RELEASING.md](docs/RELEASING.md) for what moves an `Unreleased`
section into a tagged version.

## [Unreleased]

### Added
- `harness-link.sh enforce-profile` gates Python, Go, and JS/TS projects.
  JS/TS covers Node's built-in `node --test` and Vitest
  (`coverage-summary.json`); Go uses `go test -coverprofile` and
  `go tool cover`. Jest/Mocha and unrecognized project types get an
  honest "not implemented" and exit 0 — or fail under the new `--strict`
  flag, so CI
  can require full coverage of the projects it gates.
- `harness-link.sh generate-clients <project> [--client …]` — runs the
  client-adapter generators into a consumer project in one command
  (AGENTS.md, GEMINI.md, Copilot, Cursor, Kilo) instead of the
  per-generator manual steps (P1-01 first increment).
- `tools/verify-skill-symlinks.sh` — verifies `.agents/skills/` stays 1:1
  with `.claude/skills/`, so a missing/broken symlink can't silently hide
  a skill from Agent-Skills-standard tools. Wired into `check.sh` + CI.
- `languages/rust/CONVENTIONS.md` (Rust guide, plus generated
  `rust.instructions.md`) and `patterns/accessibility/README.md` (a
  WCAG 2.2 / ARIA baseline).
- `docs/STATUS.md` and `docs/KNOWN_LIMITATIONS.md` — single current-state
  and open-gaps entry points.
- `tools/eval/.env.sample`, a documented instruction-quality (P2-03) eval
  plan, and `docs/operational/planning/DOGFOODING.md` (dogfood plan +
  tracking template).
- `AGENTHARNESS_SUBMODULE_REMOTE` override and `tools/check.sh --offline`
  for hermetic, network-free test runs (P1-05); lifecycle-transition
  tests (P1-06).
- Expanded worktree guidance (parallel-agent workflow, shared-hooks
  caveat) in the `branching` skill + `BRANCHING_STRATEGY.md`.
- Agent workflow: reviewers' comments must now be answered on the PR
  thread with an assessment + action taken, not only in a commit message
  or status file.

### Changed
- `enforce-profile` documentation corrected across `CODING_GUIDELINES.md`,
  `patterns/profiles/README.md`, `STATUS.md`, and the compatibility
  matrix to reflect the Go/Vitest/`--strict` reality.

### Fixed
- Four profile/workflow documentation contradictions (P1-03) and six
  stale `docs/CLIENT_COMPATIBILITY.md` cells that marked built adapters
  (Gemini/Copilot/Cursor/Kilo) as not existing yet.

## [0.2.0] - 2026-07-13

### Added
- npm as a distribution channel: `package.json`, `bin/cli.js` (CLI shim
  execing `harness-link.sh`), and `.github/workflows/release.yml` (runs
  `npm publish` on a `v*` tag push) — built and tested end-to-end
  (`npm pack` → unpack → run) via CI's `npm-package` job, including a
  prepack/postpack symlink-materialization step so npm tarballs (which
  don't preserve symlinks) still ship the `agentic-loops` skill's bundled
  `agent_loop.py` correctly. Not yet actually published — no npm
  account/org or `NPM_TOKEN` secret exists (see `docs/DECISIONS.md`).
- A deterministic eval suite (`tools/eval/`) — task/scoring/orchestration
  infrastructure proving the harness *can* be measured against real
  tasks, with a free, fully-tested fake standing in for live agent
  invocation (`invoke_agent_via_api()` intentionally raises
  `NotImplementedError`; no eval results exist yet — see
  `docs/DECISIONS.md`).
- An `AGENTS.md` adapter for Codex, generated from `CLAUDE.md` +
  `.claude/skills/` by `tools/generate-agents-md.sh` (not hand-written,
  so it can't drift) — CI drift-checks it but it has not been verified
  against a real Codex CLI session; documented as best-effort only.
- An opt-in publish-authority flag (`.agentharness-publish-mode`,
  gitignored, per-operator): the harness's default agent behavior is now
  verify-and-stage-only — commit locally, then stop and ask before
  pushing, opening a PR, or auto-implementing a recommendation. Full
  publish authority requires the flag file or explicit per-task
  instruction. See `CLAUDE.md`'s "Agent Workflow Completion" and
  `docs/INTEGRATION.md`'s "Publish Authority" section.
- `harness-link.sh enforce-profile <project>`: makes
  `.agentharness-profile` do something mechanical instead of being a
  lookup table nothing reads — for a detected Python project, gates on
  the selected tier for real (`pytest --cov-fail-under` at that tier's
  floor; skips entirely where `tests.required` is false). Other project
  types get a clear "not implemented yet" rather than a false pass.
  Invoked explicitly (same posture as `audit`/`doctor`), not wired into
  `pre-push` automatically.
- `harness-link.sh audit --json` now also reports whether the target's
  publish-authority flag is active, its selected profile, and whether
  the recorded harness checkout's own validation commands
  (`tools/check.sh`, `verify-content-quality.py`, ...) still exist —
  catching a doc that claims a script exists after it's been renamed or
  deleted upstream.
- Duplicate-policy detection in CI: `check_duplicate_policy_numbers()` in
  `tools/verify-content-quality.py` flags a numeric mandate (currently
  the test-coverage percentage) restated with a genuinely *different*
  number outside its source of truth, via a small, explicit, extensible
  registry rather than general-purpose duplicate-content detection —
  deliberately doesn't flag every same-number restatement, only real
  conflicts, after two more naive designs produced real false positives
  against this repo's own content during development.
- `MANIFEST.md` is now generated from a structured `manifest.yaml` source
  by `tools/generate-manifest.py` (mirroring the `AGENTS.md` generator
  pattern, including a CI drift-check) instead of hand-maintained prose —
  `tools/verify-manifest.sh` still validates the rendered file against
  the filesystem on top of that.
- Snippet-syntax validation extended from Python-only to bash and console
  blocks: `check_bash_snippets()` (docs/INTEGRATION.md,
  `COVERAGE_REQUIREMENTS.md`'s bc-based coverage comparison) and
  `check_console_snippets()` (docs/DEMO.md's `$`-prefixed command
  lines), both via `bash -n` syntax-only checks — same small-allowlist
  principle as the Python check, not an auto-classifier.
- `docs/DEMO.md` — a 5-minute scripted walkthrough with real,
  hand-verified commands and output; `docs/DECISIONS.md` — a compact,
  retroactive architecture-decision log.
- `CLAUDE.md` mandates for agent workflow completion (verify and commit
  locally, always — full publish authority per the opt-in flag above) and
  recommendation assessment (implement scoped low-risk fixes directly;
  get confirmation before a batch that amounts to a roadmap; escalate
  anything high-risk).
- Rigor-tier profiles as selectable YAML (`patterns/profiles/`), not
  just prose — Prototype/Internal/Production now have a machine-readable
  config, not only a table in `CODING_GUIDELINES.md`.
- A lifecycle CLI for `harness-link.sh`: `status`, `doctor`, `audit`,
  `update`, `uninstall` alongside the original `init`, so a consuming
  project can inspect and manage its integration instead of only ever
  running the initial install once.
- Consumer fixtures for all three install modes (link/copy/submodule)
  across Python, TypeScript, and Go sample projects, exercised by CI's
  `fixture-matrix` job — previously only one symlink-mode sample existed.
- Pinned dev/CI toolchain (`requirements-dev.txt`), a single local
  verification entrypoint (`tools/check.sh`), and a `content-quality` CI
  job (`git diff --check`, `markdownlint-cli2`, YAML/frontmatter/
  embedded-snippet validation via `tools/verify-content-quality.py`).
- `error-handling` and `agentic-loops` pattern guides, each with a real,
  tested reference implementation (not just prose) and matching Claude
  Code skills; `audit-review-followup` skill for re-scoring a past
  review against current repo state.
- `languages/typescript/`, `languages/go/`, and `frameworks/react/`
  (split out of the TypeScript guide) convention guides.
- A product contract in the README (target users, supported clients/
  platforms, what gets installed, advisory vs. enforced, non-goals).
- `docs/RELEASING.md` — versioning policy, release checklist, and a
  tested pin/rollback/upgrade demonstration
  (`tools/tests/harness-lifecycle.bats`).

### Changed
- `harness-link.sh` rewritten around a single lifecycle CLI shape
  (`init`/`plan`/`status`/`doctor`/`audit`/`update`/`uninstall`) recording
  state in `.agentharness-state.json`, instead of a one-shot install
  script with no memory of what it did.
- Rewrote `patterns/testing/README.md` from a ~464-line near-duplicate of
  the other testing docs into a short index; rescoped `TDD.md`,
  `COVERAGE_REQUIREMENTS.md`, `COMPLETION_CHECKLIST.md`, and
  `PLAYWRIGHT_UI_TESTING.md`'s "80% mandatory, no exceptions" language to
  the Production tier specifically, reconciling it with the rigor-tier
  table it previously contradicted.
- `docs/INTEGRATION.md` and `README.md` rewritten against what actually
  exists and what actually runs — tree diagram regenerated from
  `git ls-files`, HTTPS-primary clone instructions, per-skill symlink
  loops (not a stale 3-skill hardcoded list) verified in a clean scratch
  directory for every method (symlink/copy/submodule).
- Trimmed the language convention guides, logging docs, testing docs,
  `error-handling/README.md`, and `BRANCHING_STRATEGY.md` down to
  repo-specific decisions — cut generic, ecosystem-standard content that
  didn't need to live in this harness at all (an encyclopedia is a
  maintenance liability; a pointer to the real docs isn't).

### Fixed
- `harness-link.sh --mode submodule` recorded `source.path` as the dev
  checkout's own path instead of the submodule inside the consuming
  project, causing `update`/`audit` to report phantom drift; submodule
  add now pins to harness's exact commit instead of the remote's mutable
  default branch.
- CI supply-chain: pinned `bats-core` to its dereferenced commit SHA
  (was pointing at an annotated tag object's own SHA, which isn't a
  commit `actions/checkout` can use), pinned `markdownlint-cli2`, added a
  `--yes` non-interactive flag where the matrix job needed it.
- `docs/INTEGRATION.md`'s copy-mode example used `cp -r` (produces a
  dangling symlink for `agentic-loops/agent_loop.py`, since it copies the
  symlink instead of the file it resolves to) and a single-quoted
  heredoc that silently discarded its own `$(git rev-parse ...)`
  expansion — both reproduced, in docs, bugs already fixed in the real
  tool; fixed to `cp -rL` and an unquoted heredoc with a precomputed
  variable.
- Assorted shellcheck (SC2115, SC2034), whitespace, and markdown-lint
  violations caught only once CI actually gained the checks to catch
  them (`content-quality` job, local `shellcheck`/`git diff --check`).

## [0.1.0] - 2026-07-11

### Fixed
- `prevent-trunk-commit` hook: blocked the first commit of every fresh
  repo due to an unborn-branch bug (`git rev-parse --abbrev-ref HEAD`
  fails before any commit exists); switched to `git symbolic-ref`. Added
  `release/*` prefix matching to match the documented branch convention.
  Covered by `.github/hooks/tests/prevent-trunk-commit.bats`.
- Removed a dozen broken or non-functional shell snippets across
  `docs/`, `.github/BRANCHING_STRATEGY.md`, and `patterns/testing/` (bad
  symlink targets, wrong BFG syntax, a Go coverage check that crashed on
  floats, an invalid Python refactor example, duplicated `.gitignore`
  templates with contradictory advice).
- `.github/.gitignore.template` was ignoring `go.sum`, `lib/`, `vendor/`,
  and version-pin files (`.nvmrc`, `.python-version`, …) that should be
  committed for reproducible builds.
- Reconciled three conflicting coverage-tier tables (one had an
  off-by-one split at 79% instead of 75%) into a single source of truth
  in `COVERAGE_REQUIREMENTS.md`.
- Reconciled a genuine contradiction between "one comprehensive
  assertion" and "one assertion per test" testing guidance.

### Added
- `MANIFEST.md` — accurate index of every real asset in the repo.
- `ROADMAP.md` — aspirational directory structure moved here, clearly
  labeled as not-yet-built (previously presented as current state).
- `LICENSE` (MIT).
- `SECURITY.md` — secrets-in-history procedure.
- Rigor tiers in `CODING_GUIDELINES.md` (Prototype / Internal Tool /
  Production Service) — reconciles the doc's minimalism principles with
  its 80%-coverage/Playwright/OTEL mandates, which previously applied
  uniformly with no scale-down path.
- `.claude/skills/{committing,branching,python-conventions}/` — the
  first real Claude Code skills in the repo, loaded on demand instead of
  via manual copy/symlink.
- `tools/setup/harness-link.sh` — one-command project integration.
- `.github/workflows/ci.yml` — shellcheck, hook tests (bats), markdown
  link check. The repo mandates CI for consuming projects but had none
  of its own until now.
- Concrete mechanisms for two previously-unenforceable mandates:
  screenshot-approval (`PLAYWRIGHT_UI_TESTING.md`) and
  logging-verification (`LOGGING_STANDARDS.md`) now specify what to
  actually do and record, not just "must be reviewed."

### Changed
- Repository renamed `awesome-harness` → `agentharness` (the `awesome-*`
  prefix conventionally signals a curated link list on GitHub; this is a
  toolkit).
- `CLAUDE.md` slimmed from ~450 lines of prose to a short router — it's
  loaded into every session of every consuming project, so its size is a
  per-task cost.
- Standardized on `.env.sample` over `.env.example` repository-wide.
- Branch protection enabled on `main` (PRs required; admin bypass left
  open).

### Removed
- `.github/accessibility.instructions.md` — was entirely VS Code
  source-internal (`AccessibleContentProvider`,
  `CONTEXT_ACCESSIBILITY_MODE_ENABLED`, a specific VS Code PR number)
  despite claiming general applicability. Noted as a real gap in
  `ROADMAP.md` rather than silently dropped.
- Fabricated before/after statistics ("~95% of bugs prevented," "0
  failed deployments") from four docs.
- Hand-written "Last Updated" date lines (18 files) — git already tracks
  this, and the hand-maintained dates had all drifted to the same value
  regardless of actual last edit.
