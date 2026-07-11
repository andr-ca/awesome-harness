# .github – Repository Configuration & Guidelines

This directory contains repository-wide configuration files, guidelines, and best practices for awesome-harness and projects that reference it.

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

- **[pull_request_template.md](./pull_request_template.md)** – PR template for consistency
  - Summary, changes, motivation sections
  - Testing checklist
  - Links to related guidelines

### Configuration Files

- **dependabot.yml** – Dependency update automation
- **CODEOWNERS** – Code ownership and review routing
- Other GitHub-specific configurations

## 🎯 How to Use These Guidelines

### For Contributors

1. **Before writing code:** Read [CODING_GUIDELINES.md](./CODING_GUIDELINES.md)
   - Understand naming conventions for your language
   - Review comment rules (especially the hard limits)
   - Check code quality principles

2. **Before committing:** Read [COMMITTING_GUIDELINES.md](./COMMITTING_GUIDELINES.md)
   - Ensure commits are atomic and meaningful
   - Write clear commit messages
   - Don't bypass hooks

3. **When creating a PR:**
   - PR template is auto-populated — fill it out carefully
   - Reference the guidelines in your PR description
   - Link to related issues

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
2. Add a "Last Updated" date
3. Consider adding a "Learnings" section noting why the change was made
4. Create a PR clearly explaining the change

## 🌍 Using in Your Projects

Projects can reference these guidelines in their own `.github/` or `CLAUDE.md`:

```markdown
## Guidelines

This project follows awesome-harness guidelines:
- [Coding Guidelines](https://github.com/andrey/awesome-harness/.github/CODING_GUIDELINES.md)
- [Committing Guidelines](https://github.com/andrey/awesome-harness/.github/COMMITTING_GUIDELINES.md)

See `.github/` in this project for project-specific customizations.
```

Or create your own extensions:

```
your-project/.github/
├── CODING_GUIDELINES.md (extends awesome-harness)
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
- **Framework Specifics:** See `frameworks/{framework}/README.md`
- **Pattern Documentation:** See `patterns/{pattern}/README.md`

## ❓ Questions?

- **About code style?** Check `CODING_GUIDELINES.md`
- **About committing?** Check `COMMITTING_GUIDELINES.md`
- **About PR process?** Use the PR template and reference guidelines

---

**Remember:** Guidelines exist to help, not hinder. They're based on real lessons learned and should make your work easier, not harder.

**Last Updated:** 2026-07-11
