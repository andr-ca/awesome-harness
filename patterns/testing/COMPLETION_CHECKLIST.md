---
name: work-completion-checklist
description: Mandatory checklist before marking work as complete - NEVER skip these steps
complexity: low
frameworks: all
languages: all
---

# Work Completion Checklist

**🚨 CRITICAL: DO NOT MARK WORK COMPLETE UNTIL ALL ITEMS ARE VERIFIED**

The coverage number below is the Production-tier requirement — see
`.github/CODING_GUIDELINES.md#rigor-tiers` and `COVERAGE_REQUIREMENTS.md`.
At Prototype/Internal tier, skip item 2 (or apply whatever coverage floor
that tier actually has, which may be none); everything else still
applies — tests passing and lint passing aren't tier-gated.

Work is NOT done until:
1. ✅ All tests PASS (no exceptions, no skips)
2. ✅ Coverage is >= 80% (Production tier — verified, measured)
3. ✅ ALL lint checks PASS (no exceptions)
4. ✅ Edge cases are tested
5. ✅ No failures from other work (even if caused by someone else)

## Pre-Completion Verification

### 1. Run All Tests

**MUST DO:**
```bash
# Run ALL tests, don't filter or skip
pytest                    # Python
npm test                  # JavaScript/TypeScript
go test ./...            # Go
./gradlew test           # Java
cargo test               # Rust

# Expected result: ALL PASS ✅
```

**DO NOT:**
- ❌ Skip failing tests
- ❌ Mark flaky tests as skip
- ❌ Accept test failures
- ❌ Run only your changes
- ❌ Ignore failures in other packages

**If ANY test fails:**
1. Understand why it failed
2. If it's YOUR change: fix your code
3. If it's SOMEONE ELSE's broken test: fix it anyway
   - Leave a note in the PR about the fix
   - Coordinate with the other contributor
4. Verify the fix works: run tests again

### 2. Verify Test Coverage

**MUST DO:**
```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term
pytest --cov=src --cov-fail-under=80      # Python

jest --coverage                           # JavaScript/TypeScript
go test ./... -cover                      # Go

# Expected result: >= 80% coverage
```

**Coverage tiers:** see `COVERAGE_REQUIREMENTS.md` — that file is the
single source of truth for the tier thresholds so this checklist doesn't
drift out of sync with it. Short version: 80% is the floor.

**If coverage < 80%:**
1. Identify untested code
2. Write tests for that code
3. Verify all edge cases are tested
4. Re-run coverage check
5. Repeat until >= 80%

**Coverage must be measured, not assumed:**
```bash
# WRONG: "I think coverage is fine"
# RIGHT: "Coverage report shows 87%"
```

### 3. Run Linting & Formatting

**MUST DO:**
```bash
# Format code
black .                    # Python
ruff format .             # Python
prettier . --write        # JavaScript/TypeScript
go fmt ./...              # Go
gofmt -w .                # Go (alternative)

# Lint code
ruff check .              # Python (with fixes)
ruff check . --fix        # Python (auto-fix)
npm run lint              # JavaScript/TypeScript
npm run lint -- --fix     # JavaScript/TypeScript (auto-fix)
go vet ./...              # Go
```

**Expected result: NO LINT ERRORS ✅**

**If lint fails:**
1. Understand the lint rule
2. Fix the code to comply
3. Don't suppress the lint rule unless:
   - The rule is genuinely wrong for this case
   - You've discussed with team
   - You document WHY with a comment
4. Re-run linting

**NEVER suppress lint errors just to pass:**
```python
# ❌ WRONG: Hiding lint errors
# noqa: E501  (suppress long line warning)
def function_with_very_long_name_that_exceeds_line_limit():
    pass

# ✅ RIGHT: Fix the underlying issue
def shorter_function_name():
    pass
```

### 4. Test Edge Cases

**MUST DO: For every piece of code, test:**

- ✅ **Happy path** – Normal operation
- ✅ **Error cases** – Invalid input, exceptions
- ✅ **Boundary conditions** – Empty, null, min/max values
- ✅ **Special cases** – Unicode, very large data, concurrent access
- ✅ **Integration points** – APIs, databases, external services

**Example:**

```python
# Function: calculate_discount(price, discount_rate)

# Happy path ✅
def test_calculate_discount_normal():
    assert calculate_discount(100, 0.1) == 90

# Boundary ✅
def test_calculate_discount_zero_price():
    assert calculate_discount(0, 0.1) == 0

def test_calculate_discount_zero_discount():
    assert calculate_discount(100, 0) == 100

def test_calculate_discount_full_discount():
    assert calculate_discount(100, 1.0) == 0

# Error cases ✅
def test_calculate_discount_negative_price():
    with pytest.raises(ValueError):
        calculate_discount(-100, 0.1)

def test_calculate_discount_invalid_rate():
    with pytest.raises(ValueError):
        calculate_discount(100, -0.1)

def test_calculate_discount_rate_over_100():
    with pytest.raises(ValueError):
        calculate_discount(100, 1.5)

# Edge cases ✅
def test_calculate_discount_very_small_price():
    assert calculate_discount(0.01, 0.5) == 0.005

def test_calculate_discount_very_large_price():
    assert calculate_discount(999999999, 0.1) == 899999999.1
```

