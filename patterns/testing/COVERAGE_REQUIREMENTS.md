---
name: test-coverage-requirements
description: Mandatory test coverage requirements (80% minimum) and enforcement
complexity: medium
frameworks: all
languages: all
---

# Test Coverage Requirements

This applies at the **Production** rigor tier — see
`.github/CODING_GUIDELINES.md#rigor-tiers` and `patterns/profiles/`.
Prototypes have no coverage requirement; internal tools cover what's
expensive to get wrong and skip pure glue, with no numeric floor. Nothing
below assumes otherwise — every "mandatory"/"no exceptions" statement in
this doc is scoped to Production-tier code, the same tier the 80% number
itself belongs to.

## The requirement

**At Production tier: minimum 80% test coverage**, measured as line +
branch coverage (every if/else path, every case, every exception path
exercised by at least one test). This applies to all production code,
libraries, and agents/orchestrators — not to test code itself, generated
code, third-party dependencies, or configuration-only files.

| Coverage | Status | Action |
|----------|--------|--------|
| 80–100% | Meets requirement | Approve & merge |
| 75–79% | Below minimum | Request additional tests |
| <75% | Unacceptable | Reject, require rewrite |

Rough pyramid shape, as a guide for where tests should concentrate, not a
mechanically-enforced ratio: ~70% unit, ~25% integration, ~5% end-to-end.

### The only two exceptions: pragma comments and test code

`# pragma: no cover` (or your language's equivalent) is for code that is
genuinely unreachable — not a way to skip something inconvenient to
test:

```python
# Acceptable: truly unreachable in this codebase's supported versions
if sys.version_info >= (3, 10):
    new_feature()
else:  # pragma: no cover
    old_feature()

# NOT ACCEPTABLE: hides real, reachable logic from the coverage report
def important_function():
    if never_happens:  # pragma: no cover
        critical_logic()
```

Test fixtures and test utilities don't themselves need coverage — but a
"passing" test that doesn't actually exercise the assertion it claims to
(a mocked-away code path, an assertion that can't fail) doesn't count
either.

## Measuring coverage

Each language's own coverage tool (`pytest-cov`, Jest's `--coverage`,
`go test -cover`, JaCoCo, ...) reports this the same way any project
would use it — see that tool's own docs for install/config/CI wiring.

One repo-specific gotcha: `go tool cover -func` reports a float
(`87.5%`), so a plain `-lt` integer comparison in a shell script breaks
with "integer expression expected". Use `bc` for the comparison instead:

```bash
COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    echo "Coverage $COVERAGE% below minimum 80%"
    exit 1
fi
```

## Handling low coverage

Don't lower the requirement, don't reach for `# pragma: no cover` to
make a red number go away, and don't merge with a plan to "add tests
later." If code is too complex to test, that's a signal the code itself
needs to be simplified (smaller functions, injected dependencies, fewer
responsibilities) — not that the test requirement should bend.

## Aiming above the floor

The 80% number is the floor, not a target — the actual enforced minimum
is the single flat number from `patterns/profiles/production.yaml`, not a
per-module breakdown (there isn't a mechanically-checked one). Where you
choose to aim higher is a project call, but as a rule of thumb, risk goes
up with these categories, in roughly this order:

- **Core/shared libraries** — the foundation; a bug here affects everything
  that imports it, so push toward 95%+
- **Business logic** — the part of the app that's actually worth
  protecting; aim for 90%+
- **Integrations & APIs** — external failure modes are numerous and easy
  to miss; 85%+ with mocked success/failure paths
- **Configuration & utilities** — still real code with real bugs; the
  80% floor applies same as anywhere else

This ordering is guidance for where to spend extra effort, not a second
set of mandates layered on top of the one enforced number.

## Code review checklist

- [ ] All new code has tests; coverage report shows >= 80%
- [ ] No pragma comments hiding reachable code; no skipped tests
- [ ] Tests verify behavior, not implementation, and are deterministic
- [ ] Happy path, error cases, and edge/boundary conditions are all tested
- [ ] Integration points (API/DB/external calls) are mocked appropriately

**If coverage < 80%, request changes before approval.**

---

**At Production tier:** 80% is the floor, not the target — see
`.github/CODING_GUIDELINES.md#rigor-tiers` for what this requirement does
and doesn't apply to. See also `TDD.md`.
