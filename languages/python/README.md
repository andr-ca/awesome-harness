# Python – Language Guide

Complete guide to Python conventions, best practices, and tools for writing idiomatic, maintainable Python code.

## 📚 Documentation

### [COPILOT_INSTRUCTIONS.md](./COPILOT_INSTRUCTIONS.md)
AI/Copilot-specific guidance for working with Python projects:
- Core operating principles (understand repo first, preserve behavior)
- Repository inspection checklist
- Change planning and navigation
- Scope and change discipline
- Python version compatibility
- Formatting, linting, style
- Testing, type checking, documentation
- Dependencies and error handling
- Common pitfalls and checklist

**Use this when:** Working with AI tools or implementing features in Python projects

### [CONVENTIONS.md](./CONVENTIONS.md)
Language-specific naming, style, and best practices:
- Naming conventions (snake_case, PascalCase, UPPER_SNAKE_CASE)
- File organization and imports
- Type hints and docstrings
- Code style (spacing, line length, string quotes)
- Common patterns (context managers, comprehensions, f-strings)
- Pitfalls to avoid (mutable defaults, bare except, global state)
- Testing organization
- Tools and configuration
- Version-specific features

**Use this when:** Writing Python code or reviewing style decisions

## 🎯 Quick Reference

### Naming at a Glance

| Element | Style | Example |
|---------|-------|---------|
| Functions/Variables | `snake_case` | `user_count`, `validate_email` |
| Classes | `PascalCase` | `UserRepository`, `EmailValidator` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `API_BASE_URL` |
| Private members | `_prefix` | `_internal_data`, `_validate` |
| Exceptions | `PascalCase` + Error | `ValidationError`, `ConnectionError` |

### Essential Tools

| Tool | Purpose | Command |
|------|---------|---------|
| **Ruff** | Linter + Formatter | `ruff check .`, `ruff format .` |
| **Black** | Code Formatter | `black .` |
| **mypy** | Type Checker | `mypy .` |
| **pytest** | Testing | `pytest` |
| **uv** | Package Manager | `uv run pytest` |

### Code Quality Checklist

Before committing Python code:
- [ ] Imports are organized (stdlib, third-party, local)
- [ ] Type hints on public APIs
- [ ] Docstrings for public functions/classes
- [ ] Tests added and passing
- [ ] Linter passes (`ruff check .`)
- [ ] Formatter passes (`ruff format .`)
- [ ] Type checker passes (`mypy .`)
- [ ] No mutable default arguments
- [ ] Specific exception handling (not bare `except`)
- [ ] Context managers for resource management

## 🔧 Setting Up a Python Project

### Using uv (Recommended)

```bash
# Create new project
uv init my-project
cd my-project

# Add dependencies
uv add requests

# Run code
uv run python main.py

# Run tests
uv run pytest
```

### Using Poetry

```bash
# Create new project
poetry new my-project
cd my-project

# Add dependencies
poetry add requests

# Run code
poetry run python main.py

# Run tests
poetry run pytest
```

## 📋 Documentation Standards

### Function Docstring (Google Style)

```python
def calculate_total(items: list[dict], tax_rate: float = 0.1) -> float:
    """Calculate total cost of items including tax.
    
    Args:
        items: List of item dictionaries with 'price' keys.
        tax_rate: Tax rate as decimal (0.1 = 10%). Defaults to 0.1.
    
    Returns:
        Total cost including tax.
    
    Raises:
        ValueError: If items list is empty or tax_rate is negative.
        KeyError: If item dict doesn't contain 'price' key.
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")
    
    subtotal = sum(item['price'] for item in items)
    return subtotal * (1 + tax_rate)
```

### Class Docstring

