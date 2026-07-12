---
name: error-handling
description: Use when building error recovery, handling exceptions, designing error flows, or implementing logging for errors — covers retry, circuit-breaker, error wrapping, structured logging.
metadata:
  type: skills
  scope: ["Python", "Go", "JavaScript", "TypeScript"]
  when: "Before writing error handling code; when designing exception flows; when building resilience patterns"
---

# Error Handling & Recovery

Structured approaches to errors, recovery, and observability. **Never silently hide errors.**

## Core Patterns

### 1. Explicit Errors (Always)
Return errors as values or raise them; never ignore them.

```python
# ✅ Good: Explicit handling
try:
    user = parse_user_data(raw)
except json.JSONDecodeError as e:
    # Never log the raw payload — it can carry passwords/PII. Log a
    # bounded, redaction-safe summary instead.
    logger.error("Invalid user JSON", extra={"error": str(e), "payload_length": len(raw)})
    return None

# ❌ Bad: Silent failure
try:
    parse_user_data(raw)
except:
    pass  # User data silently ignored
```

### 2. Error Wrapping (Across Boundaries)
Add context as errors propagate—original error + where + why.

```python
# ✅ Python: Preserve cause
try:
    return repository.find(user_id)
except DatabaseError as e:
    raise UserNotFoundError(f"find user {user_id}") from e

# ✅ Go: Wrap with context
user, err := repo.Find(userID)
if err != nil {
    return nil, fmt.Errorf("find user %s: %w", userID, err)
}
```

### 3. Error Classification
Decide recovery strategy based on error type.

```python
def classify_error(error):
    if isinstance(error, (ConnectionError, TimeoutError)):
        return "transient"  # Retry
    elif isinstance(error, (ValueError, KeyError)):
        return "validation"  # Reject, don't retry
    else:
        return "unknown"

# Transient → retry with backoff
# Validation → log and fail
# Fatal → panic
```

### 4. Retry with Backoff (for Transient Errors)
Retry flaky operations; don't retry permanent failures.

```python
import time

def retry(func, max_attempts=3, backoff_base=2):
    """Retry with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt < max_attempts - 1:
                wait_time = backoff_base ** attempt
                logger.warning(f"Retry {attempt + 1}/{max_attempts}, waiting {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
        except (ValueError, KeyError):
            raise  # Don't retry validation errors

# Usage
user = retry(lambda: fetch_user(user_id), max_attempts=3)
```

### 5. Circuit Breaker (for Cascading Failures)
Fail fast when a service is down; stop hammering it.

```python
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = timeout
        self.state = self.CLOSED
        self.last_failure = None

    def call(self, func, *args, **kwargs):
        if self.state == self.OPEN:
            if time.time() - self.last_failure > self.timeout:
                self.state = self.HALF_OPEN
            else:
                raise RuntimeError("Circuit is OPEN")

        try:
            result = func(*args, **kwargs)
            self.failures = 0  # Success: reset
            self.state = self.CLOSED
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.threshold:
                self.state = self.OPEN
            raise
```

### 6. Fallback (Default When Primary Fails)
Provide sensible default when operation fails.

```python
def get_user_with_fallback(user_id):
    """Try cache → database → guest fallback."""
    try:
        return cache.get(user_id)
    except CacheError:
        pass

    try:
        user = database.find(user_id)
        cache.set(user_id, user)  # Warm cache
        return user
    except DatabaseError as e:
        logger.error("Database down", extra={"error": str(e)})
        return User.guest()  # Fallback
```

### 7. Structured Error Logging (Always)
Log errors with full context, not just the message.

```python
# ❌ Bad: Lost context
logger.error(str(error))

# ✅ Good: Full context
logger.error("Failed to fetch user", extra={
    "user_id": user_id,
    "operation": "fetch",
    "error_type": type(error).__name__,
    "error_message": str(error),
    "retry_count": attempt,
})
```

---

## Decision Tree

```
Error occurs
├─ Catch it?
│  ├─ Yes → Can recover?
│  │        ├─ Yes → Transient? (network, timeout, rate limit)
│  │        │        ├─ Yes → Retry with backoff + circuit breaker
│  │        │        └─ No → Fallback or fail fast
│  │        └─ No → Log + re-raise
│  └─ No → Let it propagate up
└─ Always wrap with context (where + why)
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Catching `Exception` broadly | Catch specific errors you can handle |
| Ignoring errors silently | Log errors with full context |
| No backoff on retry | Exponential backoff: 1s, 2s, 4s, 8s… |
| Retrying permanent errors | Classify errors first; don't retry 404, 401 |
| Lost error chain | Preserve cause: `from e` (Python), `%w` (Go) |

---

## References

This file is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout, not just this skill):
- Full guide: `patterns/error-handling/README.md`
- Logging: `patterns/logging/LOGGING_STANDARDS.md`
