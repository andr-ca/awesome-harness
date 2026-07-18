# Integration Guide – Using agentharness in Projects

Step-by-step guide for integrating components from agentharness into your
projects. Every command below is tested against what actually exists in
this repo today — see [MANIFEST.md](../MANIFEST.md) for the inventory.

## The Fast Path

```bash
~/agentharness/tools/setup/harness-link.sh init /path/to/your-project --mode link
```

This is `harness-link.sh`'s lifecycle CLI: `init` symlinks (or copies, or
adds a submodule and symlinks from it — see Method 1/2/3 below) skills,
merges `.github/.gitignore.template` into `.gitignore`, optionally
installs the trunk-protection hook (`--with-hook`) or a real,
project-owned coverage-enforcing pre-push hook on top of that
(`--with-coverage-hook` — see "Coverage enforcement" below, P0-03), and
records everything in `<project>/.agentharness-state.json` so the other
subcommands can act on it later:

| Subcommand | What it does |
|---|---|
| `init` | Install (see modes below). `--dry-run` (or the `plan` alias) shows what would happen without changing anything. |
| `status` | What's installed, from where, and whether the source has moved on since. |
| `doctor` | Validate the install is healthy (skills present, bundled resources resolve, hook configured); nonzero exit if not — usable as a CI check. |
| `audit` | Report drift: skills available upstream but not installed, installed skills no longer available, commits since your recorded revision; your selected profile, whether `.agentharness-publish-mode` is active, and whether the recorded harness checkout's own validation commands still exist. `--json` for machine-readable output (CI/scripting). Doesn't run policy-conflict detection itself — points at `tools/verify-content-quality.py` instead. |
| `enforce-profile` | Read `.agentharness-profile` and gate on it for real: Python (`pytest --cov-fail-under` at the selected tier's floor), or JS/TS if `package.json`'s `"test"` script already runs `node --test`. Other project types/test runners get "not implemented yet". Invoked automatically by `--with-coverage-hook`'s generated pre-push hook; otherwise not wired in anywhere — invoke it explicitly. |
| `update` | Re-sync to the current harness state; shows a diff and asks for confirmation (`--yes` to skip it) before changing anything. |
| `uninstall` | Reverse everything `init` recorded — skills, gitignore block, hook (including a generated coverage hook), profile file, state file (and the submodule/durable npm copy, in those modes). |

### Coverage enforcement (`--with-coverage-hook`, P0-03)

`--with-hook` alone only installs `prevent-trunk-commit` — the shared
`pre-push` hook this repo's own `core.hooksPath` points at is hardcoded
to test *agentharness's own* suites and deliberately no-ops for any
other repo (see `.github/hooks/pre-push`'s own comments). Calling that
combination "coverage hooks" for a consumer was never accurate.

`--with-coverage-hook` (implies `--with-hook`) generates a real,
project-owned `pre-push` script at `<project>/.github/hooks/pre-push`
that calls `harness-link.sh enforce-profile <project>` before allowing
a push — this is genuinely gated on whatever `.agentharness-profile`
tier the project has selected, regardless of install `--mode`. `doctor`
verifies the generated script is present, executable, and hasn't been
hand-edited (a marker comment identifies it); `uninstall` removes it
along with everything else.

The generated script hardcodes the absolute path to the
`harness-link.sh` this repo was installed *from* at generation time —
for `--mode link`/`copy`, that's this harness checkout's own path, not
a copy inside the project. If that checkout moves or is deleted,
coverage enforcement fails on the next push. `update` never touches
hooks (same convention as `--with-hook`), so recovering requires
re-running `init --with-coverage-hook` to regenerate the script against
a valid `harness-link.sh` path.

`harness-link.sh /path/to/your-project [options]` (no subcommand) still
works — it's sugar for `init` with those same options, kept for anything
that already calls it that way.

Everything below is the manual, step-by-step version of what `--mode`
does, useful for understanding what's actually happening or for
integrating a single component by hand instead of everything at once.

## Integration Methods

### Method 1: Symlinks (recommended for active development)

Keep your project in sync with harness updates automatically.

Automated: `harness-link.sh init ~/my-project --mode link` (the default —
`--mode` can be omitted).

Manual, what that does under the hood (symlinking each skill
individually, not the whole `skills/` directory as one symlink — that
way your project can still have its own local skills alongside the
harness's, and you can pick a subset):

```bash
cd ~/my-project
mkdir -p .claude/skills
for skill in ~/agentharness/.claude/skills/*/; do
  ln -s "$skill" ".claude/skills/$(basename "$skill")"
done
```

**Pros:** Always up-to-date. **Cons:** Requires the harness checked out
locally at that exact path; breaks if you move it.

⚠️ Never symlink into `~/.claude` (your global Claude Code config) — that
clobbers or fights with settings that aren't part of this harness.
Symlink into the *project's* `.claude/`, not your home directory.

### Method 2: Copy (for release stability)

Lock to a specific snapshot of harness components — no drift, no
dependency on the harness being checked out locally.

Automated: `harness-link.sh init ~/my-project --mode copy`. Run
`harness-link.sh update ~/my-project` later to see (and, after
confirming) apply upstream changes — it diffs your copy against the
current source first, so local edits aren't silently overwritten.

Manual, what that does under the hood (`-L` dereferences any bundled-
resource symlinks inside a skill — e.g. agentic-loops' `agent_loop.py` —
instead of copying them as symlinks that only resolve inside the harness
checkout):

```bash
cd ~/my-project
mkdir -p .claude
cp -rL ~/agentharness/.claude/skills .claude/skills

# Record what you copied and from where, so future-you can diff and update
harness_rev="$(git -C ~/agentharness rev-parse --short HEAD)"
cat >> CLAUDE.md <<EOF

## Harness Integration
Copied from agentharness @ $harness_rev
- .claude/skills/ ($(ls ~/agentharness/.claude/skills | paste -sd, -))
EOF
```

The hand-append above is what `harness-link.sh init`/`update` now do for you
automatically, and more carefully (idempotent, reversible, never touching
your file's other content) — see "Existing Agent Surfaces" below.

**Pros:** Independent of harness changes. **Cons:** Manual sync when the
harness improves (`harness-link.sh update` automates the sync itself, but
you still decide when to run it).

### Method 3: Git Submodule (for teams, or heavier integrations)

Automated: `harness-link.sh init ~/my-project --mode submodule` — adds
this harness as a submodule at `~/my-project/.agentharness` (pinned via
the submodule's own commit, not a mutable external path) and symlinks
skills from there.

Manual, what that does under the hood (per-skill symlinks again, same
reasoning as Method 1):

```bash
cd ~/my-project
git submodule add https://github.com/andr-ca/agentharness.git .agentharness
mkdir -p .claude/skills
for skill in .agentharness/.claude/skills/*/; do
  ln -s "../../$skill" ".claude/skills/$(basename "$skill")"
done

# Update later:
git submodule update --remote .agentharness
```

**Pros:** Version-controlled, explicit pin. **Cons:** Submodule
operational overhead (contributors need `git submodule update --init`).

### Method 4: npm/npx (durable copy, no local checkout needed)

`--mode npm` is what `npx agentharness-toolkit init` defaults to
automatically — you won't normally pass this flag by hand. It exists
because `npx` runs the package from an ephemeral cache/temp extraction,
not a durable path: `--mode link`'s "symlink straight from wherever this
is running" would silently break every installed skill the next time
`npx` cleans that cache up (P0-02). Instead, `init` copies the whole
running package into `<project>/.agentharness-pkg` (excluding `.git`)
and symlinks skills from that durable local copy, recording the npm
package's own version (e.g. `0.2.0`) as the source revision instead of a
git SHA.

`harness-link.sh update` on an npm-mode install re-copies from whatever
package is currently running the update (so `npx agentharness-toolkit@latest update ~/my-project`
picks up a newer release), not from the old durable copy's own content —
diffing the copy against itself would always report "nothing to do".

**Pros:** No git checkout required at all, survives npx cache cleanup.
**Cons:** Not version-controlled the way `--mode submodule` is; the
durable copy is local-only state, not tracked in your project's git
history (add `.agentharness-pkg/` to `.gitignore`, which the harness's
own gitignore template already does).

## Existing Agent Surfaces

If your project already has a `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or
`.github/copilot-instructions.md` before you ever run `harness-link.sh`,
you don't need to hand-merge anything. `init` and `update` render a
marker-delimited block into each of those files that already exists (or
create the file if it doesn't), leaving everything else in the file byte-
for-byte untouched:

```
<!-- agentharness:begin id=core-instructions version=0.2.1 -->
... harness routing/precedence content, regenerated on every init/update ...
<!-- agentharness:end id=core-instructions -->
```

Re-running `init`/`update` replaces only the content between those
markers — never anything outside them. `uninstall` removes the block
entirely and restores your file to what it would have looked like without
the harness, preserving your own content exactly.

**Precedence:** where the harness enforces something mechanically (a git
hook, the completion gate), your project's own instructions cannot weaken
it — but for everything else, your project's own instructions in that
same file take precedence over the harness's *defaults*. See
[the design spec, section 3](superpowers/specs/2026-07-17-existing-surface-integration-design.md#3-precedence)
for the exact wording this block itself carries.

**Whole-file generated surfaces** (directory-style outputs like
`.cursor/rules/*.mdc` from `generate-cursor-rules.sh` — see the Cursor
section below) use a different, coarser mechanism: since there's no safe
way to merge a whole generated file the way a marker block merges into an
existing one, a pre-existing file at that exact path is a *collision*,
and `init`/`update` will:

- **prompt interactively** (`[o]verwrite / [k]eep yours / [a]ll / [n]one`)
  when stdin is a real, attended session;
- **skip and report, exiting non-zero**, if unattended and neither flag
  below is given — an unattended run never silently overwrites a file the
  harness doesn't own;
- honor **`--force`** to overwrite every collision (backing up what it
  replaces to `<file>.pre-agentharness.<install-id>` first — restorable
  by `uninstall` if the file is later removed and hasn't been edited
  since), or **`--keep-existing`** to skip every collision without asking.
- **`--dry-run`** shows the full plan — including any collisions found —
  without writing anything.

Run `harness-link.sh doctor` at any time to check for a managed block
that's drifted from what the harness would currently render (hand-edited,
or stale relative to the harness's current source revision), or a crash
journal left behind by an install/update that was interrupted mid-apply.

## Per-Component Integration

### Claude Code Skills

```bash
mkdir -p .claude/skills
for skill in ~/agentharness/.claude/skills/*/; do
  name="$(basename "$skill")"
  ln -s "$skill" ".claude/skills/$name"
done
```

(Or symlink only the ones you want — see `ls ~/agentharness/.claude/skills/`
for the current list; `harness-link.sh init --skills name1,name2` does
this filtering for you.)

Verify: a skill with valid `SKILL.md` frontmatter is picked up
automatically — no registration step. In a session working in that
project, Claude Code lists it as an available skill (you'll see it
mentioned as loadable when its description matches what you're doing, or
via a system reminder listing available skills); if it doesn't show up,
run `doctor` (see Troubleshooting below) or check the frontmatter is
valid YAML with `name` and `description` fields.

### Codex (`AGENTS.md` + `.agents/skills/`)

Codex CLI's real skill mechanism (the Agent Skills open standard, shared
with Claude Code since December 2025) scans `.agents/skills/` from the
working directory up to the repo root, reads each skill's `SKILL.md`
`name`/`description` metadata up front, and loads a skill's full body
only once its description matches the task at hand — the same
progressive-disclosure model Claude Code uses, not "no on-demand
loading" as an earlier version of this adapter assumed (P0-06).

`harness-link.sh init`/`update` install every skill into `.agents/skills/`
alongside `.claude/skills/` automatically (same source, same `SKILL.md`)
— no separate flag needed. `AGENTS.md` itself only needs to cover
repo-wide routing rules plus a lightweight name+description index so
Codex's own metadata scan has something to match against before it lists
`.agents/skills/` itself:

```bash
~/agentharness/tools/generate-agents-md.sh --output AGENTS.md
```

Re-run it whenever `CLAUDE.md` or the skill catalog changes, the same
way you'd re-run `update` for skills — there's no CI check keeping
*your* project's copy in sync (only this harness's own root `AGENTS.md`
has that), so treat it as a copy-mode integration (see Method 2 above):
pin it, regenerate deliberately.

Redesigning this adapter (previously an 880-line/33.7KB file
concatenating every skill's full body into every task) cut this harness's
own generated `AGENTS.md` to 201 lines/11.6KB — routing rules plus a
6-line skill index, with full skill content loaded only on demand from
`.agents/skills/`.

### Gemini CLI / Antigravity (`GEMINI.md` + `.agents/skills/`)

Gemini CLI supports the same Agent Skills open standard as Claude Code
and Codex: it injects every enabled skill's `name`/`description` into
the system prompt at session start, then calls an `activate_skill` tool
to load a skill's full body only once its description matches the task
at hand (see https://geminicli.com/docs/cli/skills/). Google Antigravity
reads the same `GEMINI.md` filename and gives it precedence over
`AGENTS.md` when both are present.

`harness-link.sh init`/`update` already install every skill into
`.agents/skills/` (same mechanism Codex uses above), so `GEMINI.md`
itself only needs the same routing-rules-plus-index shape as `AGENTS.md`:

```bash
~/agentharness/tools/generate-gemini-md.sh --output GEMINI.md
```

Re-run it the same way you'd re-run the `AGENTS.md` generator — no CI
check keeps a *consumer* project's copy in sync, only this harness's own
root `GEMINI.md` has that. **Not verified against a live Gemini CLI or
Antigravity session** — built from public docs as of 2026-07-14 (see
`docs/CLIENT_COMPATIBILITY.md`).

### GitHub Copilot (`.github/copilot-instructions.md` + `.github/instructions/*.instructions.md`)

Copilot (VS Code, github.com, the Copilot coding agent) reads
`.github/copilot-instructions.md` as a repo-wide, always-applied file,
plus optional path-scoped `.github/instructions/*.instructions.md`
files — each carrying an `applyTo` glob frontmatter field Copilot uses
to decide whether the file applies to the path currently being edited
(not a regex, despite that being a common assumption — see
https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot).
Copilot also added support for the Agent Skills open standard to VS
Code's agent mode in April 2026 and recognizes `.agents/skills/` the
same way Codex and Gemini CLI do.

This harness's own `languages/*/CONVENTIONS.md` files already carry
`applyTo`/`description` frontmatter written for exactly this purpose —
the generator reuses it as the source of truth instead of restating the
glob pattern a second time:

```bash
~/agentharness/tools/generate-copilot-instructions.sh --output-dir .
```

This writes both `.github/copilot-instructions.md` and one
`.github/instructions/<lang>.instructions.md` per language guide you
have under `languages/`. Re-run it whenever `CLAUDE.md` or a
`CONVENTIONS.md` file changes. **Not verified against a live Copilot
session** — built from public docs as of 2026-07-14. (Separately,
`languages/python/COPILOT_INSTRUCTIONS.md` is a generic, non-generated
Python/Copilot best-practices reference — a different document from the
project-specific conventions this generator produces; both are useful,
neither replaces the other.)

### Kilo Code (`.kilo/rules/agentharness.md`)

Kilo Code auto-discovers every file placed under `.kilo/rules/` — no
`kilo.jsonc` entry is required for a new file there to take effect. Kilo
also recognizes `.agents/skills/` as an Agent-Skills-standard-compliant
path, so this file follows the same routing-rules-plus-index shape as
`AGENTS.md`/`GEMINI.md`:

```bash
mkdir -p .kilo/rules
~/agentharness/tools/generate-kilo-rules.sh --output .kilo/rules/agentharness.md
```

Re-run it the same way as the other generators above. **Not verified
against a live Kilo Code session** — built from public docs as of
2026-07-14.

### Cursor (`.cursor/rules/*.mdc`)

Cursor is the one platform researched with no confirmed Agent Skills
(SKILL.md) support — its native mechanism is structurally different:
`.cursor/rules/*.mdc` files, each with `description`/`globs`/
`alwaysApply` frontmatter and four activation modes (Always,
Auto-Attached-by-glob, Agent-Requested-by-description, Manual — see
https://docs.cursor.com/context/rules). Because there's no shared
metadata-scan step to delegate to, this generator produces one `.mdc`
per skill (full body inline, not just an index) plus one always-on
router file:

```bash
~/agentharness/tools/generate-cursor-rules.sh --output-dir .
```

This writes `.cursor/rules/agentharness-router.mdc` (`alwaysApply:
true`, `CLAUDE.md`'s routing prose) and one
`.cursor/rules/<skill-name>.mdc` per skill (that skill's own
`description` copied verbatim into the frontmatter, no `globs` — Cursor's
agent reads the description and decides whether to pull the rule in,
the closest native analog to SKILL.md's own progressive disclosure).
Re-run it whenever `CLAUDE.md` or the skill catalog changes. **Not
verified against a live Cursor session** — built from public docs as of
2026-07-14.

Generating cursor rules is a separate, manual step from `init`/`update` —
running `generate-cursor-rules.sh` is not currently part of the automatic
existing-surface collision handling described above; if you run it
against a project where `.cursor/rules/*.mdc` files already exist, it
follows its own overwrite rules (see `--help`), independent of the
`--force`/`--keep-existing` collision flow `init`/`update` use for the
four instructions files.

### Custom Agents (sub-agent delegation)

Separate from every generator above: those cover always-on instructions
and on-demand skills, content the *current* agent reads. This section
covers **task delegation to a separate, specialized agent instance** —
Claude Code's own `.claude/agents/*.md` + Task/Agent tool is the origin
case. This repo defines one such subagent,
`.claude/agents/coding-guidelines-reviewer.md` (a read-only reviewer
scoped to `.github/CODING_GUIDELINES.md`'s rigor tiers), and ports it to
every tool confirmed to support genuine delegation — Codex CLI,
OpenCode, Cursor, Kilo Code, GitHub Copilot, and Gemini CLI:

```bash
~/agentharness/tools/generate-codex-agents.sh --output-dir .     # .codex/agents/*.toml
~/agentharness/tools/generate-opencode-agents.sh --output-dir .  # .opencode/agents/*.md
~/agentharness/tools/generate-cursor-agents.sh --output-dir .    # .cursor/agents/*.md
~/agentharness/tools/generate-kilo-agents.sh --output-dir .      # .kilo/agents/*.md
~/agentharness/tools/generate-copilot-agents.sh --output-dir .   # .github/agents/*.agent.md
~/agentharness/tools/generate-gemini-agents.sh --output-dir .    # .gemini/agents/*.md
```

Each is a manual-regeneration step (re-run whenever `.claude/agents/`
changes), CI-drift-checked against its committed output the same way as
every generator above. **None of these six translate tool/permission
scoping** — Claude Code's `tools:` field, Cursor's
`readonly`/`is_background`, Kilo's `permission`/`permission.task`,
Copilot's `target`/`disable-model-invocation`/`user-invocable`, and
Gemini's `tools`/`temperature`/`max_turns` are all real, documented
fields on their respective platforms, but mapping between them is
unverified against a live session; ported files carry only
`name`/`description`/`model` and the body verbatim, and adopting one for
real use means re-specifying its tool/permission scope by hand.

Zed has no equivalent to generate for: real subagent delegation exists
architecturally (isolated `Thread` instances, `SpawnAgentTool`), but no
confirmed user-facing named-config-file format was located to port
into. GitHub Copilot's own custom-agent mechanism (CLI/VS Code, not the
cloud coding agent) and Gemini CLI's subagents both genuinely spin up an
isolated-context subagent — an earlier research pass here initially got
both wrong, classifying them as persona-only (the same root-cause error
each time: conflating "can't nest further subagents" with "no
delegation at all"); see `docs/CLIENT_COMPATIBILITY.md`'s dated
correction notes. **Not verified against a live session of any of these
six tools** — built from public docs as of 2026-07-13, the same
"not verified" caveat as everything else in this document.

### Language Guidelines

Python, TypeScript, and Go exist today (`languages/{python,typescript,go}/`),
plus a React framework add-on (`frameworks/react/CONVENTIONS.md`, layered
on top of the TypeScript guide — see that guide's own "React" section).
Reference them directly rather than copying — conventions docs are meant
to be read, not vendored:

```markdown
<!-- In your project's CLAUDE.md -->
## Language Guide
TypeScript conventions: see ~/agentharness/languages/typescript/CONVENTIONS.md
React conventions: see ~/agentharness/frameworks/react/CONVENTIONS.md
```

### Testing & Logging Patterns

```bash
cp ~/agentharness/patterns/testing/COMPLETION_CHECKLIST.md ./docs/
cp ~/agentharness/patterns/logging/logging.yaml.example ./config/logging.yaml
```

Then edit the copy — these are templates, not symlink targets, because
you'll customize thresholds and backends per project.

### Git Hook

```bash
git config core.hooksPath /path/to/agentharness/.github/hooks
```

Or copy it in so it travels with the project instead of depending on the
harness path:

```bash
mkdir -p .githooks
cp ~/agentharness/.github/hooks/prevent-trunk-commit .githooks/pre-commit
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

### `.gitignore`

```bash
cp ~/agentharness/.github/.gitignore.template .gitignore
```

### Publish Authority

`CLAUDE.md`'s "Agent Workflow Completion" section defaults an agent to
verify-and-stage-only: it commits locally but stops before pushing,
opening a PR, or auto-implementing recommendations, and asks first.

To grant an agent standing commit/push/PR authority for a repo you
control (skip the per-task confirmation), create the flag file at that
repo's root:

```bash
touch .agentharness-publish-mode
```

It's gitignored by `.github/.gitignore.template` — never commit it; it's
a per-operator/per-machine grant, not a repo-wide policy. Remove the
file (`rm .agentharness-publish-mode`) to drop back to the safer default.
This doesn't override an explicit instruction in a given request either
way — telling an agent "commit and push this" (or "just stage this,
don't push") always wins for that one task regardless of the flag.

## Project-Specific CLAUDE.md Template

```markdown
## Harness Integration

This project uses agentharness for:
- Skills: committing, branching, python-conventions (symlinked from .claude/skills/)
- Language: Python — see ~/agentharness/languages/python/CONVENTIONS.md
- Testing: patterns/testing/COMPLETION_CHECKLIST.md (copied to docs/)

Integration method: Symlinks
Location: ~/agentharness
Last synced: 2026-07-12 (commit abc1234)
```

## Keeping Projects Updated

All three modes: `harness-link.sh update ~/my-project` — shows what
changed (skills added/removed upstream; for copy mode, which files
diverged) and asks for confirmation before applying. `--yes` skips the
prompt for non-interactive use.

**Symlinks:** content is always current automatically; `update` only
matters here for picking up newly-added skills or a widened/narrowed
`--skills` filter.

**Copies:** `update` diffs your copy against the current source per
skill and only touches ones that actually changed.

**Submodules:** `update` re-syncs the skill symlinks the same way as
link mode; to also pull the submodule itself to the harness's latest
commit, run `git -C ~/my-project submodule update --remote .agentharness`
first (deliberately manual — the CLI won't move your pinned commit for
you without being asked).

## Troubleshooting

**Issue:** Skills not appearing in Claude Code
- Verify the symlink resolves: `ls -la .claude/skills/`
- Check the skill's `SKILL.md` has valid frontmatter

**Issue:** Symlink breaks when the harness moves
- Use an absolute path when creating the symlink, or move both together
- Consider the submodule method instead if the harness path isn't stable

**Issue:** `core.hooksPath` conflicts with an existing hook manager (husky, pre-commit)
- Only one `core.hooksPath` can be active. Either copy the harness hook's
  logic into your existing hook manager's config, or drop the other
  manager for this repo.

**Issue:** not sure what's actually installed, or whether it's still working
- `harness-link.sh status ~/my-project` shows what's recorded.
- `harness-link.sh doctor ~/my-project` validates it against reality
  (nonzero exit on any problem) — run this after moving the harness
  checkout, after a manual edit to `.claude/skills/`, or in your own CI.

**Issue:** integrated by hand (not via `harness-link.sh`) and want to switch to it
- There's no import path for a manual integration's state — run
  `harness-link.sh init` fresh; it's safe to re-run over an existing
  manual symlink setup that matches its own layout, but check `status`
  and `doctor` afterward rather than assuming it merged cleanly.

---

This guide covers what exists today — `languages/{python,typescript,go}/`,
`frameworks/react/`, and the `tools/` scripts referenced above. As more
frameworks and languages are added (see [ROADMAP.md](../ROADMAP.md)), this
guide will grow matching per-component sections. Don't reference paths
that don't exist — check [MANIFEST.md](../MANIFEST.md) first.
