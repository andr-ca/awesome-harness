# Current Status

A single, maintained snapshot of **what actually works in this repo
today** — so you don't have to reconstruct it from
[MANIFEST.md](../MANIFEST.md) (asset inventory),
[ROADMAP.md](../ROADMAP.md) (what's *not* built), and the dated review
notes under [docs/operational/reviews/](./operational/reviews/) all at
once. Open gaps live in one companion file:
[KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

This page is a **summary that links to the authoritative source for each
row** — it deliberately does not restate detail those files own, so it
can't drift into a competing third version (the exact failure mode
[ROADMAP.md](../ROADMAP.md)'s P1-03/P1-10 exist to prevent). If a fact
here disagrees with the linked source, the linked source wins and this
line is the bug.

- **Maintained by hand** — update it in the same PR that changes what it
  describes.
- **Last verified against the tree:** 2026-07-13.
- **Standing caveat:** everything except Claude Code is implemented
  against each tool's *published* behavior, **not** dogfooded against a
  live session — see
  [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s intro and
  [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

## Release

- **Current version:** `v0.2.0` (git tag + `package.json`), published to
  npm as `agentharness-toolkit`. See
  [RELEASING.md](./RELEASING.md) and [DECISIONS.md](./DECISIONS.md).

## Client support (built)

Per-tool loading behavior and the full matrix (including the ⚠️/❌ rows)
live in [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md); this is
just what's generated and committed here today.

| Tool | Always-on instructions | On-demand skills |
|---|---|---|
| Claude Code | `CLAUDE.md` (hand-authored source) | `.claude/skills/` (source) |
| Codex CLI | `AGENTS.md` | `.agents/skills/` |
| Gemini CLI / Antigravity | `GEMINI.md` | `.agents/skills/` |
| GitHub Copilot | `.github/copilot-instructions.md` + `.github/instructions/*` | `.agents/skills/` |
| Cursor | `.cursor/rules/*.mdc` | `.cursor/rules/<skill>.mdc` |
| Kilo Code | `.kilo/rules/agentharness.md` | `.agents/skills/` |
| OpenCode / Zed | `AGENTS.md` (their own convention) | `.agents/skills/` |

Generate these into a consumer project in one command with
`harness-link.sh generate-clients <project> --client all` (P1-01 first
increment).

Every generated file is drift-checked in CI against its `CLAUDE.md` /
`CONVENTIONS.md` / skill source. **One custom sub-agent**
(`coding-guidelines-reviewer`) and its per-tool ports are tracked
separately — see [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s
custom-agent table.

## Install modes (built)

`link`, `copy`, `submodule`, and `npm` — all installable via
`tools/setup/harness-link.sh` (or `npx agentharness-toolkit`), with
`init`/`plan`/`status`/`doctor`/`audit`/`enforce-profile`/`update`/
`uninstall` lifecycle commands and state in
`<project>/.agentharness-state.json`. See [INTEGRATION.md](./INTEGRATION.md).

## Content (built)

| Area | Built today | Source of truth |
|---|---|---|
| Languages | Python, TypeScript, Go, Rust | [languages/](../languages/) |
| Frameworks | React | [frameworks/react/](../frameworks/react/) |
| Patterns | testing, logging, agentic-loops, error-handling, profiles, accessibility | [patterns/](../patterns/) |
| Skills | 6 (`agentic-loops`, `audit-review-followup`, `branching`, `committing`, `error-handling`, `python-conventions`) | [.claude/skills/](../.claude/skills/) |

## Enforcement (partial)

- **Profile enforcement** (`harness-link.sh enforce-profile`) gates for
  real on **Python** (`pytest`), **Go** (`go test` + `go tool cover`),
  and **`node --test`/Vitest JS/TS** projects at the selected tier's
  coverage floor; Jest/Mocha and unrecognized project types are advisory
  (exit 0, or fail under `--strict`). Not yet wired into the pre-push
  hook. Source of truth: [patterns/profiles/README.md](../patterns/profiles/README.md).
- **Publish authority** defaults to verify-and-stage; push/PR requires
  the opt-in `.agentharness-publish-mode` flag. See
  [DECISIONS.md](./DECISIONS.md).

## Verification (built)

`tools/check.sh` runs everything CI runs locally: shellcheck, bats
suites, ruff, mypy, pytest with coverage gates, `MANIFEST.md`
verification, skill-symlink integrity, and the content-quality checks
(markdownlint, YAML/frontmatter/snippet validation, `MANIFEST`/`AGENTS`
sync, duplicate-policy detection). CI mirrors these as separate jobs
plus a sample-project integration matrix and an npm pack/unpack drive.
