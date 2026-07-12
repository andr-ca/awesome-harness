#!/bin/bash
# Verify harness integration

echo "Verifying harness integration..."
echo ""

STATUS=0

[ -d ".claude/skills" ] && echo "✅ .claude/skills exists" || { echo "❌ .claude/skills missing"; STATUS=1; }
[ -d ".github/hooks" ] && echo "✅ .github/hooks exists" || { echo "❌ .github/hooks missing"; STATUS=1; }
[ -f ".claude/skills/committing/SKILL.md" ] && echo "✅ Committing skill available" || { echo "❌ Committing skill missing"; STATUS=1; }
[ -f ".github/hooks/prevent-trunk-commit" ] && echo "✅ prevent-trunk-commit hook available" || { echo "❌ prevent-trunk-commit hook missing"; STATUS=1; }
[ -f ".github/CLAUDE.md" ] && echo "✅ Project CLAUDE.md configured" || { echo "❌ Project CLAUDE.md missing"; STATUS=1; }

echo ""
if [ "$STATUS" -eq 0 ]; then
    echo "✅ All checks passed! Integration verified."
    exit 0
else
    echo "❌ Some checks failed"
    exit 1
fi
