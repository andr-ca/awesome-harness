---
name: python-conventions
description: Use when writing or reviewing Python code — naming conventions, type hints, common pitfalls (mutable defaults, bare except, is-vs-==), and testing structure.
metadata:
  type: skills
  complexity: low
  languages: [python]
---

# Python Conventions

This file is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout, not just this skill — these aren't bundled
here since they're documentation, not something this skill runs):
`languages/python/CONVENTIONS.md` (complete examples) and
`languages/python/COPILOT_INSTRUCTIONS.md` (general agent operating
principles for Python repos — inspect before changing, scope discipline,
never claim a command passed without running it).

## Naming

- `snake_case` — functions, variables. `PascalCase` — classes.
  `UPPER_SNAKE_CASE` — module-level constants.
- Single underscore prefix for private (`_internal`); avoid double
  underscore except for genuine name-mangling needs.
- Exceptions: `PascalCase` + `Error`/`Exception` suffix, specific not
  generic (`ValidationError`, not `BadThing`).

## Imports & structure

Standard library → third-party → local, each group separated by a blank
line. Absolute imports over relative. No `from module import *`.

## Type hints

Use them on function parameters and returns. Match syntax to the
project's minimum Python version — check `requires-python` in
`pyproject.toml` before using `list[str]` (3.9+), `X | None` (3.10+), or
`match/case` (3.10+). Don't silently raise the minimum version.

## Pitfalls to catch in review

```python
# Mutable default argument — persists across calls, shared state bug
def f(item, container=[]):  # WRONG
def f(item, container=None):  # RIGHT — default to None, create inside

# Bare/broad except — swallows KeyboardInterrupt, hides real errors
except:  # WRONG
except Exception:  # still too broad, usually
except ValueError as e:  # RIGHT — catch what you expect

# `is` for value comparison — checks identity, not equality
if user_id is 5:  # WRONG
if user_id == 5:  # RIGHT (== for values, `is` only for None/True/False)
```

## Testing

`tests/` directory, `test_*.py` files, `test_*` functions, pytest
fixtures for setup. See `patterns/testing/TDD.md` for the broader
methodology — this skill covers Python-specific structure only.

## Formatting & tooling

Defer to the project's `pyproject.toml` — don't impose Black/Ruff
defaults over an existing configured formatter/linter. If unconfigured:
Black or `ruff format` (88-char lines), `ruff check`, `mypy` for typing,
`pytest` for tests.
