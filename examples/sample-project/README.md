# Sample Integration Project

Minimal example project that demonstrates how to integrate the agentharness into your project.

This sample documents all three integration methods from `docs/INTEGRATION.md`,
but only Method 1 is checked by CI — the `sample-project-integration` job in
`.github/workflows/ci.yml` runs `harness-link.sh --with-hook` against a
scratch copy of this directory on every push. Methods 2 and 3 below are
accurate as written but not automatically re-verified; treat them as
documentation, not as continuously tested.

1. **Symlink** — Link skills and hooks from the harness (lightweight, immediate updates) — **CI-verified**
2. **Copy** — Copy guidelines, patterns, hooks into your project (independent, one-time) — documented, not CI-checked
3. **Submodule** — Git submodule for shared history and versioning (full control, more overhead) — documented, not CI-checked

---

## Quick Start

Choose one method below:

### Method 1: Symlink (Recommended)

```bash
# Link harness components into this project
~/agentharness/tools/setup/harness-link.sh . --with-hook

# This creates:
# - .claude/skills/<name> → individual symlinks to each harness skill
#   (.claude/skills/ itself is a real directory, not a symlink)
# - .gitignore merged with harness template
# - core.hooksPath set to the harness's .github/hooks (via --with-hook;
#   requires this project to already be a git repo)
```

### Method 2: Copy

```bash
# Copy harness components into your project
cp -r ~/agentharness/.claude/skills .claude/
cp -r ~/agentharness/.github/hooks .github/
cp ~/agentharness/.github/.gitignore.template .gitignore.harness
cat .gitignore.harness >> .gitignore
rm .gitignore.harness

# Copy key guidelines
mkdir -p docs/harness
cp ~/agentharness/.github/COMMITTING_GUIDELINES.md docs/harness/
cp ~/agentharness/.github/CODING_GUIDELINES.md docs/harness/
```

### Method 3: Submodule

```bash
# Add harness as a git submodule
git submodule add https://github.com/andr-ca/agentharness.git vendor/agentharness

# Link from submodule
ln -s vendor/agentharness/.claude/skills .claude/skills
ln -s vendor/agentharness/.github/hooks .github/hooks

git config core.hooksPath vendor/agentharness/.github/hooks
```

---

## Verify Integration

Run the verification script to check that skills, hooks, and guidelines are accessible:

```bash
bash verify.sh
```

Expected output:
```
✅ .claude/skills exists
✅ Committing skill linked
✅ core.hooksPath points at the harness's prevent-trunk-commit hook
✅ Project CLAUDE.md configured
✅ All checks passed! Integration verified.
```

---

## File Structure

```
sample-project/
├── README.md                           # This file
├── verify.sh                           # Validation script
├── .claude/
│   └── skills/                         # Real dir; each skill inside is a
│       ├── committing/                 # symlink (or copy) from the harness
│       ├── branching/
│       └── python-conventions/
├── .github/
│   └── CLAUDE.md                       # Project-specific instructions
├── docs/
│   └── harness/                        # (If using copy method)
│       ├── CODING_GUIDELINES.md
│       └── COMMITTING_GUIDELINES.md
└── .gitignore                          # Merged with harness template
```

Note: `.claude/skills/` itself is never a symlink — `harness-link.sh`
creates it as a real directory and symlinks each skill inside it. Hook
installation (`--with-hook`) sets `core.hooksPath` directly to the
harness's `.github/hooks`; no `.github/hooks` symlink is created in the
target project.

---

## Project-Specific CLAUDE.md

Create a `.github/CLAUDE.md` in your project with overrides for project-specific rules:

```markdown
# Your Project

This project uses the agentharness for shared conventions.

## Overrides

- **Coverage tier**: Internal Tool (see `.github/CODING_GUIDELINES.md#rigor-tiers`)
  Not all mandates apply; see below.
- **Logging**: Optional; only in critical paths

## How to Use Harness

- Branch strategy: Read `.claude/skills/branching/SKILL.md`
- Committing: Read `.claude/skills/committing/SKILL.md`
- Python: Read `.claude/skills/python-conventions/SKILL.md`
```

---

## CI Integration

This repo's own `.github/workflows/ci.yml` keeps this sample validated: the
`sample-project-integration` job copies this directory into a scratch git
repo, runs `harness-link.sh --with-hook` against it exactly as Method 1
above describes, and then runs `verify.sh` — so every push exercises the
real symlink/hook-install path, not just documentation.

If you're consuming this harness from your own project (rather than working
in this repo), adapt the same idea in your own CI:

```yaml
- name: Verify harness integration
  run: bash verify.sh   # or your own project's equivalent check
```

---

## Notes

- **Symlink method** updates automatically when harness updates (best for shared orgs)
- **Copy method** gives independence; updates are manual (best for stable branches)
- **Submodule method** pins to specific harness versions (best for reproducible builds)
- All methods can coexist (mix and match for different teams)
- The `prevent-trunk-commit` hook requires `git config core.hooksPath`; it won't work without it

---

## Further Reading

- Full integration guide: `../../docs/INTEGRATION.md`
- Harness overview: `../../README.md`
- Architecture: `../../docs/ARCHITECTURE.md`
