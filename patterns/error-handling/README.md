# Error Handling Patterns

Structured approaches to error handling, recovery, and observability across languages and frameworks.

| Pattern | Purpose | When to use |
|---------|---------|------------|
| [Explicit errors](#explicit-errors) | Return errors as values; never hide failures | Always, in all code |
| [Error wrapping](#error-wrapping) | Add context to errors as they propagate | When errors cross function/module boundaries |
| [Error recovery](#error-recovery) | Retry, fallback, or circuit-break | When operations are flaky or downstream services fail |
| [Structured error logging](#structured-error-logging) | Log errors with full context for debugging | In error handlers and production code |
| [Error classification](#error-classification) | Distinguish recoverable from fatal errors | Before deciding retry/panic/fallback strategy |

---

## Explicit Errors

**Never silently hide errors.** Errors are data; propagate them or handle them deliberately.

### ❌ Anti-patterns

```python
# Python: Silent failure
try:
    parse_user_data(raw_json)
except:
    pass  # User data silently ignored; downstream code breaks mysteriously

# JavaScript: Ignored promise
fetchUser(id).then(process)  // No .catch(); error silently drops

// Go: Ignored error
_ = os.Rename(oldPath, newPath)  // File might not have renamed
```

### ✅ Correct

```python
# Python: Explicit handling
try:
    user_data = parse_user_data(raw_json)
except json.JSONDecodeError as e:
    logger.error("Invalid user JSON", extra={"raw": raw_json, "error": str(e)})
    return None  # Or raise

# JavaScript: Explicit handling
try {
  const user = await fetchUser(id);
  await process(user);
} catch (error) {
  logger.error("User fetch failed", { id, error });
  // Decide: retry, return default, or rethrow
}

// Go: Explicit handling
if err := os.Rename(oldPath, newPath); err != nil {
  return fmt.Errorf("rename %s to %s: %w", oldPath, newPath, err)
}
```

---

## Error Wrapping

**Add context as errors propagate.** The original error tells *what* went wrong; wrapping adds *where* and *why*.

### ❌ Anti-patterns

```python
# Loses context
def get_user(user_id):
    try:
        return repository.find(user_id)
    except Exception:
        raise Exception("Error")  # Lost original error and context

# Repetitive context
def get_user(user_id):
    try:
        return repository.find(user_id)
    except DatabaseError as e:
        raise UserServiceError(str(e))  # Repackages, loses `e`
```

### ✅ Correct

```python
# Adds context, preserves cause
def get_user(user_id: str) -> User:
    try:
        return repository.find(user_id)
    except DatabaseError as e:
        raise UserNotFoundError(f"find user {user_id}") from e

# Modern Python 3.11+
def get_user(user_id: str) -> User:
    try:
        return repository.find(user_id)
    except DatabaseError as e:
        raise UserNotFoundError(f"find user {user_id}") from e

// Go: Wrap with context
func GetUser(userID string) (*User, error) {
    user, err := repo.Find(userID)
    if err != nil {
        return nil, fmt.Errorf("find user %s: %w", userID, err)
    }
    return user, nil
}

// JavaScript: Wrap errors
async function getUser(userId) {
  try {
    return await repository.find(userId);
  } catch (error) {
    throw new UserServiceError(
      `Failed to fetch user ${userId}`,
      { cause: error }
    );
  }
}
```

---

## Error Recovery

### Retry

Retry transient failures (network timeouts, rate limits, temporary server errors). Don't retry permanent failures (404, auth errors, bad input).

```python
import time
from typing import Callable, TypeVar

T = TypeVar('T')

def retry(func: Callable[..., T], max_attempts: int = 3, 
          backoff_base: float = 1.0) -> T:
    """Retry function with exponential backoff."""
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < max_attempts - 1:
                wait_time = backoff_base ** attempt
                logger.warn(f"Retry {attempt + 1}/{max_attempts}", 
                           extra={"wait_seconds": wait_time})
                time.sleep(wait_time)
        except (ValueError, KeyError) as e:
            # Don't retry validation errors
            raise
    
    raise last_error

# Usage
user = retry(lambda: fetch_user(user_id), max_attempts=3)
```

### Circuit Breaker

Stop repeatedly calling a failing service; fail fast and check periodically if it recovers.

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing; reject calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise RuntimeError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
breaker = CircuitBreaker(failure_threshold=5)
user = breaker.call(fetch_user, user_id)
```

### Fallback

Provide a sensible default when the primary operation fails.

```python
def get_user_with_fallback(user_id: str) -> User:
    """Get user from cache, fallback to database, then guest."""
    try:
        return cache.get(user_id)
    except CacheError:
        logger.warn("Cache miss", extra={"user_id": user_id})
    
    try:
        user = database.find(user_id)
        cache.set(user_id, user)  # Warm cache
        return user
    except DatabaseError as e:
        logger.error("Database unavailable", extra={"error": str(e)})
        return User.guest()  # Fallback
```

---

## Structured Error Logging

Log errors with full context, not just the message.

```python
# ❌ Bad
logger.error(str(error))

# ✅ Good
logger.error(
    "Failed to process user",
    extra={
        "user_id": user_id,
        "step": "validation",
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
)

// Go example
log.WithFields(log.Fields{
    "user_id": userID,
    "operation": "validate",
    "error": err.Error(),
}).Error("User validation failed")

// JavaScript example
logger.error("Failed to process user", {
    userId,
    step: "validation",
    errorType: error.constructor.name,
    errorMessage: error.message,
    stack: error.stack,
});
```

---

## Error Classification

Distinguish error types to decide recovery strategy:

- **Transient**: Retry (network, timeout, rate limit)
- **Validation**: Reject & log (bad input, auth failure)
- **Fatal**: Panic or fail fast (database corrupt, config missing)
- **Unknown**: Log carefully, treat conservatively

```python
def classify_error(error: Exception) -> str:
    """Classify error for recovery strategy."""
    if isinstance(error, (ConnectionError, TimeoutError)):
        return "transient"  # Retry
    elif isinstance(error, (ValueError, KeyError, PermissionError)):
        return "validation"  # Reject, don't retry
    elif isinstance(error, MemoryError):
        return "fatal"      # Panic
    else:
        return "unknown"    # Log, treat conservatively

def handle_error(error: Exception, operation: str):
    error_type = classify_error(error)
    
    if error_type == "transient":
        retry(operation, max_attempts=3)
    elif error_type == "validation":
        logger.error(f"Invalid {operation}", extra={"error": error})
        raise
    elif error_type == "fatal":
        logger.critical(f"Fatal {operation}", extra={"error": error})
        raise
    else:
        logger.warn(f"Unknown error in {operation}", extra={"error": error})
        raise
```

---

## Best Practices

1. **Fail fast, fail loudly.** Errors are data; losing them is worse than crashing.
2. **Wrap errors with context.** Original error + where it happened + what you were trying to do.
3. **Classify errors.** Know which are retryable, which are permanent.
4. **Log with structure.** Don't log just the message; include request ID, user ID, step name.
5. **Don't catch generic exceptions.** Catch specific errors you know how to handle.
6. **Preserve error chains.** Use `from e` (Python), `%w` (Go), or `cause` (JavaScript).
7. **Test error paths.** Errors are code paths; test them.

---

## See Also

- [LOGGING_STANDARDS.md](../logging/LOGGING_STANDARDS.md) — Logging errors with telemetry
- [Testing patterns](../testing/) — Testing error conditions
