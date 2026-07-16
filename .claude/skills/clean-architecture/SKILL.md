---
name: clean-architecture
description: Use when business logic is entangled with frameworks or databases. Covers hexagonal architecture (ports and adapters), layer diagram, dependency direction rules, and violation symptoms.
metadata:
  type: skill
  scope: ["Python", "TypeScript", "JavaScript", "Go", "Java"]
  when: "Designing a new service; business logic imports FastAPI/Express/SQLAlchemy; can't test domain without spinning up infrastructure"
---

# Clean Architecture (Hexagonal / Ports & Adapters)

**Core rule:** business logic must not depend on infrastructure. Infrastructure depends on business logic.

```
     ┌─────────────────────────────────────────┐
     │           Infrastructure                │
     │  (HTTP, DB, Queue, Email, S3, ...)      │
     │                                         │
     │     ┌───────────────────────────┐       │
     │     │     Application Layer     │       │
     │     │  (Use cases, Commands)    │       │
     │     │                           │       │
     │     │   ┌─────────────────┐    │       │
     │     │   │  Domain Layer   │    │       │
     │     │   │  (Entities,     │    │       │
     │     │   │  Value Objects, │    │       │
     │     │   │  Domain Events) │    │       │
     │     │   └─────────────────┘    │       │
     │     └───────────────────────────┘       │
     └─────────────────────────────────────────┘
         Dependencies only point INWARD →
```

---

## Layers

### Domain (innermost)
- Entities: objects with identity and lifecycle (`Order`, `User`)
- Value Objects: immutable, defined by value (`Money`, `Email`)
- Domain Events: things that happened (`OrderPlaced`, `PaymentFailed`)
- Domain Services: stateless logic that spans entities
- **Zero infrastructure imports** — no SQLAlchemy, FastAPI, Stripe, etc.

### Application
- Use cases / handlers: orchestrate domain objects
- Input/output ports (interfaces): what the use case needs from outside
- **No infrastructure imports** — depends only on domain + port interfaces

### Infrastructure (outermost)
- Adapters that implement ports: `SqlUserRepository`, `StripePaymentGateway`
- Framework glue: FastAPI routes, Django views, Express controllers
- **Depends on application layer** — adapters implement domain/application interfaces

---

## Ports & Adapters

A **port** is an interface defined in the domain/application layer.
An **adapter** is an infrastructure class that implements a port.

```python
# Port (in application/domain layer)
class UserRepository(Protocol):
    def find_by_id(self, id: UserId) -> User | None: ...
    def save(self, user: User) -> None: ...

# Adapter (in infrastructure layer)
class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, id: UserId) -> User | None:
        return self._session.get(UserModel, id.value)

    def save(self, user: User) -> None:
        self._session.merge(UserModel.from_domain(user))
```

---

## Directory Layout

```
src/
  domain/
    order.py            # Order entity
    order_repository.py # port (Protocol)
    events.py           # OrderPlaced, OrderCancelled
  application/
    place_order.py      # PlaceOrderUseCase
    cancel_order.py     # CancelOrderUseCase
  infrastructure/
    sql_order_repository.py  # implements port
    stripe_payment.py        # implements PaymentGateway port
  interfaces/
    http/
      order_routes.py   # FastAPI/Express routes
    cli/
      commands.py       # CLI entry points
```

---

## Dependency Direction Rules

1. **Imports only point inward**: infrastructure → application → domain
2. **Domain never imports from infrastructure** or application
3. **Use cases depend on ports (interfaces)**, never on adapters (concretions)
4. **Test domain/application layers** without infrastructure — use fakes for ports

---

## When You're Violating This

| Symptom | Fix |
|---|---|
| `from sqlalchemy import ...` in a domain entity | Move persistence to an adapter; domain holds plain objects |
| Can't unit-test a use case without a database | The use case depends on a concrete repository; inject a port instead |
| HTTP status codes or request objects in business logic | Business logic returns domain results; the controller translates to HTTP |
| Feature requires changing 5 different layers | Layers may be too granular; check if use case logic leaked into infrastructure |

---

## See Also

- `patterns/clean-architecture/README.md` — pattern directory entry
- `.claude/skills/design-patterns/SKILL.md` — Repository, Facade, Strategy used in clean arch
- `.claude/skills/dependency-injection/SKILL.md` — how DI wires the layers together
