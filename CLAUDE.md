# awesome-harness – Claude Code Integration Guide

Instructions for using this central harness repository with Claude Code, Claude agents, and coding workflows.

## 🤖 Agent Workflow Completion (MANDATORY)

**When an agent finishes work on a task, it MUST always complete the workflow:**

1. ✅ **Verify all work is done** — tests pass, coverage ≥80%, lint passes, no TODOs
2. ✅ **Create atomic commits** — one logical unit per commit, clear message explaining WHY
3. ✅ **Push to remote** — push branch to origin with tracking (`git push -u origin branch-name`)
4. ✅ **Create pull request** — use `gh pr create` with title, body summary, and checklist
5. ✅ **Never leave work uncommitted** — work in progress that isn't pushed is work that doesn't exist

**An agent claiming work is "complete" without a PR/commit is incomplete.** Always finish the workflow.

## 🔍 Agent Recommendation Assessment & Implementation (MANDATORY)

**When an agent is asked to address/review/look into recommendations:**

1. **Assess each item** — evaluate positive vs. negative impact (complexity, effort, risk, benefit)
2. **If overall impact is POSITIVE:**
   - ✅ Implement all changes **despite** complexity or effort required
   - ✅ Create atomic commits for each logical change
   - ✅ Push all commits to remote with PR
   - ✅ **Report status in `<recommendations>-status.md`** with:
     - Timestamp (ISO 8601: `2026-07-11T14:30:00Z`)
     - Summary of what was implemented
     - Rationale for positive/negative aspects of each recommendation
     - Link to PR(s)
   - ✅ Never decline recommendations because "they're too much work"

3. **If potential outcome is NEGATIVE or HIGH-RISK:**
   - 🚨 **Escalate to user immediately** — do not implement
   - Include: specific concern, risk analysis, request guidance
   - Provide the assessment document for user review

**This applies to:**
- Recommendations from reviews, audits, or assessments
- All work on this repository (awesome-harness)
- All harnesses and projects consuming this harness

**Rationale:** Recommendations only improve systems if they're acted upon. Complexity is not a reason to decline improvements. Risk is a reason to consult, not abandon.

---

## 🎯 Core Principles

