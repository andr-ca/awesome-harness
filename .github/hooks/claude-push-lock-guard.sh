#!/usr/bin/env bash
# PreToolUse guard for Claude Code (wired in .claude/settings.json):
# before a Bash tool call runs `git push`, verify no OTHER live agent
# session holds the multi-agent lock for the current branch. This fires
# whether or not the agent ever loaded the multi-agent-coordination
# skill — the adoption gap that let two sessions collide on one branch
# on 2026-07-16 (see docs/operational/planning/
# public-launch-review-disagreements-2026-07-16.md).
#
# Exit 0  -> allow the tool call.
# Exit 2  -> block it; stderr is shown to the agent as feedback.
#
# The same check runs again in .github/hooks/pre-push (defense in depth:
# that layer also covers pushes from non-Claude sessions).
set -euo pipefail

payload="$(cat 2>/dev/null || true)"
cmd="$(printf '%s' "$payload" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

case "$cmd" in
    *"git push"*) ;;
    *) exit 0 ;;
esac

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] && [ -x "$repo_root/tools/agent-lock.sh" ] || exit 0

branch="$(git branch --show-current 2>/dev/null || true)"
[ -n "$branch" ] || exit 0

if ! "$repo_root/tools/agent-lock.sh" check-branch "$branch" >/dev/null 2>&1; then
    "$repo_root/tools/agent-lock.sh" check-branch "$branch" >&2 || true
    echo "Blocked: branch '$branch' is locked by another live agent session." >&2
    echo "Wait or coordinate (multi-agent-coordination skill); the pre-push hook enforces the same rule." >&2
    exit 2
fi
exit 0
