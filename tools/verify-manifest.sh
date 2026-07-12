#!/bin/bash
# ============================================================================
# Verify Manifest — Check MANIFEST.md claims against actual files
# ============================================================================
#
# Extracts the Path column (3rd pipe-delimited field) from MANIFEST.md's
# tables and verifies each path actually exists. Catches regressions
# where docs reference phantom files. Also checks the reverse direction
# for .claude/skills/*/SKILL.md: every installed skill must actually be
# listed in MANIFEST.md, catching a skill that was added without
# indexing it.
#
# Deliberately extracts only field 3 (the Path column) via awk, rather
# than grepping for any backtick-quoted text in the row — a description
# cell that itself contains a backtick-quoted code example (e.g. "`git
# config core.hooksPath .github/hooks`") would otherwise be misread as a
# second path to check.
#
# Exit codes: 0 = all checks pass, 1 = missing or unlisted entries
#
# ============================================================================

MANIFEST_FILE="MANIFEST.md"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "ERROR: $MANIFEST_FILE not found"
    exit 1
fi

echo "Verifying manifest entries..."
echo ""

extract_paths() {
    awk -F'|' '
        # Separator rows look like |---|---|---|---|
        /^\|[-| ]+\|$/ { next }
        {
            cell = $3
            gsub(/^[ \t]+|[ \t]+$/, "", cell)
            # Skip the header row (Path column literally "Path")
            if (cell == "Path") next
            print cell
        }
    ' "$MANIFEST_FILE" | \
        grep -E '^`[^`]*`$' | \
        sed -E 's/^`(.*)`$/\1/' | \
        grep -E '^\.?[^:]*/'
}

missing_count=0

extract_paths | sort -u | while read -r fullpath; do
    [ -z "$fullpath" ] && continue

    # Strip anchor references (file.md#section → file.md)
    path="${fullpath%#*}"

    # Skip non-filesystem entries
    [ "${path#http}" != "$path" ] && continue
    [ "${path#\#}" != "$path" ] && continue
    [ -z "$path" ] && continue

    if [ -e "$path" ]; then
        echo "  ✓ $path"
    else
        echo "  ✗ MISSING: $path"
    fi
done

# Recomputed rather than accumulated in the loop above: that loop runs in
# a subshell (it's fed by a pipe), so a counter incremented inside it
# wouldn't be visible out here.
missing_count=$(extract_paths | sort -u | while read -r fullpath; do
    [ -z "$fullpath" ] && continue
    path="${fullpath%#*}"
    [ "${path#http}" != "$path" ] && continue
    [ "${path#\#}" != "$path" ] && continue
    [ -z "$path" ] && continue
    [ ! -e "$path" ] && echo "$path"
done | wc -l)

echo ""

# ----------------------------------------------------------------------------
# Reverse check: every installed skill must be listed in MANIFEST.md.
# Catches a skill added without an index entry (verified prior bug: adding
# an unlisted skill directory previously returned success).
# ----------------------------------------------------------------------------
unlisted_count=0

if [ -d .claude/skills ]; then
    for skill_file in .claude/skills/*/SKILL.md; do
        [ -e "$skill_file" ] || continue
        if ! grep -qF "\`$skill_file\`" "$MANIFEST_FILE"; then
            echo "  ✗ UNLISTED: $skill_file (exists but not in MANIFEST.md)"
            unlisted_count=$((unlisted_count + 1))
        fi
    done
fi

[ "$unlisted_count" -gt 0 ] && echo ""

if [ "$missing_count" -eq 0 ] && [ "$unlisted_count" -eq 0 ]; then
    echo "✅ All manifest entries exist and all skills are listed."
    exit 0
else
    [ "$missing_count" -gt 0 ] && echo "❌ $missing_count manifest entries missing."
    [ "$unlisted_count" -gt 0 ] && echo "❌ $unlisted_count skill(s) not listed in MANIFEST.md."
    exit 1
fi
