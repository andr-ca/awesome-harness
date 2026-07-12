# Results Ledger

`ledger.jsonl` (created on first run, not checked in empty) is an
append-only JSON-lines file — one object per line, one line per
`(task, condition)` run:

```json
{"date": "2026-07-12", "task": "python-input-validation", "condition": "treatment", "score": 1.0, "cost": 0.0312, "model": "claude-sonnet-5"}
```

| Field | Meaning |
|---|---|
| `date` | ISO 8601 date the run happened |
| `task` | Task id under `tools/eval/tasks/` |
| `condition` | `baseline` (no harness) or `treatment` (harness installed) |
| `score` | `overall_score` from `score.py` — fraction of the rubric met, 0.0-1.0 |
| `cost` | USD spent on the API call(s) for this run |
| `model` | Model identifier used |

Committed to git (like the rest of this repo's operational history) so
score trends over time are visible without extra infrastructure — append
to it, don't rewrite past lines.

See [`../README.md`](../README.md) for how a run actually gets produced.
