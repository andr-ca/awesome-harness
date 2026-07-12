# .github – Repository Configuration & Guidelines

This directory contains repository-wide configuration files, guidelines, and best practices for agentharness and projects that reference it.

## 📋 Files Overview

### Guidelines

- **[CODING_GUIDELINES.md](./CODING_GUIDELINES.md)** – Universal coding standards for quality and consistency
  - Naming conventions across languages
  - Comment best practices and hard rules
  - Code quality principles (no `any`, avoid repetition, etc.)
  - Type safety, strings, UI conventions
  - Testing patterns
  - When to refactor and code review guidelines

- **[COMMITTING_GUIDELINES.md](./COMMITTING_GUIDELINES.md)** – Git commit standards
  - Core rules: respect signing, always run hooks
  - Atomic commits and clear messages
  - What NOT to commit (secrets, debug code, artifacts)
  - Handling hook failures
  - Good/bad commit message examples
  - CI/CD implications

- **[BRANCHING_STRATEGY.md](./BRANCHING_STRATEGY.md)** – Git branching discipline and workflow
  - Never commit to trunk branches (main, master, develop)
  - Branch naming conventions with consistent prefixes
  - Git worktree usage and best practices
  - Comprehensive .gitignore configuration
  - Branch protection and pre-commit hooks
  - Complete lifecycle examples

- **[pull_request_template.md](./pull_request_template.md)** – PR template for consistency
  - Summary, changes, motivation sections
  - Testing checklist
  - Links to related guidelines

- **[ISSUE_TEMPLATE/](./ISSUE_TEMPLATE/)** – `bug_report.md`,
  `feature_request.md`

### Tools & Templates

- **[.gitignore.template](./.gitignore.template)** – Comprehensive gitignore template
  - Worktrees, IDE files, OS files
  - Dependencies, build artifacts
  - Environment variables and secrets (CRITICAL!)
  - Language and framework-specific sections
  - Copy and customize for your project

- **[hooks/](./hooks/)** – Reusable git hooks
  - `prevent-trunk-commit` – Block commits to main/master branches
  - `pre-push` – Run this repo's own test suites and enforce >=80%
    coverage before every push (see `hooks/README.md` for what it
    no-ops on for a consumer repo)
  - Hook setup instructions (manual and Husky)
  - Custom hook templates
  - Troubleshooting guide

### Configuration Files

- **[CODEOWNERS](./CODEOWNERS)** – Required reviewers for protected paths
- **[dependabot.yml](./dependabot.yml)** – Automated dependency updates
- **[workflows/](./workflows/)** – CI (`ci.yml`) and the scheduled online
  link check (`link-check-scheduled.yml`)

## 🎯 How to Use These Guidelines

### For Contributors

1. **Before starting work:** Read [BRANCHING_STRATEGY.md](./BRANCHING_STRATEGY.md)
   - Never commit directly to main/master/trunk
   - Create a feature branch with proper naming
   - Understand worktrees for complex work
   - Configure .gitignore to protect secrets

2. **Before writing code:** Read [CODING_GUIDELINES.md](./CODING_GUIDELINES.md)
   - Understand naming conventions for your language
   - Review comment rules (especially the hard limits)
   - Check code quality principles

3. **Before committing:** Read [COMMITTING_GUIDELINES.md](./COMMITTING_GUIDELINES.md)
   - Ensure commits are atomic and meaningful
   - Write clear commit messages
   - Don't bypass hooks

4. **When creating a PR:**
   - PR template is auto-populated — fill it out carefully
   - Reference the guidelines in your PR description
   - Link to related issues
   - Ensure branch is up-to-date with main

### For Code Reviewers

1. **Check against guidelines:**
   - Do names follow conventions?
   - Are there unnecessary comments?
   - Are there code quality violations?
   - Are tests written properly?

2. **Verify commit quality:**
   - Are commits atomic?
   - Are messages clear and meaningful?
   - Can any commits be squashed or reordered?

## 🔄 Updating Guidelines

When guidelines change or new practices are established:

1. Update the relevant `.md` file
2. Consider adding a "Learnings" section noting why the change was made
3. Create a PR clearly explaining the change
4. Git commit history will record when updates were made — no manual timestamps needed

## 🌍 Using in Your Projects

Projects can reference these guidelines in their own `.github/` or `CLAUDE.md`:

```markdown
## Guidelines

This project follows agentharness guidelines:
- [Coding Guidelines](https://github.com/andr-ca/agentharness/blob/main/.github/CODING_GUIDELINES.md)
- [Committing Guidelines](https://github.com/andr-ca/agentharness/blob/main/.github/COMMITTING_GUIDELINES.md)

See `.github/` in this project for project-specific customizations.
```

Or create your own extensions:

```
your-project/.github/
├── CODING_GUIDELINES.md (extends agentharness)
└── CUSTOM_GUIDELINES.md
```

## 📝 Guidelines Philosophy

These guidelines are designed to:

- **Maintain clarity** – Code should be obvious from naming and structure
- **Respect security** – Never bypass security measures like commit signing
- **Honor contribution history** – Commits should clearly explain decisions
- **Enable collaboration** – Clear standards help teams work together
- **Prevent common mistakes** – Rules address real problems, not theoretical ones

## 🔗 Related Documentation

- **Coding Guidelines Detail:** See specific language guides in `languages/{language}/CONVENTIONS.md`
- **Framework Specifics:** See `frameworks/{framework}/CONVENTIONS.md` (see `frameworks/README.md` for what exists today)
- **Pattern Documentation:** See `patterns/{pattern}/README.md`

## ❓ Questions?

- **About branching and workflows?** Check `BRANCHING_STRATEGY.md`
- **About branch naming?** See prefix conventions in `BRANCHING_STRATEGY.md`
- **About git worktrees?** Check `BRANCHING_STRATEGY.md` for when/how to use
- **About .gitignore?** Use the template in `.gitignore.template`
- **About pre-commit hooks?** See `hooks/README.md`
- **About code style?** Check `CODING_GUIDELINES.md`
- **About committing?** Check `COMMITTING_GUIDELINES.md`
- **About PR process?** Use the PR template and reference guidelines

---

**Remember:** Guidelines exist to help, not hinder. They're based on real lessons learned and should make your work easier, not harder.
