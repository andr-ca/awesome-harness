#!/bin/bash
# Verify harness integration against this Go fixture's pre-existing,
# realistic .gitignore and project layout.

echo "Verifying harness integration (go-project)..."
echo ""

STATUS=0

[ -d ".claude/skills" ] && echo "✅ .claude/skills exists" || { echo "❌ .claude/skills missing"; STATUS=1; }
[ -e ".claude/skills/committing" ] && echo "✅ committing skill linked" || { echo "❌ committing skill not linked"; STATUS=1; }

for entry in "/bin/" "*.exe" "*.test" "vendor/"; do
    if grep -qF "$entry" .gitignore; then
        echo "✅ pre-existing .gitignore entry preserved: $entry"
    else
        echo "❌ pre-existing .gitignore entry lost: $entry"
        STATUS=1
    fi
done
if grep -qF ".env" .gitignore; then
    echo "✅ harness .gitignore template merged in"
else
    echo "❌ harness .gitignore template entries missing"
    STATUS=1
fi

if [ -d ".git" ]; then
    HOOKS_PATH=$(git config core.hooksPath || true)
    if [ -n "$HOOKS_PATH" ]; then
        echo "✅ core.hooksPath configured ($HOOKS_PATH)"
    else
        echo "❌ core.hooksPath not set"
        STATUS=1
    fi
fi

[ -f ".github/CLAUDE.md" ] && echo "✅ Project CLAUDE.md configured" || { echo "❌ Project CLAUDE.md missing"; STATUS=1; }
[ -f "go.mod" ] && echo "✅ Fixture's own content untouched" || { echo "❌ Fixture's own content missing"; STATUS=1; }

echo ""
if [ "$STATUS" -eq 0 ]; then
    echo "✅ All checks passed! Integration verified."
    exit 0
else
    echo "❌ Some checks failed"
    exit 1
fi
