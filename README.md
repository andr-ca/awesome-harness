# agentharness

[![CI](https://github.com/andr-ca/agentharness/actions/workflows/ci.yml/badge.svg)](https://github.com/andr-ca/agentharness/actions/workflows/ci.yml)

Portable engineering policies for coding agents — git, testing, logging,
and language conventions written once and referenced everywhere, instead
of re-authored (and drifting) in every project's own `CLAUDE.md`.

## Purpose

Every project accumulates its own CLAUDE.md, commit conventions, and CI
rituals; drift between projects is real and costly. This repo is the
single source of truth for that shared context — read once here, referenced
(not copy-pasted-and-forgotten) from every consuming project.

**Status:** early. See [MANIFEST.md](MANIFEST.md) for what actually exists
today and [ROADMAP.md](ROADMAP.md) for what's planned but not built. Don't
trust a directory tree in prose — trust the manifest.

### Why not just CLAUDE.md?

A single project's `CLAUDE.md` works fine — until there's a second
project, and its `CLAUDE.md` quietly diverges: a different coverage bar,
a branch-naming rule that contradicts the first repo's, a logging
convention nobody remembers deciding. Multiply by N projects and the
conventions aren't really policies anymore, just N independent guesses
that happen to overlap. agentharness is the fix for that specific
problem: one `CLAUDE.md` router plus a set of skills and convention docs
that every project's own (short) `CLAUDE.md` *references* — see
[docs/INTEGRATION.md](docs/INTEGRATION.md). You still write a
project-specific `CLAUDE.md`; it just stops being where the shared rules
live.

**Before** (two real projects, each with their own copy-pasted-and-drifted rules):

```markdown
<!-- project-a/CLAUDE.md -->
## Testing
Aim for 80% coverage. Use pytest. Don't mock the database.

<!-- project-b/CLAUDE.md, written six months later by someone else -->
## Testing
Try to keep coverage reasonable (70%+ ok for now). pytest preferred.
```

Neither number is *wrong* on its own — but now there are two "the
policy," a reviewer moving between repos has to remember which applies
where, and nobody can say which one is actually current.

**After** (both projects reference the same source instead of restating it):

```markdown
<!-- project-a/CLAUDE.md and project-b/CLAUDE.md, identical on this point -->
## Testing
See agentharness's `patterns/testing/COVERAGE_REQUIREMENTS.md` for the
coverage bar by rigor tier. This project is Production tier.
```

One number, one place it can drift from — see
`patterns/testing/COVERAGE_REQUIREMENTS.md` for what that file actually
says today. Updating the bar means editing agentharness once; every
project referencing it picks up the change the next time its harness
checkout syncs (see "Pin, Upgrade, Rollback" in
[docs/RELEASING.md](docs/RELEASING.md) for exactly when that happens per
install mode).

## Product Contract

**Target users:** teams or individuals running multiple projects with a
coding agent, who want git/testing/logging/language conventions written
once and referenced everywhere instead of re-authored (and drifting) per
project.

**Supported clients:** Claude Code is the only client this repo is
*tested* against — the skills under `.claude/skills/` and the
`CLAUDE.md` router are built for and dogfooded there. Structurally,
though, this harness now generates an always-on routing file plus a
skill index for every major agentic coding tool researched, since 6 of
7 non-Claude platforms (Codex, Gemini CLI/Antigravity, GitHub Copilot,
Kilo Code — OpenCode/Zed too, via the plain `AGENTS.md` they already
read) recognize `.agents/skills/` as an Agent-Skills-standard-compliant
path, the same directory `harness-link.sh` already populates for every
consumer. Cursor is the one platform with no confirmed Agent Skills
support, so it gets a structurally different generator instead
(`.cursor/rules/*.mdc`). None of this is a claim of end-to-end testing
outside Claude Code — every generated file says so, and
`docs/CLIENT_COMPATIBILITY.md` is the full per-platform matrix with
sources and caveats.

| Platform | Always-on file | Skill/rule mechanism | Status |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/skills/*/SKILL.md` | ✅ built + dogfooded |
| Codex CLI | `AGENTS.md` | `.agents/skills/*/SKILL.md` | ✅ built, not live-tested |
| OpenCode | `AGENTS.md` | `.agents/skills/*/SKILL.md` | ⚠️ passively covered |
| Zed | `AGENTS.md` | `.agents/skills/*/SKILL.md` | ⚠️ passively covered |
| Gemini CLI / Antigravity | `GEMINI.md` | `.agents/skills/*/SKILL.md` | ✅ built, not live-tested |
| GitHub Copilot | `.github/copilot-instructions.md` | `.github/instructions/*.instructions.md` (`applyTo` glob) + `.agents/skills/` | ✅ built, not live-tested |
| Kilo Code | `.kilo/rules/agentharness.md` | `.agents/skills/*/SKILL.md` | ✅ built, not live-tested |
| Cursor | `.cursor/rules/agentharness-router.mdc` (`alwaysApply: true`) | `.cursor/rules/<skill>.mdc` (full body, no Agent Skills support) | ✅ built, not live-tested |

Each generator is a manual-regeneration script
(`tools/generate-*.sh --output[-dir] ...`), not auto-wired into
`harness-link.sh init` — see each platform's section in
`docs/INTEGRATION.md` for the exact recipe.

The table above is always-on instructions + on-demand skills only. A
third, separate dimension — **custom agents that a primary agent can
delegate a task to**, rather than content the current agent loads
inline — has its own set of generators. This repo defines one real
subagent, `.claude/agents/coding-guidelines-reviewer.md` (a read-only
reviewer scoped to `.github/CODING_GUIDELINES.md`'s rigor tiers), and
ports it to every tool that supports genuine delegation:

| Target | Generator | Produces |
|---|---|---|
| Codex CLI | `tools/generate-codex-agents.sh` | `.codex/agents/*.toml` |
| OpenCode | `tools/generate-opencode-agents.sh` | `.opencode/agents/*.md` |
| Cursor | `tools/generate-cursor-agents.sh` | `.cursor/agents/*.md` (distinct from `.cursor/rules/*.mdc` above — a different Cursor feature) |
| Kilo Code | `tools/generate-kilo-agents.sh` | `.kilo/agents/*.md` |

Copilot, Gemini CLI, and Zed only offer persona/tool-scope switching for
the same agent, not true delegation — nothing to port to there. **None
of these four generators translate tool/permission scoping** (Claude
Code's `tools:` field, Cursor's `readonly`/`is_background`, Kilo's
`permission`) — that vocabulary is unverified per platform, so ported
files carry only `name`/`description`/`model`/body; re-specify the
tool/permission scope by hand for the target platform. See
`docs/CLIENT_COMPATIBILITY.md`'s "Custom agents / sub-agent delegation"
section for the full per-tool table and sources.

**Supported platforms:** Linux and macOS (Bash scripts, POSIX shell
conditionals, `bats-core` for shell tests). Windows is untested; WSL
should work but hasn't been verified.

**What gets installed** by `tools/setup/harness-link.sh init` (a
lifecycle CLI — also exposes `plan`/`status`/`doctor`/`audit`/`update`/
`uninstall`; see [docs/INTEGRATION.md](docs/INTEGRATION.md)) into a
consuming project:
- Selected (or all) `.claude/skills/<name>` directories, symlinked
  (`--mode link`, default for a `git clone` install), physically copied
  (`--mode copy`), symlinked from a git submodule this creates at
  `.agentharness` (`--mode submodule` — the one mode that does reach the
  network, to add that submodule), or symlinked from a durable local copy
  this creates at `.agentharness-pkg` (`--mode npm`, the default when
  installed via `npx`/`npm` — see "npm distribution" below for why `link`
  isn't safe there).
- A merge of `.github/.gitignore.template` into the project's `.gitignore`
  (additive — never overwrites existing entries).
- With `--with-hook`: `core.hooksPath` pointed at this repo's
  `.github/hooks/` (refuses to overwrite an existing, different
  `core.hooksPath` unless `--force` is passed — see
  `tools/tests/harness-link.bats`).
- A `.agentharness-state.json` recording mode, source revision, and
  installed skills, so `status`/`doctor`/`update`/`uninstall` know what
  they're working with.

Nothing else is installed. No telemetry, no background processes; no
network calls except the one submodule-mode clone above, which only
happens if you asked for that mode.

**Advisory vs. enforced:**
- *Advisory* (a convention the agent is expected to follow, not something
  that blocks anything): `CLAUDE.md`, the skill files under
  `.claude/skills/`, and every guide under `languages/` and `patterns/`.
  An agent (or a human) can ignore these; nothing stops them mechanically.
- *Enforced* (a script that actually blocks an action): the
  `prevent-trunk-commit` pre-commit hook (blocks direct commits to trunk
  branches), installed once a project opts in via `--with-hook`. The
  shared `pre-push` hook this repo installs on *itself* (blocks a push
  below 80% test coverage or a failing suite) only ever tests *this*
  repo's own suites, and no-ops for a consumer that's merely borrowed
  `core.hooksPath` (see `.github/hooks/pre-push`'s own comments) — for
  coverage enforcement in *your own* project, use
  `init --with-coverage-hook` instead, which generates a project-owned
  `pre-push` hook that runs `enforce-profile` against your project (P0-03).

**Agent publish authority is opt-in, not default.** `CLAUDE.md` has an
agent verify and stage work locally, then stop and ask before pushing,
opening a PR, or auto-implementing a recommendation — full authority to
do those requires a local `.agentharness-publish-mode` flag file (never
committed) or explicit per-task instruction. See
[docs/INTEGRATION.md](docs/INTEGRATION.md)'s "Publish Authority" section.

**Non-goals** — this project deliberately does not:
- Orchestrate or run agents itself (no agent loop, scheduler, or runtime
  lives here beyond the one tested reference example in
  `patterns/agentic-loops/`).
- Replace language-specific linters, formatters, or CI systems — it
  documents conventions for using them, not a competing implementation.
- Guarantee behavior on any agent harness other than Claude Code today
  (see "Supported clients" above).
- Auto-update a consuming project. The symlink mode means a project
  picks up changes when this repo's checkout changes, but nothing here
  pushes updates or reaches into a consumer uninvited.

## What's here today

This tree lists tracked files only (a fresh clone won't have empty
placeholder directories) — see [MANIFEST.md](MANIFEST.md) for the full,
current inventory with a one-line purpose per file; treat this as an
orientation map, not the source of truth.

```
agentharness/
├── README.md                    # This file
├── CLAUDE.md                    # Agent-facing router + mandatory rules
├── AGENTS.md                    # Codex routing rules, generated from CLAUDE.md (skills load on demand from .agents/skills/)
├── MANIFEST.md                  # Index of every real asset
├── ROADMAP.md                   # What's planned but not built yet
├── CHANGELOG.md                 # Release history
├── SECURITY.md                  # Secrets-in-history + instruction-attack-surface procedure
├── CONTRIBUTING.md              # Contribution workflow
├── CODE_OF_CONDUCT.md           # Contributor Covenant
├── requirements-dev.txt         # Pinned dev/CI toolchain
├── .markdownlint-cli2.yaml      # Markdown lint rules for CI
├── .github/
│   ├── BRANCHING_STRATEGY.md
│   ├── COMMITTING_GUIDELINES.md
│   ├── CODING_GUIDELINES.md
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/          # bug_report.md, feature_request.md
│   ├── .gitignore.template
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── workflows/               # ci.yml, link-check-scheduled.yml
│   └── hooks/                   # prevent-trunk-commit, pre-push (+ tests)
├── .claude/
│   └── skills/                  # committing, branching, python-conventions,
│                                 # error-handling, agentic-loops,
│                                 # audit-review-followup
├── languages/
│   ├── python/                  # CONVENTIONS.md, COPILOT_INSTRUCTIONS.md
│   ├── typescript/              # CONVENTIONS.md
│   └── go/                      # CONVENTIONS.md
├── frameworks/
│   └── react/                   # CONVENTIONS.md (add-on to the TS guide)
├── patterns/
│   ├── testing/                 # TDD, coverage, Playwright, completion checklist
│   ├── logging/                 # logging standards + example config + loader
│   ├── error-handling/          # retry, circuit-breaker, structured logging
│   ├── agentic-loops/           # tested agent-loop reference implementation
│   └── profiles/                # rigor-tier profiles (prototype/internal/production)
├── examples/                    # sample-project + python/typescript/go fixtures,
│                                 # each verified in CI across every install mode
├── tools/
│   ├── setup/harness-link.sh    # Lifecycle CLI: init/plan/status/doctor/audit/update/uninstall
│   ├── check.sh                 # One local entrypoint for every CI check
│   ├── verify-manifest.sh       # This file's own accuracy check
│   ├── verify-content-quality.py
│   └── tests/                   # bats tests for harness-link.sh
└── docs/
    ├── ARCHITECTURE.md
    ├── INTEGRATION.md
    ├── RELEASING.md              # Versioning policy, release checklist, pin/upgrade/rollback
    └── operational/              # working notes, review history
```

Everything else you might expect (more `frameworks/`, more `languages/`,
`.claude/agents/`, `.codex/`) is intentionally not here yet — see
[ROADMAP.md](ROADMAP.md).

## Quick Start

**Prerequisites:** `git`, `bash`, `python3` (used to read/write the
lifecycle CLI's state file). See "Supported platforms" above.

```bash
git clone https://github.com/andr-ca/agentharness.git ~/agentharness
```

(Or `git@github.com:andr-ca/agentharness.git` if you have SSH access set
up and prefer it — HTTPS works with no additional setup, which is why
it's the default above.)

Integrate into a project with the setup script (installs skills, merges
the gitignore template, and — if you opt in via `--with-hook` — the
trunk-protection hook; `--with-coverage-hook` adds a generated
coverage-enforcing pre-push hook on top of that):

```bash
~/agentharness/tools/setup/harness-link.sh init /path/to/your-project
```

Preview what that would do without changing anything: add `--dry-run` (or
run `plan` instead of `init`). Verify afterward with
`~/agentharness/tools/setup/harness-link.sh doctor /path/to/your-project`.

Or by hand — see [docs/INTEGRATION.md](docs/INTEGRATION.md) for the
symlink/copy/submodule/npm tradeoffs, troubleshooting, and
update/uninstall. See [docs/DEMO.md](docs/DEMO.md) for a 5-minute
walkthrough with real commands and real output — what `init` actually
installs, and what the enforced trunk-protection hook looks like when it
fires.

**npm, as an alternative to `git clone`:** `npx agentharness-toolkit init /path/to/your-project`
runs the same lifecycle CLI without a separate clone step (still needs
`bash`/`python3` on your machine; installed globally, the CLI command
itself is just `agentharness`). This defaults to `--mode npm`, which
copies the package into a durable `.agentharness-pkg` directory inside
your project before linking skills from it — not `--mode link` straight
into the npx cache, which would break the next time npx cleans that
cache up. See
[docs/RELEASING.md#npm-distribution](docs/RELEASING.md#npm-distribution)
for the package's current publish status.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow (branching,
local verification, review routing). Short version: check
[MANIFEST.md](MANIFEST.md) before adding anything, run
`bash tools/check.sh` before opening a PR, and go through a feature
branch — never commit directly to `main`. This project follows the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

See [LICENSE](LICENSE).
