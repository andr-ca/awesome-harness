---
applyTo: "*.ts,*.tsx"
description: "TypeScript-specific naming conventions, style, and best practices"
---

Generated from `languages/typescript/CONVENTIONS.md` by
`tools/generate-copilot-instructions.sh`
(https://github.com/andr-ca/agentharness) — do not hand-edit; regenerate
instead. Only applied by Copilot when editing a file matching
`*.ts,*.tsx`.

---

## TypeScript Conventions & Best Practices

Naming (`camelCase` functions/variables, `PascalCase` classes/types,
`UPPER_SNAKE_CASE` module constants), import grouping (external → internal
→ types), and generics (`T`/`U` for simple cases, descriptive names for
complex ones) follow standard TypeScript/JS convention — see the
[TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
and [Google's TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
for the parts not worth restating here. Below are the places this repo
makes an actual decision among genuinely competing options.

### Private Members: `#` vs. `_prefix`

Prefer native `#` private fields (ES2022+/TS 3.8+) in new code — real
runtime privacy, not just erased at compile time and still reachable via
a cast or `["_name"]`. A leading underscore (`_name`) is an older
*convention*, not a deprecated language feature: it's still common in
code that predates `#` fields, and isn't something to rewrite on sight.

```typescript
class User {
  #internalState: Map<string, unknown>;   // true runtime privacy
  #validate(): boolean { /* ... */ }
}
```

### Null vs. Undefined

TypeScript's own idioms don't universally favor one over the other, and
neither should this guide — optional properties (`?`), optional
parameters, and destructuring defaults all naturally produce `undefined`,
not `null`. Pick based on what the absence *means*, not by habit:

- `undefined` (via `?`) for "not provided / not yet set" — the
  language's own default for anything optional.
- `null` for an explicit, deliberate "no value" the code sets on purpose
  (a nullable database column, "user cleared this field").
- Whichever you pick for a given API, apply it consistently — the bug is
  mixing both for the same *kind* of absence within one module, not the
  specific choice.

```typescript
interface User {
  middleName?: string;       // absent = "not provided" -> undefined
}
interface UserRecord {
  deletedAt: Date | null;    // absent = "explicitly cleared" -> null
}
```

### Comments: explain the non-obvious constraint, not the syntax

```typescript
/**
 * Pragmatic email format check: rejects obviously-malformed input
 * (no @, no domain). NOT a full RFC 5322 validator — that grammar is
 * far too permissive to usefully check with a regex (it allows quoted
 * strings, comments, and forms almost no real mail system accepts). If
 * you need to know the address actually works, send a verification
 * email; don't try to make this regex stricter.
 */
export function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
```

A comment restating what the code already says (`// Validate email`
above a function called `validateEmail`) is worse than no comment — see
`.github/CODING_GUIDELINES.md`'s comment rules.

### Async/Await: a caught error must not become a silent success

Logging a caught error is not the same as handling it. Unless the caller
genuinely doesn't need to know the operation failed, rethrow (or return
an error result) after logging — a caught-and-swallowed error makes an
`async function` resolve successfully even though the work it promised
never happened.

```typescript
async function fetchAndProcess(id: string): Promise<void> {
  try {
    const user = await fetchUser(id);
    await processUser(user);
  } catch (error) {
    logger.error('Failed to process user', { id, error });
    throw error;  // caller needs to know this failed, not see a false success
  }
}
```

### React

React/JSX conventions (component naming, props typing) are a framework
add-on on top of this guide, not part of it — see
[`frameworks/react/CONVENTIONS.md`](../../frameworks/react/CONVENTIONS.md).
Everything above applies to React code too; only what's actually
React-specific lives there.
