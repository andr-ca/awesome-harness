---
language: Go
description: Go-specific naming conventions, style, and best practices
applyTo: "*.go"
---

# Go Conventions & Best Practices

Naming (`camelCase` unexported / `PascalCase` exported, singular
interface names like `Reader`), import grouping, error-sentinel naming
(`Err*`), `if err != nil` handling, context-first concurrency, and
table-driven tests are all standard Go community convention — see
[Effective Go](https://go.dev/doc/effective_go) and the
[Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md)
for the parts not worth restating here. Below are the places this repo
makes an actual decision, or corrects a mistake this guide itself used
to make.

## Receiver naming: short is idiomatic, not lazy

Idiomatic Go favors short receivers (usually the type's first letter) —
`u *User`, not `user *User`. Keep it consistent within a type; don't
spell it out "for clarity," and don't abbreviate inconsistently across a
type's methods.

```go
func (u *User) IsActive() bool { }
func (r *postgresUserRepository) FindByID(ctx context.Context, id string) (*User, error) { }
```

## Interface methods live on the implementing type, not the interface

An interface can't have methods defined on it — only a concrete type
can. When writing an example implementing `UserRepository`, the receiver
is the concrete type (`*postgresUserRepository` below), never the
interface name itself:

```go
type UserRepository interface {
	FindByID(ctx context.Context, id string) (*User, error)
}

func (r *postgresUserRepository) FindByID(ctx context.Context, id string) (*User, error) {
	return r.queryByID(ctx, id)
}
```

## No fixed line-count ceiling on functions

Idiomatic Go doesn't enforce one, and a rigid limit pushes people to
extract meaningless helpers just to hit a number. Split a function when
it does more than one thing or its cyclomatic complexity makes it hard
to test — not when it crosses a line count.

## Export documentation starts with the symbol's name

`godoc` convention, not optional style: a comment on an exported symbol
should begin with that symbol's own name, so it reads correctly both
inline and when rendered by tooling.

```go
// User represents a user in the system.
type User struct { /* ... */ }

// GetUser retrieves a user by ID. Returns ErrNotFound if the user
// does not exist.
func (r *postgresUserRepository) GetUser(ctx context.Context, id string) (*User, error) { }
```
