# Error Handling Patterns

Explicit errors, error wrapping, retry/circuit-breaker/fallback recovery,
and error classification are standard resilience patterns — see
[Google SRE Book, ch. 22](https://sre.google/sre-book/addressing-cascading-failures/)
for circuit breakers and backoff, and each language's own error-handling
idiom (`raise ... from e` in Python, `%w` wrapping in Go, `{ cause }` in
JavaScript) for the mechanics. This repo expects all four patterns to be
used where they apply (see `.github/CODING_GUIDELINES.md` for the
Production-tier "handle all documented failure modes" rule) but doesn't
re-teach them here.

## The one thing worth calling out: what an error handler logs

A caught error commonly carries more than the message — HTTP client
errors can embed full request config (including auth headers) on the
error object itself, and a raw request payload can contain passwords or
other PII. Log a bounded, redaction-safe summary instead of the raw
object or payload:

```python
try:
    user_data = parse_user_data(raw_json)
except json.JSONDecodeError as e:
    logger.error(
        "Invalid user JSON",
        extra={"payload_length": len(raw_json), "error": str(e)},
    )
    return None
```

```javascript
try {
  const user = await fetchUser(id);
} catch (error) {
  // error.message/.stack, not the raw error object — some HTTP clients
  // attach full request config (incl. auth headers) to their errors.
  logger.error("User fetch failed", { id, errorMessage: error.message, stack: error.stack });
}
```

See `../logging/LOGGING_STANDARDS.md#what-not-to-log` for the full list
of what never belongs in a log line.

---

**See Also:** `../logging/LOGGING_STANDARDS.md`, `../testing/`
