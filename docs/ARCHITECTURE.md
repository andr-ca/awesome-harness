# Architecture – agentharness Design

Technical architecture and design philosophy of the agentharness repository.

**This document describes the target architecture, not current inventory.**
Several component categories below (frameworks, most languages, most
pattern categories, `.claude/agents/`) don't have content yet — see
[MANIFEST.md](../MANIFEST.md) for what exists and [ROADMAP.md](../ROADMAP.md)
for what's planned. The layering and design principles are already the
policy for whatever gets built next.

## 🎯 Design Philosophy

### Core Principles

1. **DRY (Don't Repeat Yourself)**
   - Maintain shared knowledge once
   - Reference from multiple projects
   - Update in one place, benefit everywhere

2. **Composability**
   - Components work independently
   - Mix and match as needed
   - Minimal dependencies between components

3. **Discoverability**
   - Clear directory structure
   - Consistent naming conventions
   - Good documentation in every component

4. **Flexibility**
   - Symlink for development
   - Copy for stability
   - Extend for customization

5. **Maintainability**
   - Version control everything
   - Document decisions
   - Regular audits for obsolescence

## 📐 Layered Structure

The harness is organized in conceptual layers:

```
┌─────────────────────────────────────┐
│  Projects (using the harness)      │
├─────────────────────────────────────┤
│  Framework-Specific Layers          │
│  (React, Django, Go, etc.)         │
├─────────────────────────────────────┤
│  Language-Specific Layer            │
│  (TypeScript, Python, Go, etc.)    │
├─────────────────────────────────────┤
│  Pattern & Architecture Layer       │
│  (Agentic loops, error handling,   │
│   testing, API design)              │
├─────────────────────────────────────┤
│  Claude Code & Tools Layer          │
│  (Skills, agents, hooks, tools)    │
├─────────────────────────────────────┤
│  Universal Best Practices           │
│  (Git, development workflow, docs)  │
└─────────────────────────────────────┘
```

## 📦 Component Categories

### 1. Claude Code Assets (`.claude/`)
**Purpose:** Enhance Claude Code and agentic workflows

- **Skills** – Superpowers for specialized tasks
- **Agents** – Custom agent configurations
- **Hooks** – Automation and event handling

**Design:** Minimal dependencies, well-documented, self-contained
**Usage:** Symlink into projects or reference in prompts

### 2. Frameworks (`frameworks/`)
**Purpose:** Framework-specific configurations and best practices

- **Structure:** Each framework is a subdirectory
- **Content:** Config templates, patterns, examples, conventions
- **Scope:** Everything needed to bootstrap a project in that framework

**Design:** Self-contained per framework, links to language guidelines
**Usage:** Copy config files, reference patterns, follow conventions

### 3. Languages (`languages/`)
**Purpose:** Language-specific conventions and idioms

- **Structure:** Each language is a subdirectory
- **Content:** Conventions, idioms, tools, libraries, anti-patterns

**Design:** Framework-agnostic, extended by framework-specific docs
**Usage:** Reference when writing code, share with team

### 4. Patterns (`patterns/`)
**Purpose:** Reusable solutions to common problems

- **Structure:** Pattern category directories (agentic-loops, testing, etc.)
- **Content:** Problem statement, solution, examples, trade-offs

**Design:** Framework and language agnostic where possible
**Usage:** Reference in architecture decisions, implement variations

### 5. Tools (`tools/`)
**Purpose:** Standalone utilities and scripts

- **Structure:** Tool category / tool name subdirectories
- **Content:** Executable, README, config templates, examples

**Design:** Independent, installable, cross-project usable
**Usage:** Symlink, copy, or add to PATH

### 6. Hooks (`.github/hooks/`)
**Purpose:** Automation triggered by events

- **Structure:** Flat directory of hook scripts (currently just
  `prevent-trunk-commit`)
- **Content:** Shell scripts, README, integration instructions

**Design:** Minimal, focused, composable
**Usage:** `git config core.hooksPath .github/hooks` (this repo does this
for itself)

### 7. Documentation (`docs/`)
**Purpose:** Guides and architectural documentation

- **INTEGRATION.md** – How to use harness in projects
- **ARCHITECTURE.md** – This document

**Design:** High-level guidance
**Usage:** Reference when setting up new projects

## 🔄 Dependency Flow

```
Project
  ├─> Skills (.claude/skills/)
  ├─> Framework (frameworks/{framework}/)
  │    └─> Language (languages/{language}/)
  ├─> Patterns (patterns/)
  ├─> Tools (tools/)
  └─> Hooks (hooks/)

Language
  └─> Framework (framework extends language)

Patterns
  └─> Language/Framework (can be applied to any)

Tools
  └─> Standalone (no dependencies)
```

**Design Goal:** Minimize cross-component dependencies, maximize reusability

## 🏗️ Adding New Components

### New Framework
1. Create `frameworks/{framework}/` directory
2. Copy minimal config files
3. Write README with setup instructions
4. Document framework-specific patterns
5. Link to applicable language guidelines

### New Language
1. Create `languages/{language}/` directory
2. Document naming conventions
3. List recommended tools and libraries
4. Note language idioms
5. Document common anti-patterns

### New Pattern
1. Create `patterns/{category}/` directory
2. Write clear problem statement
3. Explain the solution
4. Include before/after examples
5. Document trade-offs and variations

### New Tool
1. Create `tools/{category}/{tool}/` directory
2. Write main executable
3. Include comprehensive README
4. Add configuration templates
5. Create working examples

## 🔍 Discoverability

### By Component Type
- `/frameworks/` – For framework-specific content
- `/languages/` – For language-specific content
- `/.claude/` – For Claude Code tools
- `/patterns/` – For reusable patterns
- `/tools/` – For utilities

### By Metadata
Each component includes frontmatter/metadata:
- Name and description
- Applicable frameworks/languages
- Complexity level
- Dependencies

### By Documentation
- README in every directory
- Clear examples
- Cross-references
- Integration guides

## ⚙️ Integration Architecture

```
agentharness (source)
      ↓
   symlink ├─→ .claude/skills (auto-loaded)
   or copy ├─→ Framework config files
          ├─→ Language guides
          ├─→ Tools in PATH
          └─→ Hooks in git
      ↓
  my-project (target)
```

**Design:** Loose coupling, high cohesion
- Projects don't modify harness
- Harness is read-only from projects
- Projects define CLAUDE.md to document integration

## 📈 Scaling Considerations

As the harness grows:

1. **Version Management**
   - Tag releases in git
   - Projects can pin to versions
   - Breaking changes documented

2. **Organization**
   - Sub-categorize as needed
   - Index files guide navigation
   - Metadata helps with search

3. **Duplication Detection**
   - Regular audits for similar patterns
   - Consolidate or link duplicates
   - Cross-reference variations

4. **Maintenance**
   - Archive outdated content
   - Update links when moving things
   - Keep language/framework versions current

## 🔐 Version Control Strategy

**Harness Repository**
- Store all harnesses in git
- Tag releases in git (v0.1.0 onward — see [CHANGELOG.md](../CHANGELOG.md))
- Keep git history clean
- Document breaking changes in CHANGELOG
- See [RELEASING.md](RELEASING.md) for the versioning policy, release
  checklist, and how a consuming project pins, upgrades, or rolls back

**Project Integration**
- Option 1 (Symlink): No versioning, always latest
- Option 2 (Copy): Commit version reference
- Option 3 (Submodule): Pin in .gitmodules

**Benefits**
- Reproducible builds
- Easy rollback
- Clear history of changes
- Auditable decisions

## 🎓 Evolution & Feedback Loop

```
Use pattern → Discover improvement → Update harness → Benefit all projects
     ↓              ↓                      ↓                  ↓
  in project    by feeding back      centralized          applies
                                      repository          everywhere
```

**Mechanism:**
1. Use harness components in projects
2. Improve or extend as needed
3. Contribute improvements back to harness
4. Document in CHANGELOG
5. All projects benefit from next update

## 📊 Metrics & Health

Monitor harness health:
- **Usage:** How many projects use which components?
- **Maintenance:** Which components are stale?
- **Adoption:** Are new components being used?
- **Quality:** Are components solving real problems?

---

The harness succeeds when it reduces duplication, speeds up development, and improves consistency across projects.
