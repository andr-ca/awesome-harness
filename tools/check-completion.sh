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
# Output:
#   stdout — JSON only: {"can_declare_complete":bool,"gates_passed":[...],"gates_failed":[...]}
#   stderr — human-readable progress and error messages
#
# Usage:
#   bash tools/check-completion.sh          # from repo root
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

gates_passed=()
gates_failed=()

run_gate() {
    local name="$1"
    shift
    local exit_code=0
    echo "--- Gate: $name ---" >&2
    if "$@" >/dev/null 2>&1; then
        gates_passed+=("$name")
        echo "  PASS: $name" >&2
    else
        exit_code=$?
        gates_failed+=("$name: exited $exit_code")
        echo "  FAIL: $name (exit $exit_code)" >&2
        # Re-run to show errors on stderr
        "$@" 2>&1 | head -20 >&2 || true
    fi
    echo "" >&2
}

# ---------------------------------------------------------------------------
# Gate 1: Content quality (YAML, frontmatter, snippet syntax)
# ---------------------------------------------------------------------------
run_gate "content-quality" python3 tools/verify-content-quality.py

# ---------------------------------------------------------------------------
# Gate 2: Ruff lint — mirrors CI's exact configured core surfaces
# ---------------------------------------------------------------------------
if command -v ruff >/dev/null 2>&1; then
    if [ -d src ] || [ -d tools/runtime ]; then
        # Core surfaces (configured via pyproject.toml)
        local_targets=()
        [ -d src ] && local_targets+=("src")
        [ -d tools/runtime ] && local_targets+=("tools/runtime")
        [ -d tests/unit ] && local_targets+=("tests/unit")
        run_gate "ruff-core" ruff check "${local_targets[@]}"
    fi
    # Legacy surfaces (--isolated, pre-pyproject contract)
    legacy_targets=()
    for f in \
        patterns/logging/config_loader.py \
        patterns/agentic-loops/agent_loop.py \
        tools/verify-content-quality.py \
        tools/generate-manifest.py \
        tools/release/materialize-skill-symlinks.py; do
        [ -f "$f" ] && legacy_targets+=("$f")
    done
    if [ ${#legacy_targets[@]} -gt 0 ]; then
        run_gate "ruff-legacy" ruff check --isolated "${legacy_targets[@]}"
    fi
else
    gates_failed+=("ruff: ruff not installed — install with: pip install ruff")
fi

# ---------------------------------------------------------------------------
# Gate 3: mypy type check — mirrors CI's exact configured core surfaces
# ---------------------------------------------------------------------------
if command -v mypy >/dev/null 2>&1; then
    if [ -d src ] || [ -d tools/runtime ]; then
        core_targets=()
        [ -d src ] && core_targets+=("src")
        [ -d tools/runtime ] && core_targets+=("tools/runtime")
        run_gate "mypy-core" mypy --strict --no-error-summary "${core_targets[@]}"
    fi
    # Legacy surfaces (no strict)
    legacy_mypy=()
    for f in \
        patterns/logging/config_loader.py \
        patterns/agentic-loops/agent_loop.py \
        tools/verify-content-quality.py \
        tools/generate-manifest.py \
        tools/release/materialize-skill-symlinks.py; do
        [ -f "$f" ] && legacy_mypy+=("$f")
    done
    if [ ${#legacy_mypy[@]} -gt 0 ]; then
        run_gate "mypy-legacy" mypy --config-file=/dev/null --no-error-summary "${legacy_mypy[@]}"
    fi
else
    gates_failed+=("mypy: mypy not installed — install with: pip install mypy")
fi

# ---------------------------------------------------------------------------
# Gate 4: Python tests (bootstrap policy core)
# ---------------------------------------------------------------------------
if [ -d tests ] && python3 -m pytest --version >/dev/null 2>&1; then
    run_gate "pytest-coverage" python3 -m pytest tests/ \
        --ignore=tests/integration/test_runtime_upgrade.py \
        --ignore=tests/unit/runtime/test_runtime_lock.py \
        --cov=src/agentharness \
        --cov-branch \
        --cov-fail-under=65 \
        -q
elif [ -d tests ]; then
    gates_failed+=("pytest-coverage: pytest not installed — install with: pip install pytest pytest-cov")
fi

# ---------------------------------------------------------------------------
# Gate 4b: JavaScript / TypeScript lint + type check
# Detects JS/TS projects by package.json presence and runs the project's
# own lint/typecheck scripts (defer to the project's config rather than
# hard-coding eslint/tsc flags).
# ---------------------------------------------------------------------------
if [ -f package.json ] && command -v node >/dev/null 2>&1; then
    has_npm=$(command -v npm >/dev/null 2>&1 && echo true || echo false)
    # TypeScript type check — if tsconfig.json exists and tsc is available
    if [ -f tsconfig.json ] && command -v tsc >/dev/null 2>&1; then
        run_gate "tsc-typecheck" tsc --noEmit
    elif [ -f tsconfig.json ] && [ -f node_modules/.bin/tsc ]; then
        run_gate "tsc-typecheck" node_modules/.bin/tsc --noEmit
    fi
    # Use the project's own lint script if one exists in package.json
    if $has_npm && node -e "
const d = require('./package.json');
const s = (d.scripts || {});
process.exit(('lint' in s || 'typecheck' in s || 'type-check' in s) ? 0 : 1)
" 2>/dev/null; then
        # Determine the lint script name — prefer 'lint', then 'typecheck', then 'type-check'
        if node -e "const d=require('./package.json'); process.exit(('lint' in (d.scripts||{})) ? 0 : 1)" 2>/dev/null; then
            run_gate "npm-lint" npm run lint
        elif node -e "const d=require('./package.json'); process.exit(('typecheck' in (d.scripts||{})) ? 0 : 1)" 2>/dev/null; then
            run_gate "npm-typecheck" npm run typecheck
        elif node -e "const d=require('./package.json'); process.exit(('type-check' in (d.scripts||{})) ? 0 : 1)" 2>/dev/null; then
            run_gate "npm-type-check" npm run type-check
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Gate 5: Shellcheck on changed/added .sh files
# ---------------------------------------------------------------------------
if command -v shellcheck >/dev/null 2>&1; then
    changed_sh=$(git diff --name-only HEAD 2>/dev/null | grep '\.sh$' || true)
    new_sh=$(git diff --cached --name-only --diff-filter=A 2>/dev/null | grep '\.sh$' || true)
    sh_files=$(printf '%s\n%s' "$changed_sh" "$new_sh" | grep -v '^$' | sort -u || true)
    if [ -n "$sh_files" ]; then
        # shellcheck disable=SC2086
        if echo "$sh_files" | xargs shellcheck -S warning 2>/dev/null; then
            gates_passed+=("shellcheck")
        else
            gates_failed+=("shellcheck: one or more .sh files have issues — run shellcheck on changed .sh files")
        fi
    else
        gates_passed+=("shellcheck (no .sh files changed)")
    fi
else
    gates_failed+=("shellcheck: shellcheck not installed — install with: apt install shellcheck")
fi

# ---------------------------------------------------------------------------
# Gate 6: Git status — no uncommitted changes to tracked files
# ---------------------------------------------------------------------------
# Guard against unborn HEAD (fresh repo with no commits)
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    uncommitted=$(git diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ')
    if [ "$uncommitted" -eq 0 ]; then
        gates_passed+=("git-clean")
    else
        gates_failed+=("git-clean: $uncommitted uncommitted change(s) — commit before declaring complete")
    fi
else
    # No commits yet — nothing to compare against, treat as clean
    gates_passed+=("git-clean (no commits yet)")
fi

# ---------------------------------------------------------------------------
# Report — JSON to stdout only; all other output went to stderr
# ---------------------------------------------------------------------------
can_complete="true"
if [ ${#gates_failed[@]} -gt 0 ]; then
    can_complete="false"
fi

passed_json=""
for g in "${gates_passed[@]}"; do
    passed_json="${passed_json:+$passed_json,}\"$g\""
done
failed_json=""
for g in "${gates_failed[@]}"; do
    failed_json="${failed_json:+$failed_json,}\"$g\""
done

printf '{"can_declare_complete":%s,"gates_passed":[%s],"gates_failed":[%s]}\n' \
    "$can_complete" "$passed_json" "$failed_json"

if [ "$can_complete" = "false" ]; then
    echo "" >&2
    echo "COMPLETION GATE: cannot declare work done. The following gates failed:" >&2
    for gate in "${gates_failed[@]}"; do
        echo "  x $gate" >&2
    done
    echo "" >&2
    echo "Fix the issues above, then re-run: bash tools/check-completion.sh" >&2
    exit 1
fi
