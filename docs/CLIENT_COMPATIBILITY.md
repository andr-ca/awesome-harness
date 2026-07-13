# Client Compatibility Matrix

What each major agentic coding tool reads for always-on project
instructions and on-demand skills, and what this harness currently does
about it. Researched from each tool's public documentation as of
2026-07-14 — **not verified against a live session of any tool except
Claude Code.** Treat every other row's "built" claim the same way this
repo already treats its Codex support: implemented against the tool's
published behavior, not dogfooded end-to-end. See
`docs/DECISIONS.md`'s "Claude-first client scope" entry for the standing
caveat this table doesn't relax.

Status legend: ✅ built and dogfooded in this repo · ⚠️ passively
covered (this repo's files match the tool's documented convention, but
nothing here targets that tool specifically and it's unverified) · ❌ no
support, mechanism doesn't exist for this tool yet.

## Always-on project instructions

| Tool | File(s) | Location / loading behavior | This repo |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | Repo root, read in full every session | ✅ hand-maintained, the source of truth for every generated file below |
| Codex CLI | `AGENTS.md` | Repo root, read in full every session | ✅ generated from `CLAUDE.md` by `tools/generate-agents-md.sh` (P0-06) |
| OpenCode | `AGENTS.md` (primary); `.claude/CLAUDE.md` recognized as a fallback | Searched from cwd up to repo root, then global (`~/.config/opencode/AGENTS.md`); first match wins | ⚠️ this repo's `AGENTS.md` is OpenCode's own primary filename |
| Gemini CLI | `GEMINI.md` (default; filename list configurable via `settings.json`'s `context.fileName`) | Hierarchical: global `~/.gemini/GEMINI.md` + every `GEMINI.md` from cwd up to `.git`, all concatenated | ❌ no `GEMINI.md` exists yet |
| Antigravity | `GEMINI.md` (precedence) or `AGENTS.md` (fallback) | Read at session start, applied for the whole session | ⚠️ fallback only, via `AGENTS.md`; no dedicated `GEMINI.md` |
| Cursor | `.cursorrules` (legacy, always-on) or `.cursor/rules/*.mdc` (current; per-file `alwaysApply`/`globs`/`description` activation) | `.cursorrules` loads unconditionally; `.mdc` files load per their own frontmatter | ❌ no `.cursor/rules/` exists yet |
| GitHub Copilot | `.github/copilot-instructions.md` (repo-wide, always-on); optional `.github/instructions/*.instructions.md` (path-scoped via `applyTo` glob) | VS Code auto-detects and applies to every chat request; path-scoped files apply only when a matching file is open | ❌ neither file exists yet |
| Zed | `AGENTS.md` (project) or `~/.config/zed/AGENTS.md` (personal) | Read at session start; project instructions override personal on conflict | ⚠️ this repo's `AGENTS.md` is Zed's own convention too |
| Kilo Code | `.kilo/rules/*.md` (auto-discovered directory) plus an optional `instructions` array in `kilo.jsonc` | Applied at session start, in filesystem order; project rules take precedence over global | ❌ no `.kilo/rules/` exists yet |

## On-demand skills

Six of the eight non-Claude tools researched implement the **Agent
Skills open standard** (SKILL.md: `name`/`description` frontmatter,
progressive disclosure — an agent sees only name+description up front
and loads the full body once the description matches its task).
Published by Anthropic in December 2025; adopted within 48 hours by
OpenAI and Microsoft, then by 32+ tools by March 2026.

| Tool | Skill directory read | Standard | This repo |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` | Agent Skills (origin) | ✅ 6 skills, the source of truth |
| Codex CLI | `.agents/skills/<name>/SKILL.md` | Agent Skills | ✅ mirrored from `.claude/skills/` by `harness-link.sh` (P0-06) |
| OpenCode | `.opencode/skills/`, `~/.config/opencode/skills/`, and recognizes `.claude/skills/` + `.agents/skills/` as compatibility paths | Agent Skills | ⚠️ `.agents/skills/` already mirrored; no `.opencode/skills/`-specific install |
| Gemini CLI | `.gemini/skills/`, `~/.gemini/skills/`, and recognizes `.agents/skills/` as an alias | Agent Skills | ⚠️ `.agents/skills/` already mirrored; no `.gemini/skills/`-specific install |
| Antigravity | `.agents/skills/` (default) or `.agent/skills/` (back-compat); `~/.gemini/antigravity/skills/` (global) | Agent Skills (added Jan 2026) | ⚠️ `.agents/skills/` already mirrored |
| Cursor | none — no confirmed SKILL.md support | Not adopted; uses `.mdc` rules instead | ❌ no equivalent exists yet |
| GitHub Copilot | `.github/skills/`, `~/.copilot/skills/`, and recognizes `.claude/skills/` + `.agents/skills/` | Agent Skills (added VS Code agent mode, April 2026) | ⚠️ `.agents/skills/` already mirrored; no `.github/skills/`-specific install |
| Zed | `.agents/skills/` (project, worktree-scoped), `~/.agents/skills/` (global) | Agent Skills | ⚠️ `.agents/skills/` already mirrored |
| Kilo Code | `.kilo/skills/`, `~/.kilo/skills/`, and recognizes `.agents/skills/` + `.claude/skills/` | Agent Skills | ⚠️ `.agents/skills/` already mirrored; no `.kilo/skills/`-specific install |

**Practical read:** installing skills into `.agents/skills/` (already
done for every consumer project via `harness-link.sh init`/`update`,
every mode) is the one action with the widest payoff — six tools
recognize that exact directory as a compatibility path today. Cursor is
the outlier requiring a genuinely different mechanism.

## Distinctive per-tool mechanisms worth knowing

- **Cursor's four activation modes** (`.mdc` frontmatter): `alwaysApply:
  true` (Always), `globs: <pattern>` (Auto-Attached when a matching file
  is open), a `description` with no `globs` (Agent-Requested — the agent
  reads the description and decides), or no metadata at all (Manual —
  user must attach explicitly). The closest native analog to SKILL.md's
  progressive disclosure is Agent-Requested.
- **GitHub Copilot's `applyTo` glob** on `.github/instructions/*.instructions.md`
  scopes a whole instructions file to matching paths (e.g. `**/*.py`) —
  a good structural fit for this repo's per-language
  `languages/*/CONVENTIONS.md` guides, which nothing else here has a
  path-scoped mechanism for.
- **Gemini CLI's `@file.md` import syntax** inside `GEMINI.md` lets one
  file pull in others by reference, and `/memory show`/`/memory refresh`
  let a user inspect/reload the concatenated context mid-session.
- **Antigravity's precedence rule**: if both `GEMINI.md` and `AGENTS.md`
  exist, `GEMINI.md` wins for conflicts — the two aren't just redundant
  copies from Antigravity's point of view.
- **Kilo Code's `.kilo/rules/` vs `kilo.jsonc`'s `instructions` array**:
  the directory is auto-discovered; the config array is only needed for
  instructions that live outside that directory or need explicit
  ordering.

## Sources

Research conducted 2026-07-14 via each tool's public documentation.
Full citation lists and per-tool detail are preserved in this session's
research-agent transcripts; representative sources:

- Agent Skills open standard: <https://agentskills.me/specification>,
  <https://github.com/agentskills/agentskills>
- OpenCode: <https://opencode.ai/docs/agents/>, <https://opencode.ai/docs/skills/>
- Gemini CLI: <https://geminicli.com/docs/cli/gemini-md/>, <https://geminicli.com/docs/cli/skills/>
- Cursor: <https://code.visualstudio.com/docs/agent-customization/agent-skills> (comparison context), community guides on `.cursor/rules/*.mdc`
- GitHub Copilot: <https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot>, <https://code.visualstudio.com/docs/agent-customization/agent-skills>
- Antigravity: <https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/>
- Zed: <https://zed.dev/docs/ai/instructions>, <https://github.com/zed-industries/zed/discussions/36609>
- Kilo Code: <https://kilo.ai/docs/customize/skills>, <https://kilo.ai/docs/customize/custom-rules>
