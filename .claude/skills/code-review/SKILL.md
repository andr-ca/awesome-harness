---
name: code-review
description: Use when reviewing a diff, pull request, or code change — systematic checklist for correctness, clarity, security, testability, and adherence to the project's conventions. Covers what to look for, how to give actionable feedback, and when to approve vs. request changes.
metadata:
  type: skills
  complexity: medium
  scope: [all]
---

# Code Review

A systematic approach to reviewing diffs and pull requests. Work through
the categories below in order — correctness first, style last.

---

## Pre-read checklist

Before reading the diff:
- Read the PR description. Does it explain *why* the change is needed?
  If the description is missing or just "fixes stuff", ask for one before
  reviewing — the diff alone won't tell you whether the approach is right.
- Check the linked issue or ticket if there is one.
- Note the rigor tier (`patterns/profiles/` or `.agentharness-profile`)
  — the coverage and testing requirements differ.

---

## 1. Correctness

The most important category. Ask: *"Can this code produce wrong results?"*

- Does the logic match the stated goal?
- Are there off-by-one errors, wrong comparisons, or incorrect
  assumptions about the data?
- Are all inputs validated before use?
- Are edge cases handled: empty collections, zero, null/None/undefined,
  negative numbers, max values, concurrent access?
- Does error handling actually handle the error, or does it swallow it?

```python
# Swallowed error — caller sees success, wrong data silently used
try:
    value = parse_config(raw)
except Exception:
    pass  # WRONG: value is now unset or stale

# RIGHT: propagate or at minimum log + re-raise
try:
    value = parse_config(raw)
except ConfigError as e:
    logger.error("config parse failed", error=e)
    raise
```

---

## 2. Security

Run through the relevant items from the `security-review` skill (load it
for the full checklist). The most common PR-level findings:

- Secrets or API keys hardcoded or logged.
- SQL/shell/HTML built via string formatting with user input.
- Missing ownership/permission checks on resource access.
- New dependency with known CVEs (`npm audit` / `pip-audit` not run).

---

## 3. Test coverage

At Production tier, new code must have tests. Check:

- Is there a test for the happy path?
- Is there a test for at least one failure/edge case?
- Do the tests assert on behaviour (what the code does), not
  implementation (how it does it)?
- Are mocks covering real logic paths, not short-circuiting the code
  being tested?

```python
# BAD: mocks away the thing being tested
def test_send_email():
    with patch("mailer.send") as mock_send:
        service.send_welcome(user)
    mock_send.assert_called_once()
    # Proved nothing about send_welcome's logic

# GOOD: test the observable outcome
def test_send_email_queues_message(fake_queue):
    service.send_welcome(user)
    assert len(fake_queue.messages) == 1
    assert fake_queue.messages[0].to == user.email
```

---

## 4. Clarity and naming

Code is read far more often than it's written. Ask:

- Do variable, function, and type names say what the thing *is*, not
  what it *does* or how it's used? (`user_id`, not `the_id_to_look_up`)
- Is there a comment explaining the *why* of non-obvious code?
- Are magic numbers named as constants?
- Is the function doing more than one thing? (If yes, it's a candidate
  for splitting — but only flag this if it makes review harder, not just
  because a function is long.)

---

## 5. Design and structure

Only flag design issues if they would make the code hard to maintain or
extend. Don't redesign working code during review.

- Does the change introduce a circular dependency or tightly couple two
  previously independent modules?
- Is state mutated in a non-obvious place (global, injected side effect)?
- Is there a simpler way that doesn't sacrifice correctness?

---

## 6. Conventions and style

Check last — style is the least important category. If the project has a
linter/formatter, let the CI catch style issues; don't repeat them in
comments.

- Does the code follow the project's naming conventions (`go-conventions`,
  `python-conventions`, `typescript-conventions` skills)?
- Are imports grouped and ordered correctly?
- Are error messages user-facing or dev-facing? (User-facing messages
  should not expose stack traces or internal identifiers.)

---

## How to write review comments

**Be specific.** "This could be cleaner" is not actionable. "The `user_id`
variable here is actually a UUID string — renaming it to `user_uuid` would
match the type it holds" is.

**Distinguish required from suggested:**
- `Required:` (or `[blocking]`) — must change before merge
- `Suggested:` (or `[nit]`) — worth doing but not a blocker
- `Question:` — you need more context before deciding

**Reference the reason, not just the fix:**
```
Required: This query isn't parameterised — the `email` variable is
interpolated directly into the SQL string, which allows SQL injection
if the caller passes user-controlled input. Use a parameterised query:
    cursor.execute("SELECT ... WHERE email = %s", (email,))
```

---

## Approve vs. request changes

**Approve** when:
- All Required items are addressed.
- You would be comfortable maintaining this code.
- The tests give you confidence the behaviour is correct.

**Request changes** when:
- There is at least one Required finding.
- You can't confidently assess correctness without more context
  (in which case ask, don't block).

**Don't block on style preferences** that aren't in the project's
enforced conventions. Suggest them as `[nit]` and approve if everything
else is clean.
