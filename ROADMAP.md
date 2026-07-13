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

- **Profile-enforcement wiring in `.github/hooks/pre-push`.** Not started.
  `patterns/profiles/` defines `.agentharness-profile` (prototype/internal/
  production) as a lookup a project or agent can consult, but no script
  reads it yet. The hook currently only ever runs *this* repo's own
  hardcoded test suites and no-ops for a consumer's push, so there's
  nothing for a profile to gate there today. Wiring this up depends on
  the hook (or a successor lifecycle CLI) first learning to discover and
  run a *consumer's own* test suite — do both together, not the gate
  alone with nothing real to enforce.

- **Duplicate-policy detection in CI (part of P1-08).** Not started.
  The rest of P1-08's content-quality gate is implemented (`git diff
  --check`, markdownlint, YAML/frontmatter validation, tested-snippet
  syntax checks — see `.github/workflows/ci.yml`'s `content-quality` job).
  Automated detection of the *same rule restated with a different number*
  across docs (this repo's actual "one source of truth per rule" bug
  class) was originally deferred until after P1-10 consolidated the
  testing/logging policy docs. P1-10 and P2-06 (the encyclopedia-reduction
  pass) are both now done, so the blocking condition is resolved, but the
  detector itself is still unbuilt — see
  `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md` for the
  scoping question this needs before work starts (still needs to avoid
  hard-failing on legitimate cross-references vs. an allow-list too
  narrow to catch anything new).

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
