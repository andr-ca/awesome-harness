# docs/operational – Temporary & Working Documents

This directory contains temporary, transient, and operational documents that support the development and maintenance of agentharness. Content here is **not permanent** and follows different lifecycle rules than the main harness components.

## 📁 Structure

```
docs/operational/
├── README.md                    # This file
├── INDEX.md                     # Current index of active documents
├── research/                    # Temporary research and exploration
│   └── {topic}/                 # Organized by topic
├── experiments/                 # Tests, trials, and experimentation
├── agent-logs/                  # Claude agent execution transcripts
├── planning/                    # Planning docs, brainstorms, strategies
└── archives/                    # Older operational docs for reference
```

Only `README.md` and `INDEX.md` exist yet — the subdirectories above are
created on demand, the first time something actually goes in them. Don't
pre-create empty directories; git doesn't track them anyway.

## 🎯 Purpose

This directory serves as a **working space** for:
- Claude agents exploring and researching topics
- Planning new harness components
- Testing and validating ideas
- Documenting exploratory work
- Capturing agent execution logs for reference
- Temporary problem-solving notes

**It is NOT** where:
- Finalized harness components go (they go to root structure)
- Permanent documentation lives (see `docs/` instead)
- Configuration files belong (see specific component dirs)

## 📋 Subdirectory Guide

### `research/`
**Purpose:** Store temporary research, exploration notes, and findings

- Used when investigating new frameworks, languages, or patterns
- Created by Claude agents during discovery/analysis
- Organized by research topic (e.g., `research/react-hooks-patterns/`)
- Cleaned up once findings are consolidated into harness

**Example:**
```
research/
├── typescript-conventions/
│   ├── style-comparison.md      # Comparing 3 TS style approaches
│   ├── tooling-survey.md        # Notes on TS linters/formatters
│   └── examples/                # Working examples during research
└── django-patterns/
    ├── db-design-exploration.md # Database pattern research
    └── orm-comparison.md        # ORM evaluation notes
```

### `experiments/`
**Purpose:** Test ideas and validate approaches before documenting

- Proof-of-concept implementations
- Test runs of potential patterns
- Validation of harness components
- Benchmark or performance testing
- Can be deleted once findings are documented

**Example:**
```
experiments/
├── agentic-loop-v2/
│   ├── test-implementation.md   # Experimental loop implementation
│   ├── results.md               # Test outcomes and metrics
│   └── code/                    # Working code samples
└── skill-optimization/
    ├── performance-test.md      # Speed comparisons
    └── refactoring-notes.md     # Optimization attempts
```

### `agent-logs/`
**Purpose:** Store Claude agent execution logs and transcripts

- Execution logs from planning/research agents
- Brainstorming session transcripts
- Multi-agent orchestration logs
- Analysis and investigation results
- Reference for understanding decisions made

**Example:**
```
agent-logs/
├── 2026-07-11-framework-research.md    # Agent research on React patterns
├── 2026-07-10-architecture-design.md   # Agent architecture planning
└── 2026-07-09-pattern-validation.md    # Agent testing pattern ideas
```

**Naming:** Use date prefix (YYYY-MM-DD) for easy chronological reference

### `planning/`
**Purpose:** Strategic planning and brainstorming documents

- Roadmaps for harness development
- Feature planning and prioritization
- Brainstorming new harness components
- Project retrospectives
- Decision records during planning phases
- Strategic direction documents

**Example:**
```
planning/
├── H2-2026-roadmap.md           # Second half 2026 priorities
├── framework-additions.md       # Plan for adding new frameworks
├── pattern-expansion.md         # Ideas for new patterns
└── infrastructure-redesign.md   # Exploring harness restructuring
```

### `archives/`
**Purpose:** Store older operational documents for reference

- Outdated research that remains relevant as context
- Completed projects with historical value
- Old experimental results
- Previous brainstorm sessions
- Superseded planning documents

**When to move to archives:**
1. Document is no longer actively used
2. Content is still valuable for context/history
3. Findings have been consolidated elsewhere
4. Ready to clean up the main operational directory

**Example:**
```
archives/
├── 2026-Q1-experiments/         # Q1 experimentation results
├── old-framework-research/      # Superseded by new research
└── deprecated-patterns/         # Patterns that didn't work out
```

## 📝 Guidelines

