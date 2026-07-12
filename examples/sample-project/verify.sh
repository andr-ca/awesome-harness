#!/bin/bash
# Verify harness integration
#
# Checks the actual output of tools/setup/harness-link.sh: individual skill
# symlinks under .claude/skills/, and (when --with-hook was used) that
# core.hooksPath points at the harness's hooks directory. It never creates a
# .github/hooks symlink, so this does not check for one.

echo "Verifying harness integration..."
echo ""

STATUS=0

[ -d ".claude/skills" ] && echo "✅ .claude/skills exists" || { echo "❌ .claude/skills missing"; STATUS=1; }
[ -L ".claude/skills/committing" ] && echo "✅ Committing skill linked" || { echo "❌ Committing skill not linked"; STATUS=1; }

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
