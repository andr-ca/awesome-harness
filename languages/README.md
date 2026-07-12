# languages – Language-Specific Guidelines

Language-specific conventions, idioms, best practices, and style guidelines.

## 📁 Language Directories

What exists today (see [MANIFEST.md](../MANIFEST.md) for the authoritative
list):

- **typescript/** – `CONVENTIONS.md`
- **python/** – `README.md`, `CONVENTIONS.md`, `COPILOT_INSTRUCTIONS.md`
- **go/** – `CONVENTIONS.md`

Other languages (Rust, Java, …) aren't built yet — see
[ROADMAP.md](../ROADMAP.md) before assuming one exists.

## 📦 What a Language Directory Can Contain

Not a required shape — `CONVENTIONS.md` alone is enough to start. Add the
others only if there's real content for them, not as placeholders:

```
languages/{language}/
├── README.md              # Language overview and philosophy (optional)
├── CONVENTIONS.md         # Naming conventions and style (the one required file)
├── IDIOMS.md              # Language-specific idioms (optional)
├── TOOLING.md             # Recommended tools and setup (optional)
├── LIBRARIES.md           # Recommended libraries (optional)
└── ANTI_PATTERNS.md       # Common pitfalls to avoid (optional)
```

## 📝 Convention Categories

### Naming Conventions
- Variable naming (camelCase, snake_case, PascalCase)
- Function naming
- Class and type naming
- Constants and enums
- File and directory naming

### Code Style
- Indentation and whitespace
- Line length limits
- Formatting rules
- Comment style

### Best Practices
- Error handling approaches
- Memory management (if applicable)
- Concurrency patterns
- Testing conventions

### Recommended Tools
- Formatters and linters
- Type checkers
- Build tools
- Test frameworks
- Package managers

## 🔗 Linking Framework-Specific Variations

Language guidelines are extended with framework-specific details:
- React-specific TypeScript conventions → `frameworks/react/CONVENTIONS.md`
  (exists today)
- Other frameworks (Django, Vue, …) aren't built yet — see
  [ROADMAP.md](../ROADMAP.md)

## 📝 Adding a New Language

1. Create directory: `languages/{language-name}/`
2. Write README describing language philosophy
3. Document naming and style conventions
4. List common idioms
5. Recommend tools and libraries
6. Note common anti-patterns
7. Link to framework-specific variations

## 🎓 Using Language Guidelines

When coding in a language:
1. Reference `README.md` for overview
2. Check `CONVENTIONS.md` for style decisions
3. Review `IDIOMS.md` for language-specific patterns
4. Consult `LIBRARIES.md` for tool recommendations
5. Avoid patterns listed in `ANTI_PATTERNS.md`

---

These guidelines evolve as you gain experience with each language and discover new conventions.
