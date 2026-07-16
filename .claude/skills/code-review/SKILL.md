---
name: code-review
description: Use when reviewing a diff, pull request, or code change — systematic checklist for correctness, clarity, security, testability, and adherence to the project's conventions. Covers what to look for, how to give actionable feedback, and when to approve vs. request changes.
metadata:
  type: skills
  complexity: medium
  scope: [all]
---

# Code Review

A systematic approach to reviewing diffs and pull requests. Work through
the categories below in order — correctness first, style last.

---

## Pre-read checklist

Before reading the diff:
- Read the PR description. Does it explain *why* the change is needed?
  If the description is missing or just "fixes stuff", ask for one before
  reviewing — the diff alone won't tell you whether the approach is right.
- Check the linked issue or ticket if there is one.
- Note the rigor tier (`patterns/profiles/` or `.agentharness-profile`)
  — the coverage and testing requirements differ.

---

## 1. Correctness

The most important category. Ask: *"Can this code produce wrong results?"*

- Does the logic match the stated goal?
- Are there off-by-one errors, wrong comparisons, or incorrect
  assumptions about the data?
- Are all inputs validated before use?
- Are edge cases handled: empty collections, zero, null/None/undefined,
  negative numbers, max values, concurrent access?
- Does error handling actually handle the error, or does it swallow it silently?
- Are exceptions caught at the right level (not too broad, not too narrow)?
- Are resources (files, connections, locks) released even on exception?

```python
# Swallowed error — caller sees success, wrong data silently used
try:
    value = parse_config(raw)
except Exception:
    pass  # WRONG: value is now unset or stale

# RIGHT: propagate or at minimum log + re-raise
try:
    value = parse_config(raw)
except ConfigError as e:
    logger.error("config parse failed", error=e)
    raise
```

---

## 2. Security

Run through the relevant items from the `security-review` skill (load it
for the full checklist). The most common PR-level findings:

- Secrets or API keys hardcoded or logged.
- SQL/shell/HTML built via string formatting with user input.
- Missing ownership/permission checks on resource access.
- New dependency with known CVEs (`npm audit` / `pip-audit` not run).

---

## 3. Test coverage

At Production tier, new code must have tests. Check:

- Is there a test for the happy path?
- Is there a test for at least one failure/edge case?
- Do the tests assert on behaviour (what the code does), not
  implementation (how it does it)?
- Are mocks covering real logic paths, not short-circuiting the code
  being tested?

```python
# BAD: mocks away the thing being tested
def test_send_email():
    with patch("mailer.send") as mock_send:
        service.send_welcome(user)
    mock_send.assert_called_once()
    # Proved nothing about send_welcome's logic

# GOOD: test the observable outcome
def test_send_email_queues_message(fake_queue):
    service.send_welcome(user)
    assert len(fake_queue.messages) == 1
    assert fake_queue.messages[0].to == user.email
```

---

## 4. Clarity and naming

Code is read far more often than it's written. Ask:

- Do variable, function, and type names say what the thing *is*, not
  what it *does* or how it's used? (`user_id`, not `the_id_to_look_up`)
- Is there a comment explaining the *why* of non-obvious code?
- Are magic numbers named as constants?
- Is the function doing more than one thing? (If yes, it's a candidate
  for splitting — but only flag this if it makes review harder, not just
  because a function is long.)

---

## 5. Design and structure

Only flag design issues if they would make the code hard to maintain or
extend. Don't redesign working code during review.

- Does the change introduce a circular dependency or tightly couple two
  previously independent modules?
- Is state mutated in a non-obvious place (global, injected side effect)?
- Is there a simpler way that doesn't sacrifice correctness?

---

## 6. Conventions and style

Check last — style is the least important category. If the project has a
linter/formatter, let the CI catch style issues; don't repeat them in
comments.

- Does the code follow the project's naming conventions (`go-conventions`,
  `python-conventions`, `typescript-conventions` skills)?
- Are imports grouped and ordered correctly?
- Are error messages user-facing or dev-facing? (User-facing messages
  should not expose stack traces or internal identifiers.)

---

## How to write review comments

**Be specific.** "This could be cleaner" is not actionable. "The `user_id`
variable here is actually a UUID string — renaming it to `user_uuid` would
match the type it holds" is.

**Distinguish required from suggested:**
- `Required:` (or `[blocking]`) — must change before merge
- `Suggested:` (or `[nit]`) — worth doing but not a blocker
- `Question:` — you need more context before deciding

**Reference the reason, not just the fix:**
```
Required: This query isn't parameterised — the `email` variable is
interpolated directly into the SQL string, which allows SQL injection
if the caller passes user-controlled input. Use a parameterised query:
    cursor.execute("SELECT ... WHERE email = %s", (email,))
```

---

