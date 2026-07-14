---
name: mutation-testing
description: Mutation testing — verifying test suite quality beyond line/branch coverage by introducing deliberate code changes and checking whether tests detect them
complexity: medium
frameworks: all
languages: all
---

# Mutation Testing

## What it is and why it matters

**Line/branch coverage measures whether your tests *execute* code. Mutation
testing measures whether your tests *detect bugs* in that code.**

A "mutation" is a small, deliberate change to the source code — a single
operator flip, constant replacement, or statement removal. If your tests
pass after a mutation, the mutation "survived": your test suite would not
have caught that real bug.

```python
# Original
def is_above_threshold(value: float, threshold: float) -> bool:
    return value > threshold

# Mutation (> changed to >=)
def is_above_threshold(value: float, threshold: float) -> bool:
    return value >= threshold
```

If `test_is_above_threshold` only checks `is_above_threshold(5, 3) is True`,
it passes with the mutation — a surviving mutant that reveals a weak test.

---

## Mutation operators

Tools apply mutations systematically. Common operator categories:

| Category | Example mutation |
|---|---|
| Arithmetic | `+` → `-`, `*` → `/` |
| Relational | `>` → `>=`, `==` → `!=` |
| Logical | `and` → `or`, `not x` → `x` |
| Assignment | `x += 1` → `x -= 1` |
| Statement | delete a `return` or `raise` statement |
| Constant | `0` → `1`, `True` → `False` |
| Boundary | `< n` → `<= n`, `== 0` → `== -1` |

---

## Mutation score

$$\text{mutation score} = \frac{\text{killed mutants}}{\text{total mutants} - \text{equivalent mutants}} \times 100\%$$

An **equivalent mutant** is one that changes the code but not its
observable behaviour — it cannot be killed by any test. Exclude them from
the denominator.

**Suggested thresholds (Production tier):**

| Score | Verdict |
|---|---|
| ≥ 80% | Strong test suite; mutants that survive warrant inspection |
| 60–79% | Adequate; identify the surviving mutant categories and add targeted tests |
| Below 60% | Test suite quality is insufficient; line/branch percentages alone are misleading |

Note: mutation testing is computationally expensive. Apply it to critical
business logic and security-sensitive paths first, not to every file.

---

## Python — mutmut

```bash
# Install
pip install mutmut

# Run against a module
mutmut run --paths-to-mutate src/billing.py

# Show surviving mutants
mutmut results

# Show the diff for a specific surviving mutant
mutmut show 15

# HTML report
mutmut html
```

**Tips:**
- Scope `--paths-to-mutate` to the critical module, not the whole project.
  Full-project mutation runs can take hours.
- Cache between runs: mutmut stores results in `.mutmut-cache/`.
- To run only on changed files in CI:
  ```bash
  git diff --name-only HEAD~1 | grep '\.py$' | xargs -I{} mutmut run --paths-to-mutate {}
  ```

**Alternative: cosmic-ray** (supports distributed execution):

```bash
pip install cosmic-ray
cosmic-ray init config.toml session.sqlite
cosmic-ray exec config.toml session.sqlite
cosmic-ray report session.sqlite
```

---

## JavaScript / TypeScript — Stryker

```bash
# Install
npm install --save-dev @stryker-mutator/core @stryker-mutator/jest-runner

# Init config
npx stryker init

# Run
npx stryker run
```

`stryker.config.js` (or `.json`):

```javascript
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
module.exports = {
  testRunner: 'jest',
  reporters: ['html', 'clear-text', 'progress'],
  coverageAnalysis: 'perTest',
  mutate: ['src/billing/**/*.ts'],   // scope to critical code
  thresholds: { high: 80, low: 60, break: 50 },
};
```

- `thresholds.break` causes Stryker to exit non-zero (CI gate) if the
  score falls below this value.
- `coverageAnalysis: 'perTest'` runs only the tests that cover each
  mutant — significantly faster than `'all'`.

---

## Go — gremlins

```bash
# Install
go install github.com/nicholasgasior/go-gremlins@latest
# or the more actively maintained fork:
go install github.com/go-gremlins/gremlins/cmd/gremlins@latest

# Run
gremlins unleash ./...

# Scope to a specific package
gremlins unleash ./internal/billing/...
```

Gremlins outputs a summary showing killed/survived/timed-out mutants per
file. Timed-out mutants (the test suite hung) are treated as killed for
scoring purposes.

---

## Interpreting surviving mutants

A surviving mutant is not always a test you need to write. Categorise
before acting:

| Type | Meaning | Action |
|---|---|---|
| **True gap** | Real code path not covered by any assertion | Write the missing test |
| **Weak assertion** | Code is executed but no assertion verifies the outcome | Strengthen the test (assert the output, not just that no exception was raised) |
| **Equivalent mutant** | The change doesn't affect observable behaviour | Document and exclude from score |
| **Acceptable risk** | The mutant is in a non-critical path and the test cost is high | Document the decision; revisit if the path becomes critical |

Use `mutmut show <id>` / Stryker's HTML report to read the exact diff
before deciding which category applies.

---

## Cost management

Mutation testing is significantly slower than line-coverage measurement.
Strategies to keep CI fast:

1. **Scope to critical paths.** Run mutation testing only on modules with
   high business impact (payment processing, auth, data validation).
2. **Run on schedule, not on every push.** A nightly CI job is a common
   pattern — failures create issues rather than blocking PRs.
3. **Use per-test coverage analysis** (Stryker's `coverageAnalysis: 'perTest'`
   or mutmut's `--use-coverage`). Only test the mutants actually covered by
   the test suite.
4. **Run in parallel.** mutmut and Stryker support parallel execution.
5. **Incremental runs.** Run only against files changed in the current PR.

---

## Review checklist

- [ ] Mutation testing scoped to critical/security-sensitive modules only
- [ ] Mutation score: 60% or higher for covered modules (80%+ for payment/auth paths)
- [ ] Surviving mutants triaged: true gaps have new tests; equivalent
      mutants documented; acceptable-risk decisions recorded
- [ ] CI configured to run mutation tests on schedule (not on every push
      unless the module is small)
- [ ] Thresholds enforced via exit code (Stryker `break`, or `mutmut` +
      a score check script)
