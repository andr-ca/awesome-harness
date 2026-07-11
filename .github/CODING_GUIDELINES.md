---
description: Universal coding guidelines for quality and consistency across projects
applyTo: all projects using awesome-harness
---

# Coding Guidelines

Core principles for writing clear, maintainable, and consistent code across all languages and frameworks.

## Naming Conventions

- **Types/Classes:** PascalCase
- **Functions/Methods:** camelCase
- **Variables/Properties:** camelCase
- **Constants:** UPPER_SNAKE_CASE (if language supports)
- **Files:** Use whole words, avoid abbreviations
- **Use whole words** when possible — clarity beats brevity

## Comments

### Hard Rules

- **Default to NO comment.** Only add comments when code cannot be self-explanatory through naming.
- **JSDoc/Doc comments:** 1-2 short sentences max. Don't enumerate features, restate signatures, or explain obvious parameters.
- **Inline comments:** Maximum 1 line. Use only for genuine workarounds, non-obvious ordering constraints, or surprising side effects.
- **Never narrate code** — Don't write comments that just repeat what the code does.

### When Comments ARE Needed

- Explaining a workaround or hack with a reference (bug number, external system constraint)
- Documenting a non-obvious design decision or constraint
- Noting subtle ordering requirements or race conditions
- Recording surprising behavior or side effects

### Before Writing a Comment

Stop and ask: *"Can I improve the code itself instead?"*
- Can I rename a variable or function to be clearer?
- Can I extract a well-named function?
- Can I simplify the logic?
- Is the code trying to do too much?

If yes, do that instead. Comments are a code smell pointing to unclear logic.

## Code Quality

### General Principles

- **Don't repeat yourself** – Reuse existing utilities, helpers, and patterns before writing new code.
- **Explicit over implicit** – Clear is better than clever.
- **Simple over complex** – Optimize for readability first, performance second.
- **Obvious dependencies** – All dependencies should be declared/injected, never hidden.

### Specific Practices

- **Avoid `any` or `unknown` types** – Use proper types; if you can't type something, the code design needs improvement.
- **Import management** – Never duplicate imports; reuse existing ones if available. Don't leave blank lines where imports were removed.
- **Use idiomatic patterns** – Before creating new structures, look for existing test patterns and utilities in the codebase.
- **One assertion per test** – Prefer snapshot-style assertions (`assert.deepStrictEqual`) over multiple precise assertions—they're easier to understand and update.
- **Prefer standard async patterns** – Use `async`/`await` over `.then()`/`.catch()` chains in languages that support both.

## Type Safety

### For Typed Languages (TypeScript, Go, etc.)

- Do not export types or functions unless they're genuinely shared across components.
- Do not introduce new types/values to global namespace.
- Prefer explicit type annotations for parameters and return values when they clarify intent.
- Use generics for reusable data structures, not as a workaround for unclear types.

## String & UI Conventions

### Strings

- **User-visible strings:** Marked for externalization/localization with appropriate method per language
- **Avoid string concatenation** for localized text — use placeholder/format syntax instead
- Quote style: Follow your language's idiom (Python: double quotes preferred; TypeScript: your choice)

### UI Labels (If Applicable)

- **Buttons/Commands/Menu items:** Title Case (each major word capitalized)
- **Don't capitalize** prepositions of 4+ letters unless first or last word
- **View titles/Headings:** Sentence case (only first word capitalized), no trailing period

## Style & Formatting

### General

- **Arrow functions** over anonymous function expressions (in languages that support both)
- **Minimize arrow function parameters** – `x => x + x` not `(x) => x + x` where unnecessary
- **Always use braces** for loops and conditionals, even single-statement bodies
- **Opening braces:** Same line as the construct that requires them
- **Spacing:** Single space after commas, colons, semicolons in constructs

### Loops & Conditionals

```
// Good
for (let i = 0; i < n; i++) {
    if (condition) {
        doSomething();
    }
}

// Bad
for (let i = 0; i < n; i++) doSomething();
```

### Functions

- **Prefer named function declarations** over anonymous function expressions at top-level
  - Better stack traces during debugging
  - Easier to reference and understand intent
- Top-level scope: `function x(…) { … }` over `const x = (…) => { … }`

## Testing

### General Rules

- **Don't add tests to wrong suite** – Keep tests organized by the code they test
- **Look for existing patterns** before creating new test structures
- **Use `describe`/`test` consistently** with what's already in the codebase
- **Minimize assertions** – Prefer one comprehensive assertion over many small ones
- **Make dependencies injectable** – Don't stub globals or use `any` casts to inject fakes
  - Add optional constructor parameter with real default
  - Test passes mock that implements the real interface

## Dependency Management

### Dependency Injection

- **Declare dependencies explicitly** in constructors/function parameters
- **Never lazy-resolve** dependencies through service locators
- If a constructor cycle prevents direct injection, break the cycle by:
  - Passing dependency into an `init()` method from the orchestrator
  - Relocating the call site
  - Restructuring the component

### Lifecycle Management

For languages with explicit resource management (Rust, C++, or languages with GC):
- **Register disposables immediately** after creation
- Use helpers like `DisposableStore`, `MutableDisposable`, or `this._register()`
- **Never register a disposable to containing class** if the object is created in a repeatedly-called method (causes memory leaks)
  - Return `IDisposable` and let caller register it
- **File watching:** Prefer correlated file watchers (via service) to shared ones

## Refactoring & Code Review Guidelines

### Before Refactoring

- Don't add features, refactor, or introduce abstractions beyond what the task requires
- A bug fix doesn't need surrounding cleanup; a one-off operation doesn't need a helper
- Three similar lines don't need a premature abstraction
- No half-finished implementations

### During Code Review

- **Trust internal code** and framework guarantees
- **Only validate at boundaries** – user input, external APIs, untrusted data
- **Don't add error handling** for scenarios that can't happen
- **Don't use feature flags** or backwards-compatibility shims when you can just change code

### When Promoting Code

- Avoid backwards-compatibility hacks
- If code is truly unused, delete it completely (no `// removed` comments, no `_` prefixes)
- Don't re-export unused types

## Language-Specific Guidelines

For detailed language-specific conventions, see `languages/{language-name}/CONVENTIONS.md` in awesome-harness.

## Learning & Iteration

When you discover a violation of these guidelines:
1. Note what went wrong
2. Identify why it was a problem
3. Record the learning for future reference
4. Update the relevant instruction file

---

**Philosophy:** These guidelines aim for code that is clear, maintainable, and consistent. When in doubt, choose clarity. When guidelines conflict, defer to your language's idioms and your project's established patterns.

**Last Updated:** 2026-07-11
