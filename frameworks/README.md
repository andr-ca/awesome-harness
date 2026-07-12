# frameworks – Framework-Specific Harnesses

Framework-specific configurations, templates, best practices, and patterns.

## 📁 Framework Directories

What exists today (see [MANIFEST.md](../MANIFEST.md) for the authoritative
list):

- **react/** – `CONVENTIONS.md` only (component naming, props typing — an
  add-on layered on top of `languages/typescript/CONVENTIONS.md`)

Other frameworks (Vue, Angular, Django, Express, …) aren't built yet —
see [ROADMAP.md](../ROADMAP.md) before assuming one exists.

## 📦 What a Framework Directory Can Contain

Not a required shape — `react/` today is just `CONVENTIONS.md`. Add the
others only once there's real content for them:

```
frameworks/{framework}/
├── README.md              # Framework-specific overview (optional)
├── CONVENTIONS.md         # Style and naming conventions (the one required file)
├── setup/                 # Initial setup templates (optional)
├── patterns/              # Framework-specific patterns (optional)
├── examples/               # Working examples (optional)
└── tools/                 # Framework-specific utilities (optional)
```

## 🚀 Using a Framework Guide

Reference it directly rather than copying — like the `languages/` guides,
these are meant to be read, not vendored (see
[docs/INTEGRATION.md](../docs/INTEGRATION.md)'s "Language Guidelines"
section):

```markdown
<!-- In your project's CLAUDE.md -->
React conventions: see ~/agentharness/frameworks/react/CONVENTIONS.md
```

## 📝 Adding a New Framework

1. Create a directory: `frameworks/{framework-name}/`
2. Add a README explaining the framework
3. Include setup templates and common configurations
4. Document patterns specific to this framework
5. Add examples showing best practices
6. Link to language-specific guidelines in `languages/`

---

Each framework should be relatively self-contained but reference shared patterns from `patterns/` directory.