## 7. Smells, Inefficiencies & Pattern Misuse

Check for these cross-cutting problems regardless of layer:

### Exception handling
- **Bare/empty catch** — `except: pass` (Python), `catch (e) {}` (JS/TS), `catch (Exception ignored) {}` (Java) — silently swallows errors; bugs become invisible. Always log or re-throw.
- **Catching too broadly** — bare `except:` (Python) or `catch (Throwable t)` (Java) catches truly everything including keyboard interrupt and VM errors that cannot be recovered from. Even `except Exception` or `catch (Exception e)` is too broad when the try block is long: narrow the scope instead. Catch only the specific exception types you know how to handle.
- **Swallowing and continuing** — catching an error, logging it, then continuing as if nothing happened. If recovery is possible, do it explicitly; otherwise re-throw.
- **Exception used for control flow** — throwing to signal a normal condition ("not found" as a raised exception instead of an Optional). Exceptions are for unexpected failures, not expected branches.
- **Missing cleanup on error** — a resource (file, DB connection, lock) opened in a try block but not released on exception; needs `finally`/`with`/`using`/`defer`.
- **Re-raising loses original cause** — `raise NewException(...)` without `from e` (Python) / missing cause arg (Java: `new MyException(msg, cause)`) / missing `innerException` (C#) — loses the original stack trace. Chain exceptions.
- **Error message contains secrets** — exception message or log line includes passwords, tokens, or PII. Sanitize before logging.

### Logging
- **Log level too high for routine events** — `ERROR` or `WARN` for expected, recoverable conditions inflates alert noise. Use `DEBUG`/`INFO` for normal flow, `WARN` for degraded-but-continuing, `ERROR` for failures that need attention, `FATAL`/`CRITICAL` only for unrecoverable states.
- **Log level too low for real failures** — a caught exception that reaches the caller, or a security event, logged at `DEBUG` is invisible in production. Failures surfaced to the caller should be `ERROR` or above.
- **Unstructured log messages** — `logger.info(f"User {user.id} logged in at {ts}")` is hard to query and alert on. Prefer structured key=value or JSON fields: `logger.info("user.login", user_id=user.id, ts=ts)`.
- **Logging PII or secrets** — passwords, tokens, full credit card numbers, SSNs, or health data in log lines. Mask, hash, or omit sensitive fields before logging.
- **Logging request/response bodies unconditionally** — request bodies can contain credentials or PII. Only log in debug mode and with explicit field allowlists.
- **Duplicate log lines** — the same event logged at multiple call depths (e.g., both in a service and its caller). Log once at the right layer.
- **Missing correlation ID** — requests/jobs that span multiple services or async steps with no trace/request ID. Impossible to reconstruct a timeline from logs without one.
- **Print instead of logger** — `print(...)` (Python), `console.log(...)` (JS/TS), `fmt.Println(...)` (Go) in production code. These bypass log level control, sampling, and structured output.
- **Overly verbose hot path** — `DEBUG`-level logging inside a tight loop or a high-frequency function. Even `if logger.isDebugEnabled()` guards have overhead at scale; log outside the loop or sample.

### Database / persistence
- **N+1 queries** — loading a list then fetching related records per item in a loop. Look for `for item in items: item.load_relation()`.
- **Loading all records** — `SELECT *` with no limit/pagination; `repo.find_all()` with no bound.
- **Missing index** — a `WHERE`, `ORDER BY`, or `JOIN` clause on a column not in the index list.
- **Missing transaction** — two or more writes that must succeed or fail together, without a transaction boundary.
- **Reading stale data** — reading inside a write path without locking or version checks.

### Repeated/inefficient calls
- **Repeated API calls to the same resource** — same request made multiple times in a loop or in both a condition and a body; should be cached in a local variable.
- **Chatty pattern** — 10 individual property reads where one bulk load would do.
- **Bypassed cache** — a cache exists but the code path goes around it.

### Concurrency & shared state
- **Race condition on shared mutable state** — two goroutines/threads reading and writing the same variable without synchronization (mutex, channel, atomic, `synchronized`). Look for global/static state mutated from multiple threads without a lock.
- **Locking at the wrong granularity** — a lock that covers an entire function when only one field needs protection (over-locking causes contention); or a field read/written outside a lock that should be inside it (under-locking causes races).
- **Lock held across I/O or long computation** — acquiring a lock, then making a network call or doing a heavy computation while holding it. Other threads are blocked for the duration; release the lock before I/O or move to lock-free alternatives.
- **Double-checked locking without volatile/atomic** — `if (!initialized) { synchronized { if (!initialized) { ... } } }` is broken without a memory barrier on the check field (Java: `volatile`; C++: `std::atomic`).
- **`Thread.sleep` / `time.sleep` in production path** — used to "wait for something to be ready" instead of a proper condition variable, semaphore, or event notification. Brittle and slow.
- **Goroutine/thread leak** — a goroutine or thread started but never joined, cancelled, or bounded. Accumulates over time until the process runs out of resources.
- **Deadlock risk** — two lock acquisitions where another code path acquires the same locks in the opposite order. Establish a consistent lock ordering convention.
- **Async fire-and-forget without error handling** — `asyncio.create_task(...)`, `Promise` or `setTimeout` without `.catch()` / error propagation. Exceptions don't propagate to the caller; they may be logged late (asyncio logs them as warnings at GC time) or not at all, making failures hard to detect and debug. Always attach an error handler or `await` the result.

### Memory & resource management
- **Memory leak via unclosed listener/subscription** — event listener, observer, or pub/sub subscription registered but never removed when the owning object is destroyed. Common in frontend components and long-lived services.
- **Growing unbounded collection** — a `dict`, `list`, or `map` that accumulates entries forever (e.g., a cache with no eviction policy, a queue with no consumer). Will exhaust memory eventually.
- **Large object allocated in a hot loop** — a buffer, regex pattern, or complex object created fresh on every iteration when it could be allocated once outside the loop.
- **Closure retaining large scope** — a closure or lambda that captures a large object/array unnecessarily (e.g., capturing the entire request context when only one field is needed). Prevents GC.
- **Resource not released in error path** — file, network connection, or DB cursor opened in a try block but only closed in the happy path; needs `finally`/`with`/`using`/`defer`.
- **Returning a reference to a mutable internal field** — a getter that exposes the internal `list`/`array`/`map` directly; callers can modify it without the owning object knowing. Return a defensive copy or an immutable view.

### Input validation
- **Missing boundary validation** — numeric input used as an index, allocation size, or loop bound without checking it's in a safe range. Leads to out-of-bounds, OOM, or infinite loops.
- **Trusting user-controlled format strings** — passing user input as the format string itself (e.g., `printf(user_input)` in C, `logger.log(level, user_input)` in some frameworks) rather than as an argument. In C, this leaks memory or crashes; in Python/Java the typical risk is information disclosure or unexpected output. Always use a fixed literal format string: `printf("%s", user_input)`.
- **Path traversal** — file path built from user input without sanitizing `../` sequences. Use `os.path.realpath` / `Path.resolve()` and verify the result is within the allowed prefix.
- **Regex catastrophic backtracking** — a regex with nested quantifiers on overlapping character classes (e.g., `(a+)+`) applied to user input. Exponential time; exploitable as ReDoS. Validate regex complexity or use a linear-time engine.
- **Trusting `Content-Type` for deserialization** — deserializing a body without validating the content matches the declared type. Specific risks: YAML parsers with unsafe loaders (e.g., PyYAML's `yaml.load` without `Loader=yaml.SafeLoader`) can instantiate arbitrary objects; XML parsers may be vulnerable to XXE (external entity injection) which can read local files or make server-side requests. JSON is generally safe. Always use safe/restricted deserializer modes.
- **Missing max-length enforcement** — accepting arbitrarily long strings, files, or payloads without a size limit. Leads to OOM, DoS, or storage exhaustion.
- **Integer overflow in user-supplied arithmetic** — multiplying or adding user inputs before checking for overflow, then using the result as an allocation size or loop count.

### Dependency injection & patterns
- **Missing DI** — `new Service()` inside a class constructor or method body; makes the class hard to test and tightly coupled. Should be injected.
- **Service locator** — calling `container.get(...)` or `locator.resolve(...)` inside business logic. Prefer constructor injection.
- **Pattern where none is needed** — a Factory to construct a plain value object; a Strategy for a fixed enum; a Repository wrapping a single in-memory list. Premature abstraction is a bug.
- **Missing pattern for real duplication** — copy-paste of the same algorithm in 3 places that could be a Strategy; repeated decoration logic that could be a Decorator; 5-clause `if type == X` that could be a Factory.
- **Inheritance for code reuse** — a subclass that only exists to share code (not to express a true is-a relationship). Use composition (Strategy, Decorator, delegation) instead.

### Performance
- **Blocking I/O on the event loop / main thread** — synchronous disk reads, DNS lookups, or HTTP calls inside a Node.js `async` function, a Python `asyncio` coroutine, or a UI thread. Blocks all other work. Use async I/O or a thread pool offload.
- **Unnecessary serialization/deserialization in a hot path** — JSON-encoding and decoding the same structure multiple times in a request, or marshalling to/from a format that's only consumed internally. Serialize once at the boundary.
- **Missing pagination in data pipelines** — a background job that loads all rows from a table, transforms them, then inserts results, with no chunking. Will OOM or time out at scale. Add batch/cursor-based processing.
- **Synchronous work hiding behind async** — `await asyncio.to_thread(heavy_cpu_task)` or `await executor.submit(...)` adds threads but doesn't reduce CPU time. Profile first; CPU-bound tasks belong in a separate process or worker pool, not the async thread pool.
- **Re-computing expensive derived values on every access** — a getter that recalculates a sum, sorts a list, or runs a regex on every call. Memoize or cache the result unless the input changes frequently.
- **Payload too large for the use case** — an endpoint that returns 50 fields when a summary response with 5 would serve the caller. Increases bandwidth, parse time, and serialization cost on every request.

### API contracts
- **Breaking change without version bump** — removing a field, renaming a required field, changing a type, or adding a required request field to an existing API version. Any of these break existing callers silently. Version the endpoint or maintain backward compat.
- **Optional field added as required** — a new request field with no default and no null-tolerance. Existing callers that don't send it will start failing.
- **Response shape drift** — the actual JSON/schema differs from the documented shape (missing fields, wrong types). Breaks contract-test suites and auto-generated clients.
- **No deprecation notice before removal** — removing or renaming something that callers depend on without a documented deprecation period. Always add `Deprecation` header or `X-Deprecated` before removing.
- **Implicit contract in error responses** — callers branching on error message strings instead of stable error codes. If you change the message, callers break silently. Always include a stable `error_code` in every error response.
- **Silent coercion of invalid input** — accepting `"true"` as a boolean, or `"123abc"` as a number, without surfacing a validation error. Callers don't discover their bugs and the API becomes unpredictable.

### Observability
- **No structured event for a critical state transition** — a payment succeeding, an order being placed, or an authentication failing — with no log entry, metric increment, or trace span. Impossible to monitor or alert on.
- **Hardcoded timeout values** — `timeout=30` scattered across the codebase. Timeouts belong in configuration; hardcoded values make them impossible to tune without a code deploy.
- **No health-check endpoint** — a service deployed behind a load balancer or in a container without a `/health` or `/readiness` endpoint. Orchestrators can't distinguish a starting pod from a dead one.
- **Missing trace propagation** — an HTTP call to a downstream service that doesn't forward trace context (`traceparent`, `X-B3-TraceId`). Breaks distributed traces; can't correlate frontend and backend spans.
- **Counter instead of histogram for latency** — recording request count but not latency distribution. Counts tell you volume; histograms tell you p99. Both are needed for SLO monitoring.
- **Alert only on errors, not on latency or saturation** — an alert for `5xx > threshold` but nothing for "p99 > 2s" or "queue depth > 1000". The USE method (Utilization, Saturation, Errors) needs all three.

### Configuration
- **Hardcoded environment-specific values** — URLs, ports, or feature flags embedded in source code instead of environment variables or a config file. Requires a code change to point at a different environment.
- **Secrets in source code or config files** — API keys, DB passwords, or private keys committed to the repository or present in a non-secret config file. Use environment variables, a secrets manager, or `.env` files excluded from version control.
- **No config validation at startup** — a service that reads config lazily (on first use) will fail in production hours after deployment. Validate all required config values at startup and fail fast with a clear error.
- **Inconsistent config key naming** — some keys are `SCREAMING_SNAKE_CASE`, others are `camelCase`, others are `dot.notation`. Pick one convention per scope and document it.
- **Default config values that are unsafe for production** — `DEBUG=true`, `ALLOW_ANY_ORIGIN=true`, or `DB_MAX_CONNECTIONS=unlimited` as defaults. Production-safe defaults should be the out-of-the-box behaviour; opt-in to relaxed settings in dev.
- **No config drift detection** — configuration values that can change at runtime without any validation or audit trail. If a secret is rotated or a flag is toggled in prod, there should be a record of who changed it and when.


---

## Approve vs. request changes

**Approve** when:
- All Required items are addressed.
- You would be comfortable maintaining this code.
- The tests give you confidence the behaviour is correct.

**Request changes** when:
- There is at least one Required finding.
- You can't confidently assess correctness without more context
  (in which case ask, don't block).

**Don't block on style preferences** that aren't in the project's
enforced conventions. Suggest them as `[nit]` and approve if everything
else is clean.

---

## See Also — Domain-Specific Review Skills

Load these instead of (or alongside) this skill when reviewing a specific layer to avoid polluting context with irrelevant instructions:

- `.claude/skills/code-review-db/SKILL.md` — database/persistence layer: indexes, N+1, migrations, transactions
- `.claude/skills/code-review-api/SKILL.md` — REST/HTTP API layer: status codes, idempotency, versioning, auth, pagination
- `.claude/skills/code-review-ui/SKILL.md` — UI/frontend layer: accessibility, state management, bundle size, keyboard navigation
