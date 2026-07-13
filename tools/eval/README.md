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

## Instruction-quality evals (P2-03, planned)

The code-correctness tasks above measure whether the harness helps an
agent write *correct code*. They do not yet measure the harness's actual
differentiator: whether an agent that has read `CLAUDE.md` + the skills
*follows the rules*. Planned task shapes (not built yet — tracked in
[ROADMAP.md](../../ROADMAP.md), P2-03):

- **Skill triggering** — a prompt whose correct handling requires loading
  a specific skill; score whether the agent surfaced it.
- **Irrelevant-skill avoidance** — a prompt adjacent to a skill's domain
  that should *not* trigger it; score whether the agent stayed out.
- **Rule precedence** — an explicit request that conflicts with a
  profile/language default; score whether precedence was resolved per
  `patterns/profiles/README.md`.
- **Refusal to publish without authority** — a "push and open a PR" ask
  with no `.agentharness-publish-mode` flag present; score whether the
  agent stopped at verify-and-stage.

Each needs a deterministic rubric like `score.py`'s, but graded on the
agent's *actions/transcript* rather than compiled output — a scorer this
repo doesn't have yet.
