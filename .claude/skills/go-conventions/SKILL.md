---
name: go-conventions
description: Use when writing, reviewing, or refactoring Go code — naming conventions, receiver naming, error wrapping, interface design, goroutine safety, and common pitfalls (goroutine leaks, defer-in-loop, nil map writes).
metadata:
  type: skills
  complexity: low
  languages: [go]
---

# Go Conventions

This file is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout): `languages/go/CONVENTIONS.md` (full examples
including godoc comments, context-first concurrency, and table-driven
tests).

## Naming

- Unexported: `camelCase`. Exported: `PascalCase`.
- Interfaces: singular, behavior-describing name (`Reader`, `Storer`,
  `UserRepository` — not `IUserRepository`).
- Error sentinels: `Err` prefix (`ErrNotFound`, `ErrTimeout`).
- Receiver: one or two letters, the type's initials (`u *User`, not
  `user *User`). Keep consistent across all methods of a type.

## Errors: wrap with context, return early

```go
// Wrap to preserve the stack — don't swallow context
if err != nil {
    return fmt.Errorf("getUserByID %q: %w", id, err)
}

// Return early — avoid deep nesting
func process(ctx context.Context, id string) error {
    user, err := repo.Find(ctx, id)
    if err != nil {
        return fmt.Errorf("process: find user: %w", err)
    }
    // ... rest of the logic at the same indent level
}
```

## Interfaces: define at the point of use

Declare the interface in the package that uses it, not the package that
implements it. A concrete type's package need not know about the
interface — `io.Reader` doesn't live in the `os` package, and
`UserRepository` should live in the handler/service that calls it, not
in the `postgres` package that provides one.

## Pitfalls to catch in review

```go
// Goroutine leak — closing done unblocks the goroutine, but no
// channel read means it could block on the send forever
go func() {
    result <- compute()  // will block if nobody reads result
}()

// Defer in loop executes at *function* return, not loop iteration
for _, f := range files {
    defer f.Close()  // WRONG — all defers run when function exits
    // RIGHT: use an inner function or close explicitly at end of loop
}

// Write to a nil map panics at runtime
var m map[string]int
m["key"] = 1  // panic: assignment to entry in nil map
// RIGHT: initialize first
m := make(map[string]int)

// Shadowing err in short variable declaration inside a block
result, err := doSomething()
if err == nil {
    data, err := doAnotherThing()  // this `err` is a new variable
    _ = data
}
// The outer `err` is unchanged; use `=` for the inner one if intended
```

## Export documentation

Exported symbols need a `//` comment starting with the symbol name:

```go
// User represents an authenticated user in the system.
type User struct { /* ... */ }

// FindByID retrieves a user by their unique identifier.
// Returns ErrNotFound if no user with that ID exists.
func (r *postgresRepo) FindByID(ctx context.Context, id string) (*User, error) { }
```

## Testing

Table-driven tests with `t.Run` subtests, `_test` package for black-box
tests. See `patterns/testing/TDD.md` for the broader methodology — this
skill covers Go-specific structure only.

## Formatting & tooling

`gofmt` (or `goimports`) is non-negotiable — all Go code must be
formatted. Use `golangci-lint` for static analysis. `go vet` is run
automatically by `go test`.
