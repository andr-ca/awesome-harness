---
name: solid-principles
description: >
  Use when designing classes, modules, or APIs to evaluate whether the design follows SOLID principles —
  Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion.
  Covers what each principle means, how to detect violations, and how to refactor.
metadata:
  type: skill
  scope: ["Python", "TypeScript", "JavaScript", "Go", "Java"]
  when: "Design review; noticing a class does too much; adding a feature requires changing many files"
---

# SOLID Principles

Five principles for writing code that's easy to change.

---

## S — Single Responsibility Principle

**A class should have one reason to change.**

One class doing two unrelated things = two reasons to change it.

```python
# Violation: UserService handles auth AND notifications
class UserService:
    def login(self, email, password): ...
    def send_welcome_email(self, user): ...  # belongs elsewhere

# Better
class AuthService:
    def login(self, email, password): ...

class UserNotifier:
    def send_welcome(self, user): ...
```

**Signal**: method names have unrelated verbs; the class imports from many unrelated modules.

---

## O — Open/Closed Principle

**Open for extension, closed for modification.**

Add behavior by adding code, not by editing existing code.

```typescript
// Violation: every new payment method requires editing
function processPayment(type: string, amount: number) {
    if (type === 'card') { ... }
    if (type === 'crypto') { ... }  // keep adding ifs
}

// Better: polymorphism or strategy
interface PaymentProcessor {
    process(amount: number): Promise<void>;
}
class CardProcessor implements PaymentProcessor { ... }
class CryptoProcessor implements PaymentProcessor { ... }
```

**Signal**: feature additions require editing a `switch`/`if-else` chain in a stable class.

---

## L — Liskov Substitution Principle

**Subtypes must be substitutable for their supertypes.**

If `B extends A`, code using `A` must work with `B` without knowing the difference.

```python
# Violation: Square breaks Rectangle invariants
class Rectangle:
    def set_width(self, w): self.width = w
    def set_height(self, h): self.height = h
    def area(self): return self.width * self.height

class Square(Rectangle):
    def set_width(self, w):
        self.width = w
        self.height = w  # breaks Rectangle callers who set W and H independently
```

**Signal**: overriding a method throws an exception, does nothing, or changes invariants the parent declares.

---

## I — Interface Segregation Principle

**Clients should not depend on methods they don't use.**

Prefer many small interfaces over one large one.

```typescript
// Violation: Printer forced to implement fax
interface Machine {
    print(doc: Document): void;
    scan(doc: Document): void;
    fax(doc: Document): void;   // not all machines fax
}

// Better
interface Printer { print(doc: Document): void; }
interface Scanner { scan(doc: Document): void; }
```

**Signal**: a class implements an interface but leaves methods empty or throws `NotImplementedError`.

---

## D — Dependency Inversion Principle

**Depend on abstractions, not concretions.** High-level modules must not depend on low-level modules; both should depend on abstractions.

```python
# Violation: high-level OrderService knows about MySQL
from mysql_connector import MySQLDatabase

class OrderService:
    def __init__(self):
        self.db = MySQLDatabase()  # low-level detail

# Better
class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...

class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self.repo = repo
```

See `.claude/skills/dependency-injection/SKILL.md` for the full DI pattern.

---

## Quick Diagnosis

| Symptom | Likely principle violated |
|---|---|
| One class file is hundreds of lines | SRP |
| Every new feature requires editing many existing files | OCP |
| Subclass throws `NotImplementedError` on some parent methods | LSP |
| Class implements an interface but leaves half the methods empty | ISP |
| Business logic imports database/framework classes directly | DIP |

---

## See Also

- `patterns/solid-principles/SOLID_GUIDE.md` — extended examples per language
- `.claude/skills/dependency-injection/SKILL.md` — DIP in practice
- `.claude/skills/design-patterns/SKILL.md` — patterns that implement SOLID
