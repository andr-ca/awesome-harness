#!/usr/bin/env bash
# ============================================================================
# generate-agents-md.sh — build an AGENTS.md (Codex CLI's instruction file)
# from the same CLAUDE.md this repo's own agents read.
# ============================================================================
#
# P0-06: Codex CLI's real skill mechanism (the Agent Skills open standard,
# shared with Claude Code since Dec 2025) discovers skills by scanning
# .agents/skills/ up from the working directory to the repo root, reading
# only each SKILL.md's name+description metadata up front, and loading a
# skill's full body only once its description matches the task at hand —
# see https://developers.openai.com/codex/skills. It is NOT true that
# Codex has no on-demand loading; it uses the same progressive-disclosure
# model Claude Code does. harness-link.sh installs every skill under
# .agents/skills/ alongside .claude/skills/ (same source, same SKILL.md)
# specifically so this works for a consumer project too.
#
# AGENTS.md therefore only needs repo-wide routing rules (from CLAUDE.md)
# plus a lightweight skill index — name + description, not full bodies —
# so Codex's own metadata-scan step has something to match against even
# before it lists .agents/skills/ itself. Concatenating every skill body
# here would defeat the point: it would front-load unrelated Python,
# error-handling, and agent-loop material into every task regardless of
# relevance, the exact problem this redesign fixes (previously an 880-line
# adapter; see docs/INTEGRATION.md's Codex section for the measured
# before/after).
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

Generated from this repo's own `CLAUDE.md` by `tools/generate-agents-md.sh`
— do not hand-edit; regenerate instead
(`tools/generate-agents-md.sh --output AGENTS.md`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.agents/skills/` — Codex CLI's real skill mechanism (the
Agent Skills open standard, shared with Claude Code) scans that
directory from the working directory up to the repo root, reads each
`SKILL.md`'s `name`/`description` metadata up front, and loads a skill's
full body only once its description matches the task at hand. The index
below exists so that metadata-scan step has something to match against;
it is not a substitute for reading the matched `SKILL.md` itself.

---

HEADER

    # Reproduced content: CLAUDE.md doesn't itself claim a specific
    # skill-loading mechanism (that's client-specific behavior, not
    # something asserted in this file's text). Headings demoted (see
    # above) so its own "# agentharness – Agent Router" H1 doesn't
    # collide with this file's H1.
    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    echo "## Skills (loaded on demand from \`.agents/skills/\`)"
    echo

    while IFS= read -r skill; do
        [ -z "$skill" ] && continue
        local_skill_md="$skills_dir/$skill/SKILL.md"
        [ -f "$local_skill_md" ] || continue
        # Only the frontmatter's name/description — the same metadata
        # Codex's own progressive-disclosure scan reads before deciding
        # whether to load the full SKILL.md. Not the skill body: that
        # defeats the point of on-demand loading (see script header).
        description="$(awk 'BEGIN{n=0} /^---$/{n++; next} n==1 && /^description: /{sub(/^description: /,""); print; exit}' "$local_skill_md")"
        echo "- \`.agents/skills/$skill/SKILL.md\` — $description"
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
