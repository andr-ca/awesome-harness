#!/usr/bin/env bash
# ============================================================================
# adapter-common.sh — shared helpers for this repo's client-adapter
# generators (generate-agents-md.sh, generate-gemini-md.sh,
# generate-copilot-instructions.sh, generate-kilo-rules.sh,
# generate-cursor-rules.sh).
# ============================================================================
#
# Every "routing-rules-only" adapter (AGENTS.md, GEMINI.md, Kilo's rules
# file) shares the same shape: CLAUDE.md's prose with headings demoted,
# plus a name+description skill index pointing at .agents/skills/ — never
# full skill bodies (see generate-agents-md.sh's header for why: that
# would defeat the point of on-demand loading). This file extracts the
# logic once instead of five times, per this repo's own "one source of
# truth per rule" principle (CLAUDE.md), now applied to the generator
# code itself, not just policy prose.
#
# Sourced (not executed) — has no shebang-guarded dispatch of its own.
# ============================================================================

# Shift every heading down one level (H1->H2, ... H5->H6), skipping lines
# inside fenced code blocks — several skills have Python/shell comments
# starting with "# " inside ```-fences (e.g. error-handling's "# ✅ Good:
# ..." examples) that must NOT be mistaken for Markdown headings and
# mangled. Demoting avoids every source doc's own H1 colliding with the
# generated file's single top-level H1 (MD025), while preserving each
# doc's internal heading hierarchy relative to itself.
demote_headings() {
    awk '
        /^```/ { in_fence = !in_fence; print; next }
        in_fence { print; next }
        /^#{1,5} / { print "#" $0; next }
        { print }
    '
}

# Extracts a single-line frontmatter field's value (key: value, between
# the first two '---' lines), stripping optional surrounding double
# quotes. Restricted to the frontmatter block (n==1) so a matching
# "key: " string appearing later in the body text is never mistaken for
# the metadata field.
frontmatter_field() {
    local file="$1" key="$2"
    awk -v key="$key" 'BEGIN{n=0} /^---$/{n++; next} n==1 && $0 ~ "^"key": "{sub("^"key": ",""); print; exit}' "$file" \
        | sed -E 's/^"(.*)"$/\1/'
}

# Extracts a SKILL.md's frontmatter `description:` value — the same
# metadata every Agent-Skills-compliant client reads before deciding
# whether to load a skill's full body.
skill_description() {
    frontmatter_field "$1" description
}

# Renders the "## Skills (loaded on demand from .agents/skills/)" section
# shared by every routing-rules-only adapter — name+description index
# only, never full bodies.
render_skill_index() {
    local harness_dir="$1" skills_dir="$2"
    echo "## Skills (loaded on demand from \`.agents/skills/\`)"
    echo
    while IFS= read -r skill; do
        [ -z "$skill" ] && continue
        local local_skill_md="$skills_dir/$skill/SKILL.md"
        [ -f "$local_skill_md" ] || continue
        local description
        description="$(skill_description "$local_skill_md")"
        echo "- \`.agents/skills/$skill/SKILL.md\` — $description"
    done < <(list_available_skills "$harness_dir" | sort)
}

# Parses the common `[harness-dir] [--output <path>]` CLI shape shared by
# every single-file generator. Sets globals harness_dir/output
# (deliberately not `local` — the calling script reads them afterward)
# rather than returning a value, since bash functions can't return
# strings directly.
parse_common_adapter_args() {
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
}

# Same shape, for generators that write multiple files under one target
# directory (Copilot's instructions/ tree, Cursor's rules/ directory)
# instead of a single --output path. output_dir defaults to harness_dir
# so running the script bare in this repo checkout regenerates the real,
# dogfooded files in place; the content-quality sync check overrides it
# to a temp directory to sandbox the comparison.
parse_multi_file_adapter_args() {
    harness_dir="$HARNESS_DIR"
    output_dir=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --output-dir)
                output_dir="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $(basename "$0") [harness-dir] [--output-dir <dir>]"
                exit 0
                ;;
            *)
                harness_dir="$1"
                shift
                ;;
        esac
    done
    [ -n "$output_dir" ] || output_dir="$harness_dir"
}

# Strips a file's YAML frontmatter block (the two '---' lines and
# everything between them) — used when re-embedding a source document's
# body (a SKILL.md, a CONVENTIONS.md) into a generated adapter file that
# renders its own frontmatter instead.
strip_frontmatter() {
    awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$1"
}

# cat -s squeezes the runs of consecutive blank lines that appear at the
# seams between concatenated documents (a generator's own blank-line
# spacing plus whatever blank line each source file already ended/started
# with) down to one — simpler and more robust than hand-tracking exact
# spacing across every seam. $(...) then strips all trailing newlines (a
# bash command-substitution property, not a bug) so printf can put back
# exactly one — otherwise the file ends in a lone blank line that
# markdownlint's MD012 flags as a second consecutive blank at EOF.
#
# Reads generated content from stdin, writes the squeezed result to stdout.
squeeze_blank_lines() {
    local content
    content="$(cat -s)"
    printf '%s\n' "$content"
}

# Same squeeze, but for single-file generators using the --output/stdout
# CLI shape from parse_common_adapter_args: writes to $output if set,
# else stdout, instead of always stdout.
write_generated_content() {
    if [ -n "$output" ]; then
        squeeze_blank_lines > "$output"
    else
        squeeze_blank_lines
    fi
}
