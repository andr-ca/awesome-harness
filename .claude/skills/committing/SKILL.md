---
name: committing
description: Use when creating a git commit — atomic commits, message format, what never to commit, and the agent workflow-completion requirement (run completion gate; stage or publish per publish authority).
metadata:
  type: skills
  complexity: low
---

# Committing

Full reference: `.github/COMMITTING_GUIDELINES.md` (examples, git aliases,
commit template). This skill is the actionable summary.

## Before you commit

1. `git status` and `git diff` — know exactly what you're about to commit.
2. Stage specific files, not `git add .` / `git add -A` blind.
3. `git diff --cached` — review staged content one more time, scan for
   secrets (API keys, tokens, passwords).
4. Let hooks run. Never `--no-verify`, never `--no-gpg-sign`. If a hook
   fails, fix the underlying issue and re-stage — don't bypass it.

## Writing the commit

- **Atomic**: one logical change per commit. Don't mix a feature, a fix,
  and a refactor in one commit.
- **Message explains WHY, not WHAT** — the diff already shows what
  changed.
- Imperative mood summary ("Add X", not "Added X"), ideally under ~50
  chars, blank line, then body wrapped at ~72 chars if more explanation
  is needed.
- Reference issues (`Fixes #123`, `Relates to #456`) when applicable.

## What never gets committed

- Secrets: API keys, tokens, passwords, private credentials.
- `.env` and its variants — but DO commit `.env.sample` (sanitized
  template).
- Debug code: stray `console.log`/`print`, commented-out code, debugger
  statements.
- Build artifacts, `node_modules/`, and anything covered by
  `.github/.gitignore.template`.

## After the commit — run the completion gate, then follow publish authority

1. **Run `bash tools/check-completion.sh`** — all quality gates must pass
   before declaring work done. This is enforced by the Stop hook in
   `.github/hooks/completion-gate.json` (Copilot) and `.claude/settings.json`
   (Claude Code).

   **This path is specific to the agentharness repo itself.** If this
   skill file is symlinked/copied into a *consumer* project instead
   (the normal case — see `harness-link.sh`), `tools/check-completion.sh`
   does not exist there and will exit 127. Check for it
   first (`[ -f tools/check-completion.sh ]` or equivalent); if it's
   missing, the consumer-side equivalent is `harness-link.sh
   enforce-profile <this-project>` (from wherever this install's
   harness checkout lives — `.agentharness/` for submodule mode,
   `.agentharness-pkg/` for npm mode, or the harness's own directory
   for link mode), plus this project's own lint/type/test commands if
   it has any not covered by `enforce-profile`. Don't silently skip
   verification just because the harness's own path doesn't resolve —
   find the equivalent for *this* repo.

2. **Default (no publish authority): stop at the commit.**
   Stage the commit locally, summarize what was done, and ask the user to
   confirm before pushing or opening a PR. Work is "done" when the user
   has reviewed and approved the staged changes.

3. **With publish authority**: push and open a PR.
   Publish authority is granted when `.agentharness-publish-mode`
   **exists** at the repo root — check with `[ -f
   .agentharness-publish-mode ]` (or `test -e`), never by reading its
   contents. The file is typically empty by design; an agent that
   `cat`s it, sees nothing, and concludes "not active" has the check
   backwards — presence alone grants authority, content is
   irrelevant. `harness-link.sh audit --json`'s `publish_mode_active`
   field already implements this correctly if you'd rather not shell
   out to `test` directly.
   Publish authority is also granted when the user explicitly
   authorizes it in the current session.
   - `git push -u origin <branch>` (first push) or `git push` (subsequent).
     **If this fails with an SSH key error** (`Permission denied
     (publickey)`) even though `gh auth status` shows a valid session:
     the remote is an SSH URL (`git@github.com:...`) but no SSH key is
     configured in this environment — a real, seen-in-practice mismatch,
     not a sign the push itself is wrong. Don't
     permanently reconfigure the remote to work around a one-off
     environment gap. Instead, push to an explicit HTTPS URL for this
     one invocation, using `gh`'s own credentials:
     `git push "https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner).git" <branch>`.
     If pushing will be a recurring need in this environment, `gh auth
     setup-git` is the durable fix (configures git's credential helper
     to use `gh`'s token for HTTPS) — but that's a persistent
     environment change, so confirm with the user before running it,
     the same as any other durable configuration change.
   - `gh pr create` with a real title, body, and test/verification notes.
   - Work is not "done" until the PR exists, CI is green, and review
     comments have been addressed.

See `CLAUDE.md`'s "Agent Workflow Completion" section for the full rules
and the `📋 Completion Gate` section for the gate commands.

## If tests or hooks fail

Fix the underlying issue (lint error, failing test, secret detected).
Don't commit broken code planning to fix it "in the next commit."