### Creating Operational Documents

1. **Date everything** – Use ISO format (YYYY-MM-DD) in filename or front matter
2. **Link to context** – Reference what this document relates to
3. **Mark status** – Note if it's in-progress, pending review, or complete
4. **Plan the outcome** – Will this become a harness component, be archived, or deleted?
5. **Include metadata** – Topic, creator/agent, purpose at the top

**Template:**
```markdown
---
date: 2026-07-11
status: in-progress         # in-progress, pending-review, completed
topic: [research|experiment|planning|logs]
purpose: Brief description of what this document explores
related-harness: [path/to/component] (if any)
---

# Title

## Overview
What is this document about?

## Status
Current status and next steps

## Findings/Results
Key takeaways

## Next Actions
What happens with this work?
```

### Lifecycle of an Operational Document

```
CREATED (in docs/operational/{category}/)
    ↓
DEVELOPED (researched, tested, refined)
    ↓
    ├─ COMPLETE & VALUABLE ──→ MOVE to harness structure
    ├─ USEFUL FOR CONTEXT ───→ ARCHIVE (docs/operational/archives/)
    └─ OBSOLETE ────────────→ DELETE
```

### When to Archive

Move documents to `archives/` when they are:
- No longer actively referenced
- Superseded by newer versions
- Contain valuable historical context
- Keep indefinitely for reference value

**Example:** "Old React patterns research before we established our current standard"

### When to Delete

Delete documents when they are:
- Truly obsolete with no reference value
- Replaced by better documentation
- Duplicative of content elsewhere
- Sensitive or confidential

**Policy:** Review operational docs quarterly; archive or delete outdated items

### When to Promote to Harness

Move content from operational to permanent harness when:
- Findings are validated and stable
- Pattern/approach is proven reusable
- Ready for project-wide reference
- Sufficiently documented

**Example:** `docs/operational/research/typescript-conventions/` → `languages/typescript/CONVENTIONS.md`

## 🔍 Finding What You Need

### INDEX.md
Keep an active index at `docs/operational/INDEX.md`:

```markdown
# Operational Documents Index

## Active Documents
- research/react-patterns/ – Ongoing React pattern research
- planning/H2-roadmap.md – Second half 2026 priorities
- agent-logs/2026-07-11-*.md – Recent agent executions

## Recently Completed
- experiments/skill-optimization/ – Performance testing complete

## Archives
See archives/ for historical documents and superseded research
```

### Search Tips
- Use `docs/operational/INDEX.md` for quick navigation
- Prefix files with dates for chronological sorting
- Use topic subdirectories for related materials
- Cross-link between operational docs

## 🧹 Maintenance

### Regular Cleanup (Monthly)
1. Review `docs/operational/` contents
2. Archive completed documents
3. Delete truly obsolete items
4. Update `INDEX.md`
5. Move promoted items to harness

### Quarterly Review (Seasonal)
1. Evaluate archived documents
2. Consolidate duplicate research
3. Update planning documents
4. Clean old agent logs (keep last 3 months active)
5. Publish summary of findings

### Before Major Releases
1. Archive all active-dated documents
2. Promote any findings to harness components
3. Clean up archives of truly obsolete items
4. Update INDEX with current state

## ⚠️ Important Notes

- **Not for secrets** – Never commit sensitive information here
- **Tracked in git, like everything else in this repo** – see
  `CLAUDE.md`'s Version Control principle. "Temporary" describes the
  content's expected lifespan and promote/archive/delete workflow, not
  whether it's version-controlled — it always is.
- **Confidentiality** – Ensure no private project details
- **Size limits** – Keep individual docs under 50KB if possible
- **No binary files** – Keep everything text-based for git efficiency

## 📌 Quick Reference

| Type | Storage | Lifetime | Action |
|------|---------|----------|--------|
| Research findings | `research/` | Until promoted or archived | Consolidate or archive |
| Experiments | `experiments/` | While in testing | Delete if proven wrong, archive if valuable |
| Planning docs | `planning/` | Active planning period | Archive when period ends |
| Agent logs | `agent-logs/` | 3-6 months active | Archive older logs |
| Validated findings | ← Move to harness → | Permanent | Part of main repository |

---

**Remember:** This is a working space. Keep it clean, organized, and purposeful. When something becomes stable and reusable, graduate it to the main harness structure.
