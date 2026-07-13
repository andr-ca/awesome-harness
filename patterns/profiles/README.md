# Rigor-Tier Profiles

`.github/CODING_GUIDELINES.md#rigor-tiers` describes three tiers in
prose. The files in this directory are the same three tiers as
machine-readable YAML — `prototype.yaml`, `internal.yaml`,
`production.yaml` — so a project (or a script) can *select* a tier
instead of an agent re-reading and re-interpreting a table every time.

The YAML files are the source of truth for which values apply; the
prose table remains the source of truth for *why* — don't let the two
drift apart, update both together.

## Selecting a profile

A project declares its tier by creating a one-line `.agentharness-profile`
file at its repo root, containing exactly one of `prototype`, `internal`,
or `production`:

```bash
echo production > .agentharness-profile
```

**Current state — enforced for Python, Go, and JS/TS (`node --test` or
Vitest) projects; advisory for everything else.** `harness-link.sh
enforce-profile <project>` reads `.agentharness-profile` and gates on it
for real, at a tier where `tests.required` is not `false` (prototype
skips entirely):

- **Python** (`pyproject.toml`/`setup.py`/`requirements.txt` present):
  runs `pytest --cov-fail-under=<tier's coverage_min>` and fails if it
  doesn't pass.
- **Go** (`go.mod` present): runs `go test -coverprofile ./...` and gates
  the `go tool cover -func` total against the tier's `coverage_min` —
  both standard-toolchain, no third-party dependency.
- **JS/TS** (`package.json` present): a project whose `"test"` script
  invokes Node's built-in `node --test` (per-file coverage summary) or
  Vitest (`coverage-summary.json`'s `total.lines.pct`) gets real
  enforcement — the two JS runners with a stable, machine-readable
  coverage output this repo can parse without guessing. Jest, Mocha, or
  anything else gets a clear "not implemented for this runner" and, by
  default, exits 0.

A project this can't classify at all (no recognizable project file)
gets "not implemented yet" and exits 0 — it never falsely blocks or
falsely passes something it can't actually check. Pass **`--strict`** to
turn every such "not implemented" case into a failure instead, so a CI
job can require that every project it runs against is one enforcement
actually understands.

This is **not** wired into `.github/hooks/pre-push` automatically —
that hook still only ever runs *this* repo's own hardcoded test suites
and no-ops for a consumer's push (see the hook's own comments and
`docs/operational/reviews/gpt-5.6-review-status.md`, finding 1).
Silently changing that default for every project that already has
`--with-hook` installed is its own decision; `enforce-profile` ships
first as an explicitly-invoked subcommand, same posture as
`audit`/`doctor`, so a project or CI job opts in by calling it.

Go profile enforcement, and JS/TS enforcement for runners other than
`node --test`, remain unimplemented — tracked in `ROADMAP.md` as natural
extensions once there's real usage to learn from.

## Precedence order

When a rule in the Rigor Tiers table could apply at more than one level,
higher wins:

1. **Explicit instruction in the current request** — a human saying
   "treat this as production tier" (or naming a specific bar like "add
   tests for this") overrides everything below, for that request only.
2. **A repo-local override** — a project's own `CLAUDE.md` or equivalent
   stating a different tier for a specific directory or module (e.g. "the
   `scripts/` directory stays prototype tier even though the rest of this
   repo is production").
3. **The profile selected via `.agentharness-profile`.**
4. **Language/framework-specific add-on guidance** — e.g.
   `languages/python/CONVENTIONS.md` — where it's more specific than the
   generic tier table for that language.
5. **The generic default** — the Rigor Tiers table's `internal` column,
   used when nothing above says otherwise. If profile selection is ever
   wired into a mechanical gate (see "Current state" above), that gate
   must default to `production` (fail-safe) rather than `internal`
   whenever `.agentharness-profile` is absent or unrecognized — a missing
   or misspelled file must never silently relax enforcement.

## Disabling a profile requirement locally

There's no override flag beyond precedence level 2 above (a repo-local
statement) — if a specific rule genuinely doesn't apply to your project,
say so explicitly in your own `CLAUDE.md` rather than deleting or
downgrading `.agentharness-profile`, so the exception is visible in your
own repo's history and isn't silently inherited by every rule at once.
