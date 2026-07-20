#!/bin/bash
# Verify harness integration
#
# Checks the actual output of tools/setup/harness-link.sh: individual skill
# files (symlinked or copied, depending on install mode) under
# .claude/skills/, and (when --with-hook was used) that core.hooksPath
# points at the harness's hooks directory. It never creates a
# .github/hooks symlink, so this does not check for one.
#
# Mode-agnostic on purpose: checks skill content is present and readable,
# not that it's specifically a symlink — this runs against whatever
# harness-link.sh's default install mode currently is (see
# docs/DECISIONS.md "Copy as the default install mode"), and asserting
# -L here would fail under --mode copy for no real reason.

echo "Verifying harness integration..."
echo ""

STATUS=0

[ -d ".claude/skills" ] && echo "✅ .claude/skills exists" || { echo "❌ .claude/skills missing"; STATUS=1; }
[ -f ".claude/skills/committing/SKILL.md" ] && echo "✅ Committing skill present" || { echo "❌ Committing skill not present"; STATUS=1; }

if [ -d ".git" ]; then
    HOOKS_PATH=$(git config core.hooksPath || true)
    if [[ "$HOOKS_PATH" == *".github/hooks" ]]; then
        echo "✅ core.hooksPath points at the harness's prevent-trunk-commit hook"
    else
        echo "❌ core.hooksPath not set to the harness hooks dir (got: '${HOOKS_PATH:-<unset>}')"
        STATUS=1
    fi
else
    echo "⚠️  Not a git repo — skipping core.hooksPath check"
fi

[ -f ".github/CLAUDE.md" ] && echo "✅ Project CLAUDE.md configured" || { echo "❌ Project CLAUDE.md missing"; STATUS=1; }

echo ""
if [ "$STATUS" -eq 0 ]; then
    echo "✅ All checks passed! Integration verified."
    exit 0
else
    echo "❌ Some checks failed"
    exit 1
fi
