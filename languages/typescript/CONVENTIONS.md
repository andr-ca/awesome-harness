---
language: TypeScript
description: TypeScript-specific naming conventions, style, and best practices
applyTo: "*.ts,*.tsx"
---

# TypeScript Conventions & Best Practices

Language-specific guidelines for writing idiomatic, type-safe, and maintainable TypeScript code.

## Naming Conventions

### Functions and Variables
- Use `camelCase` for function and variable names
- Use descriptive names that explain purpose and intent
- Avoid single-letter names (except loop counters `i`, `j` in obvious contexts)
- Avoid abbreviations (unless domain-standard, e.g., `HTTP`, `UUID`)
- Prefix boolean variables with `is`, `has`, `can`, `should`

```typescript
// Good
const userCount = 0;
const isActive = true;
const hasPermission = false;

function validateEmailAddress(email: string): boolean {
  return email.includes('@');
}

// Bad
const uc = 0;
const active = true;  // Unclear if it's a value or flag
const validate = (e: string) => e.includes('@');  // Too short
```

### Classes and Types
- Use `PascalCase` for class names, interfaces, types, and enums
- Use nouns that describe what the class/type represents
- Use adjectives for boolean-returning functions (e.g., `isValid`, `hasNext`)

```typescript
// Good
class UserRepository {
  findById(id: string): User | null { }
}

interface EmailValidator {
  validate(email: string): boolean;
}

type UserStatus = 'active' | 'inactive' | 'deleted';

enum HttpStatus {
  OK = 200,
  NotFound = 404,
}

// Bad
class user_repository { }  // snake_case for class
interface validator { }    // Too generic
type user_status = string; // Should be specific union
```

### Constants
- Use `UPPER_SNAKE_CASE` for module-level constants (especially enum-like constants)
- Use `camelCase` for regular const values (since TypeScript infers the constant nature)

```typescript
// Good
const MAX_RETRIES = 3;
const DEFAULT_TIMEOUT_MS = 30000;
const API_BASE_URL = 'https://api.example.com';

// Type-level constants
const defaultConfig = { timeout: 5000 };  // camelCase for inferred constants

// Bad
const max_retries = 3;  // Inconsistent with TypeScript style
const MaxRetries = 3;   // PascalCase for constants is non-standard
```

### Private Members
- Prefix private methods and properties with `#` (modern TypeScript)
- Alternative (deprecated but still seen): single underscore `_` prefix
- Type private properties explicitly

```typescript
// Good (modern)
class User {
  private name: string;
  #internalState: Map<string, any>;

  constructor(name: string) {
    this.name = name;
    this.#internalState = new Map();
  }

  #validate(): boolean {
    return this.name.length > 0;
  }

  public getName(): string {
    return this.name;
  }
}

// Acceptable (if project standard)
class User {
  private _name: string;

  constructor(name: string) {
    this._name = name;
  }

  private _validate(): boolean {
    return this._name.length > 0;
  }
}
```

### Exceptions and Errors
- Use `PascalCase` with `Error` suffix for error classes
- Extend `Error` base class, not generic `Exception`
- Use specific, descriptive names

```typescript
// Good
class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

class DatabaseConnectionError extends Error {
  constructor(public readonly host: string, public readonly port: number) {
    super(`Failed to connect to ${host}:${port}`);
    this.name = 'DatabaseConnectionError';
  }
}

// Bad
class Error1 extends Error { }     // Generic
class bad_error extends Error { }  // snake_case
```

### Generics
- Use single-letter names for simple generics (`T`, `U`, `K`, `V`)
- Use descriptive names for complex generics (e.g., `TResponse`, `TEntity`)
- Maintain consistency with TypeScript conventions

```typescript
// Good
function identity<T>(value: T): T {
  return value;
}

interface Repository<TEntity> {
  findById(id: string): Promise<TEntity>;
}

// Bad
function identity<TYPE>(value: TYPE): TYPE { }  // Overly verbose
interface Repository<E> { }  // Ambiguous
```

## File Organization

### Module Structure

```typescript
/**
 * Module description: what this file exports and why
 */

// Imports: external, then internal, then types
import { EventEmitter } from 'events';
import express from 'express';

import { logger } from '../logging';
import { UserService } from '../services';

import type { User, UserInput } from '../types';

// Module-level constants
const DEFAULT_TIMEOUT_MS = 5000;
const MAX_RETRIES = 3;

// Interfaces/Types
interface ConfigOptions {
  timeout: number;
  retries: number;
}

// Classes
export class UserController {
  constructor(private userService: UserService) {}

  async getUser(req: express.Request): Promise<User> {
    // Implementation
  }
}

// Module functions
export async function createUser(input: UserInput): Promise<User> {
  // Implementation
}
```

### Imports

