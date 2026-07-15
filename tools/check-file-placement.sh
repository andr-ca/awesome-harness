#!/usr/bin/env bash
# check-file-placement.sh — verify staged files don't violate guarded-paths policy.
#
# Reads .agentharness-guarded-paths.json if it exists, then checks whether
# any staged new file paths match guarded patterns.
#
# Exit codes:
#   0 — all staged files are in permitted locations
#   1 — one or more staged files require explicit permission
#
# Usage (called from pre-commit hook):
#   bash tools/check-file-placement.sh [<project-root>]
#
# To generate .agentharness-guarded-paths.json for a project:
#   python3 tools/analyze_structure.py <project-root> \
#       --output .agentharness-guarded-paths.json

set -euo pipefail

PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CONFIG_FILE="$PROJECT_ROOT/.agentharness-guarded-paths.json"

# ---------------------------------------------------------------------------
# Early exit if no guarded-paths config exists
# ---------------------------------------------------------------------------
if [[ ! -f "$CONFIG_FILE" ]]; then
    exit 0
fi

# Move to project root so git commands work relative to the repo
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Read config — fail CLOSED: any parse error blocks the commit rather than
# silently allowing guarded files through.
# ---------------------------------------------------------------------------
if ! python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
    echo "FILE PLACEMENT POLICY: could not parse $CONFIG_FILE — aborting." >&2
    exit 1
fi

guard_root=$(python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
print('true' if d.get('guard_root_level_new_items', False) else 'false')
")

guarded_dirs=$(python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
for p in d.get('guarded_dirs', []):
    print(p)
")

guarded_files=$(python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
for p in d.get('guarded_root_files', []):
    print(p)
")

# ---------------------------------------------------------------------------
# Read allowed-additions escape hatch (one path per line, '#' comments ignored)
# ---------------------------------------------------------------------------
ALLOWED_FILE="$PROJECT_ROOT/.agentharness-allowed-additions.txt"
allowed_additions=()
if [[ -f "$ALLOWED_FILE" ]]; then
    while IFS= read -r line; do
        line="${line%%#*}"
        line="${line#"${line%%[! ]*}"}"
        line="${line%"${line##*[! ]}"}"
        [[ -z "$line" ]] && continue
        allowed_additions+=("$line")
    done < "$ALLOWED_FILE"
fi

is_allowed() {
    local path="$1"
    for allowed in "${allowed_additions[@]}"; do
        if [[ "$path" == "$allowed" || "$path" == "$allowed/"* ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# Check staged new files (A = added)
# ---------------------------------------------------------------------------
staged_new=$(git diff --cached --name-only --diff-filter=A 2>/dev/null || true)

if [[ -z "$staged_new" ]]; then
    exit 0
fi

violations=()

while IFS= read -r file; do
    [[ -z "$file" ]] && continue

    # Skip explicitly allowed additions
    is_allowed "$file" && continue

    # Check root-level files (no / in path = root level)
    if [[ "$guard_root" == "true" && "$file" != */* ]]; then
        # Use exact-line match (-x) to avoid false positives (e.g. 'foo' vs 'foobar')
        if echo "$guarded_files" | grep -qxF "$file"; then
            violations+=("ROOT FILE: $file")
        else
            violations+=("ROOT LEVEL: $file (new root-level file in established project)")
        fi
        continue
    fi

    # Check guarded directories
    while IFS= read -r guarded; do
        [[ -z "$guarded" ]] && continue
        guarded="${guarded%/}"  # strip trailing slash for comparison
        if [[ "$file" == "$guarded/"* ]]; then
            violations+=("GUARDED DIR: $file (in $guarded/)")
            break
        fi
    done <<< "$guarded_dirs"

done <<< "$staged_new"

# ---------------------------------------------------------------------------
# Report violations
# ---------------------------------------------------------------------------
if [[ ${#violations[@]} -gt 0 ]]; then
    echo "" >&2
    echo "FILE PLACEMENT POLICY: The following staged files require explicit permission:" >&2
    for v in "${violations[@]}"; do
        echo "  x $v" >&2
    done
    echo "" >&2
    echo "Resolution options:" >&2
    echo "  1. Ask the user for explicit permission to create this file/directory." >&2
    echo "  2. If permission was granted, add the path to .agentharness-allowed-additions.txt" >&2
    echo "     and re-stage the file." >&2
    echo "  3. Move the file to a non-guarded location." >&2
    echo "" >&2
    echo "See patterns/file-placement-policy/POLICY.md for the full protocol." >&2
    exit 1
fi

exit 0
