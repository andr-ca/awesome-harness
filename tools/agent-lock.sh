#!/usr/bin/env bash
# agent-lock.sh — per-feature lock file management for concurrent agent sessions.
#
# Usage:
#   tools/agent-lock.sh acquire <feature> <branch> [worktree]
#   tools/agent-lock.sh release <feature> <agent_id>
#   tools/agent-lock.sh check   <feature>
#   tools/agent-lock.sh list
#   tools/agent-lock.sh clean
#   tools/agent-lock.sh suggest-branch <feature>
#
# See patterns/multi-agent-coordination/COORDINATION.md for the full protocol.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${AGENTHARNESS_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
LOCKS_DIR="$REPO_ROOT/.agentharness-locks"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_slug() {
    local feature="$1"
    local trimmed
    trimmed="$(echo "$feature" | tr '[:upper:]' '[:lower:]' | tr ' /' '-' | cut -c1-40)"
    local hash
    hash="$(printf '%s' "$feature" | sha256sum | cut -c1-8)"
    echo "${trimmed}-${hash}"
}

_lock_path() {
    echo "$LOCKS_DIR/$(_slug "$1").json"
}

_is_stale() {
    local pid="$1"
    if kill -0 "$pid" 2>/dev/null; then
        return 1  # still alive
    fi
    return 0  # stale
}

_make_agent_id() {
    # Use /proc/sys/kernel/random/uuid when available, else Python fallback
    if [[ -r /proc/sys/kernel/random/uuid ]]; then
        cat /proc/sys/kernel/random/uuid
    else
        python3 -c "import uuid; print(uuid.uuid4())"
    fi
}

_atomic_write() {
    local target="$1"
    local content="$2"
    local tmp
    tmp="$(mktemp "$LOCKS_DIR/.tmp-XXXXXX.json")"
    trap 'rm -f "$tmp"' EXIT
    printf '%s\n' "$content" > "$tmp"
    mv "$tmp" "$target"
    trap - EXIT
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_acquire() {
    local feature="$1"
    local branch="$2"
    local worktree="${3:-null}"

    mkdir -p "$LOCKS_DIR"
    local path
    path="$(_lock_path "$feature")"

    if [[ -f "$path" ]]; then
        local pid
        pid="$(python3 -c "import json,sys; d=json.load(open('$path')); print(d['pid'])" 2>/dev/null || echo "0")"
        if [[ "$pid" -gt 0 ]] && ! _is_stale "$pid"; then
            echo "LOCKED: '$feature' is already being worked on." >&2
            python3 -c "
import json, sys
d = json.load(open('$path'))
print(f\"  agent_id : {d['agent_id']}\")
print(f\"  branch   : {d['branch']}\")
print(f\"  worktree : {d.get('worktree', 'none')}\")
print(f\"  since    : {d['started_at']}\")
print()
print('Options:')
print('  1. Wait for the agent to finish and release the lock.')
print(f\"  2. Create your own branch: git worktree add -b feat/{d['branch']}-2 .worktrees/alt main\")
" >&2
            return 1
        fi
        # Stale lock — remove it
        rm -f "$path"
    fi

    local agent_id
    agent_id="$(_make_agent_id)"
    local started_at
    started_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    local pid="${AGENT_LOCK_PID:-$PPID}"

    local worktree_json
    local worktree_val
    if [[ "$worktree" == "null" ]]; then
        worktree_val="None"
    else
        worktree_val="'$worktree'"
    fi

    local content
    content="$(python3 -c "
import json
print(json.dumps({
    'agent_id':   '$agent_id',
    'feature':    '$feature',
    'branch':     '$branch',
    'worktree':   $worktree_val,
    'started_at': '$started_at',
    'pid':        $pid,
}, indent=2, sort_keys=True))
")"

    _atomic_write "$path" "$content"
    echo "ACQUIRED: locked '$feature' (agent_id=$agent_id)"
    echo "$agent_id"
}

cmd_release() {
    local feature="$1"
    local agent_id="$2"

    local path
    path="$(_lock_path "$feature")"
    if [[ ! -f "$path" ]]; then
        echo "NOT FOUND: no lock for '$feature'" >&2
        return 1
    fi

    local lock_agent_id
    lock_agent_id="$(python3 -c "import json; d=json.load(open('$path')); print(d['agent_id'])" 2>/dev/null || echo "")"
    if [[ "$lock_agent_id" != "$agent_id" ]]; then
        echo "FORBIDDEN: lock belongs to agent '$lock_agent_id', not '$agent_id'" >&2
        return 1
    fi

    rm -f "$path"
    echo "RELEASED: lock for '$feature' removed"
}

cmd_check() {
    local feature="$1"
    local path
    path="$(_lock_path "$feature")"

    if [[ ! -f "$path" ]]; then
        echo "FREE: no lock for '$feature'"
        return 0
    fi

    local pid
    pid="$(python3 -c "import json; d=json.load(open('$path')); print(d['pid'])" 2>/dev/null || echo "0")"
    if [[ "$pid" -gt 0 ]] && _is_stale "$pid"; then
        rm -f "$path"
        echo "FREE: stale lock removed for '$feature'"
        return 0
    fi

    echo "LOCKED: '$feature'"
    python3 -c "
import json
d = json.load(open('$path'))
print(f\"  agent_id : {d['agent_id']}\")
print(f\"  branch   : {d['branch']}\")
print(f\"  worktree : {d.get('worktree', 'none')}\")
print(f\"  since    : {d['started_at']}\")
"
    return 1
}

cmd_list() {
    mkdir -p "$LOCKS_DIR"
    local count=0
    for f in "$LOCKS_DIR"/*.json; do
        [[ -f "$f" ]] || continue
        local pid
        pid="$(python3 -c "import json; d=json.load(open('$f')); print(d['pid'])" 2>/dev/null || echo "0")"
        if [[ "$pid" -gt 0 ]] && _is_stale "$pid"; then
            rm -f "$f"
            continue
        fi
        count=$((count + 1))
        python3 -c "
import json
d = json.load(open('$f'))
print(f\"  [{d['feature']}] branch={d['branch']} agent={d['agent_id'][:8]}...\")
"
    done
    if [[ $count -eq 0 ]]; then
        echo "No active locks."
    fi
}

cmd_clean() {
    mkdir -p "$LOCKS_DIR"
    local removed=0
    for f in "$LOCKS_DIR"/*.json; do
        [[ -f "$f" ]] || continue
        local pid
        pid="$(python3 -c "import json; d=json.load(open('$f')); print(d['pid'])" 2>/dev/null || echo "0")"
        if _is_stale "$pid"; then
            rm -f "$f"
            removed=$((removed + 1))
        fi
    done
    echo "Cleaned $removed stale lock(s)."
}

cmd_suggest_branch() {
    local feature="$1"
    local slug
    slug="$(_slug "$feature" | cut -c1-20)"
    local ts
    ts="$(date +%s)"
    echo "feat/${slug}-agent-${ts}"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    command="${1:-}"
    shift || true
    case "$command" in
        acquire)        cmd_acquire "$@" ;;
        release)        cmd_release "$@" ;;
        check)          cmd_check "$@" ;;
        list)           cmd_list ;;
        clean)          cmd_clean ;;
        suggest-branch) cmd_suggest_branch "$@" ;;
        *)
            echo "Usage: tools/agent-lock.sh <acquire|release|check|list|clean|suggest-branch> ..." >&2
            echo "See patterns/multi-agent-coordination/COORDINATION.md" >&2
            exit 1 ;;
    esac
fi
