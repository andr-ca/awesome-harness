#!/bin/bash
# Verify harness integration against this fixture's pre-existing AGENTS.md
# and .cursor/rules/testing.mdc — see ../README.md for what distinguishes
# this fixture from the others (existing-surface managed-block/collision
# handling, not skill-linking or .gitignore merging in isolation).

echo "Verifying harness integration (existing-surface-project)..."
echo ""

STATUS=0

[ -d ".claude/skills" ] && echo "✅ .claude/skills exists" || { echo "❌ .claude/skills missing"; STATUS=1; }
[ -e ".claude/skills/committing" ] && echo "✅ committing skill linked" || { echo "❌ committing skill not linked"; STATUS=1; }

# The pre-existing AGENTS.md content must survive the merge untouched,
# with a managed block appended.
if grep -qF "Custom project note: do not delete this line in tests." AGENTS.md; then
    echo "✅ pre-existing AGENTS.md content preserved"
else
    echo "❌ pre-existing AGENTS.md content lost"
    STATUS=1
fi
if grep -q "agentharness:begin id=core-instructions" AGENTS.md; then
    echo "✅ managed block rendered into AGENTS.md"
else
    echo "❌ managed block missing from AGENTS.md"
    STATUS=1
fi

# The pre-existing .cursor/rules/testing.mdc is NOT one of the four
# block-managed instructions files, and nothing in this harness's
# init/update currently generates or collides with it — it must be left
# completely untouched (see the comment inside the file itself).
if [ -f ".cursor/rules/testing.mdc" ] && \
   grep -qF "This is the consumer's own pre-existing Cursor rule file" ".cursor/rules/testing.mdc"; then
    echo "✅ pre-existing .cursor/rules/testing.mdc left untouched"
else
    echo "❌ .cursor/rules/testing.mdc was modified or removed"
    STATUS=1
fi

# The pre-existing .gitignore entries must survive the merge untouched.
for entry in "local-notes.txt" "*.mytool-cache/"; do
    if grep -qF "$entry" .gitignore; then
        echo "✅ pre-existing .gitignore entry preserved: $entry"
    else
        echo "❌ pre-existing .gitignore entry lost: $entry"
        STATUS=1
    fi
done
# And the harness template's own entries must have been merged in.
if grep -qF ".env" .gitignore; then
    echo "✅ harness .gitignore template merged in"
else
    echo "❌ harness .gitignore template entries missing"
    STATUS=1
fi

echo ""
if [ "$STATUS" -eq 0 ]; then
    echo "✅ All checks passed! Integration verified."
    exit 0
else
    echo "❌ Some checks failed"
    exit 1
fi
