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
installs the trunk-protection + coverage hooks (`--with-hook`), and
records everything in `<project>/.agentharness-state.json` so the other
subcommands can act on it later:

| Subcommand | What it does |
|---|---|
| `init` | Install (see modes below). `--dry-run` (or the `plan` alias) shows what would happen without changing anything. |
| `status` | What's installed, from where, and whether the source has moved on since. |
| `doctor` | Validate the install is healthy (skills present, bundled resources resolve, hook configured); nonzero exit if not — usable as a CI check. |
| `audit` | Report drift: skills available upstream but not installed, installed skills no longer available, commits since your recorded revision. `--json` for machine-readable output (CI/scripting). |
| `update` | Re-sync to the current harness state; shows a diff and asks for confirmation (`--yes` to skip it) before changing anything. |
| `uninstall` | Reverse everything `init` recorded — skills, gitignore block, hook, profile file, state file (and the submodule, in that mode). |

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

### Codex (`AGENTS.md`)

Codex has no on-demand skill-loading mechanism — it reads one `AGENTS.md`
file in full. Generate one from this harness's own `CLAUDE.md` +
`.claude/skills/` catalog instead of hand-writing a separate copy that
drifts:

```bash
~/agentharness/tools/generate-agents-md.sh --output AGENTS.md
```

Re-run it whenever the harness updates, the same way you'd re-run
`update` for skills — there's no CI check keeping *your* project's copy
in sync (only this harness's own root `AGENTS.md` has that), so treat it
as a copy-mode integration (see Method 2 above): pin it, regenerate
deliberately.

**This adapter has not been verified against a real Codex CLI session —
best-effort only.** See the README's "Supported clients" section before
relying on it.

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
