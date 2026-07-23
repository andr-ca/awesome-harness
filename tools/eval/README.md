# Eval Suite

Measures whether installing this harness (skills + conventions docs)
actually changes a coding agent's output on a fixed set of small tasks —
baseline (no harness) vs. treatment (harness installed via
`harness-link.sh init`), scored the same deterministic way both times.

| File | Covers |
|---|---|
| [`tasks/`](./tasks/) | Task definitions: prompt, starter code, hidden grading tests |
| [`score.py`](./score.py) | Deterministic scorer — runs the task's hidden tests against a candidate's code, no LLM calls |
| [`run.py`](./run.py) | Orchestrates baseline/treatment conditions and appends to the ledger — the actual agent call is a pluggable dependency, unimplemented by default (see below) |
| [`fixtures/`](./fixtures/) | Hand-written correct/broken implementations per task, used to test `score.py` itself |
| [`results/`](./results/) | The append-only score ledger |

## Task format

Each `tasks/<id>/` directory has:

- `task.yaml` — `id`, `title`, `language`, `entry_module`,
  `coverage_threshold`, `prompt` (what the agent is asked to do).
- `starter/` — the code handed to the agent, as-is.
- `tests/` — hidden tests the agent never sees, copied in alongside the
  agent's output at scoring time. These encode the rubric: a happy-path
  test, plus edge-case tests (named with `edge`/`Edge`) that must also
  pass for `edge_cases_pass` to be true.

Adding a task means adding a new `tasks/<id>/` directory in this shape,
plus a `fixtures/<id>/{correct,broken}/` pair so `score.py`'s own test
suite (`tests/test_score.py`) covers it.

## Scoring a candidate directly

```bash
python3 tools/eval/score.py --task tools/eval/tasks/python-input-validation \
  --candidate /path/to/some/implementation
```

Prints a JSON rubric result (`tests_pass`, `coverage_met`, `lint_clean`,
`edge_cases_pass`, `overall_score`) and exits 0 only if every criterion
was met.

## Running a real eval

`run.py`'s `invoke_agent_via_api` — the piece that would drive a live
coding-agent session against the Anthropic API — is deliberately left
`NotImplementedError`. This is intentional, not unfinished: a real run
spends real API credits per call, and this repo's standing rule is that
nothing spends a user's money without their explicit go-ahead on that
specific run.

Before running a real eval:

1. Implement `invoke_agent_via_api` (or pass your own callable matching
   `run.InvokeAgent`'s signature) to actually drive a session — write
   the task's `prompt` to a working copy of `starter/` (already staged
   for you by `run_condition`), invoke your agent of choice, and return
   an `AgentResult` pointing at wherever it left its output.
2. Copy [`.env.sample`](./.env.sample) to `.env` and set
   `ANTHROPIC_API_KEY` (or whatever your chosen agent needs). `.env` is
   gitignored — never commit real keys.
3. Confirm the expected cost with whoever is paying for it.
4. Call `run.run_condition(task_id, condition, invoke_agent_via_api)` for
   both `"baseline"` and `"treatment"`, and `run.append_to_ledger(...)`
   each result into `results/ledger.jsonl`.

`tools/eval/tests/test_run.py` exercises all of the orchestration logic
above (condition setup, harness install for `treatment`, scoring, ledger
writing) with a fake `invoke_agent` that costs nothing — that's what's
verified in CI, not a real API call.

## Instruction-quality / whole-journey evals (P2-03)

The code-correctness tasks above measure whether the harness helps an
agent write *correct code*. They do not measure the harness's actual
differentiator: whether an agent that has read `CLAUDE.md` + the skills
*follows the rules*, and how much human rework the whole journey cost.

`journey_score.py` is the deterministic scorer for that — the
actions/transcript analog of `score.py`, graded on a **recorded session**
instead of compiled output, with **no API calls and no money spent**. It
takes a session record (`schemas/session-v1.json` shape) plus a scenario
rubric and returns per-check booleans + always-reported journey metrics
(corrective prompts, implementation attempts, human interventions,
plan-to-code divergence, cost-to-acceptance).

Fixed check vocabulary (a rubric activates the ones a scenario needs):
`expected_skill_triggered`, `irrelevant_skill_avoided`,
`refused_publish_without_authority`, `existing_hooks_preserved`.

Scenarios live in `scenarios/<id>/` with a `rubric.yaml` plus a
`correct/` and `violating/` fixture session — the same shape as the
`fixtures/` pairs that test `score.py`. Score one directly:

```bash
python3 journey_score.py --scenario scenarios/skill-triggering \
  --record scenarios/skill-triggering/correct/session.json
```

### Producing real sessions (the paid step, deliberately unimplemented)

`journey_run.py` mirrors `run.py`'s seam: `run_scenario(scenario_id,
condition, invoke_agent)` runs a scenario under `baseline`/`treatment`,
hands off to an injected `invoke_agent` to *produce* the session record,
scores it, and writes a ledger entry. The producer is the **only** place
a live LLM call would ever happen — and `invoke_agent_via_api` is left
`NotImplementedError` for the same reason it is in `run.py`: a real run
needs `ANTHROPIC_API_KEY` and spends real money, so it stays a
user-triggered step. Adding real evals means implementing that one
function to emit a `session-v1` record; the scorer and everything above
are unchanged.
