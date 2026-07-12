#!/usr/bin/env bash
# ============================================================================
# generate-agents-md.sh — build an AGENTS.md (Codex CLI's instruction file)
# from the same CLAUDE.md + skill catalog Claude Code reads on demand.
# ============================================================================
#
# Codex has no on-demand skill-loading mechanism like Claude Code's
# .claude/skills/ — everything Codex should know has to live in one file
# it reads in full. This script concatenates CLAUDE.md's routing prose
# (with the "loaded on demand" framing rewritten, since nothing here is
# lazy for Codex) with every skill's SKILL.md body, so the two clients
# stay in sync from one source instead of a hand-maintained copy that
# silently drifts — the same class of bug fixed for docs in P1-13.
#
# NOT verified against a real Codex CLI session — see README.md's
# "Supported clients" section. Best-effort until someone actually tests
# it against Codex.
#
# Usage:
#   tools/generate-agents-md.sh [harness-dir] [--output <path>]
#
# harness-dir defaults to this script's own repo root. Without --output,
# writes to stdout.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sourced (not executed) so its dispatch never runs — see the
# BASH_SOURCE-vs-$0 guard at the bottom of harness-link.sh. Reuses
# list_available_skills and its own HARNESS_DIR computation instead of
# reimplementing skill discovery here.
# shellcheck source=./setup/harness-link.sh
source "$SCRIPT_DIR/setup/harness-link.sh"

harness_dir="$HARNESS_DIR"
output=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output)
            output="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $(basename "$0") [harness-dir] [--output <path>]"
            exit 0
            ;;
        *)
            harness_dir="$1"
            shift
            ;;
    esac
done

claude_md="$harness_dir/CLAUDE.md"
skills_dir="$harness_dir/.claude/skills"

if [ ! -f "$claude_md" ]; then
    echo "Error: $claude_md not found." >&2
    exit 1
fi

# Shift every heading down one level (H1->H2, ... H5->H6), skipping lines
# inside fenced code blocks — several skills have Python/shell comments
# starting with "# " inside ```-fences (e.g. error-handling's "# ✅ Good:
# ..." examples) that must NOT be mistaken for Markdown headings and
# mangled. Demoting avoids every source doc's own H1 colliding with this
# file's single top-level "# AGENTS.md" title (MD025), while preserving
# each doc's internal heading hierarchy relative to itself.
demote_headings() {
    awk '
        /^```/ { in_fence = !in_fence; print; next }
        in_fence { print; next }
        /^#{1,5} / { print "#" $0; next }
        { print }
    '
}

generate() {
    cat <<'HEADER'
# AGENTS.md

Generated from this repo's own `CLAUDE.md` and `.claude/skills/` catalog
by `tools/generate-agents-md.sh` — do not hand-edit; regenerate instead
(`tools/generate-agents-md.sh --output AGENTS.md`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

Codex has no on-demand skill-loading mechanism — everything below is
always in context, not loaded on demand the way Claude Code loads a
matching skill. Content is otherwise identical to what a Claude Code
session reads from `CLAUDE.md` and `.claude/skills/*/SKILL.md`.

**This adapter has not been verified against a real Codex CLI session —
best-effort until someone tests it. See `README.md`'s "Supported
clients" section.**

---

HEADER

    # Reproduced content: CLAUDE.md doesn't itself claim a specific
    # skill-loading mechanism (that's Claude Code's own behavior, not
    # something asserted in this file's text) — the on-demand-vs-always-
    # included distinction that actually matters for Codex is covered
    # once, clearly, in the header above. Headings demoted (see above)
    # so its own "# agentharness – Agent Router" H1 doesn't collide with
    # this file's H1.
    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    echo "## Skills (always included — see note above)"
    echo

    while IFS= read -r skill; do
        [ -z "$skill" ] && continue
        local_skill_md="$skills_dir/$skill/SKILL.md"
        [ -f "$local_skill_md" ] || continue
        echo "### Skill: $skill"
        echo
        # Skip the YAML frontmatter (the two '---' lines and everything
        # between them) — its name/description exist to drive Claude
        # Code's on-demand matching, which doesn't apply here; the
        # heading above already conveys the skill name. Demote the
        # remaining headings so the skill's own H1 nests under "###
        # Skill: $skill" instead of colliding with this file's H1.
        awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$local_skill_md" | demote_headings
        echo
    done < <(list_available_skills "$harness_dir" | sort)
}

# cat -s squeezes the runs of consecutive blank lines that appear at the
# seams between concatenated documents (this script's own blank-line
# spacing plus whatever blank line each source file already ended/started
# with) down to one — simpler and more robust than hand-tracking exact
# spacing across every seam. $(...) then strips all trailing newlines
# (a bash command-substitution property, not a bug) so printf can put
# back exactly one — otherwise the file ends in a lone blank line that
# markdownlint's MD012 flags as a second consecutive blank at EOF.
content="$(generate | cat -s)"
if [ -n "$output" ]; then
    printf '%s\n' "$content" > "$output"
else
    printf '%s\n' "$content"
fi
