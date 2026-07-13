---
applyTo: "*.py"
description: "Python-specific naming conventions, style, and best practices"
---

Generated from `languages/python/CONVENTIONS.md` by
`tools/generate-copilot-instructions.sh` — do not hand-edit; regenerate
instead. Only applied by Copilot when editing a file matching
`*.py`.

---

## Python Conventions & Best Practices

`.claude/skills/python-conventions/SKILL.md` has the terse, actionable
version of this doc (naming, imports, type hints, three pitfalls,
testing structure) — load that for day-to-day work. This doc adds: the
handful of choices this repo actually makes among multiple valid
options (most Python style below is just PEP 8/typing convention, not a
decision — see [PEP 8](https://pep8.org/) and the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
for everything not listed here), plus two pitfalls the skill doesn't
cover.

### Choices this repo makes (not just "the PEP 8 default")

- **Line length:** 88 characters (Black's default), not PEP 8's
  original 79 — check the project's own `pyproject.toml` first, since
  an existing project may have picked something else.
- **String quotes:** double by default (`"like this"`); single only to
  avoid escaping (`'It\'s here'` reads better than `"It's here"` when
  it would otherwise need a backslash). A formatter normalizes this —
  don't hand-police it in review.
- **Docstrings:** Google style
  ([reference](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)),
  unless the project's existing code already uses a different one
  consistently.

### Two pitfalls the skill doesn't cover

**Global mutable state** — module-level dicts/lists accumulating shared
state are hard to test and reason about; encapsulate in a class instead:

```python
# Avoid: module-level cache any caller can mutate
_cache = {}
def get_cached(key):
    if key not in _cache:
        _cache[key] = expensive_operation(key)
    return _cache[key]

# Prefer: instance-scoped, explicit lifetime
class Cache:
    def __init__(self):
        self._cache = {}
    def get(self, key):
        return self._cache.setdefault(key, expensive_operation(key))
```

**Loading everything into memory instead of using a generator** — for
any collection large enough that this matters:

```python
# Avoid: builds the whole list before returning
def get_all_users():
    return [fetch_user(i) for i in range(1, 1_000_000)]

# Prefer: lazy, one at a time
def get_all_users():
    for i in range(1, 1_000_000):
        yield fetch_user(i)
```

(For the three pitfalls this repo *does* flag most often in review —
mutable default arguments, bare/broad `except`, and `is` vs. `==` — see
the skill file linked above; it has the worked examples.)

### Tools

Ruff (lint + format) or Black + Ruff for formatting, mypy for typing,
pytest for tests — but defer to the project's own `pyproject.toml` /
`requirements-dev.txt` if one already configures something else; don't
impose a different toolchain. See each tool's own docs for commands and
config: [Ruff](https://docs.astral.sh/ruff/), [mypy](https://mypy.readthedocs.io/),
[pytest](https://docs.pytest.org/).

**See also:** `.claude/skills/python-conventions/SKILL.md` (terse
policy, loaded on demand), `COPILOT_INSTRUCTIONS.md` (AI-specific
operating guidance for this repo's Python code).
