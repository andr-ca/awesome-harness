---
description: Guidelines for creating clean, meaningful git commits across projects
applyTo: all projects using agentharness
---

# Committing Guidelines

Standards for git commits that maintain clean history, respect project configuration, and communicate intent clearly.

## Core Rules

### For Agents: Workflow Completion

See `CLAUDE.md`'s "Agent Workflow Completion" section for the current
default (verify + stage locally, then stop and ask before publishing)
and what grants full publish authority (commit → push → PR, in that
order). Not restated here — this file just adds the mechanics once
publish authority applies:

- ✅ Commits must be on a feature branch, never directly on trunk
- ✅ PR must have clear title, body, and reference to the task/issue
- ✅ Never claim work is "complete" (in the full-publish sense) without a
  PR link in the response — under the default (no publish authority),
  "complete" means verified and staged, and the response should say so
  explicitly rather than implying a PR exists

**When implementing recommendations:**
- Create a `{recommendations}-status.md` file documenting what was implemented
- Include timestamp, summary of changes, rationale, and PR link
- Commit this status report alongside the implementation
- Push everything in a single coordinated PR or series of PRs

### Security & Verification

- **Always respect signing configuration** – Do not disable, override, or work around GPG signing
  - If user has signing enabled, commits must be signed
  - Never pass `--no-gpg-sign` or equivalent flags
  - Never use `--no-verify` to bypass hooks

- **Always run verification hooks** – Let pre-commit and commit-msg hooks run
  - Hooks validate code quality, security, and conventions
  - If a hook fails, fix the underlying issue instead of bypassing it
  - This ensures standards are maintained across all commits

### Commit Quality

- **Atomic commits** – Each commit should be a logical, self-contained change
  - One feature per commit, or
  - One bug fix per commit, or
  - One refactoring per commit
  - Don't mix features, fixes, and refactoring in one commit

- **Clear commit messages** – A good commit message explains WHY, not WHAT
  - What changed is in the diff
  - Why it changed is in the message
  - Who implemented it is in the author field

### Commit Message Format

**Preferred format:**
```
Short summary (50 chars max)

Detailed explanation of the change (if needed).
Explain the reasoning and intent, not the implementation.

Reference issues if applicable:
Fixes #123
Relates to #456

Co-Authored-By: Name <email> (if applicable)
```

**Guidelines:**

- **Summary line:** Imperative mood ("Add feature" not "Added feature")
- **Keep summary under 50 characters** – Forces clarity
- **Leave blank line** after summary before detailed explanation
- **Wrap explanation at 72 characters** for readability
- **Reference issues** – Use "Fixes", "Relates to", "Closes" etc. with issue numbers
- **Mention co-authors** – If someone contributed significantly, credit them
- **One commit, one purpose** – If you're explaining multiple things, split it into multiple commits

### What NOT to Commit

- **Secrets** – Never commit API keys, tokens, passwords, or private credentials
- **Environment variables** (unless `.env.sample` with sanitized defaults)
- **Temporary files** – Build artifacts, node_modules, .DS_Store, etc.
- **Debug code** – `console.log()`, debugger statements, commented-out code
- **Large binary files** – Use appropriate storage for images, data files
- **Unrelated changes** – Keep commits focused; don't bundle unrelated work

**Check before committing:**
```bash
git diff --cached  # Review what you're about to commit
git status         # Check for stray files
```

## Workflow

### Before Creating a Commit

1. **Review your changes:** `git diff` and `git status`
2. **Stage intentionally:** Add specific files, not `git add .`
3. **Check staged content:** `git diff --cached`
4. **Look for secrets:** Scan diffs for credentials, tokens, keys
5. **Let hooks run:** Don't use `--no-verify`

### If a Hook Fails

**Don't** pass `--no-verify`.

**Do:**
1. Read the hook error message carefully
2. Fix the underlying issue (lint errors, test failures, etc.)
3. Stage the fixes
4. Try committing again

Common hook failures:
- **Linting errors** – Run linter and fix issues
- **Type errors** – Fix compilation/type check issues
- **Test failures** – Fix failing tests
- **Secret detection** – Remove secrets, use environment variables

### If Tests Fail

Fix the tests or the code. Don't commit broken code with a promise to fix it later.

- If tests are wrong, fix them
- If code is wrong, fix it
- If tests are passing but you found a bug, write a test first, then fix

## Special Cases

### Amending Commits

**Only amend unpushed commits** to your personal branch.

```bash
# Fix last commit
git add <files>
git commit --amend

# Push amended commit
git push --force-with-lease  # Safer than --force
```

**Never amend commits that are:**
- Already pushed to main/master
- Part of a pull request
- Shared with others

### Interactive Rebase

Use `git rebase -i` to clean up local history before pushing:
- Squash related commits
- Improve commit messages
- Reorganize commits logically

**Never rebase commits that are:**
- Already merged
- Shared with others
- Part of a PR others might be building on

### Merging

- **Prefer squashing** for feature branches – Cleaner history
- **Use merge commits** for release/integration branches – Clearer record
- **Avoid merge commits** in feature branches – Rebasing is cleaner

## Commit Message Examples

### Good ✅

```
Add user authentication middleware

Implement JWT-based authentication for API endpoints.
Token validation happens in middleware, protecting all
downstream handlers. Tokens are extracted from Authorization
header or cookies.

Fixes #123
```

```
Fix race condition in file watcher

When files change while watcher is processing previous change,
new events were dropped. Now we queue subsequent events and
process them sequentially.

Relates to #456
```

```
Refactor database connection pooling

Extract pool management into separate module for reusability.
Reduces complexity in main connection handler by ~40 lines.
```

### Bad ❌

```
wip
```

```
Update stuff
```

```
Fixed the thing that was broken
```

```
Added feature x, fixed bug y, refactored z, updated deps
```

## Tools & Helpers

### Commit Template

Create `.gitmessage` in your project:
```
Short summary (50 chars max)

Detailed explanation here.

Fixes #
Co-Authored-By: 
```

Configure git to use it:
```bash
git config commit.template .gitmessage
```

### Git Aliases

```bash
# See clean log
git log --oneline -20

# See what you're about to commit
git diff --cached

# Safer force push
git push --force-with-lease
```

## CI/CD Implications

- **Each commit should compile/pass tests** – Even in feature branches
- **Squash before merging** to keep main history clean
- **Revert is easier** if commits are atomic
- **Bisect is more useful** with clear, atomic commits

## Learnings

- Respect pre-commit and commit-msg hooks; they protect code quality
- Atomic commits make bisecting, reverting, and code review easier
- Good commit messages are a form of documentation
- Committing is a communication tool—write for your future self and your team

---

**Remember:** A commit is permanent history. Write it as if you'll be reading it months from now trying to understand why a decision was made.
