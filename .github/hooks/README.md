# Git Hooks

Reusable git hooks for enforcing project standards and preventing common mistakes.

## Available Hooks

### prevent-trunk-commit
**Purpose:** Prevent accidental commits directly to trunk/main branches

**What it does:**
- Checks if you're trying to commit to main, master, trunk, develop, production, or release branches
- If yes, blocks the commit and provides helpful instructions
- Shows how to stash changes, create a feature branch, and proceed correctly

**Installation:**

```bash
# Option 1: Copy to .git/hooks (for this project only)
cp .github/hooks/prevent-trunk-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Option 2: Using Husky (recommended for teams)
npx husky install
npx husky add .husky/pre-commit '.github/hooks/prevent-trunk-commit'

# Option 3: git config core.hooksPath (what tools/setup/harness-link.sh
# --with-hook does, and what this repo uses on itself)
git config core.hooksPath /path/to/agentharness/.github/hooks
```

**Why there's also a `pre-commit` file in this directory:** `core.hooksPath`
only ever invokes a file named exactly `pre-commit` inside the configured
directory — it does not run every file there. `.github/hooks/pre-commit`
is a thin dispatcher that execs `prevent-trunk-commit`; without it, Option 3
silently installs nothing and commits to trunk succeed uninterrupted. Options
1 and 2 already target the correct filename themselves, so they don't need
the dispatcher.

**Testing:**

```bash
# Try to commit on main (should fail)
git checkout main
echo "test" > test.txt
git add test.txt
git commit -m "test"  # ✗ Will be blocked

# Correct way: create feature branch
git checkout -b feature/test
git add test.txt
git commit -m "test"  # ✓ Will succeed
```

### pre-push
**Purpose:** Run the test suite and enforce >=80% coverage before every push

**What it does:**
- Runs all bats suites (`.github/hooks/tests/`, `tools/tests/harness-link.bats`)
- Runs Python unit tests with `pytest-cov`, failing if total coverage for
  the module under test drops below 80% — this repo's own
  `patterns/testing/COVERAGE_REQUIREMENTS.md` bar, enforced on itself
- Blocks the push (nonzero exit) if any suite fails, coverage is below
  80%, or the required tooling (`bats`, `pytest`) isn't installed —
  missing tools fail the push rather than silently skipping, since the
  point is enforcement, not a best-effort reminder
- New Python test suites should be added to the `PYTHON_SUITES` array
  near the top of the script as they're created

**Installation:** Git only ever needs a file named exactly `pre-push` in
the configured hooks directory — no dispatcher required (unlike
`pre-commit`/`prevent-trunk-commit`, see above). All three installation
options above wire this up automatically, since `core.hooksPath` and
`.git/hooks/` both apply per-filename, not per-directory-contents:

```bash
# Any of these also installs pre-push:
cp .github/hooks/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
npx husky add .husky/pre-push '.github/hooks/pre-push'
git config core.hooksPath /path/to/agentharness/.github/hooks   # already covers it
```

**Testing:**

```bash
# Should pass cleanly against this repo's current state
bash .github/hooks/pre-push
```

## Setting Up Hooks in Your Project

### Manual Setup

```bash
# 1. Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# 2. Copy hooks from agentharness
cp ~/agentharness/.github/hooks/* .git/hooks/

# 3. Make them executable
chmod +x .git/hooks/*

# 4. Test
git commit --allow-empty -m "test"  # Should succeed on feature branch
```

### Using Husky (Recommended for Teams)

Husky makes hooks easy to manage and commit to git.

```bash
# 1. Install Husky
npm install --save-dev husky
npx husky install

# 2. Add prevent-trunk-commit hook
npx husky add .husky/pre-commit '.github/hooks/prevent-trunk-commit'

# 3. Commit the hook configuration
git add .husky/
git commit -m "Add git hooks via Husky"

# 4. Team members will automatically have hooks installed
#    (via prepare script in package.json)
```

### Skipping Hooks (Don't Do This!)

If a hook legitimately blocks something, fix the underlying issue instead of skipping:

```bash
# WRONG: Bypass the hook
git commit --no-verify  # Don't do this!

# RIGHT: Fix the issue
git checkout -b feature/correct-branch
git add .
git commit -m "Your message"
```

The only valid reason to skip a hook is during recovery after a genuine mistake, and even then you should fix it properly afterward.

## Creating Custom Hooks

To add your own hooks:

1. **Create the script** in `.github/hooks/`
2. **Make it executable** – `chmod +x`
3. **Document it** in this README
4. **Test thoroughly** before committing
5. **Add to your `.git/hooks/`** or Husky configuration

### Hook Template

```bash
#!/bin/bash
# ============================================================================
# Pre-commit Hook: [Your Hook Name]
# ============================================================================
#
# Purpose: [What does this hook do?]
# When it runs: Before each commit
#
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Your hook logic here

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Hook failed: [error message]${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Hook passed${NC}"
exit 0
```

## Common Pre-Commit Hooks

### Check for Debug Code

```bash
#!/bin/bash
# Prevent commits with debug statements

if git diff --cached | grep -E "console\.log|debugger|pdb\.set_trace|print\("; then
    echo "✗ Debug code found. Remove before committing."
    exit 1
fi

exit 0
```

### Check for Large Files

```bash
#!/bin/bash
# Prevent commits of large files

MAX_FILE_SIZE=10485760  # 10MB in bytes

for file in $(git diff --cached --name-only); do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt "$MAX_FILE_SIZE" ]; then
            echo "✗ File $file is too large ($(numfmt --to=iec $size 2>/dev/null || echo $size bytes))"
            exit 1
        fi
    fi
done

exit 0
```

### Run Linter

```bash
#!/bin/bash
# Run linter before commit

npm run lint || exit 1
exit 0
```

### Run Tests

```bash
#!/bin/bash
# Run tests before commit

pytest . || exit 1
exit 0
```

## Troubleshooting

### Hook isn't running

```bash
# 1. Check if hook file exists and is executable
ls -la .git/hooks/pre-commit

# 2. Make sure it's executable
chmod +x .git/hooks/pre-commit

# 3. Check shebang line (should be #!/bin/bash)
head -1 .git/hooks/pre-commit

# 4. Test manually
bash .git/hooks/pre-commit
```

### Hook is too strict

If a hook is blocking legitimate work:
1. Don't bypass it with `--no-verify`
2. Fix the underlying issue
3. Or update the hook if the rule should change
4. Discuss with the team before changing shared hooks

### Unexpected failures

Debug hooks by adding verbose output:

```bash
#!/bin/bash
set -x  # Enable debug mode

# ... your hook code ...

set +x  # Disable debug mode
```

Then run the hook manually to see what's happening.

## Best Practices

- **Keep hooks fast** – Slow hooks discourage usage
- **Clear error messages** – Tell developers exactly what's wrong and how to fix it
- **Test hooks locally** – Before sharing with team
- **Document all hooks** – Include in README with examples
- **Don't make hooks too strict** – Balance safety with usability
- **Get team consensus** – Before enforcing new hooks
- **Use Husky for teams** – Makes hooks easier to maintain

## References

- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Husky Documentation](https://typicode.github.io/husky/)
- [Awesome Hooks Collection](https://github.com/aitemr/awesome-git-hooks)

---

**See Also:** BRANCHING_STRATEGY.md, COMMITTING_GUIDELINES.md
