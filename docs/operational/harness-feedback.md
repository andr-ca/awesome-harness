---
date: 2026-07-17
topic: operational
purpose: Dated log of harness friction found while using agentharness itself, per the harness-feedback skill
---

# Harness Feedback Log

Friction found while *using* this harness, recorded per
`.claude/skills/harness-feedback/SKILL.md`: what happened → root cause →
impact → what agentharness should change → corrective action taken. In
consuming projects this file lives at the same path; entries here are the
self-hosted (dogfood) case.

## 2026-07-17 – content-quality scan descends into `.claude/worktrees/`, false-failing the completion gate

**What happened:** Running `tools/check-completion.sh` before a commit on
PR #82, the content-quality gate failed with 12 mandate-restatement errors,
all inside `.claude/worktrees/agent-*/docs/operational/reviews/` — stale
checkouts left by finished subagent sessions, not current repo content.
The change under test was clean and CI was green throughout.

**Root cause:** Same failure class as launch-readiness item E9: that fix
pruned `.worktrees/` from the markdown scan in
`tools/verify-content-quality.py`, but Claude Code's agent worktrees live
under `.claude/worktrees/`, which the prune didn't cover.

**Impact:** The Stop-hook completion gate blocks on false failures whenever
a finished subagent worktree lingers; a commit was pushed with the gate red
(CI authoritative for this class), which is a bad pattern to normalize.

**What agentharness should change:** Exclude any `worktrees` path component
and `node_modules` from the markdown scan (the launch-plan addendum already
flagged nested `.kilo/node_modules`/`.opencode/node_modules`).

**Corrective action taken:** Removed the three stale agent worktrees
(`git worktree remove`), turning the gate green immediately; extended the
scanner exclusion in the same PR as this entry. Logged upstream as
[#83](https://github.com/andr-ca/agentharness/issues/83).

## 2026-07-18 – `safe-pr-merge.sh`'s post-merge CI wait can report a false green

**What happened:** Merging PR #93 with
`tools/safe-pr-merge.sh 93 --delete-branch`, the script's final step
reported "Post-merge CI is green" and "Safe merge complete" — but the run it polled
(`29645328747`) was a stale, already-`success` run left over from the
PR #91 merge ~50 minutes earlier, not the run PR #93's merge commit
(`8abf99a`) actually triggered (`29646923757`, still `queued` at that
moment).

**Root cause:** `wait_for_ci_run()` fetches "most recent run for
branch `main`" immediately after merging via `gh run list --limit 1`.
GitHub's run-list index can lag a few seconds behind the merge, so the
query can return the *previous* run instead of the new one. The
function never verifies the polled run's `headSha` matches the merge
commit, so a stale-but-green run silently satisfies the check.

**Impact:** The script exists specifically to enforce this repo's own
"never report a push/merge as done while CI is still running or red"
mandate, and in the race window it violates that mandate itself. No
bad state landed on `main` this time (the real run also passed), but
the script would have reported "complete" identically had the real run
failed.

**What agentharness should change:** `wait_for_ci_run` should take the
merge commit's SHA and verify the fetched run's `headSha` matches
before trusting it, retrying the lookup with backoff until a run for
that exact SHA appears.

**Corrective action taken:** Manually verified the real post-merge run
(`gh run watch 29646923757 --exit-status`) before reporting PR #93 as
done, so no false-green reached the user this session. Logged upstream
as [#94](https://github.com/andr-ca/agentharness/issues/94).

## 2026-07-18 – `safe-pr-merge.sh` reproduced the just-fixed false-green bug by running a stale copy of itself

**What happened:** Immediately after #94/#96 (above) merged, merging
PR #95 from a local checkout still on branch
`docs/harness-feedback-ci-race-94` — forked from `main` *before* #96
landed — ran that branch's pre-fix copy of `tools/safe-pr-merge.sh`. It
reported "Post-merge CI is green" for run `29650734547`, whose
`headSha` (`98b7e124`) did not match PR #95's actual merge commit
(`db75a6e2`); the real run (`29651378346`) was still `in_progress` at
that moment.

**Root cause:** the script's correctness depends entirely on which
version happens to be checked out in the caller's shell — it has no
self-check against `origin/main`, so a long-lived branch that forked
before a fix lands silently regresses the exact bug that fix closed.

**Impact:** a normal, correct workflow (working on a branch that forked
before a fix merged, then running the merge helper from that same
shell without an explicit `git checkout main` first) reintroduces a
just-fixed correctness bug with no warning from the tool itself.

**What agentharness should change:** `safe-pr-merge.sh` should warn (or
refuse) when invoked from a non-`main` branch, and/or compare its own
content against `origin/main`'s copy before trusting its own output.

**Corrective action taken:** Manually diffed the reported run's
`headSha` against `gh pr view --json mergeCommit` before trusting the
script's "complete" output, then watched the real run to a genuine
green. Logged upstream as
[#99](https://github.com/andr-ca/agentharness/issues/99).
