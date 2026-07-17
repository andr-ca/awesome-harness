---
name: harness-feedback
description: "Triggers on harness friction events (hook failures, ambiguous guidance, violated mandates, mismatched reality) encountered during any session. Agent must: address the immediate problem, log it locally to docs/operational/harness-feedback.md, and file it upstream to andr-ca/agentharness. Default-on; skip upstream filing only if .agentharness-no-upstream-feedback exists at repo root."
metadata:
  type: skills
  when: "Hook/gate not firing as expected, router guidance ambiguous or contradictory, mandate hard to apply in practice, tool output not matching reality"
---

# Harness Feedback Loop

When friction is discovered during harness usage — a hook that didn't fire, guidance that was contradictory, a mandate violated in practice, or tool output diverging from documentation — capture and escalate it by default. The goal is to ensure harness improvements flow upstream without requiring users to notice and report them manually.

## Procedure

### 1. Address the immediate problem

Work around or fix the specific friction blocking your session — do not defer this
step or leave it for later. Examples:
- A hook expected to run but didn't? Inspect `core.hooksPath`, check hook file
  permissions, run it manually if necessary.
- Guidance was unclear? Disambiguate it by reading related docs or asking for clarification.
- A mandate was hard to apply? Document what made it hard and propose a better framing.

### 2. Log it locally

Append a dated entry to `docs/operational/harness-feedback.md` (create it with a
short header if it doesn't exist). Use this template:

```markdown
## [ISO 8601 date] – [one-line summary]

**What happened:** [The friction event and when you noticed it]

**Root cause:** [Why did this happen? What in the harness design or docs caused it?]

**Impact:** [How did it affect your session or workflow?]

**What agentharness should change:** [Concrete recommendation — a new check, clearer guidance, a new tool, a code fix, etc.]

**Corrective action taken:** [What you did to work around or fix it] Logged upstream as #[issue-number].
```

### 3. File upstream

Unless `.agentharness-no-upstream-feedback` exists at this repo's root (a flag at
the consuming repository, not the harness itself), file the same finding as a GitHub
issue on andr-ca/agentharness. Use `gh issue create -R andr-ca/agentharness` with:

**Title:** Short, actionable summary (e.g., "Hook X doesn't fire on merge commits",
"Mandate Y is ambiguous without threshold")

**Body:** Include these three structural elements in order:

1. **Origin repo**: Consuming project name and repo URL where friction was discovered
2. **Full context**: Not just the symptom, but the chain of events, what you tried, what failed.
   Match the detail bar set by exemplar issues #76 (hook gap + impact), #77 (mandate
   ambiguity + recurring failure), #78 (staleness detection gap).
3. **Concrete recommendation**: What specifically agentharness should change — a new
   script, a clarity edit, a schema addition, etc.

Record the issue number in the local entry's **Corrective action taken** field and
link back to it. The GitHub issue should reference the origin repo and this entry so
both directions are auditable.

## Rules

- **No ask-the-user step for logging or filing.** The absence of
  `.agentharness-no-upstream-feedback` is standing authorization — do not prompt
  the operator when the flag is absent.
- **Do this as part of handling the friction, not afterward.** If you fix a hook
  failure, log it and file it *before* moving on to the next task. Memory is not a
  backup plan.
- **Both directions always.** Local entry → issue link; GitHub issue → origin
  repo reference and local entry. Bidirectional traceability.
- **Keep dates in ISO 8601 format** (e.g., `2026-07-17`) for sorting and CI
  matching.

## Output shape

Issue filed? Update the calling session's context with: the issue number/URL, and
the local file path where you recorded it. Both are now part of the session's
findings — they don't need to be hidden from the operator.