- Place all imports at the top of the file
- Group imports in this order: external libraries, internal modules, types
- Separate groups with a blank line
- One import per line (or group related imports from same module)
- Use named imports; avoid `import * as` unless naming conflicts exist
- Put `import type` statements after regular imports

```typescript
// Good
import fs from 'fs';
import path from 'path';

import express from 'express';
import { z } from 'zod';

import { logger } from '../logging';
import { config } from './config';

import type { User } from '../types';

// Avoid
import * as fs from 'fs';            // Use named import
import fs from 'fs';
import express from 'express';
import { logger } from '../logging';  // Mixed order
import type { User } from '../types'; // Type import before other imports
```

## Type Safety

### Type Annotations

- Always annotate function parameters and return types (no implicit `any`)
- Use explicit types for public APIs
- Omit return type only for obviously simple functions

```typescript
// Good
function add(a: number, b: number): number {
  return a + b;
}

async function fetchUser(id: string): Promise<User> {
  // Implementation
}

// Bad
function add(a, b) {  // Missing types
  return a + b;
}

function fetchUser(id): Promise<any> {  // Implicit any, wrong return type
  // Implementation
}
```

### Null and Undefined

- Prefer `null` for intentional absence of value (not `undefined`)
- Use optional properties (`?`) for optional fields
- Use non-null assertion (`!`) sparingly and only when type system cannot infer safety

```typescript
// Good
interface User {
  id: string;
  email: string;
  middleName?: string;  // Optional field
}

function getUserOrNull(id: string): User | null {
  // Return null, not undefined
}

// Bad
function getUserOrUndefined(id: string): User | undefined { }
const user = null ?? undefined;  // Confusing
```

### Union Types Over Function Overloads

- Prefer union types to function overloads for clarity
- Use discriminated unions (tagged unions) for complex type cases

```typescript
// Good
function process(value: string | number): string {
  if (typeof value === 'string') {
    return value.toUpperCase();
  }
  return value.toString();
}

type Result<T> = 
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

// Avoid (unless overload is truly clearer)
function process(value: string): string;
function process(value: number): string;
function process(value: string | number): string { }
```

## Code Style

### Comments and Documentation

- Use JSDoc for public APIs and complex logic
- Use `//` for inline comments explaining *why*, not *what*
- Keep comments short and update them when code changes

```typescript
// Good
/**
 * Validates an email address using RFC 5322 rules.
 * @param email - The email to validate
 * @returns true if valid, false otherwise
 */
export function validateEmail(email: string): boolean {
  // Complex regex is intentional: RFC 5322 compliance requires it
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Bad
// Validate email
function validateEmail(email: string): boolean { }

/**
 * Validates an email
 */
function validateEmail(email: string): boolean { }
```

### Arrow Functions vs Function Declarations

- Use arrow functions for callbacks and short operations
- Use function declarations for named functions in module scope
- Be consistent within a file

```typescript
// Good
function createUser(input: UserInput): User {
  return { id: generateId(), ...input };
}

users.filter((u) => u.isActive);

const handleClick = (event: React.MouseEvent) => {
  // Handler
};

// Bad
const createUser = (input: UserInput): User => {  // Should be declaration
  return { id: generateId(), ...input };
};

function handleClick(event: React.MouseEvent) {  // Should be arrow function in most contexts
  // Handler
}
```

### Async/Await Over Promises

- Prefer async/await over `.then()` chains
- Always handle errors with try/catch or `.catch()`

```typescript
// Good
async function fetchAndProcess(id: string): Promise<void> {
  try {
    const user = await fetchUser(id);
    await processUser(user);
  } catch (error) {
    logger.error('Failed to process user', { id, error });
  }
}

// Avoid
function fetchAndProcess(id: string): Promise<void> {
  return fetchUser(id)
    .then(user => processUser(user))
    .catch(error => logger.error('Failed', { error }));
}
```

## React-Specific Conventions (if applicable)

### Component Naming
- Use `PascalCase` for component names
- File name should match component name
- Use descriptive, specific component names

```typescript
// Good
export function UserProfileCard({ user }: { user: User }): JSX.Element {
  return <div>{user.name}</div>;
}

// File: UserProfileCard.tsx

// Bad
export function Card({ user }: { user: User }): JSX.Element { }  // Too generic

// File: card.tsx (should match component name)
```

### Props Typing
- Define prop types explicitly (don't rely on inference)
- Use `React.FC` or explicit return type
- Destructure props in function signature when possible

```typescript
// Good
interface UserCardProps {
  user: User;
  onSelect?: (user: User) => void;
}

export function UserCard({ user, onSelect }: UserCardProps): JSX.Element {
  return (
    <div onClick={() => onSelect?.(user)}>
      {user.name}
    </div>
  );
}

// Avoid
export const UserCard: React.FC<{ user: User }> = ({ user }) => { }  // Inline types
```