**If you haven't tested edge cases, work is NOT complete.**

### 5. Handle Inherited Failures

**CRITICAL: You are responsible for ALL test failures, regardless of origin.**

**If ANY test fails in your test run:**

```bash
# You see this:
FAILED: src/payment/processor.py::test_process_payment
ERROR: src/user/validator.py::test_validate_email

# Even if you didn't write that code, YOU must:
1. ✅ Understand why it's failing
2. ✅ Fix it
3. ✅ Verify the fix
4. ✅ Document your fix in the PR description
```

**Why this matters:**
- Failing tests hide real problems
- You can't merge with failing tests
- Someone else's broken code blocks everyone
- Fixing it helps the whole team

**Example scenario:**

```
You: "I'm done with my feature"
CI: ❌ test_validate_email is failing
You: "That's not my code"
WRONG! ✅ You must fix it or find who can
You: *fixes the test*
You: "Ready to review, also fixed validate_email issue in PR description"
```

**Exceptions (there are none):**
- ❌ "Someone else broke it" - Still your responsibility
- ❌ "It was already failing" - Fix it before your PR
- ❌ "It's flaky" - Make it deterministic
- ❌ "It's slow" - Optimize it

## Logging & Telemetry Requirements (MANDATORY)

**All code MUST have proper logging and telemetry.**

- [ ] Centralized logging configuration created (logging.yaml or equivalent)
- [ ] All settings configurable via environment variables
- [ ] Sensible defaults work without configuration
- [ ] Multiple backends configured (file, OTEL, console, cloud)
- [ ] Log rotation configured (daily or size-based)
- [ ] Retention policies set (by severity and functionality)
- [ ] All critical events logged (auth, operations, errors)
- [ ] All errors logged with full context
- [ ] All external API calls logged
- [ ] Structured logging used (JSON format)
- [ ] Sensitive data NOT logged (passwords, secrets, PII)
- [ ] Trace IDs used for distributed tracing
- [ ] Telemetry/metrics configured and exported
- [ ] Key metrics identified and being collected
- [ ] Logs tested in development (output visible)
- [ ] Log files created and rotation working
- [ ] OTEL export tested (if configured)
- [ ] Log parsing verified (valid JSON)
- [ ] Documentation: How to configure logging
- [ ] Documentation: How to access logs
- [ ] Documentation: How to debug using logs

**At Production tier, logging is not optional — code without it WILL NOT MERGE. See Rigor Tiers in `.github/CODING_GUIDELINES.md`.**

---

## Complete Work Checklist

Use this before saying "work is done":

### Code Quality
- [ ] Code passes all linters and formatters
- [ ] Code uses consistent naming conventions
- [ ] Code has no obvious bugs or anti-patterns
- [ ] Code is readable and maintainable
- [ ] Code follows project conventions

### Testing
- [ ] ALL unit tests PASS ✅
- [ ] ALL integration tests PASS ✅
- [ ] ALL E2E tests PASS ✅
- [ ] No skipped tests (`@skip`, `.skip()`, etc.)
- [ ] No flaky tests (deterministic, not timing-dependent)

### Coverage
- [ ] Coverage report generated and verified
- [ ] Coverage >= 80% (minimum requirement)
- [ ] Strive for 90%+ coverage
- [ ] All public functions have tests
- [ ] All error paths tested
- [ ] All edge cases tested

### Edge Cases (Non-Negotiable)
- [ ] Empty/null input tested
- [ ] Maximum/minimum values tested
- [ ] Invalid input tested
- [ ] Concurrent access tested (if applicable)
- [ ] Large data sets tested (if applicable)
- [ ] Special characters/Unicode tested (if applicable)

### Error Handling
- [ ] All exceptions caught and tested
- [ ] Error messages are clear and helpful
- [ ] Error conditions have test coverage
- [ ] Graceful degradation tested

### Integration
- [ ] External service calls mocked/stubbed in tests
- [ ] Database operations tested (with transactions)
- [ ] API endpoints tested for success and failure
- [ ] Error handling for external failures tested

### Lint & Formatting
- [ ] Code formatted (black, prettier, go fmt, etc.)
- [ ] Linter passes (ruff, eslint, golangci-lint, etc.)
- [ ] No lint suppressions without justification
- [ ] Type checking passes (mypy, tsc, etc.)

### Documentation
- [ ] Public functions documented (docstrings)
- [ ] Complex logic explained with comments
- [ ] Configuration documented
- [ ] Breaking changes noted

