# Contributing

Thanks for looking at agentharness. This is a small, single-maintainer
project — the process below is intentionally lightweight.

## Before you start

1. Check [MANIFEST.md](MANIFEST.md) — don't duplicate an existing asset.
2. Check [ROADMAP.md](ROADMAP.md) — some things are deliberately not
   built yet; if you want to build one, open an issue first so the
   scope's agreed before you invest the time.
3. For anything bigger than a small fix (a new skill, a new language
   guide, a new pattern category), open an issue describing the shape
   of it before sending a PR — see "One source of truth per rule" in
   [CLAUDE.md](CLAUDE.md): duplicating or contradicting existing
   guidance is worse than not adding it.

## Making a change

1. Branch off `main` — see
   [.github/BRANCHING_STRATEGY.md](.github/BRANCHING_STRATEGY.md) for
   naming (`feature/`, `fix/`, `docs/`, …). Never commit directly to
   `main`; branch protection enforces this for everyone but repo admins.
2. New content gets a real usage example, not just a description.
   Skills need frontmatter — see any file in `.claude/skills/` for the
   shape.
3. Run `bash tools/check.sh` before opening a PR. It runs everything CI
   runs: shellcheck (if installed locally), bats suites, ruff, mypy,
   pytest with coverage gates, `verify-manifest.sh`, markdownlint, and
   `verify-content-quality.py`. Requires `python3`,
   `pip install -r requirements-dev.txt`, and `npx` (markdownlint-cli2
   downloads on first use).
4. Add an entry to [MANIFEST.md](MANIFEST.md) for anything new.
5. Open a PR against `main` — the template will prompt for a summary,
   motivation, and testing notes.

## Review

This repo currently has one maintainer (`@andr-ca`, per
[.github/CODEOWNERS](.github/CODEOWNERS)), who reviews every PR. See
[SECURITY.md](SECURITY.md#the-instruction-attack-surface) for why changes
to `CLAUDE.md` or any `SKILL.md` get particular scrutiny: those files are
instructions an agent acts on directly in every consuming project, not
just code that runs in this repo.

## Reporting a bug

Open an issue — use the bug report template if one fits, or just
describe what happened vs. what you expected. For a bug in a hook or
setup script specifically, see
[SECURITY.md](SECURITY.md#if-you-find-a-bug-in-the-hook-script-or-setup-script).

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
