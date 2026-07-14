---
name: testing
description: Use when writing tests, deciding on test coverage, choosing between unit/integration/E2E tests, applying TDD, or reviewing test quality — covers rigor tiers, the Red-Green-Refactor cycle, coverage requirements, and Playwright for UI testing.
metadata:
  type: skills
  complexity: medium
  languages: [python, typescript, go]
---

# Testing

This skill is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout): `patterns/testing/TDD.md` (full TDD
workflow), `patterns/testing/COVERAGE_REQUIREMENTS.md` (80% rule and
pragma), `patterns/testing/PLAYWRIGHT_UI_TESTING.md` (E2E screenshots),
`patterns/testing/COMPLETION_CHECKLIST.md`.

## Rigor tiers — apply the right standard, not the maximum

| Tier | Coverage | TDD | Notes |
|---|---|---|---|
| **Production** | **≥ 80%** line+branch | Required | Libraries, agents, shipped services |
| **Internal** | Must have tests | Recommended | No numeric floor; cover what's expensive to get wrong |
| **Prototype** | None required | Optional | Skip freely; document the decision |

Check `.agentharness-profile` or `.github/CODING_GUIDELINES.md` for the
project's tier before assuming 80% applies.

## Red-Green-Refactor

1. **Red** — write a failing test for the *one* behavior you're adding.
2. **Green** — write the minimum code to make it pass (not the final
   code — the correct code comes in the next step).
3. **Refactor** — clean up duplication and naming while tests stay green.

Never skip Red — a test that never fails doesn't prove anything.

## Test one behavior per test

```python
# WRONG: five assertions for one behavior — one failure hides the rest
def test_user_creation():
    user = User.create(email="a@b.com", password="s3cr3t")
    assert user.id is not None
    assert user.email == "a@b.com"
    assert user.password_hash is not None
    assert user.created_at is not None
    assert user.is_active is True

# RIGHT: one assertion covers "all fields are set" as a single behavior
def test_user_creation_populates_all_fields():
    user = User.create(email="a@b.com", password="s3cr3t")
    assert user == {
        "id": AnyString(),
        "email": "a@b.com",
        "password_hash": AnyString(),
        "created_at": AnyDatetime(),
        "is_active": True,
    }
```

Split into multiple tests only when the behaviors can *independently*
fail for unrelated reasons.

## Test pyramid shape (guide, not hard rule)

~70% unit · ~25% integration · ~5% E2E. Bias toward cheap-to-run unit
tests; don't duplicate unit coverage with integration tests that only
exist for the coverage number.

## Coverage floor: 80% line + branch at Production tier

```python
# pragma: no cover is for truly unreachable code — not for skipping inconvenient tests
if sys.version_info >= (3, 12):
    new_behavior()
else:  # pragma: no cover — never reached on supported versions
    old_behavior()
```

Measure coverage before marking work complete. Don't approve a PR that
claims ≥ 80% without a CI report to confirm it.

## UI testing (Playwright)

For UI tests: screenshot-review every visual path at least once (not
just "it didn't crash"). State in the PR description which flows you
verified visually — CI can check that the test ran, but not that the UI
looked correct. See `patterns/testing/PLAYWRIGHT_UI_TESTING.md` for full
conventions.

## Assertion style

Prefer specific assertions that produce readable failure messages:

```typescript
// POOR: tells you nothing on failure except "false"
expect(result).toBe(true);

// GOOD: tells you what was in result
expect(result.status).toBe('active');
expect(result.items).toHaveLength(3);
```