### Final Verification
- [ ] Run full test suite: ALL PASS
- [ ] Check coverage: >= 80%
- [ ] Run linter: NO ERRORS
- [ ] All inherited failures fixed
- [ ] No @skip or .skip() in code
- [ ] No hard-coded test data or paths

## Pre-PR Checklist

Before creating a PR, verify locally:

```bash
# 1. Run tests (everything)
pytest                              # or your test runner
# Expected: ALL PASS ✅

# 2. Check coverage
pytest --cov=src --cov-fail-under=80  # Python
# Expected: >= 80% coverage ✅

# 3. Format code
ruff format .                       # Python
# Expected: Code reformatted ✅

# 4. Run linter
ruff check . --fix                  # Python
# Expected: NO ERRORS ✅

# 5. Type check (if applicable)
mypy .                              # Python
# Expected: NO TYPE ERRORS ✅

# Git status
git status
# Expected: Only your changes (no unexpected files)

# 6. Final verification
echo "All checks passed!"
git add .
git commit -m "Your commit message"
git push -u origin your-branch
```

## If Work Doesn't Pass Checks

### Tests Are Failing

```
STEP 1: Understand why
- Read the test name (should describe what failed)
- Read the assertion (what was expected vs actual)
- Look at the test code (what is it checking)

STEP 2: Fix it
- If it's your code: fix the implementation
- If it's someone else's test: investigate and fix

STEP 3: Verify
- Run the test again
- Verify it passes
- Run all related tests
- Run full test suite

STEP 4: Commit
- If you changed test: commit as part of your work
- If you changed production code: commit as part of your work
- Note in PR description if you fixed another's test
```

### Coverage Is Below 80%

```
STEP 1: Identify untested code
- Look at coverage report (shows missing lines)
- Coverage report should highlight untested paths

STEP 2: Write tests
- Test the untested code
- Include edge cases
- Include error cases

STEP 3: Verify
- Re-run coverage report
- Verify >= 80%
- Verify tests actually test something

STEP 4: Commit
- Add tests to your commit
- Note coverage increase in PR
```

### Linter Is Failing

```
STEP 1: Understand the rule
- What is the linter complaining about?
- Why does this rule exist?

STEP 2: Fix it
- Auto-fix if possible (ruff --fix)
- Manual fix if needed

STEP 3: Verify
- Re-run linter
- All errors resolved

STEP 4: Commit
- Formatting changes are part of your commit
```

## Definition of Done

Work is DONE when:

✅ **All tests PASS**
- Run full test suite
- No failures, no skips

✅ **Coverage >= 80%**
- Measured and verified
- Report available

✅ **No lint errors**
- Code formatted
- Linter passes

✅ **Edge cases tested**
- Boundaries tested
- Error conditions tested
- Special cases tested

✅ **No inherited failures**
- All test failures fixed
- Even if caused by someone else

✅ **Ready to merge**
- Code review approved
- CI/CD passes
- No blockers

## Special Requirements for Web UI Work

### ALL Web UI Development MUST Use Playwright

**Mandatory for ANY UI work:**
- ✅ Use Playwright (not optional alternative)
- ✅ Write tests BEFORE building UI (TDD)
- ✅ Include screenshot verification in every test
- ✅ Test multiple browsers (Chrome, Firefox, Safari, mobile)
- ✅ Test responsive design
- ✅ Agent/human MUST verify screenshots visually
- ✅ No visual regressions accepted
- ✅ Screenshots must match expected appearance

### UI Work Cannot Be Complete Without
- [ ] All Playwright tests written
- [ ] All tests PASS
- [ ] Coverage >= 80%
- [ ] Screenshots taken and verified
- [ ] Agent has reviewed and approved screenshots
- [ ] No visual regressions detected
- [ ] Responsive design verified
- [ ] Cross-browser tested (at minimum: Chrome, Firefox, Safari)
- [ ] Mobile responsiveness confirmed
- [ ] Accessibility verified

**Screenshots are MANDATORY - visual verification is REQUIRED**

See: `PLAYWRIGHT_UI_TESTING.md` for complete UI testing guide

---

## Never Claim Work Complete If

❌ Tests are failing
❌ Coverage < 80%
❌ Linter has errors
❌ Edge cases untested
❌ Tests are skipped
❌ Lint rules are suppressed without justification
❌ There are code TODOs
❌ Type checking fails
❌ Other tests are broken
❌ **UI work without Playwright tests** (WEB UI ONLY)
❌ **UI screenshots not reviewed and approved** (WEB UI ONLY)
❌ **Visual regressions present** (WEB UI ONLY)

---

**REMEMBER:** Done means DONE. Not "mostly done." Not "done except for tests." DONE.

**If work doesn't pass these checks, it's not done. No exceptions.**

**Status:** MANDATORY REQUIREMENTS  
**See Also:** TDD.md, COVERAGE_REQUIREMENTS.md, CODING_GUIDELINES.md
