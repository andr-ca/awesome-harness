#!/bin/bash
# ============================================================================
# Verify Manifest — Check MANIFEST.md claims against actual files
# ============================================================================
#
# Extracts asset paths from MANIFEST.md and verifies each one exists.
# Catches regressions where docs reference phantom files.
#
# Exit code: 0 = all entries exist, 1 = missing entries
#
# ============================================================================

MANIFEST_FILE="MANIFEST.md"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "ERROR: $MANIFEST_FILE not found"
    exit 1
fi

echo "Verifying manifest entries..."
echo ""

# Extract backtick-quoted paths and verify each exists
# Pattern: lines with pipes, containing backticks, extract content between backticks
grep '|' "$MANIFEST_FILE" | \
    grep -v '^---' | \
    grep '`' | \
    grep -o '`[^`]*`' | \
    sed 's/^`//;s/`$//' | \
    grep / | \
    sort -u | while read -r fullpath; do

    # Skip empty entries
    if [ -z "$fullpath" ]; then
        continue
    fi

    # Strip anchor references (file.md#section → file.md)
    path="${fullpath%#*}"

    # Skip non-filesystem entries (URLs, etc.)
    case "$path" in
        http*) continue ;;
        https*) continue ;;
        \#*) continue ;;
    esac

    # Skip empty after stripping anchors
    if [ -z "$path" ]; then
        continue
    fi

    # Check if path exists
    if [ -e "$path" ]; then
        echo "  ✓ $path"
    else
        echo "  ✗ MISSING: $path"
    fi
done

echo ""

# Count missing entries by re-running the extraction
# and counting those that don't exist
missing_count=$(
    grep '|' "$MANIFEST_FILE" | \
        grep -v '^---' | \
        grep '`' | \
        grep -o '`[^`]*`' | \
        sed 's/^`//;s/`$//' | \
        grep / | \
        sort -u | while read -r fullpath; do

        if [ -z "$fullpath" ]; then
            continue
        fi

        path="${fullpath%#*}"

        case "$path" in
            http*|https*|\#*) continue ;;
        esac

        if [ -z "$path" ]; then
            continue
        fi

        if [ ! -e "$path" ]; then
            echo "$path"
        fi
    done | wc -l
)

if [ "$missing_count" -eq 0 ]; then
    echo "✅ All manifest entries exist."
    exit 0
else
    echo "❌ $missing_count manifest entries missing."
    exit 1
fi
