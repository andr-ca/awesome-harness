---
name: test-driven-development
description: Complete TDD methodology, workflow, and enforcing minimum 80% test coverage
complexity: medium
frameworks: all
languages: all
---

# Test-Driven Development (TDD)

Full TDD + 80% coverage is required at the **Production** rigor tier —
see `.github/CODING_GUIDELINES.md#rigor-tiers` and
`COVERAGE_REQUIREMENTS.md` for the exact number and what it applies to.
Prototypes can skip TDD entirely; internal tools cover what's expensive
to get wrong.

The Red-Green-Refactor cycle, the unit/integration/E2E testing pyramid,
and general TDD practice (test one behavior at a time, test behavior not
implementation, Arrange-Act-Assert) are standard practice covered well by
[Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
(Kent Beck, the technique's creator) and
[Test Desiderata](https://kentbeck.github.io/TestDesiderata/) — this file
only covers where this repo corrects a mistake its own examples used to
make.

## Common mistake: testing multiple things at once

The fields below (`id`, `email`, `password_hash`, `created_at`,
`is_active`) aren't independent behaviors — they're all part of the same
outcome: "creating a user produces a correctly-populated user." That's one
behavior, so it should be one test with one snapshot-style assertion, not
five assertions and definitely not five separate tests.

```python
# BAD: Five assertions for one behavior — if one fails, the failure
# message doesn't tell you which without reading the whole test
def test_user_creation():
    user = User.create(email="test@example.com", password="secret")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.password_hash is not None
    assert user.created_at is not None
    assert user.is_active == True

# GOOD: one behavior, one assertion — the diff on failure shows exactly
# which field(s) were wrong
def test_user_creation_populates_all_fields():
    user = User.create(email="test@example.com", password="secret")
    assert_that(user).matches({
        "id": IsNotNone(),
        "email": "test@example.com",
        "password_hash": IsNotNone(),
        "created_at": IsNotNone(),
        "is_active": True,
    })  # or assert.deepStrictEqual against a fully-specified expected object
```

Splitting into separate tests is correct when the assertions verify
**genuinely independent behaviors** that could reasonably fail for
unrelated reasons — e.g. "creation succeeds with valid input" vs.
"creation rejects a duplicate email" are two different behaviors and
belong in two different tests, each with its own single assertion:

```python
def test_create_succeeds_with_valid_input():
    user = User.create(email="test@example.com", password="secret")
    assert user.id is not None

def test_create_rejects_duplicate_email():
    User.create(email="test@example.com", password="secret")
    with pytest.raises(DuplicateEmailError):
        User.create(email="test@example.com", password="other")
```

---

**At Production tier:** 80% coverage minimum — see `COVERAGE_REQUIREMENTS.md`.
**See Also:** `patterns/testing/`, `languages/{language}/CONVENTIONS.md`
