# Changelog

No version has been tagged yet — see "Why no v0.1.0 yet" below. This file
tracks notable changes in the meantime so the eventual first tag has a
real history behind it instead of a single squashed "initial" commit.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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

## Why no v0.1.0 yet

A version tag is a promise: "this is what agentharness looked like at a
point worth remembering." Tagging before the P0/P1 accuracy and
consistency fixes above would have meant the first tagged version was
known-broken — phantom directories in the docs, a hook that blocked
every fresh repo's first commit, contradictory coverage thresholds. The
first tag will land once this file's Unreleased section reflects a
state worth pinning to, not before.
