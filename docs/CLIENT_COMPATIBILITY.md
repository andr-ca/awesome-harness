# Client Compatibility Matrix

What each major agentic coding tool reads for always-on project
instructions, on-demand skills, and custom-agent/sub-agent delegation,
and what this harness currently does about it. Researched from each
tool's public documentation as of 2026-07-14 (custom-agent section:
2026-07-13) — **not verified against a live session of any tool except
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

## Custom agents / sub-agent delegation

A third dimension, distinct from the two tables above: several tools let
a **primary agent delegate a task to a separate, specialized agent
instance** — its own system prompt, its own tool/model scope, running in
its own thread — rather than just switching the current agent's
instructions or loading a skill's body inline. Claude Code's own
`.claude/agents/*.md` + the Task/Agent tool (`subagent_type`) is the
origin case this table is framed against. Researched 2026-07-13, same
caveat as the rest of this document (public docs only, not verified
against a live session) — one row below carries an extra confidence flag
where a primary source couldn't be confirmed directly.

| Tool | Mechanism | Config format | Delegation? | This repo |
|---|---|---|---|---|
| Claude Code | Subagents via the Task/Agent tool (`subagent_type`) | `.claude/agents/*.md` (Markdown + YAML frontmatter: name, description, tools, model) | ✅ true delegation — separate thread, restricted tools/model | ✅ `coding-guidelines-reviewer` — the first (and so far only) subagent this repo defines |
| Codex CLI | Subagents | `.codex/agents/` or `~/.codex/agents/` (TOML: name, description, developer_instructions, model, mcp_servers) | ✅ true delegation — separate threads, per-agent token budget, up to 6 parallel by default | ✅ generated from `.claude/agents/*.md` by `tools/generate-codex-agents.sh` — tool/permission scoping NOT ported (unverified against a live session) |
| OpenCode | Custom Agents | `.opencode/agents/*.md` (Markdown + YAML) or `opencode.json` | ✅ true delegation — auto-invoke by a primary agent, manual `@mention`, or the Task tool | ✅ generated by `tools/generate-opencode-agents.sh` — same tool/permission-scoping caveat |
| Cursor | Subagents | `.cursor/agents/*.md` (YAML: name, description, model, readonly, is_background) | ✅ true delegation — parallel threads, optional async/background execution | ✅ generated by `tools/generate-cursor-agents.sh` — `readonly`/`is_background` and tool scoping NOT ported (unverified defaults); distinct from `.cursor/rules/*.mdc` (that's the skill-porting generator, a different Cursor feature) |
| Kilo Code | Custom Subagents | `.kilo/agents/*.md`, `~/.config/kilo/agents/`, or `kilo.jsonc`'s `agent` section | ✅ true delegation — Task-tool auto-invoke or manual `@agent-name`; `permission.task` scopes which subagents a primary agent may call | ✅ generated by `tools/generate-kilo-agents.sh` — `permission`/`permission.task` NOT ported |
| Antigravity | Custom agents over the A2A (Agent2Agent) protocol | Unconfirmed — the A2A protocol itself is real and Google-authored (<https://a2a-protocol.org>), but Antigravity's own custom-agent config format couldn't be confirmed from a primary doc (its docs page returned no substantive content on fetch) | ✅ claimed — bidirectional agent-to-agent handoffs | ❌ none defined; **lower confidence than the rest of this table** |
| GitHub Copilot | Agent Profiles | `.github/agents/*.agent.md` (YAML frontmatter + Markdown) | ❌ persona-only — different prompt/tool/MCP scoping, still one agent, no spawning | — no delegation capability to target |
| Gemini CLI | Subagents | `.gemini/agents/*.md` (YAML frontmatter) | ❌ explicitly blocked — docs state subagents cannot call other subagents | — no delegation capability to target |
| Zed | Agent profiles | `settings.json`'s `agent.profiles` | ❌ persona/tool-scope switch only, no inter-profile invocation | — no delegation capability to target |

**Practical read:** five tools (Claude Code, Codex CLI, OpenCode, Cursor,
Kilo Code) support genuine task delegation to a separate specialized
agent — structurally close enough that this repo now ports its one real
subagent (`coding-guidelines-reviewer`, a read-only reviewer scoped to
`.github/CODING_GUIDELINES.md`'s rigor tiers) across all five via
`tools/generate-{codex,opencode,cursor,kilo}-agents.sh`, the same
relationship `.claude/skills/` has to `.agents/skills/`. Copilot, Gemini
CLI, and Zed only offer persona switching for the *same* agent — there's
nothing to port delegation *to* on those three.

**Explicit scope boundary — cross-tool tool/permission scoping is NOT
translated.** Each target platform's own tool-name and permission
vocabulary is unverified against a live session, so no generator here
attempts to map Claude Code's `tools: Read, Grep, Glob, Bash` (or
Cursor's `readonly`/`is_background`, or Kilo's `permission`/
`permission.task`) into the target format — asserting that translation
would be exactly the kind of unverifiable claim this document's caveat
exists to prevent. Every ported file carries only `name`/`description`/
`model` and the body verbatim; adopting a ported agent for real use
means re-specifying its tool/permission scope by hand for that
platform.

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

Custom-agent/sub-agent delegation section researched 2026-07-13:

- Codex CLI subagents: <https://learn.chatgpt.com/docs/agent-configuration/subagents>
- OpenCode agents: <https://opencode.ai/docs/agents/>
- Cursor subagents: <https://cursor.com/docs/context/subagents>
- Kilo Code custom subagents: <https://kilo.ai/docs/customize/custom-subagents>
- GitHub Copilot agent profiles: <https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents>
- Gemini CLI subagents: <https://geminicli.com/docs/core/subagents/>
- Zed agent profiles: <https://zed.dev/docs/ai/agent-profiles> (page unavailable at fetch time; corroborated via <https://github.com/zed-industries/zed/discussions/35956>)
- A2A protocol (Antigravity's underlying claim): <https://a2a-protocol.org/latest/>, <https://github.com/a2aproject/A2A> — Antigravity's own custom-agent config format is unconfirmed; treat that one row as directional, not sourced
