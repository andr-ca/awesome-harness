#!/usr/bin/env bash
# ============================================================================
# check.sh — one entrypoint for every check CI runs (P1-06)
# ============================================================================
#
# Usage: bash tools/check.sh [--offline]
#
# Runs, in order: shellcheck (if installed), bats suites, ruff, mypy,
# pytest with coverage gates, MANIFEST.md verification, and the P1-08
# content-quality checks (markdownlint, YAML/frontmatter/snippet
# validation). Stops at the first failure so you fix things one at a time,
# same as the pre-push hook (which runs a subset of this — bats + pytest —
# automatically).
#
# Requires: bats, python3, pip install -r requirements-dev.txt, npx (for
# markdownlint-cli2 — downloaded on first use if not already cached).
# Static analysis of shell scripts (via the shellcheck tool) is optional
# locally — CI always runs it — but installing it locally catches issues
# this script otherwise can't.
# ============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --offline (or CHECK_OFFLINE=1) skips the one step that may reach the
# network — markdownlint via `npx --yes` fetching markdownlint-cli2 on a
# cold cache (P1-05). Everything else here is already local.
OFFLINE="${CHECK_OFFLINE:-0}"
for arg in "$@"; do
    [ "$arg" = "--offline" ] && OFFLINE=1
done

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "\n${YELLOW}==>${NC} $1"; }

if command -v shellcheck >/dev/null 2>&1; then
    step "shellcheck"
    shopt -s globstar nullglob
    scripts=(.github/hooks/prevent-trunk-commit .github/hooks/pre-commit .github/hooks/pre-push tools/**/*.sh)
    shellcheck -S warning "${scripts[@]}"
else
    echo -e "${YELLOW}skipping shellcheck (not installed) — CI still runs it.${NC}"
fi

step "bats: .github/hooks/tests/"
bats .github/hooks/tests/

step "bats: tools/tests/harness-link.bats"
bats tools/tests/harness-link.bats

step "bats: tools/tests/harness-lifecycle.bats"
bats tools/tests/harness-lifecycle.bats

step "bats: tools/tests/lifecycle-transitions.bats"
bats tools/tests/lifecycle-transitions.bats

step "bats: tools/tests/generate-agents-md.bats"
bats tools/tests/generate-agents-md.bats

step "bats: tools/tests/generate-manifest.bats"
bats tools/tests/generate-manifest.bats

step "bats: tools/tests/materialize-skill-symlinks.bats"
bats tools/tests/materialize-skill-symlinks.bats

step "bats: tools/tests/verify-skill-symlinks.bats"
bats tools/tests/verify-skill-symlinks.bats

step "bats: tools/tests/publish-authority.bats"
bats tools/tests/publish-authority.bats

step "bats: tools/tests/enforce-profile.bats"
bats tools/tests/enforce-profile.bats

step "bats: tools/tests/generate-clients.bats"
bats tools/tests/generate-clients.bats

step "ruff"
ruff check patterns/logging/config_loader.py patterns/logging/test_config_loader.py \
    patterns/agentic-loops/agent_loop.py patterns/agentic-loops/test_agent_loop.py \
    tools/eval/score.py tools/eval/run.py \
    tools/verify-content-quality.py tools/tests/test_verify_content_quality.py \
    tools/generate-manifest.py tools/release/materialize-skill-symlinks.py

step "mypy"
mypy patterns/logging/config_loader.py patterns/agentic-loops/agent_loop.py \
    tools/eval/score.py tools/eval/run.py tools/verify-content-quality.py \
    tools/release/materialize-skill-symlinks.py \
    tools/generate-manifest.py

step "pytest: config_loader (>=80% coverage)"
(cd patterns/logging && python3 -m pytest test_config_loader.py --cov=config_loader --cov-branch --cov-fail-under=80 -q)

step "pytest: agent_loop (>=80% coverage)"
(cd patterns/agentic-loops && python3 -m pytest test_agent_loop.py --cov=agent_loop --cov-branch --cov-fail-under=80 -q)

step "pytest: eval suite score.py + run.py (>=80% coverage; requires go for the go-error-handling task)"
(cd tools/eval && python3 -m pytest tests/ --cov=score --cov=run --cov-branch --cov-fail-under=80 -q)

step "pytest: duplicate-policy detection (tools/tests/test_verify_content_quality.py)"
# No --cov-fail-under here: this file tests only check_duplicate_policy_
# numbers() and its helpers (B7), not the whole of verify-content-quality.py
# (that script predates having any test file at all — pre-existing gap,
# out of scope for B7). Coverage-gating the whole module against tests
# that only exercise one function would either need a low, easily-stale
# threshold or a much larger test-writing task than B7 asked for.
python3 -m pytest tools/tests/test_verify_content_quality.py -q

step "MANIFEST.md verification"
bash tools/verify-manifest.sh

step "skill symlink integrity (.claude/skills <-> .agents/skills)"
bash tools/verify-skill-symlinks.sh

if [ "$OFFLINE" = 1 ]; then
    echo -e "${YELLOW}skipping markdownlint (--offline) — the only step that may fetch markdownlint-cli2 via npx; CI still runs it.${NC}"
elif command -v npx >/dev/null 2>&1; then
    step "markdownlint"
    npx --yes markdownlint-cli2 "**/*.md"
else
    echo -e "${YELLOW}skipping markdownlint (npx not installed) — CI still runs it.${NC}"
fi

step "content quality (YAML, skill frontmatter, tested-snippet syntax)"
python3 tools/verify-content-quality.py

echo -e "\n${GREEN}All checks passed.${NC}"
