# patterns – Reusable Architecture & Implementation Patterns

Framework-agnostic patterns and best practices for common problems.

## 📁 Pattern Categories

What exists today (see [MANIFEST.md](../MANIFEST.md) for the authoritative
list):

- **agentic-loops/** – Tested agent-loop reference implementation
- **error-handling/** – Retry, circuit-breaker, structured logging
- **testing/** – TDD, coverage, Playwright, completion checklist
- **logging/** – Logging standards + example config + loader
- **profiles/** – Rigor-tier profiles (prototype/internal/production)

Other pattern categories (API design, …) aren't built yet — see
[ROADMAP.md](../ROADMAP.md) before assuming one exists.

## 📚 What a Pattern Directory Can Contain

Not a required shape — a `README.md` is enough to start; not every
pattern here has `examples/` or a separate `implementation.md` as its own
file (some fold the implementation into `README.md` directly):

```
patterns/{pattern-category}/
├── README.md           # Overview and rationale
├── examples/           # Before/after or working examples (optional)
└── implementation.md   # Step-by-step implementation guide (optional)
```

## 🎯 Pattern Template

When documenting a pattern, include:

1. **Problem Statement** – What problem does this solve?
2. **Pattern Overview** – How it works at a high level
3. **Trade-offs** – Pros and cons of this approach
4. **Before/After** – Comparison with naive approach
5. **Implementation Guide** – Step-by-step instructions
6. **Examples** – Working code examples
7. **When to Use** – Context and scenarios
8. **Variations** – Framework-specific adaptations

## 🔗 Linking to Other Resources

Patterns reference:
- **Specific frameworks** – Link to `frameworks/{framework}/`
- **Language guidelines** – Link to `languages/{language}/`
- **Tools** – Link to applicable tools in `tools/`

## 📝 Adding a New Pattern

When you discover or create a reusable pattern:

1. Name it clearly and descriptively
2. Document the problem it solves
3. Include working examples
4. Note which frameworks/languages it applies to
5. Link to related patterns

---

These patterns are language and framework-agnostic where possible, with framework-specific variations documented.
