---
description: Universal coding guidelines for quality and consistency across projects
applyTo: all projects using agentharness
---

# Coding Guidelines

Core principles for writing clear, maintainable, and consistent code across all languages and frameworks.

## Rigor Tiers

The mandates below (TDD, 80% coverage, Playwright, OTEL-grade logging)
apply in full at the **Production** tier. Applying them uniformly to
every script or prototype produces unfollowable rules, and unfollowable
rules teach agents (and humans) to discount all rules, including the ones
that matter. Pick a tier before writing code, state it in the PR
description if it's not obvious, and apply the matching column.

| | Prototype / Exploration | Internal Tool | Production Service |
|---|---|---|---|
| **Examples** | Spike, notebook, one-off script, "does this API even work" | Internal dashboard, CLI used by the team, migration script run once | Anything customer-facing, anything another service depends on, anything that handles user data |
| **Tests** | Optional | Cover the logic that would be expensive to get wrong; skip pure glue | Full TDD, 80% coverage minimum (see `COVERAGE_REQUIREMENTS.md`) |
| **UI testing** | Manual is fine | Manual is fine unless it's shared broadly | Playwright + screenshot verification mandatory (see `patterns/testing/PLAYWRIGHT_UI_TESTING.md`) |
| **Logging** | `print`/`console.log` is fine | Structured logs for anything you'll need to debug later | Full logging/telemetry standard (see `patterns/logging/`) |
| **Error handling** | Let it crash | Handle errors at boundaries you actually hit | Handle all documented failure modes; still don't handle the impossible ones |
| **Review** | None required | Self-review | PR + the full checklist in `COMPLETION_CHECKLIST.md` |

If you're not sure which tier you're in, ask: "if this breaks at 3am, does
it page someone who isn't me?" If yes, it's Production tier regardless of
how small the change looks.

**Selecting a tier, not just reading about it:** see
[`patterns/profiles/`](../patterns/profiles/README.md) for this table as
machine-readable YAML, how a project declares its tier via
`.agentharness-profile`, the precedence order between an explicit
request/repo-local override/profile/language add-on/generic default, and
the current state of mechanical enforcement (enforced for Python, Go, and
`node --test`/Vitest JS/TS projects via `harness-link.sh enforce-profile`,
with a `--strict` mode; advisory for everything else — see that file for
the exact boundary and what's planned).

The minimalism principles elsewhere in this doc ("trust internal code,"
"don't add error handling for scenarios that can't happen," "three
similar lines don't need an abstraction") apply at every tier — rigor
tiers control *how much verification* you add, not whether you're allowed
to over-engineer the solution itself.

At the Production tier specifically: TDD and 80% coverage
(`patterns/testing/TDD.md`, `COVERAGE_REQUIREMENTS.md`), Playwright +
screenshot verification for web UI (`PLAYWRIGHT_UI_TESTING.md`), and full
logging/telemetry (`patterns/logging/`) are all non-negotiable — see each
doc for specifics, and `COMMITTING_GUIDELINES.md` for the commit → push →
PR workflow completion requirement. This section doesn't restate them;
one source of truth per rule.

---

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

- **Avoid `any`** – Use proper types; if you can't type something, the code design needs improvement. `unknown` is not the same problem as `any` — it's TypeScript's type-safe alternative (forces a check/narrow before use) and is the *correct* tool when a value's type genuinely can't be known at the call site (e.g. parsing untrusted JSON). Don't ban it alongside `any`.
- **Import management** – Never duplicate imports; reuse existing ones if available. Don't leave blank lines where imports were removed.
- **Use idiomatic patterns** – Before creating new structures, look for existing test patterns and utilities in the codebase.
- **One behavior per test, one assertion where possible** – When a test's expected outcome is a single composite value (e.g. an object with several fields), assert it in one snapshot-style comparison (`assert.deepStrictEqual`) rather than one `assert` per field — same behavior, one assertion, easier to update. When two checks verify genuinely independent behaviors (e.g. "creation succeeds" vs. "duplicate email is rejected"), that's two tests, not one test with two assertions. See `patterns/testing/TDD.md`'s "Common mistake: testing multiple things at once" example for the worked case.
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
- **One behavior, one assertion** – see "Specific Practices" above; not restated here
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

For resources that need explicit cleanup (file handles, sockets, timers,
subscriptions, watchers — not memory, which the GC/borrow checker already
handles):
- **Tie cleanup to a scope, not to manual bookkeeping.** Use your
  language's native mechanism: `with` / context managers (Python),
  `using` / `IDisposable` (C#), RAII destructors (C++/Rust), `defer`
  (Go), `try-with-resources` (Java). Prefer these over a hand-rolled
  registry of things to clean up later.
- **If you do need a registry** (e.g. a component that owns several
  subscriptions with the same lifetime), create it in the constructor and
  dispose it in one place — don't scatter cleanup calls across the class.
- **Never accumulate disposables on a long-lived owner** for objects
  created inside a method that runs repeatedly (a request handler, a
  render loop) — that's a leak. Return the resource/handle to the caller
  that actually owns its lifetime instead.
- **File watching:** prefer one watcher instance shared/injected via a
  service over each component creating its own — cheaper and avoids
  duplicate events.

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

For detailed language-specific conventions, see `languages/{language-name}/CONVENTIONS.md` in agentharness.

## Learning & Iteration

When you discover a violation of these guidelines:
1. Note what went wrong
2. Identify why it was a problem
3. Record the learning for future reference
4. Update the relevant instruction file

---

**Philosophy:** These guidelines aim for code that is clear, maintainable, and consistent. When in doubt, choose clarity. When guidelines conflict, defer to your language's idioms and your project's established patterns.
