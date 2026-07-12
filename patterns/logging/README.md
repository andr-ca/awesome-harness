# Logging & Telemetry

Index for this directory — each doc/file below is the single source of
truth for its topic; this file doesn't restate their content, just
routes to it.

Logging is mandatory at the **Production** rigor tier — see
`.github/CODING_GUIDELINES.md#rigor-tiers` and `patterns/profiles/` for
what changes at Prototype/Internal tiers.

| File | Covers |
|---|---|
| [LOGGING_STANDARDS.md](./LOGGING_STANDARDS.md) | The mandate, verification requirement, config-loader usage, what NOT to log, the pre-completion checklist |
| [logging.yaml.example](./logging.yaml.example) | The real, tested config template — copy and customize, don't hand-roll a schema |
| [config_loader.py](./config_loader.py) | `${VAR:-default}` environment-variable interpolation for the YAML above (tested in `test_config_loader.py`) |

**Read LOGGING_STANDARDS.md first** — it's short and states what this
repo actually requires; everything else here supports it.
