---
name: planning-with-files
description: Use when starting a complex multi-step task, a research project, or any task requiring more than 5 tool calls — creates and maintains task_plan.md, findings.md, and progress.md to preserve state across context resets.
metadata:
  type: skills
  complexity: low
  scope: [all]
---

# Planning with Files

Use this pattern for any task where you can't complete everything in one
pass: long refactors, migrations, multi-feature buildouts, research tasks,
or anything with more than ~5 tool calls. File-based state survives context
resets and gives you (and the user) a running record of what's been done.

Place planning files in `docs/operational/` if the harness is linked, or
in a `.planning/` directory at the project root — whichever exists.

---

## Files to create at the start

### `task_plan.md`

Written **before** any implementation. Contains:

```markdown
# Task: <short title>

## Goal
One sentence: what does "done" look like?

## Scope
What's in and what's explicitly out.

## Steps
1. Step one (estimate: small/medium/large)
2. Step two
3. ...

## Open questions
- Question 1 (unblocks: step 3)

## Success criteria
- [ ] Criterion A
- [ ] Criterion B
```

### `findings.md`

Appended to **as you work**. Never edited retroactively.

```markdown
# Findings

## <ISO timestamp>
**Context:** What you were investigating.
**Finding:** What you learned.
**Impact:** Does it change the plan? If yes, add a note to task_plan.md.
```

### `progress.md`

Updated **after each step completes**:

```markdown
# Progress

## Completed
- [x] Step 1 — <one-line summary> (commit: <sha>)

## In progress
- [ ] Step 2 — started <timestamp>

## Blocked
- Step 3 — waiting on: <reason>

## Next action
<Exact next thing to do when resuming>
```

---

## Workflow

```
1. Read existing task_plan.md (if present) — don't start a second plan
   for the same task.

2. Write task_plan.md → get user approval on scope before doing anything.

3. For each step:
   a. Write findings to findings.md before and after each discovery.
   b. Do the work (code, commands, searches).
   c. Mark step complete in progress.md; record the commit SHA.
   d. If blocked, record the blocker in progress.md and surface it.

4. When context resets: read progress.md first. Resume from "Next action".

5. When all steps are complete:
   - Verify all success criteria in task_plan.md.
   - Archive or delete the planning files (they're operational docs, not
     permanent — see docs/operational/README.md for the lifecycle).
```

---

## Rules

- **One plan per task.** If a `task_plan.md` already exists, read it and
  continue — don't overwrite a plan in progress.
- **Write findings before you forget them.** Append to `findings.md`
  immediately after each discovery; don't reconstruct from memory later.
- **Keep progress.md truthful.** Only mark a step complete when its
  commit is on the branch. "In progress" is not the same as "done."
- **Surface blockers immediately.** A step that's blocked doesn't become
  "in progress" — it goes to the Blocked section with the reason.
- **Never truncate.** Append to `findings.md`; don't trim old entries to
  save space — they're the audit trail.

---

## When NOT to use this pattern

- Single-function edits or quick fixes (< 5 tool calls).
- Well-scoped tasks the agent can complete in one continuous context window.
- Tasks where the user is present and can provide all context interactively.
