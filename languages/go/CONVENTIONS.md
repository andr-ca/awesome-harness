---
language: Go
description: Go-specific naming conventions, style, and best practices
applyTo: "*.go"
---

# Go Conventions & Best Practices

Language-specific guidelines for writing idiomatic, maintainable Go code aligned with community standards.

## Naming Conventions

### Functions and Variables

- Use `camelCase` for function and variable names
- Exported symbols (package-public) use `PascalCase`
- Use descriptive names that clearly indicate purpose
- Shorter is fine in small scopes — idiomatic Go favors `ctx`, `err`, `i`,
  `w`, `r`, `buf` over spelled-out names when the type or context already
  makes the meaning obvious. Reserve fuller names (`userRepository`,
  `birthYear`) for identifiers with wider scope or where the short form
  would be genuinely ambiguous.
- Interface names are singular: `Reader`, `Writer`, `Closer` (not `IReader`)

```go
// Good
func calculateUserAge(birthYear int) int {
	return currentYear - birthYear
}

func (u *User) IsActive() bool {  // Exported
	return u.Status == "active"
}

// Bad
func calcAge(by int) int { }           // Abbreviated
func calculateUserAge(birthYear int) bool { return false }  // Wrong return type
func (u *User) isActive() bool { }  // Should be exported (capital I)
```

### Constants

- Use `camelCase` for unexported constants
- Use `PascalCase` for exported constants
- Use `UPPER_CASE` sparingly (only for very specific cases, usually avoided in Go)
- Group related constants in `const` blocks

```go
// Good
const (
	DefaultTimeout  = 30 * time.Second
	MaxRetries      = 3
	minPasswordLen  = 8
	defaultPageSize = 50
)

const (
	StatusActive   = "active"
	StatusInactive = "inactive"
	StatusDeleted  = "deleted"
)

// Bad
const DEFAULT_TIMEOUT = 30 * time.Second  // UPPER_CASE not idiomatic
const default_page_size = 50              // snake_case is not idiomatic Go
```

### Types and Interfaces

- Use `PascalCase` for type names
- Keep interface names short and specific (often single word or two words)
- Interfaces should typically describe a single behavior
- Use `-er` suffix for reader/writer style interfaces

```go
// Good
type User struct {
	ID    string
	Email string
	Name  string
}

type Reader interface {
	Read(p []byte) (n int, err error)
}

type UserRepository interface {
	FindByID(ctx context.Context, id string) (*User, error)
	Save(ctx context.Context, user *User) error
}

// The interface's methods live on whatever concrete type implements it —
// never on the interface name itself (an interface can't have methods
// defined on it; see the Receivers section below for the concrete type
// this repo's examples use: postgresUserRepository).

// Bad
type user struct { }              // Should be PascalCase
type IUserRepository interface {} // "I" prefix is not idiomatic
type Reader interface {           // Too generic without context
	Do() error
}
```

### Errors

- Define error variables starting with `Err` for sentinel errors
- Use `Error` suffix for error types (if needed)
- Make errors descriptive and contextual

```go
// Good
var (
	ErrNotFound      = errors.New("user not found")
	ErrUnauthorized  = errors.New("unauthorized")
	ErrInvalidInput  = errors.New("invalid input")
)

type ValidationError struct {
	Field   string
	Message string
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

// Bad
var NotFound = errors.New("not found")  // Should start with Err
type ValidationErr struct { }            // Use Error, not Err
```

### Receivers

- Use single-letter receivers for simple types (usually the first letter)
- Keep receivers short but readable
- Be consistent within a type

```go
// Good
func (u *User) IsActive() bool { }
func (r *postgresUserRepository) FindByID(ctx context.Context, id string) (*User, error) { }
func (c *Client) Do(req *http.Request) (*http.Response, error) { }

// Bad
func (user *User) IsActive() bool { }    // Too verbose for receiver
func (ur *postgresUserRepository) FindByID(...) { }  // Inconsistent shortening
```

## File Organization

### Package Structure

```go
// Package declaration
package userservice

// Imports: standard library, then third-party, then local
import (
	"context"
	"errors"
	"fmt"

	"github.com/lib/pq"
	"go.uber.org/zap"

	"myapp/internal/domain"
	"myapp/internal/repository"
)

// Constants
const (
	DefaultTimeout = 30 * time.Second
)

// Errors
var (
	ErrNotFound = errors.New("user not found")
)

// Types
type User struct {
	ID    string
	Email string
}

// Interfaces
type UserRepository interface {
	FindByID(ctx context.Context, id string) (*User, error)
}

// Constructor
func NewService(repo UserRepository, log *zap.Logger) *Service {
	return &Service{repo: repo, log: log}
}

// Methods
type Service struct {
	repo UserRepository
	log  *zap.Logger
}

func (s *Service) GetUser(ctx context.Context, id string) (*User, error) {
	// Implementation
}

// Module functions
func CalculateAge(birthYear int) int {
	// Implementation
}
```

### Imports

- Group imports: standard library, third-party, local packages
- Separate groups with blank lines
- Use `goimports` or `go fmt` for consistent formatting
- Import names should match package names (or use alias if needed)

```go
// Good
import (
	"context"
	"fmt"
	"os"

	"github.com/lib/pq"
	"go.uber.org/zap"

	"myapp/internal/domain"
	"myapp/internal/repository"
)

// Avoid
import (
	"context"
	"github.com/lib/pq"      // Mixed order
	"myapp/internal/domain"
	"fmt"
	"os"
)

import "fmt"  // Should use grouped imports
import "os"
```

