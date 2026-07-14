---
name: typescript-conventions
description: Use when writing, reviewing, or refactoring TypeScript or JavaScript code — naming conventions, type annotations, private fields, null vs. undefined, async/await pitfalls, and module structure.
metadata:
  type: skills
  complexity: low
  languages: [typescript, javascript]
---

# TypeScript Conventions

This file is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout): `languages/typescript/CONVENTIONS.md` (full
examples including generics and import grouping) and
`frameworks/react/CONVENTIONS.md` (React/JSX-specific additions).

## Naming

- `camelCase` — functions, variables, method names.
  `PascalCase` — classes, interfaces, type aliases, enum names.
  `UPPER_SNAKE_CASE` — module-level constants.
- Enum members: `PascalCase`.
- Generic type params: `T`/`U` for simple one-liners; descriptive names
  (`TEntity`, `TResponse`) for complex or nested generics.

## Imports & module structure

Group: external packages → internal modules → type-only imports.
Separate each group with a blank line. Prefer `import type` for
type-only imports (helps tools that strip types without full parsing).

```typescript
import fs from 'fs';
import express from 'express';

import { UserRepository } from './repositories/UserRepository';

import type { User } from './types';
```

## Private members: `#` over `_prefix`

Prefer native `#` private fields (ES2022+/TS 3.8+) in new code — real
runtime privacy, not a convention that's still readable via `["_name"]`.
Don't rewrite working `_prefix` code on sight; it's not deprecated.

```typescript
class TokenStore {
  #tokens: Map<string, string> = new Map();   // true runtime privacy
  #rotate(): void { /* ... */ }
}
```

## Null vs. Undefined

Pick based on what *absence means*, then apply it consistently:

- `undefined` (via `?`) — "not provided / not yet set."
- `null` — an explicit "no value" the code sets deliberately (nullable
  column, "user cleared this field").
- **Do not mix both for the same kind of absence in one module.**

## Pitfalls to catch in review

```typescript
// async function catches error, logs it, then resolves — hides failure
async function save(data: Data): Promise<void> {
  try {
    await db.write(data);
  } catch (err) {
    logger.error('save failed', err);
    // WRONG: caller sees a successful promise despite the failure
  }
}
// RIGHT: rethrow after logging so the caller can handle the failure
catch (err) {
  logger.error('save failed', err);
  throw err;
}

// Type-cast escape hatch silences the compiler, not the bug
const result = someValue as SomeType;  // risky without a runtime check
// Prefer a type guard:
function isSomeType(v: unknown): v is SomeType { /* ... */ }

// Non-null assertion hides null/undefined bugs
const name = user!.profile!.name;   // crashes at runtime if null
// RIGHT: optional chaining + fallback
const name = user?.profile?.name ?? 'Unknown';
```

## Testing

`tests/` or `__tests__/` directories, `*.test.ts` / `*.spec.ts` files.
Use `vitest` for Vite-based projects, `jest` for Node/Next. See
`patterns/testing/TDD.md` for the broader methodology — this skill covers
TypeScript-specific structure only.

## Formatting & tooling

Defer to the project's `tsconfig.json` and `eslint.config.*` — don't
impose defaults over an existing configured setup. If unconfigured:
`strict: true` in tsconfig, `prettier` for formatting (2-space indent,
single quotes), `eslint` with `@typescript-eslint/recommended`.
