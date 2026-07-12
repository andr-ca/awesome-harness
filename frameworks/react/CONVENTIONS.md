---
framework: React
description: React-specific naming and typing conventions, layered on top of languages/typescript/CONVENTIONS.md
applyTo: "*.tsx"
---

# React Conventions & Best Practices

React/JSX-specific conventions. This is a framework add-on, not a
language guide — apply `languages/typescript/CONVENTIONS.md` first for
everything that isn't React-specific (naming, type safety, async/await,
etc.); this file only covers what's different for components.

## Component Naming

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

## Props Typing

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