1. **DRY (Don't Repeat Yourself)** – Maintain harnesses once, reuse across all projects
2. **Composability** – Mix and match skills, tools, and patterns as needed
3. **Version Control** – Track all harnesses in git for reproducibility
4. **Documentation** – Every skill/pattern includes clear usage instructions
5. **Testability** – Harnesses are tested before being added to this repo

## 📋 What This Repo Contains

### 1. **Claude Code Skills** (`.claude/skills/`)
Custom superpowers/skills for Claude Code that enhance coding workflows:
- Testing strategies
- Code review patterns
- Architecture design
- Deployment workflows
- Language-specific tools

**How to use:**
```bash
# In a project, symlink skills from this harness
ln -s ~/awesome-harness/.claude/skills ~/.claude/skills
```

### 2. **Agent Definitions** (`.claude/agents/`)
Custom agent configurations for specialized tasks:
- Code explorers for codebase analysis
- Architects for design planning
- Reviewers for quality assurance
- Debuggers for problem-solving

**How to use:**
- Reference agents by name in Claude Code prompts
- Stack agents for complex multi-step workflows

### 3. **Hooks** (`.claude/hooks/`, `hooks/`)
Automation triggered by specific events:
- Pre-commit validation
- Post-merge workflows
- Build automation
- Test triggering

**How to use:**
```bash
# Copy or symlink hooks to project
cp ~/awesome-harness/hooks/pre-commit/* .husky/pre-commit
```

### 4. **Framework Harnesses** (`frameworks/`)
Complete tool configurations and best practices for specific frameworks:
- TypeScript/Next.js setup
- React patterns and components
- Django best practices
- Go conventions
- etc.

**How to use:**
- Reference as templates for new projects in that framework
- Copy configuration files as starting points
- Use pattern examples as reference

### 5. **Language Guidelines** (`languages/`)
Language-specific conventions and idioms:
- Naming conventions
- Code organization
- Style preferences
- Library recommendations

**How to use:**
- Consult when writing in that language
- Share with Claude Code for context
- Use as basis for project-specific style guides

### 6. **Patterns & Best Practices** (`patterns/`)
Reusable architectural and implementation patterns:
- Agentic loops for automation
- Error handling strategies
- Testing approaches
- API design patterns

**How to use:**
- Reference in design documents
- Implement in projects that need that pattern
- Extend with project-specific variations

### 7. **Tools & Utilities** (`tools/`)
Standalone scripts and utilities:
- Build helpers
- Development tools
- Deployment scripts
- Code generation utilities

**How to use:**
```bash
# Make available globally or in project
ln -s ~/awesome-harness/tools/lint /usr/local/bin/lint-custom
# OR reference in package.json scripts
```

## 🔄 Workflow Integration

### Setting Up a New Project

1. **Initialize with this harness:**
   ```bash
   # Create project
   mkdir my-project && cd my-project
   git init
   
   # Link harness components
   ln -s ~/awesome-harness/.claude/skills .claude/skills
   ln -s ~/awesome-harness/.claude/hooks .claude/hooks
   ```

2. **Choose framework/language harnesses:**
   ```bash
   # For a React project
   cp ~/awesome-harness/frameworks/react/tsconfig.json .
   cp ~/awesome-harness/frameworks/react/.eslintrc.json .
   ```

3. **Import relevant patterns:**
   - Copy pattern documentation
   - Reference in architecture decisions
   - Adapt to project-specific needs

### Using Skills in Claude Code

Skills are automatically loaded when referenced in Claude Code prompts. Examples:

```
# Use a specific skill
/code-review-advanced   # If this skill exists in .claude/skills/

# Reference patterns in your request
"Use the error-handling pattern from the harness for this API"
```

### Maintaining Consistency

- All projects should reference this harness for baseline tools/skills
- Project-specific customizations go in project `.claude/` directories
- Generic improvements should be contributed back to this harness
- Document any harness extensions you create

## 📚 File Organization Rules

### Skills Frontmatter
Every skill must include metadata:
```yaml
---
name: skill-name
description: One-line description of what this skill does
metadata:
  type: [skills|agents|hooks]
  frameworks: [react, vue, django, etc.]  # Optional
  languages: [typescript, python, etc.]   # Optional
  complexity: [low|medium|high]
  requires:
    - optional-dependency
---

<SKILL-CONTENT>
```

### Documentation Requirements
- Every tool/script includes a README or inline documentation
- Skills include usage examples
- Patterns include before/after comparisons
- Framework harnesses document required dependencies

## 📋 Operational Documents

Temporary, working, and operational documents must be stored in **`docs/operational/`** to keep the core repository clean and focused on persistent harnesses.

### What Goes in `docs/operational/`
- Work-in-progress documentation
- Temporary research or exploration notes
- Agent execution logs and transcripts
- Task planning and tracking documents
- Experiment results and findings
- Meeting notes related to harness decisions
- Iteration history and drafts

### Structure
```
docs/operational/
├── CURRENT_TASKS.md          # Active tasks and priorities
├── research/                 # Temporary research documents
│   └── {topic}/              # By topic (e.g., react-patterns, python-conventions)
├── experiments/              # Tests and explorations
├── agent-logs/               # Claude agent execution logs
├── planning/                 # Planning documents and brainstorms
└── archives/                 # Old operational docs (for reference)
```

### Key Rules
1. **Persistent content goes in main harness** – Only move to root structure when content is stable and reusable
2. **Regular cleanup** – Archive or delete outdated operational docs
3. **Not version-critical** – These documents don't need to be tracked as closely in git history
4. **Indexed for retrieval** – Keep an index/manifest of active documents
5. **Temporary only** – If it's still useful after stabilizing, move to permanent location

### Workflow
```
Claude agent creates temporary doc → stored in docs/operational/{type}/
↓
Review and validate content
↓
If reusable & stable → move to appropriate permanent location
If temporary only → archive in docs/operational/archives/
If obsolete → delete
```

## 🚀 Best Practices

### When Adding New Content
1. **Check for duplicates** – Don't add if similar exists elsewhere
2. **Write clear documentation** – Future you will thank you
3. **Include examples** – Show concrete usage, not just theory
4. **Test thoroughly** – Verify before committing
5. **Tag appropriately** – Use metadata for discoverability
6. **Link related items** – Cross-reference similar skills/patterns

### When Using This Harness
1. **Start with relevant framework harness** if it exists
2. **Review language guidelines** for idioms and conventions
3. **Search patterns** before implementing custom solutions
4. **Reference skills in Claude prompts** to guide behavior
5. **Keep project-specific customizations separate** from harness

### When Importing Into Projects
1. **Use symlinks** when possible to stay in sync
2. **Document what you imported** in project's CLAUDE.md
3. **Override only when necessary** – prefer harness patterns
4. **Feed back improvements** – Share innovations with harness
5. **Version lock if needed** – Copy specific versions for stability

## 🔍 Discovery

**Finding skills:** Check `.claude/skills/` or search by tag in filenames
**Finding patterns:** Browse `patterns/` directory
**Finding frameworks:** Look in `frameworks/{framework-name}/`
**Finding language guides:** Check `languages/{language-name}/`

## 💡 Tips

- **Symlink, don't copy** – Stay synchronized with harness updates
- **Read metadata** – Frontmatter tells you dependencies and scope
- **Check examples** – Most skills include usage examples
- **Cross-reference** – Look for linked skills in documentation
- **Extend carefully** – Override only what your project specifically needs

## 🔗 Project Integration Template

Include this in each project's CLAUDE.md:

```markdown
## Harness Integration

This project uses the awesome-harness for:
- Skills: [list what skills are used]
- Framework: [framework name and version]
- Language: [primary language and version]
- Patterns: [which patterns are implemented]

Location: ~/awesome-harness
Reference: [specific version/commit if pinned]
```

## 📞 Support

- **Questions about a skill?** Check the skill's documentation
- **Want to add something?** Ensure it fits the organizational structure
- **Found a bug?** Update it here so all projects benefit
- **Need something new?** Check if a pattern already exists first

---

**Remember:** This harness is only valuable if it's kept up-to-date and actively used. Maintain it as your "trusted toolkit" across all coding projects.