```python
class UserRepository:
    """Repository for user data persistence and queries.
    
    Handles all database operations for users including creation,
    updates, deletion, and queries. Uses a connection pool to
    manage database connections efficiently.
    
    Attributes:
        connection_pool: Database connection pool.
        logger: Logger instance for debugging.
    """
    
    def __init__(self, connection_pool):
        """Initialize repository with connection pool.
        
        Args:
            connection_pool: Database connection pool instance.
        """
        self.connection_pool = connection_pool
```

## 🧪 Testing Best Practices

### Test Structure

```python
# tests/test_user_validator.py
import pytest
from src.validators import validate_email, ValidationError

class TestEmailValidation:
    """Tests for email validation."""
    
    def test_valid_email(self):
        """Valid emails should return True."""
        assert validate_email("user@example.com") is True
    
    def test_invalid_email_no_at(self):
        """Email without @ should return False."""
        assert validate_email("userexample.com") is False
    
    def test_raises_on_empty(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_email("")

@pytest.fixture
def user_data():
    """Fixture providing test user data."""
    return {"name": "Alice", "email": "alice@example.com"}

def test_user_creation(user_data):
    """Users should be created with provided data."""
    user = User(**user_data)
    assert user.name == user_data["name"]
```

## 📦 Common Libraries

### Testing
- **pytest** – Testing framework
- **pytest-cov** – Coverage reporting
- **pytest-mock** – Mocking helpers

### Type Checking
- **mypy** – Static type checker
- **pyright** – Microsoft's static type checker
- **pydantic** – Data validation with types

### Web/API
- **requests** – HTTP client
- **httpx** – Modern async HTTP client
- **fastapi** – Fast async web framework
- **flask** – Lightweight web framework

### Data
- **pandas** – Data manipulation
- **sqlalchemy** – SQL toolkit and ORM
- **pydantic** – Data validation

### Async
- **asyncio** – Built-in async support
- **aiohttp** – Async HTTP client
- **trio** – Alternative async library

## 🚀 Performance Tips

### Generators for Large Data
```python
# Instead of building list, use generator
def process_large_file(filepath):
    with open(filepath) as f:
        for line in f:
            yield line.strip()

for line in process_large_file('huge.txt'):
    process(line)
```

### List Comprehensions Over Loops
```python
# Faster and more concise
squared = [x**2 for x in range(1000)]

# Instead of
squared = []
for x in range(1000):
    squared.append(x**2)
```

### Use `functools.cache` for Expensive Operations
```python
from functools import cache

@cache
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

## 🔗 Integration with agentharness

Projects using Python should:
1. Reference `COPILOT_INSTRUCTIONS.md` in your project's `.github/copilot-instructions.md`
2. Follow `CONVENTIONS.md` for naming, style, and testing
3. Combine with general guidelines in `../../.github/CODING_GUIDELINES.md`
4. Check `../../.github/COMMITTING_GUIDELINES.md` for commit standards

Reference it directly rather than copying — conventions docs are meant
to be read, not vendored (see
[docs/INTEGRATION.md](../../docs/INTEGRATION.md)'s "Language Guidelines"
section):

```markdown
<!-- In your project's CLAUDE.md -->
## Language Guide
Python conventions: see ~/agentharness/languages/python/CONVENTIONS.md
```

## 📖 External References

- [Python Official Docs](https://docs.python.org/3/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Real Python](https://realpython.com/)
- [Type Hints Documentation](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)

## ❓ Common Questions

**Q: Should I use type hints?**  
A: Yes, especially for public APIs. Use `from typing import` on Python 3.8, modern syntax on 3.9+.

**Q: Black or Ruff for formatting?**  
A: Either is fine; check your project's `pyproject.toml` for what's configured.

**Q: How do I organize a large project?**  
A: Use packages (directories with `__init__.py`), logical module names, and clear public APIs.

**Q: Should I commit lock files?**  
A: Yes, for reproducibility. `uv.lock`, `poetry.lock`, `Pipfile.lock` should be committed.

**Q: When do I use `async`?**  
A: For I/O-bound operations (network, file, database). Not needed for CPU-bound work.

---

**Author:** agentharness contributors
