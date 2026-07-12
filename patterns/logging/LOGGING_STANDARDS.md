---
name: logging-telemetry-standards
description: Mandatory logging and telemetry standards - centrally configured, multi-backend support
complexity: medium
frameworks: all
languages: all
---

# Logging & Telemetry Standards

Logging requirements for **Production-tier** code — see
`.github/CODING_GUIDELINES.md#rigor-tiers` for what applies to prototypes
and internal tools instead. Standard concepts (log-level taxonomy,
structured-vs-unstructured logging, OTEL architecture, log rotation) are
covered thoroughly by the tools themselves and by
[OpenTelemetry's docs](https://opentelemetry.io/docs/) — this doc only
covers what this repo actually mandates or has built.

The examples below assume a structured logging library that accepts a
message plus a fields dict as separate arguments (e.g.
[structlog](https://www.structlog.org/) or
[loguru](https://loguru.readthedocs.io/) in Python; `pino` or `winston`
in Node). Python's stdlib `logging` module does not have a `TRACE` level
and does not accept a dict as a positional argument the way these
examples show — if you're on stdlib `logging`, adapt the call shape
(`extra={...}`) or add structlog/loguru as a dependency.

## The mandate (Production tier)

Production-tier code must have centrally-configured, structured logging
with multiple backend support (file, OTEL, console at minimum), proper
rotation, and no sensitive data in log output. This does **not** override
"no sensitive data" — when logging usefulness and secrecy conflict,
redact or omit; don't log the secret "for completeness" (see "What NOT
to log" below). At Production tier, code shipped without this **will not
be accepted** — see Rigor Tiers in `.github/CODING_GUIDELINES.md`.

### What "logging verification" actually means

Before marking Production-tier work complete:

1. Run the code path locally (or in CI) and confirm log lines are
   actually emitted — grep the output/log file for the event names you
   added; don't just read the code and assume.
2. Confirm the log line is valid, parseable JSON (or your configured
   format) — pipe it through `jq` or equivalent once.
3. State in the PR description which events you verified emit correctly
   — the same way the Playwright doc's screenshot-review statement
   works; this is the audit trail for the part CI can't check
   automatically.

## Configuration

`patterns/logging/logging.yaml.example` is the real, tested config
template (its `${VAR:-default}` interpolation syntax is exercised by
`patterns/logging/test_config_loader.py`) — copy and customize it rather
than hand-rolling a schema:

```bash
cp patterns/logging/logging.yaml.example config/logging.yaml
```

### Using the config loader (Python)

`patterns/logging/config_loader.py` handles the `${VAR:-default}`
environment-variable interpolation in that YAML — cleaner than hand-
rolling substitution logic per project:

```python
from lib.config_loader import load_config

config = load_config('config/logging.yaml')
```

**Important:** the loaded config's schema (`backends`/`context`/
`loggers`) is this repo's own portable format, not a Python `dictConfig`
document — passing it straight to `logging.config.dictConfig()` raises
`ValueError: Unable to configure ...`, since `dictConfig` expects its own
shape (`version`, `formatters`, `handlers`, `loggers`). An adapter
translates between the two:

```python
import logging.config
import os


def build_dictconfig(logging_cfg: dict) -> dict:
    """Translate this repo's logging.yaml schema's console/file backends
    into a dict logging.config.dictConfig understands. OTEL/cloud
    backends need their own exporter libraries wired up separately —
    this covers the two stdlib-only backends."""
    backends = logging_cfg.get("backends", {})
    console = backends.get("console", {})
    file_backend = backends.get("file", {})

    handlers = {}
    root_handlers = []

    if console.get("enabled", True):
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": console.get("level", logging_cfg["level"]),
            "formatter": "default",
        }
        root_handlers.append("console")

    if file_backend.get("enabled", False):
        log_path = file_backend.get("path", "./logs")
        os.makedirs(log_path, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": f"{log_path}/app.log",
            "when": "midnight",
            "backupCount": file_backend.get("rotation", {}).get("max_backups", 7),
            "level": logging_cfg["level"],
            "formatter": "default",
        }
        root_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}
        },
        "handlers": handlers,
        "root": {"level": logging_cfg["level"], "handlers": root_handlers},
    }


config = load_config('config/logging.yaml')
logging.config.dictConfig(build_dictconfig(config['logging']))

logger = logging.getLogger('app.auth')
logger.info('User login', extra={'user_id': '12345'})
```

See `patterns/logging/test_config_loader.py` for tested edge cases.

### Other languages

Wire up `pino`/`winston` (Node), `slog` (Go 1.21+), or `logback`/`slf4j`
(Java) per their own docs — none of those integrations are built or
tested in this repo the way the Python `config_loader.py` is, so no
untested snippet is kept here that could mislead the way the Python
`dictConfig` mismatch above once did. If you write and test one, it
belongs here as a worked example, not as an unverified sketch.

## What NOT to log

Never: passwords, API keys/secrets, credit card numbers, SSNs, private
keys, or full request/response bodies containing any of the above.

```python
# Log sanitized fields, not the sensitive value itself
logger.info("user_authentication", {
    "user_id": "123",
    "method": "password",
    "success": True,
    # never: the password itself
})
```

## Logging checklist (before marking Production-tier work complete)

- [ ] Centralized config exists (`config/logging.yaml` or equivalent),
      overridable via environment variables, with sensible defaults
- [ ] Multiple backends configured (file, OTEL, console at minimum)
- [ ] Log rotation configured
- [ ] All critical paths, state changes, and errors logged with context
- [ ] Structured logging used (JSON or key=value), not printf-style
- [ ] No sensitive data in logs (see above)
- [ ] Verified per "What 'logging verification' actually means" above —
      not just "the code looks like it logs things"

---

**See Also:** `patterns/logging/logging.yaml.example`,
`patterns/logging/config_loader.py`, `COMPLETION_CHECKLIST.md`,
`.github/CODING_GUIDELINES.md#rigor-tiers`
