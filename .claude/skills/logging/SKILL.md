---
name: logging
description: Use when adding logging to an application, reviewing log output, choosing log levels, structuring logs for observability, or configuring logging backends — covers structured logging, YAML config patterns, what NOT to log, and local vs. production output.
metadata:
  type: skills
  complexity: low
  languages: [python, typescript, go]
---

# Logging

This skill is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout): `patterns/logging/LOGGING_STANDARDS.md`
(full mandate and config schema), `patterns/logging/logging.yaml.example`
(tested YAML template), `patterns/logging/config_loader.py` (Python
reference implementation with 99% test coverage).

## When this applies

Full structured logging with YAML config, multiple backends, and
rotation is required at **Production tier**. Prototypes: `print()`/`console.log()`
is fine. Internal tools: structured logging recommended, single-backend
acceptable. Check the project's rigor tier first.

## Log levels — pick the right one

| Level | Use for |
|---|---|
| `TRACE` | High-frequency per-call details; disabled in production by default |
| `DEBUG` | Developer diagnostic info; disabled in production by default |
| `INFO` | Normal operational events (startup, request completed) |
| `WARNING` | Something unexpected but recoverable; worth investigating |
| `ERROR` | A real failure that the system couldn't recover from |
| `CRITICAL` | The process must stop or data is corrupted |

Rule of thumb: if you'd page someone at 3am, it's `ERROR` or `CRITICAL`.

## Structured logging: message + fields, never string interpolation

```python
# WRONG: unstructured — can't query or filter by user_id or duration
logger.info(f"Request completed for user {user_id} in {duration}ms")

# RIGHT: message is a static label; context is in structured fields
logger.info("request.completed", user_id=user_id, duration_ms=duration)
```

```typescript
// Node/pino/winston equivalent
logger.info({ userId, durationMs }, 'request.completed');
```

## What NOT to log

Never log: passwords, tokens, API keys, full credit card numbers, SSNs,
session IDs, or any data under a PII/GDPR policy. Redact or omit before
logging. **If logging usefulness and secrecy conflict, redact. Do not
log the secret "for completeness."**

```python
# WRONG: logs the raw token
logger.info("auth.token_issued", token=issued_token)

# RIGHT: log only what's safe to expose
logger.info("auth.token_issued", user_id=user_id, expires_at=exp)
```

## Configuration: YAML template, not hand-rolled

Copy `patterns/logging/logging.yaml.example` as your starting point:

```bash
cp patterns/logging/logging.yaml.example config/logging.yaml
```

The template supports `${VAR:-default}` interpolation, multiple handler
backends (file, console, OTEL), and rotation. Hand-rolling a logging
schema from scratch duplicates tested work.

## Verification before marking work complete

1. Run the code path and confirm log lines actually emit — don't assume.
2. Pipe a log line through `jq` (or equivalent) to confirm it's valid
   JSON (or whatever your configured format is).
3. State in the PR description which events you verified emit correctly.

## Local vs. production output

Local/dev: human-readable (`pretty` / `dev` format, colorized).
Production: machine-parseable JSON, no color codes. Configure this via
an environment variable, not a code branch:

```yaml
handlers:
  console:
    formatter: ${LOG_FORMAT:-json}   # override to 'pretty' in dev
```