## Code Style

### Error Handling

- Always handle errors explicitly; don't ignore them
- Use `if err != nil` for error checks
- Wrap errors with context using `fmt.Errorf` or error wrapping

```go
// Good
data, err := os.ReadFile(filename)  // ioutil.ReadFile is deprecated since Go 1.16
if err != nil {
	return fmt.Errorf("read file: %w", err)
}

// Bad
data, _ := os.ReadFile(filename)  // Ignored error
if err != nil { }                      // Empty error handler
```

### Concurrency

- Use context for cancellation and timeouts
- Use goroutines for async work, but manage their lifecycle
- Use channels for communication between goroutines
- Prefer explicit context passing over storing in structs

```go
// Good
func (s *Service) ProcessUser(ctx context.Context, id string) error {
	user, err := s.repo.FindByID(ctx, id)
	if err != nil {
		return err
	}
	return s.processData(ctx, user)
}

// Use goroutines with wait group or channel
var wg sync.WaitGroup
wg.Add(1)
go func() {
	defer wg.Done()
	// Work here
}()
wg.Wait()

// Bad
func (s *Service) ProcessUser(id string) error {  // No context
	// Can't be cancelled or timed out
}
```

### Interfaces

- Define interfaces where they're used (client-side), not where they're implemented
- Keep interfaces small (often 1-3 methods)
- Use empty interface `interface{}` sparingly; prefer generics or specific types

```go
// Good
// In the package that needs this interface
type Reader interface {
	Read(p []byte) (n int, err error)
}

// In service package
type Logger interface {
	Log(level string, message string) error
}

// In handler
type UserService interface {
	GetUser(ctx context.Context, id string) (*User, error)
}

// Bad
// Defining interfaces in the implementation package
package user
type IUser interface { }  // Too generic, "I" prefix

// Using empty interface
func ProcessData(data interface{}) { }  // Loses type safety
```

### Comments and Documentation

- Export documentation: write a comment for every exported symbol
- Begin comment with symbol name (function, type, constant)
- Keep documentation concise and focused
- Use `//` for single-line comments, `/* */` for multi-line (rarely)

```go
// Good
// User represents a user in the system.
type User struct {
	ID    string // Unique user identifier
	Email string // User email address
}

// GetUser retrieves a user by ID.
// Returns ErrNotFound if the user does not exist.
func (r *postgresUserRepository) GetUser(ctx context.Context, id string) (*User, error) {
	// Complex logic here
	return r.queryByID(ctx, id)
}

// Bad
// This is a user (too obvious)
type User struct { }

// Get the user by id (lowercase, vague)
func (r *postgresUserRepository) GetUser(id string) (*User, error) { }

// Missing comment for exported function
func ProcessUser(user *User) error { }
```

### Function Design

- Functions should do one thing well
- No fixed line-count ceiling — idiomatic Go doesn't enforce one, and
  rigid limits push people to extract meaningless helpers just to hit a
  number. Split a function when it does more than one thing or its
  cyclomatic complexity makes it hard to test, not when it crosses a line
  count.
- Accept interfaces, return concrete types
- Use multiple return values for errors and results

```go
// Good
func (r *postgresUserRepository) FindByID(ctx context.Context, id string) (*User, error) {
	// Single responsibility: find user by ID
	if id == "" {
		return nil, ErrInvalidID
	}
	return r.queryByID(ctx, id)
}

// Bad
func (r *postgresUserRepository) Process(userID string) (interface{}, interface{}) {
	// Does too much, returns empty interfaces
	user, err := r.find(userID)
	// ... validation, logging, caching, etc.
}
```

### Defer Usage

- Use `defer` for cleanup (closing files, releasing locks)
- Place `defer` close to where the resource is opened
- Be aware of defer performance in tight loops (it has overhead)

```go
// Good
file, err := os.Open("data.txt")
if err != nil {
	return err
}
defer file.Close()  // Close immediately when done

// Bad
file, err := os.Open("data.txt")
if err != nil {
	return err
}
// ... lots of code ...
defer file.Close()  // Far from where file was opened
```

## Testing Conventions

### Test File Organization

- Test files live in the same package, named `*_test.go`
- Table-driven tests for multiple scenarios
- Use `t.Run` for sub-tests

```go
// Good: userservice_test.go
func TestGetUser(t *testing.T) {
	tests := []struct {
		name    string
		userID  string
		wantErr bool
	}{
		{"valid ID", "123", false},
		{"empty ID", "", true},
		{"not found", "999", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := repo.GetUser(context.Background(), tt.userID)
			if (err != nil) != tt.wantErr {
				t.Errorf("got error %v, want %v", err, tt.wantErr)
			}
		})
	}
}

// Bad
func TestGetUser_Valid(t *testing.T) { }
func TestGetUser_Empty(t *testing.T) { }
func TestGetUser_NotFound(t *testing.T) { }
// Repetitive, hard to maintain
```

### Benchmarking

- Use `Benchmark*` functions for performance-critical code
- Run with `go test -bench=. -benchmem`
- Compare before and after optimizations

```go
func BenchmarkGetUser(b *testing.B) {
	repo := setupRepo()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		repo.GetUser(context.Background(), "123")
	}
}
```
