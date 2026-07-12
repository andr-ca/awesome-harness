# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).
See [docs/RELEASING.md](docs/RELEASING.md) for what moves an `Unreleased`
section into a tagged version.

## [Unreleased]

Everything below has landed on `main` or is in open PRs since `v0.1.0`;
none of it has been cut into a tagged release yet (see
[docs/RELEASING.md](docs/RELEASING.md) for why — currently `main`'s own
CI needs to be green before the next tag).

### Added
- `CLAUDE.md` mandates for agent workflow completion (verify, commit,
  push, PR — never leave work uncommitted) and recommendation assessment
  (implement scoped low-risk fixes directly; get confirmation before a
  batch that amounts to a roadmap; escalate anything high-risk).
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
