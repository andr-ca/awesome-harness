# Sample Integration Project

Minimal example project that demonstrates how to integrate the agentharness into your project.

This sample validates all three integration methods documented in `docs/INTEGRATION.md`:
1. **Symlink** — Link skills and hooks from the harness (lightweight, immediate updates)
2. **Copy** — Copy guidelines, patterns, hooks into your project (independent, one-time)
3. **Submodule** — Git submodule for shared history and versioning (full control, more overhead)

---

## Quick Start

Choose one method below:

### Method 1: Symlink (Recommended)

```bash
# Link harness components into this project
~/agentharness/tools/setup/harness-link.sh .

# This creates:
# - .claude/skills → symlinks to harness skills
# - .github/hooks → symlinks to harness hooks
# - .gitignore merged with harness template

git config core.hooksPath .github/hooks  # Enable hooks
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
✅ .claude/skills exists and has: committing, branching, python-conventions
✅ .github/hooks exists and has: prevent-trunk-commit
✅ Key guidelines accessible: CODING_GUIDELINES.md, COMMITTING_GUIDELINES.md
✅ All integration methods validated
```

---

## File Structure

```
sample-project/
├── README.md                           # This file
├── verify.sh                           # Validation script
├── .claude/
│   └── skills/                         # Symlink or copy of harness skills
│       ├── committing/
│       ├── branching/
│       └── python-conventions/
├── .github/
│   ├── hooks/                          # Symlink or copy of harness hooks
│   │   └── prevent-trunk-commit
│   └── CLAUDE.md                       # Project-specific instructions
├── docs/
│   ├── harness/                        # (If using copy method)
│   │   ├── CODING_GUIDELINES.md
│   │   └── COMMITTING_GUIDELINES.md
│   └── INTEGRATION.md                  # Links to harness docs
├── .git/
│   └── hooks/                          # Disabled; use core.hooksPath instead
└── .gitignore                          # Merged with harness template
```

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

To keep this sample validated, add a CI job:

```yaml
# .github/workflows/integration-test.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  harness-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive  # If using submodule method
      - name: Verify harness integration
        run: bash examples/sample-project/verify.sh
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
