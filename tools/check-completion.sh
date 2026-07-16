#!/usr/bin/env bash
# check-completion.sh — Agent completion gate.
#
# Runs all required gates and reports whether the current working state
# can be declared "complete". Designed to be called from Claude Code and
# GitHub Copilot Stop hooks to prevent agents from claiming work is done
# before all quality gates pass.
#
# Exit codes:
#   0 — all gates passed; work may be declared complete
#   1 — one or more gates failed; work is NOT complete
#
# Output: JSON to stdout with structure:
#   { "can_declare_complete": bool, "gates_passed": [...], "gates_failed": [...] }
#
# Usage:
#   bash tools/check-completion.sh           # from repo root
#   bash tools/check-completion.sh --quiet   # suppress individual gate output
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

QUIET=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true

gates_passed=()
gates_failed=()

run_gate() {
    local name="$1"
    shift
    local output exit_code
    if $QUIET; then
        if output=$("$@" 2>&1); then
            gates_passed+=("$name")
        else
            exit_code=$?
            gates_failed+=("$name: exited $exit_code")
        fi
    else
        echo "--- Gate: $name ---"
        if "$@"; then
            gates_passed+=("$name")
            echo "  PASS: $name"
        else
            exit_code=$?
            gates_failed+=("$name: exited $exit_code")
            echo "  FAIL: $name (exit $exit_code)"
        fi
        echo ""
    fi
}

# ---------------------------------------------------------------------------
# Gate 1: Content quality (YAML, frontmatter, snippet syntax)
# ---------------------------------------------------------------------------
run_gate "content-quality" python3 tools/verify-content-quality.py

# ---------------------------------------------------------------------------
# Gate 2: Ruff lint
# ---------------------------------------------------------------------------
if [ -f pyproject.toml ] && command -v ruff >/dev/null 2>&1; then
    run_gate "ruff-lint" ruff check src tools/runtime tests --select E,F,I,UP
elif [ -f pyproject.toml ]; then
    gates_failed+=("ruff-lint: ruff not installed")
fi

# ---------------------------------------------------------------------------
# Gate 3: mypy type check (only if pyproject.toml has src/)
# ---------------------------------------------------------------------------
if [ -d src ] && command -v mypy >/dev/null 2>&1; then
    run_gate "mypy" mypy --strict src --no-error-summary
elif [ -d src ]; then
    gates_failed+=("mypy: mypy not installed")
fi

# ---------------------------------------------------------------------------
# Gate 4: Python tests (bootstrap policy core)
# ---------------------------------------------------------------------------
if [ -d tests ] && command -v python3 >/dev/null 2>&1 && python3 -m pytest --version >/dev/null 2>&1; then
    run_gate "pytest-coverage" python3 -m pytest tests/ \
        --ignore=tests/integration/test_runtime_upgrade.py \
        --ignore=tests/unit/runtime/test_runtime_lock.py \
        --cov=src/agentharness \
        --cov-branch \
        --cov-fail-under=65 \
        -q
elif [ -d tests ]; then
    gates_failed+=("pytest-coverage: pytest not installed")
fi

# ---------------------------------------------------------------------------
# Gate 5: Shellcheck (if any .sh files changed from HEAD)
# ---------------------------------------------------------------------------
if command -v shellcheck >/dev/null 2>&1; then
    changed_sh=$(git diff --name-only HEAD 2>/dev/null | grep '\.sh$' || true)
    new_sh=$(git diff --cached --name-only --diff-filter=A 2>/dev/null | grep '\.sh$' || true)
    sh_files="$changed_sh $new_sh"
    sh_files="${sh_files// /$'\n'}"
    sh_files=$(echo "$sh_files" | grep -v '^$' | sort -u || true)
    if [ -n "$sh_files" ]; then
        # shellcheck requires a file list — can't use stdin
        if echo "$sh_files" | xargs shellcheck 2>/dev/null; then
            gates_passed+=("shellcheck")
        else
            gates_failed+=("shellcheck: one or more .sh files have issues")
        fi
    else
        gates_passed+=("shellcheck (no .sh files changed)")
    fi
fi

# ---------------------------------------------------------------------------
# Gate 6: Git status — no uncommitted changes to tracked files
# ---------------------------------------------------------------------------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && [[ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" == "true" ]]; then
    uncommitted=$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
    untracked=$(git status --short 2>/dev/null | grep -c "^??" || true)
    if [ "$uncommitted" -eq 0 ] && [ "$untracked" -eq 0 ]; then
        gates_passed+=("git-clean")
    elif [ "$uncommitted" -gt 0 ]; then
        gates_failed+=("git-clean: $uncommitted uncommitted change(s) — commit before declaring complete")
    fi
    # Untracked files are a warning, not a blocker
fi

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
can_complete="true"
if [ ${#gates_failed[@]} -gt 0 ]; then
    can_complete="false"
fi

# Build JSON
passed_json=$(printf '"%s",' "${gates_passed[@]}" 2>/dev/null | sed 's/,$//')
failed_json=$(printf '"%s",' "${gates_failed[@]}" 2>/dev/null | sed 's/,$//')

cat << ENDJSON
{
  "can_declare_complete": $can_complete,
  "gates_passed": [$passed_json],
  "gates_failed": [$failed_json]
}
ENDJSON

if [ "$can_complete" = "false" ]; then
    echo "" >&2
    echo "COMPLETION GATE: cannot declare work done. The following gates failed:" >&2
    for gate in "${gates_failed[@]}"; do
        echo "  ✗ $gate" >&2
    done
    echo "" >&2
    echo "Fix the issues above, then re-run: bash tools/check-completion.sh" >&2
    exit 1
fi
