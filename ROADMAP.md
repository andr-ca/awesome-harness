# Roadmap

This file holds the **target** shape of the repo — components that are
planned but don't exist yet. Nothing in this file should be treated as
available. If you're an agent reading this to decide whether to symlink,
copy, or reference something: **check the actual directory first.** This
file describes intent, not inventory.

See [MANIFEST.md](MANIFEST.md) for what actually exists today.

## Planned Components

### `.claude/agents/`
Custom agent definitions for specialized tasks (code explorers, architects,
reviewers, debuggers). Not started.

### `.claude/hooks/`
Claude Code event hooks (as distinct from git hooks in `.github/hooks/`).
Not started.

### `.codex/`
Configuration for OpenAI Codex CLI, mirroring what `.claude/` does for
Claude Code (a directory of Codex-specific config/tooling, distinct from
the single generated `AGENTS.md` adapter at the repo root — see
`tools/generate-agents-md.sh`, P2-02). Not started. (Earlier drafts of
this repo mislabeled this as "Anthropic Codex" — Codex is an OpenAI
product; any future `.codex/` content should not imply Anthropic
affiliation.)

### `frameworks/{vue,angular,django,express,go}/`
Framework-specific config templates, patterns, and examples. Not started
for these frameworks. `frameworks/react/CONVENTIONS.md` is implemented
(P1-09) — component naming and props typing, split out of
`languages/typescript/CONVENTIONS.md` so the language guide isn't
React-specific.

### `languages/{rust,java,...}/`
Additional language convention guides, following the shape of the
existing `languages/{python,typescript,go}/`. Python, TypeScript, and Go
are implemented; Rust and others are not started.

### `patterns/{api-design,accessibility}/`
Additional pattern categories, following the shape of the existing
`patterns/{testing,logging,agentic-loops,error-handling,profiles}/`.
Those five exist today; API design and accessibility are not started.

A genuine cross-framework accessibility pattern doc is a real gap — an
earlier draft (`accessibility.instructions.md`) was removed because it
was entirely VS Code source-internal (`AccessibleContentProvider`,
`CONTEXT_ACCESSIBILITY_MODE_ENABLED`, references to specific VS Code
PRs) despite claiming general applicability. A real version needs to be
written from ARIA/WCAG fundamentals, not adapted from one codebase's
internal APIs.

### `tools/{lint,build,deploy}/`
Standalone per-language lint/build/deploy utility scripts — not started.
This repo's own tooling is implemented, though: `tools/setup/harness-link.sh`
(lifecycle CLI), `tools/check.sh` (single local verification entrypoint),
`tools/verify-manifest.sh`, and `tools/verify-content-quality.py`, plus
`.github/hooks/{prevent-trunk-commit,pre-push}`. See
[MANIFEST.md](MANIFEST.md) for the complete, current list.

### `.github/workflows/`
Reusable CI workflows for consuming projects. Not started. This repo's own
CI (markdown link check, shellcheck, hook tests) is implemented in `ci.yml`.

### `dependabot.yml`, `CODEOWNERS`
Implemented: `.github/dependabot.yml` (Go modules + GitHub Actions updates)
and `.github/CODEOWNERS` (review routing for framework/GitHub config areas).

### Claude Code Skills (`.claude/skills/`)
Implemented: `committing`, `branching`, `python-conventions`,
`error-handling`, `agentic-loops`, `audit-review-followup`, each with
full frontmatter, loading on demand. More language/pattern skills can
follow the same template.

## Explicitly Deferred / Needs a Decision

- ~~Sample integration project~~ — **IMPLEMENTED** (item 23, expanded
  under P1-05). `examples/sample-project/` (blank/generic) is validated
  by CI's `sample-project-integration` job against link mode +
  `--with-hook`. `examples/{python,typescript,go}-project/` (each with a
  realistic pre-existing `.gitignore`) are validated by the
  `fixture-matrix` job across all three install modes (link/copy/
  submodule) plus `doctor`/`status`/`update`/`uninstall` — not just
  install-and-check. Finding this gap live is what turned up the
  --mode copy bundled-resource-symlink bug fixed alongside P1-05.

- ~~Logging config loader~~ — **IMPLEMENTED** (item 12). Python utility
  `config_loader.py` with tests for loading YAML configs with `${VAR:-default}`
  environment variable interpolation. Documentation integrated into
  `LOGGING_STANDARDS.md`.

- **Profile-enforcement wiring in `.github/hooks/pre-push`, and
  non-Python enforcement.** Partially done. `harness-link.sh
  enforce-profile` (B4) reads `.agentharness-profile` and gates on it
  for real, but only for detected Python projects
  (`pytest --cov-fail-under` at the selected tier's `coverage_min`) —
  Go, TypeScript, and other project types still get "not implemented
  yet" and a clean exit 0. Also still not started: wiring
  `enforce-profile` into `.github/hooks/pre-push` itself. The hook
  currently only ever runs *this* repo's own hardcoded test suites and
  no-ops for a consumer's push; changing that default for every project
  that already has `--with-hook` installed is its own decision, kept
  separate from shipping the enforcement logic itself (see
  `patterns/profiles/README.md`'s "Current state").

- ~~Duplicate-policy detection in CI (part of P1-08).~~ — **IMPLEMENTED**
  (B7). `check_duplicate_policy_numbers()` in
  `tools/verify-content-quality.py` flags a numeric mandate (currently:
  the test-coverage percentage) restated with a *different* number
  outside its source of truth, using a small extensible registry rather
  than general-purpose duplicate-content detection. Deliberately does
  **not** flag every restatement of the *same* number (e.g.
  `patterns/testing/COMPLETION_CHECKLIST.md`'s dozen legitimate "80%"
  mentions) — only a genuine conflict, which is unambiguous regardless of
  phrasing. Non-numeric policy-restatement detection (e.g. the
  trunk/main-commit prohibition) remains unbuilt; a "different number"
  isn't a meaningful concept for a binary rule, so it needs a different
  detection approach, not an extension of this one.

- **P2-05 (real dogfood) has no target.** Confirmed still not done as of
  the 2026-07-13 re-audit (`gpt-5.6-completion-reaudit.md`): no evidence
  the harness is pinned and used in a real, non-fixture project. This
  isn't a coding task — it means picking at least one real repo (ideally
  not this session's author's own) to adopt `harness-link.sh init`
  against and letting friction surface over real use, then feeding
  findings back. Tracked here so it isn't silently dropped between status
  snapshots; see
  `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`.

- **P0-03's remote-write authorization model is unresolved.** Flagged as
  a missed gap by the 2026-07-13 re-audit: `CLAUDE.md`'s Agent Workflow
  Completion section still mandates commit/push/PR for every finished
  task by default, with no opt-in profile that keeps an agent
  inspection/review-only. This is a product-direction change (it alters
  the harness's default trust model), not a scoped fix — see
  `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md` for the
  scoping question posed to the user before any change is made.
