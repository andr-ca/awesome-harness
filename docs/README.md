# Documentation – agentharness Guides

Guides for understanding and using the agentharness repository.

## Documentation Index

- **[Main README](../README.md)** – repository overview and what exists today
- **[CLAUDE.md](../CLAUDE.md)** – agent-facing router and mandatory rules
- **[MANIFEST.md](../MANIFEST.md)** – full index of every real asset
- **[ROADMAP.md](../ROADMAP.md)** – what's planned but not built
- **[CHANGELOG.md](../CHANGELOG.md)** – release history
- **[SECURITY.md](../SECURITY.md)** – secrets-in-history procedure
- **[INTEGRATION.md](./INTEGRATION.md)** – symlink/copy/submodule methods, per-component steps
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** – design philosophy and target-state layering

## Finding What You Need

### "I'm starting a new project"
1. Read the main README for what exists today.
2. Run `tools/setup/harness-link.sh` (see INTEGRATION.md) or follow the
   manual steps there.
3. Reference `languages/python/` for conventions (only language
   available today).

### "I want to improve my coding practices"
1. Check `.github/CODING_GUIDELINES.md` — start with the Rigor Tiers
   section to know which mandates apply to what you're writing.
2. Review `patterns/testing/` and `patterns/logging/`.
3. Use the Claude Code skills in `.claude/skills/` — they load on
   demand instead of requiring you to read the full guide every time.

### "I need to integrate the harness into a project"
1. Read INTEGRATION.md for the three methods and their tradeoffs.
2. Run `tools/setup/harness-link.sh` for the fast path, or follow the
   manual per-component steps.

### "I want to understand the overall design"
1. Read ARCHITECTURE.md — note its "target architecture, not current
   inventory" disclaimer at the top.
2. Check MANIFEST.md for what's actually built vs. ROADMAP.md for
   what's planned.

## Component Documentation

| Directory | README | Purpose |
|-----------|--------|---------|
| `.claude/` | [README](../.claude/README.md) | Claude Code skills |
| `frameworks/` | [README](../frameworks/README.md) | Placeholder — no framework content built yet |
| `languages/` | [README](../languages/README.md) | Language conventions (Python only so far) |
| `patterns/` | [README](../patterns/README.md) | Reusable patterns (testing, logging) |
| `tools/` | [README](../tools/README.md) | Utility scripts |
| `.github/hooks/` | [README](../.github/hooks/README.md) | Git hooks |

## How Documentation is Organized

```
docs/
├── README.md                    # This file (navigation hub)
├── INTEGRATION.md               # How to use in projects
└── ARCHITECTURE.md              # Design and philosophy

Plus in component directories:
  frameworks/README.md
  languages/README.md
  patterns/README.md
  tools/README.md
  .github/hooks/README.md
  .claude/README.md
```

**Philosophy:** Documentation lives close to the code it describes.

## Contributing to Documentation

When adding new components:
1. Write a README explaining the component.
2. Include a real, runnable usage example — not just a description.
3. Add an entry to [MANIFEST.md](../MANIFEST.md).
4. Add frontmatter if it's a skill.

## FAQ

**Q: Where should I put my custom skills?**
A: In your project's `.claude/skills/` directory. Link agentharness
skills into it via `tools/setup/harness-link.sh` or a manual symlink.

**Q: Can I modify harness components?**
A: Yes — copy and customize for your project. Consider contributing
generic improvements back.

**Q: How do I stay updated?**
A: Symlinks auto-update; copies need a manual re-sync (see
INTEGRATION.md's "Keeping Projects Updated" section).

**Q: Where are framework setup templates?**
A: Not built yet — see [ROADMAP.md](../ROADMAP.md).

---

**Start here:** [README.md](../README.md) → [CLAUDE.md](../CLAUDE.md) → [INTEGRATION.md](./INTEGRATION.md)
