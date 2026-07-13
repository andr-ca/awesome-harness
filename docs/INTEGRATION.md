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
