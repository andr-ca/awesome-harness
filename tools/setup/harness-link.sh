#!/usr/bin/env bash
# ============================================================================
# harness-link.sh — agentharness lifecycle CLI
# ============================================================================
#
# Usage:
#   harness-link.sh <subcommand> [target-project-dir] [OPTIONS]
#   harness-link.sh <target-project-dir> [OPTIONS]     (legacy form, same as
#                                                        'init <target> ...')
#
# Subcommands:
#   init      Install into a project (skills, .gitignore, optional hook).
#   plan      Show what 'init' would do without changing anything.
#   status    Show what's currently installed (from .agentharness-state.json).
#   doctor    Validate the current install is healthy; nonzero exit if not.
#   audit     Report drift: newly available/removed skills, source commits
#             since install.
#   update    Re-sync an existing install to the current harness state.
#   uninstall Reverse everything 'init' recorded.
#
# All subcommands operate on a target project directory (default: '.').
# State is tracked in <target>/.agentharness-state.json, written by init and
# read by every other subcommand — a project not initialized through this
# CLI won't have one; run 'init' first.
#
# Install modes (--mode, init/update only):
#   link       (default) Symlink skills from this harness checkout. Fast,
#              always current, but the target depends on this checkout
#              persisting on disk.
#   copy       Physically copy skill files into the target. No dependency
#              on this checkout, but content is a snapshot — re-run 'update'
#              to pull in changes.
#   submodule  Add this harness as a git submodule at <target>/.agentharness
#              (version-pinned in the target's own history) and symlink
#              skills from there instead of this checkout.
#
# Requires python3 (used for reading/writing the JSON state file).
# ============================================================================

set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_FILE_NAME=".agentharness-state.json"
PROFILE_FILE_NAME=".agentharness-profile"
GITIGNORE_MARKER="# --- Added by agentharness harness-link.sh ---"
SUBMODULE_PATH=".agentharness"

usage() {
    cat <<EOF
Usage: $(basename "$0") <subcommand> [target-project-dir] [OPTIONS]
       $(basename "$0") <target-project-dir> [OPTIONS]   (legacy: same as init)

Subcommands: init, plan, status, doctor, audit, update, uninstall

init options:
  --mode link|copy|submodule   Install mode (default: link)
  --skills a,b,c               Comma-separated list of skills (default: all)
  --with-hook                  Install the trunk-protection + coverage hooks
  --force                      Overwrite an existing, different core.hooksPath
  --profile prototype|internal|production
                                Write .agentharness-profile
  --dry-run                    Show the plan; change nothing (same as 'plan')

update/uninstall options:
  --yes                        Skip the confirmation prompt

Examples:
  $(basename "$0") init ~/my-project --with-hook
  $(basename "$0") init ~/my-project --mode copy --skills committing,branching
  $(basename "$0") status ~/my-project
  $(basename "$0") doctor ~/my-project
  $(basename "$0") update ~/my-project --yes
  $(basename "$0") uninstall ~/my-project
EOF
}

# ----------------------------------------------------------------------------
# State file (JSON) — read/write via python3, with values passed through the
# real environment (never interpolated into the python source) so a value
# containing quotes can't break out of the heredoc.
# ----------------------------------------------------------------------------

state_path() { echo "$1/$STATE_FILE_NAME"; }

state_write() {
    # $1=target $2=mode $3=skills_csv $4=skills_filter(or "") $5=with_hook(true/false)
    # $6=profile(or "") $7=source_path $8=source_revision $9=source_remote(or "")
    local target="$1" mode="$2" skills_csv="$3" skills_filter="$4" with_hook="$5"
    local profile="$6" source_path="$7" source_revision="$8" source_remote="$9"
    local existing_installed_at=""
    if [ -f "$(state_path "$target")" ]; then
        existing_installed_at="$(state_field "$target" "installed_at" || true)"
    fi
    AH_MODE="$mode" AH_SKILLS_CSV="$skills_csv" AH_SKILLS_FILTER="$skills_filter" \
    AH_WITH_HOOK="$with_hook" AH_PROFILE="$profile" AH_SOURCE_PATH="$source_path" \
    AH_SOURCE_REVISION="$source_revision" AH_SOURCE_REMOTE="$source_remote" \
    AH_EXISTING_INSTALLED_AT="$existing_installed_at" \
    python3 - "$(state_path "$target")" <<'PYEOF'
import datetime
import json
import os
import sys

path = sys.argv[1]
skills_csv = os.environ.get("AH_SKILLS_CSV", "")
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
existing_installed_at = os.environ.get("AH_EXISTING_INSTALLED_AT") or now

data = {
    "version": 1,
    "mode": os.environ["AH_MODE"],
    "source": {
        "path": os.environ["AH_SOURCE_PATH"],
        "revision": os.environ["AH_SOURCE_REVISION"],
        "remote": os.environ.get("AH_SOURCE_REMOTE") or None,
    },
    "skills": [s for s in skills_csv.split(",") if s],
    "skills_filter": os.environ.get("AH_SKILLS_FILTER") or None,
    "with_hook": os.environ.get("AH_WITH_HOOK") == "true",
    "profile": os.environ.get("AH_PROFILE") or None,
    "installed_at": existing_installed_at,
    "updated_at": now,
}
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
}

# Dotted-path field accessor. Lists print comma-joined; missing -> exit 1.
state_field() {
    local target="$1" field="$2"
    local path
    path="$(state_path "$target")"
    [ -f "$path" ] || return 1
    python3 - "$path" "$field" <<'PYEOF'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)
cur = data
for part in sys.argv[2].split("."):
    cur = cur.get(part) if isinstance(cur, dict) else None
    if cur is None:
        sys.exit(1)
if isinstance(cur, list):
    print(",".join(cur))
elif isinstance(cur, bool):
    # Lowercase, matching JSON/shell convention (and what state_write's
    # own reader compares against) — Python's str(True) == "True" would
    # otherwise silently fail every `== "true"` check downstream.
    print("true" if cur else "false")
else:
    print(cur)
PYEOF
}

require_state() {
    local target="$1"
    if [ ! -f "$(state_path "$target")" ]; then
        echo "Error: no $STATE_FILE_NAME found in $target." >&2
        echo "Not initialized through this CLI (or initialized before it existed) — run 'init' first." >&2
        exit 1
    fi
}

# ----------------------------------------------------------------------------
# Skill discovery / validation (shared by init, update, audit)
# ----------------------------------------------------------------------------

list_available_skills() {
    local src="$1/.claude/skills"
    [ -d "$src" ] || return 0
    for d in "$src"/*/; do
        [ -d "$d" ] && basename "$d"
    done
}

# Prints one validated skill name per line; warns and skips anything invalid
# or unknown. --skills is user-supplied, so reject anything but a plain
# directory name — "../../etc" or an absolute path must never make the
# resolved source path escape the skills directory.
resolve_wanted_skills() {
    local skills_src_root="$1" filter="$2"
    local wanted=()
    if [ -n "$filter" ]; then
        IFS=',' read -ra wanted <<< "$filter"
    else
        while IFS= read -r name; do wanted+=("$name"); done < <(list_available_skills "$skills_src_root")
    fi
    for skill in "${wanted[@]}"; do
        case "$skill" in
            */*|.*|'')
                echo "  Skipping invalid skill name: $skill" >&2
                continue
                ;;
        esac
        if [ ! -d "$skills_src_root/.claude/skills/$skill" ]; then
            echo "  Skipping unknown skill: $skill" >&2
            continue
        fi
        echo "$skill"
    done
}

# ----------------------------------------------------------------------------
# init / plan
# ----------------------------------------------------------------------------

cmd_init() {
    local target="" mode="link" skills_filter="" with_hook=false force=false
    local profile="" dry_run=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --mode) mode="$2"; shift 2 ;;
            --skills) skills_filter="$2"; shift 2 ;;
            --with-hook) with_hook=true; shift ;;
            --force) force=true; shift ;;
            --profile) profile="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *)
                if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; usage; exit 1; fi
                shift
                ;;
        esac
    done
    target="${target:-.}"

    case "$mode" in
        link|copy|submodule) ;;
        *) echo "Error: --mode must be link, copy, or submodule (got: $mode)" >&2; exit 1 ;;
    esac
    if [ -n "$profile" ]; then
        case "$profile" in
            prototype|internal|production) ;;
            *) echo "Error: --profile must be prototype, internal, or production (got: $profile)" >&2; exit 1 ;;
        esac
    fi
    if [ ! -d "$target" ]; then
        echo "Error: target directory does not exist: $target" >&2
        exit 1
    fi
    target="$(cd "$target" && pwd)"

    # Where skills/hooks are actually sourced from depends on mode: link and
    # copy read straight from this checkout; submodule reads from the
    # submodule this init creates inside the target itself.
    local skills_src_root="$HARNESS_DIR"
    local hooks_src_dir="$HARNESS_DIR/.github/hooks"

    if [ "$dry_run" = true ]; then
        echo "Plan for 'init' on $target (mode: $mode):"
        echo "  Skills to install:"
        resolve_wanted_skills "$skills_src_root" "$skills_filter" | sed 's/^/    - /'
        echo "  .gitignore: merge $HARNESS_DIR/.github/.gitignore.template (additive)"
        if [ "$with_hook" = true ]; then
            echo "  Hook: install trunk-protection + coverage hooks (mode: $mode)"
        fi
        [ -n "$profile" ] && echo "  Profile: write $PROFILE_FILE_NAME = $profile"
        echo "  State: write $target/$STATE_FILE_NAME"
        echo "(dry run — nothing was changed)"
        return 0
    fi

    echo "Initializing agentharness ($HARNESS_DIR) into $target (mode: $mode)"

    if [ "$mode" = "submodule" ]; then
        if ! git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            echo "Error: --mode submodule requires $target to be a git repo." >&2
            exit 1
        fi
        local harness_remote
        harness_remote="$(git -C "$HARNESS_DIR" remote get-url origin 2>/dev/null || true)"
        if [ -z "$harness_remote" ]; then
            echo "Error: --mode submodule requires this harness checkout to have an 'origin' remote." >&2
            exit 1
        fi
        if [ ! -e "$target/$SUBMODULE_PATH/.git" ]; then
            git -C "$target" submodule add "$harness_remote" "$SUBMODULE_PATH"
            echo "  Added agentharness as a submodule at $SUBMODULE_PATH"
            # 'submodule add' checks out the remote's default branch, which
            # is not necessarily what this checkout (HARNESS_DIR) actually
            # has: if HARNESS_DIR is on an unmerged branch/tag ahead of the
            # remote's default, the submodule would silently diverge from
            # it (fewer/different skills than what 'init' just planned
            # against). Pin the submodule to HARNESS_DIR's exact commit
            # when the remote has it, so submodule mode really does pin to
            # what you're running from, not "whatever the default branch
            # currently is". Falls back to the default-branch checkout
            # 'submodule add' already did if that commit isn't reachable
            # (e.g. purely local, never-pushed commits).
            local harness_rev
            harness_rev="$(git -C "$HARNESS_DIR" rev-parse HEAD 2>/dev/null || true)"
            if [ -n "$harness_rev" ]; then
                git -C "$target/$SUBMODULE_PATH" cat-file -e "$harness_rev" 2>/dev/null \
                    || git -C "$target/$SUBMODULE_PATH" fetch --quiet origin "$harness_rev" 2>/dev/null || true
                if git -C "$target/$SUBMODULE_PATH" cat-file -e "$harness_rev" 2>/dev/null; then
                    git -C "$target/$SUBMODULE_PATH" checkout --quiet "$harness_rev"
                fi
            fi
        else
            echo "  Submodule already present at $SUBMODULE_PATH"
        fi
        skills_src_root="$target/$SUBMODULE_PATH"
        hooks_src_dir="$target/$SUBMODULE_PATH/.github/hooks"
    fi

    # ------------------------------------------------------------------
    # 1. Skills
    # ------------------------------------------------------------------
    local skills_dst="$target/.claude/skills"
    mkdir -p "$skills_dst"
    local linked_skills=()

    while IFS= read -r skill; do
        linked_skills+=("$skill")
        local src="$skills_src_root/.claude/skills/$skill"
        local dst="$skills_dst/$skill"
        case "$mode" in
            link|submodule)
                if [ -L "$dst" ]; then
                    rm "$dst"
                elif [ -e "$dst" ]; then
                    echo "  Skipping $skill: $dst exists and is not a symlink (not overwriting)" >&2
                    continue
                fi
                ln -s "$src" "$dst"
                echo "  Linked skill: $skill"
                ;;
            copy)
                rm -rf "$dst"
                cp -rL "$src" "$dst"
                echo "  Copied skill: $skill"
                ;;
        esac
    done < <(resolve_wanted_skills "$skills_src_root" "$skills_filter")

    # ------------------------------------------------------------------
    # 2. .gitignore
    # ------------------------------------------------------------------
    local gitignore_template="$HARNESS_DIR/.github/.gitignore.template"
    local gitignore_dst="$target/.gitignore"
    if [ -f "$gitignore_template" ]; then
        if [ -f "$gitignore_dst" ]; then
            local new_entries
            new_entries="$(comm -23 \
                <(grep -vE '^\s*(#|$)' "$gitignore_template" | sort -u) \
                <(grep -vE '^\s*(#|$)' "$gitignore_dst" | sort -u))"
            if [ -n "$new_entries" ]; then
                { echo ""; echo "$GITIGNORE_MARKER"; echo "$new_entries"; } >> "$gitignore_dst"
                echo "  Merged new entries into existing .gitignore"
            else
                echo "  .gitignore already covers everything in the template"
            fi
        else
            cp "$gitignore_template" "$gitignore_dst"
            echo "  Created .gitignore from template"
        fi
    else
        echo "  No gitignore template found at $gitignore_template — skipping." >&2
    fi

    # ------------------------------------------------------------------
    # 3. Hooks (opt-in)
    # ------------------------------------------------------------------
    if [ "$with_hook" = true ]; then
        if ! git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            echo "  --with-hook requested but $target is not a git repo — skipping." >&2
        else
            local hooks_path
            if [ "$mode" = "copy" ]; then
                mkdir -p "$target/.github/hooks"
                cp "$hooks_src_dir/prevent-trunk-commit" "$hooks_src_dir/pre-commit" "$hooks_src_dir/pre-push" "$target/.github/hooks/"
                hooks_path="$target/.github/hooks"
            else
                hooks_path="$hooks_src_dir"
            fi
            local existing_hooks_path
            existing_hooks_path="$(git -C "$target" config --get core.hooksPath 2>/dev/null || true)"
            if [ -z "$existing_hooks_path" ] || [ "$existing_hooks_path" = "$hooks_path" ]; then
                git -C "$target" config core.hooksPath "$hooks_path"
                echo "  Installed trunk-protection + coverage hooks (core.hooksPath)"
            elif [ "$force" = true ]; then
                git -C "$target" config core.hooksPath "$hooks_path"
                echo "  Overwrote existing core.hooksPath ($existing_hooks_path) with agentharness hooks (--force)"
            else
                echo "  --with-hook requested but $target already has a different core.hooksPath set:" >&2
                echo "    $existing_hooks_path" >&2
                echo "  Not overwriting — rerun with --force, or 'git -C $target config --unset core.hooksPath' first." >&2
            fi
        fi
    fi

    # ------------------------------------------------------------------
    # 4. Profile
    # ------------------------------------------------------------------
    if [ -n "$profile" ]; then
        echo "$profile" > "$target/$PROFILE_FILE_NAME"
        echo "  Wrote $PROFILE_FILE_NAME = $profile"
    fi

    # ------------------------------------------------------------------
    # 5. State file (written last — a failure above never leaves a state
    #    file describing work that didn't actually finish; if init fails
    #    partway, everything printed above is a paper trail for manual
    #    cleanup, and 'uninstall' can still be run once a state file from
    #    a prior successful init exists).
    # ------------------------------------------------------------------
    # For link/copy mode skills_src_root is HARNESS_DIR (unchanged); for
    # submodule mode it's the submodule inside the target itself — record
    # *that* as the source, not HARNESS_DIR. A real consumer installing via
    # a submodule never has HARNESS_DIR's path on their machine at all; only
    # the submodule clone is theirs to track drift against.
    local source_revision
    source_revision="$(git -C "$skills_src_root" rev-parse HEAD 2>/dev/null || echo unknown)"
    local source_remote
    source_remote="$(git -C "$skills_src_root" remote get-url origin 2>/dev/null || true)"
    local skills_csv
    skills_csv="$(IFS=,; echo "${linked_skills[*]}")"
    state_write "$target" "$mode" "$skills_csv" "$skills_filter" "$with_hook" \
        "$profile" "$skills_src_root" "$source_revision" "$source_remote"

    echo "Done."
}

cmd_plan() {
    cmd_init "$@" --dry-run
}

# ----------------------------------------------------------------------------
# status
# ----------------------------------------------------------------------------

cmd_status() {
    local target="${1:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"
    require_state "$target"

    echo "agentharness install status for $target"
    echo "  mode:          $(state_field "$target" mode)"
    echo "  source path:   $(state_field "$target" source.path)"
    echo "  source rev:    $(state_field "$target" source.revision)"
    local remote
    remote="$(state_field "$target" source.remote 2>/dev/null || echo "(none)")"
    echo "  source remote: $remote"
    echo "  skills:        $(state_field "$target" skills)"
    echo "  with_hook:     $(state_field "$target" with_hook)"
    local profile
    profile="$(state_field "$target" profile 2>/dev/null || echo "(none)")"
    echo "  profile:       $profile"
    echo "  installed_at:  $(state_field "$target" installed_at)"
    echo "  updated_at:    $(state_field "$target" updated_at)"

    local source_path source_rev current_rev
    source_path="$(state_field "$target" source.path)"
    source_rev="$(state_field "$target" source.revision)"
    if [ -d "$source_path" ]; then
        current_rev="$(git -C "$source_path" rev-parse HEAD 2>/dev/null || echo unknown)"
        if [ "$current_rev" != "$source_rev" ] && [ "$current_rev" != "unknown" ]; then
            echo "  note: source has moved on ($source_rev -> $current_rev) — run 'audit' or 'update'"
        fi
    else
        echo "  note: source path no longer exists ($source_path) — 'update'/'doctor' will fail until it's restored"
    fi
}

# ----------------------------------------------------------------------------
# doctor
# ----------------------------------------------------------------------------

cmd_doctor() {
    local target="${1:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"
    require_state "$target"

    local failed=0
    echo "Checking agentharness install in $target..."

    local skills_csv
    skills_csv="$(state_field "$target" skills)"
    IFS=',' read -ra skills <<< "$skills_csv"
    for skill in "${skills[@]}"; do
        [ -z "$skill" ] && continue
        local dir="$target/.claude/skills/$skill"
        if [ ! -e "$dir/SKILL.md" ]; then
            echo "  ✗ $skill: SKILL.md not found at $dir" >&2
            failed=1
            continue
        fi
        echo "  ✓ $skill: SKILL.md present"
        local broken=0
        while IFS= read -r link; do
            if [ ! -e "$link" ]; then
                echo "  ✗ $skill: broken bundled-resource link: $link" >&2
                failed=1
                broken=1
            fi
        done < <(find -L "$dir" -type l 2>/dev/null)
        [ "$broken" -eq 0 ] && echo "  ✓ $skill: bundled resources resolve"
    done

    local with_hook
    with_hook="$(state_field "$target" with_hook)"
    if [ "$with_hook" = "true" ]; then
        local hooks_path
        hooks_path="$(git -C "$target" config --get core.hooksPath 2>/dev/null || true)"
        if [ -z "$hooks_path" ]; then
            echo "  ✗ with_hook is recorded true, but core.hooksPath is unset" >&2
            failed=1
        else
            echo "  ✓ core.hooksPath set ($hooks_path)"
        fi
    fi

    if [ -f "$target/.gitignore" ] && grep -qF "$GITIGNORE_MARKER" "$target/.gitignore"; then
        echo "  ✓ .gitignore contains the agentharness block"
    elif [ -f "$target/.gitignore" ]; then
        echo "  (info) .gitignore has no agentharness block — fine if the template had nothing new to add"
    fi

    local profile
    profile="$(state_field "$target" profile 2>/dev/null || echo "")"
    if [ -n "$profile" ] && [ "$profile" != "None" ]; then
        if [ -f "$target/$PROFILE_FILE_NAME" ] && [ "$(tr -d '[:space:]' < "$target/$PROFILE_FILE_NAME")" = "$profile" ]; then
            echo "  ✓ $PROFILE_FILE_NAME matches recorded profile ($profile)"
        else
            echo "  ✗ $PROFILE_FILE_NAME missing or doesn't match recorded profile ($profile)" >&2
            failed=1
        fi
    fi

    if [ "$failed" -ne 0 ]; then
        echo "doctor: FAILED — see ✗ items above."
        return 1
    fi
    echo "doctor: all checks passed."
}

# ----------------------------------------------------------------------------
# audit
# ----------------------------------------------------------------------------

cmd_audit() {
    local target="${1:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"
    require_state "$target"

    local source_path
    source_path="$(state_field "$target" source.path)"
    if [ ! -d "$source_path" ]; then
        echo "Error: recorded source path no longer exists: $source_path" >&2
        exit 1
    fi

    local skills_csv installed=()
    skills_csv="$(state_field "$target" skills)"
    IFS=',' read -ra installed <<< "$skills_csv"

    local available=()
    while IFS= read -r name; do available+=("$name"); done < <(list_available_skills "$source_path")

    echo "Skill drift for $target:"
    local found_drift=0
    for name in "${available[@]}"; do
        if ! printf '%s\n' "${installed[@]}" | grep -qxF "$name"; then
            echo "  + available upstream, not installed: $name"
            found_drift=1
        fi
    done
    for name in "${installed[@]}"; do
        [ -z "$name" ] && continue
        if ! printf '%s\n' "${available[@]}" | grep -qxF "$name"; then
            echo "  - installed, no longer available upstream: $name"
            found_drift=1
        fi
    done
    [ "$found_drift" -eq 0 ] && echo "  (none)"

    local source_rev current_rev
    source_rev="$(state_field "$target" source.revision)"
    current_rev="$(git -C "$source_path" rev-parse HEAD 2>/dev/null || echo unknown)"
    if [ "$current_rev" != "$source_rev" ] && [ "$current_rev" != "unknown" ] && git -C "$source_path" cat-file -e "$source_rev" 2>/dev/null; then
        echo ""
        echo "Commits in source since install ($source_rev..$current_rev):"
        git -C "$source_path" log --oneline "$source_rev..$current_rev" -- .claude/skills patterns languages 2>/dev/null | head -20 || true
    else
        echo ""
        echo "Source revision unchanged or not comparable ($source_rev)."
    fi
}

# ----------------------------------------------------------------------------
# update
# ----------------------------------------------------------------------------

confirm() {
    local yes="$1" prompt="$2"
    [ "$yes" = true ] && return 0
    read -r -p "$prompt [y/N] " reply
    [[ "$reply" =~ ^[Yy]$ ]]
}

cmd_update() {
    local target="" yes=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --yes) yes=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; exit 1; fi; shift ;;
        esac
    done
    target="${target:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"
    require_state "$target"

    local mode source_path skills_filter with_hook profile
    mode="$(state_field "$target" mode)"
    source_path="$(state_field "$target" source.path)"
    skills_filter="$(state_field "$target" skills_filter 2>/dev/null || echo "")"
    [ "$skills_filter" = "None" ] && skills_filter=""
    with_hook="$(state_field "$target" with_hook)"
    profile="$(state_field "$target" profile 2>/dev/null || echo "")"
    [ "$profile" = "None" ] && profile=""

    if [ ! -d "$source_path" ]; then
        echo "Error: recorded source path no longer exists: $source_path" >&2
        exit 1
    fi

    local skills_csv installed=()
    skills_csv="$(state_field "$target" skills)"
    IFS=',' read -ra installed <<< "$skills_csv"

    local current=()
    while IFS= read -r name; do current+=("$name"); done < <(resolve_wanted_skills "$source_path" "$skills_filter")

    local to_add=() to_remove=()
    for name in "${current[@]}"; do
        printf '%s\n' "${installed[@]}" | grep -qxF "$name" || to_add+=("$name")
    done
    for name in "${installed[@]}"; do
        [ -z "$name" ] && continue
        printf '%s\n' "${current[@]}" | grep -qxF "$name" || to_remove+=("$name")
    done

    local to_refresh=()
    if [ "$mode" = "copy" ]; then
        for name in "${current[@]}"; do
            if printf '%s\n' "${to_add[@]}" | grep -qxF "$name"; then
                continue
            fi
            if ! diff -rq "$source_path/.claude/skills/$name" "$target/.claude/skills/$name" >/dev/null 2>&1; then
                to_refresh+=("$name")
            fi
        done
    fi

    echo "Update plan for $target (mode: $mode):"
    [ "${#to_add[@]}" -gt 0 ] && printf '  + add: %s\n' "${to_add[@]}"
    [ "${#to_remove[@]}" -gt 0 ] && printf '  - remove: %s\n' "${to_remove[@]}"
    [ "${#to_refresh[@]}" -gt 0 ] && printf '  ~ content changed upstream: %s\n' "${to_refresh[@]}"

    if [ "${#to_add[@]}" -eq 0 ] && [ "${#to_remove[@]}" -eq 0 ] && [ "${#to_refresh[@]}" -eq 0 ]; then
        echo "  (nothing to do)"
        return 0
    fi

    confirm "$yes" "Apply this update?" || { echo "Aborted."; return 1; }

    for name in "${to_remove[@]}"; do
        local dst="$target/.claude/skills/$name"
        if [ -L "$dst" ] || [ -d "$dst" ]; then
            rm -rf "$dst"
        fi
        echo "  Removed: $name"
    done

    for name in "${current[@]}"; do
        local src="$source_path/.claude/skills/$name"
        local dst="$target/.claude/skills/$name"
        case "$mode" in
            link|submodule)
                [ -e "$dst" ] && [ ! -L "$dst" ] && continue
                [ -L "$dst" ] && rm "$dst"
                ln -s "$src" "$dst"
                ;;
            copy)
                rm -rf "$dst"
                # -L: dereference symlinks instead of copying them as
                # symlinks. Skills bundle relative symlinks back to
                # patterns/<name>/ (see P1-03) that only resolve from
                # inside this checkout; a plain `cp -r` would copy those
                # links literally into the target, where they point at a
                # patterns/ directory copy mode never creates.
                cp -rL "$src" "$dst"
                ;;
        esac
    done
    echo "  Re-synced ${#current[@]} skill(s)"

    local gitignore_template="$HARNESS_DIR/.github/.gitignore.template"
    local gitignore_dst="$target/.gitignore"
    if [ -f "$gitignore_template" ] && [ -f "$gitignore_dst" ]; then
        local new_entries
        new_entries="$(comm -23 \
            <(grep -vE '^\s*(#|$)' "$gitignore_template" | sort -u) \
            <(grep -vE '^\s*(#|$)' "$gitignore_dst" | sort -u))"
        if [ -n "$new_entries" ]; then
            { echo ""; echo "$GITIGNORE_MARKER"; echo "$new_entries"; } >> "$gitignore_dst"
            echo "  Merged new .gitignore entries"
        fi
    fi

    local source_revision
    source_revision="$(git -C "$source_path" rev-parse HEAD 2>/dev/null || echo unknown)"
    local source_remote
    source_remote="$(git -C "$source_path" remote get-url origin 2>/dev/null || true)"
    local new_skills_csv
    new_skills_csv="$(IFS=,; echo "${current[*]}")"
    state_write "$target" "$mode" "$new_skills_csv" "$skills_filter" "$with_hook" \
        "$profile" "$source_path" "$source_revision" "$source_remote"
    echo "Updated."
}

# ----------------------------------------------------------------------------
# uninstall
# ----------------------------------------------------------------------------

cmd_uninstall() {
    local target="" yes=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --yes) yes=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; exit 1; fi; shift ;;
        esac
    done
    target="${target:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"
    require_state "$target"

    local mode with_hook
    mode="$(state_field "$target" mode)"
    with_hook="$(state_field "$target" with_hook)"
    local skills_csv installed=()
    skills_csv="$(state_field "$target" skills)"
    IFS=',' read -ra installed <<< "$skills_csv"

    echo "This will remove from $target:"
    printf '  - skill: %s\n' "${installed[@]}"
    [ -f "$target/.gitignore" ] && grep -qF "$GITIGNORE_MARKER" "$target/.gitignore" && echo "  - the agentharness block in .gitignore"
    { [ "$with_hook" = "true" ]; } && echo "  - core.hooksPath (if still pointing at agentharness)"
    [ -f "$target/$PROFILE_FILE_NAME" ] && echo "  - $PROFILE_FILE_NAME"
    [ "$mode" = "submodule" ] && [ -e "$target/$SUBMODULE_PATH/.git" ] && echo "  - the $SUBMODULE_PATH submodule"
    echo "  - $STATE_FILE_NAME"

    confirm "$yes" "Proceed with uninstall?" || { echo "Aborted."; return 1; }

    for name in "${installed[@]}"; do
        [ -z "$name" ] && continue
        local dst="$target/.claude/skills/$name"
        if [ -L "$dst" ] || [ -d "$dst" ]; then
            rm -rf "$dst"
            echo "  Removed skill: $name"
        fi
    done

    if [ -f "$target/.gitignore" ] && grep -qF "$GITIGNORE_MARKER" "$target/.gitignore"; then
        # The merge always appends "" + marker + entries to the end of the
        # file and nothing else ever writes past that point, so truncating
        # at the marker's line number cleanly removes exactly what we added.
        local marker_line
        marker_line="$(grep -nF "$GITIGNORE_MARKER" "$target/.gitignore" | head -1 | cut -d: -f1)"
        head -n "$((marker_line - 1))" "$target/.gitignore" > "$target/.gitignore.tmp"
        mv "$target/.gitignore.tmp" "$target/.gitignore"
        echo "  Removed the agentharness block from .gitignore"
    fi

    if [ "$with_hook" = "true" ]; then
        git -C "$target" config --unset core.hooksPath 2>/dev/null || true
        echo "  Unset core.hooksPath"
    fi

    [ -f "$target/$PROFILE_FILE_NAME" ] && rm -f "$target/$PROFILE_FILE_NAME" && echo "  Removed $PROFILE_FILE_NAME"

    if [ "$mode" = "submodule" ] && [ -e "$target/$SUBMODULE_PATH/.git" ]; then
        git -C "$target" submodule deinit -f "$SUBMODULE_PATH" 2>/dev/null || true
        rm -rf "$target/.git/modules/$SUBMODULE_PATH"
        git -C "$target" rm -f "$SUBMODULE_PATH" 2>/dev/null || rm -rf "${target:?}/${SUBMODULE_PATH:?}"
        echo "  Removed the $SUBMODULE_PATH submodule"
    fi

    rm -f "$(state_path "$target")"
    echo "Uninstalled."
}

# ----------------------------------------------------------------------------
# Dispatch
# ----------------------------------------------------------------------------

case "${1:-}" in
    init|plan|status|doctor|audit|update|uninstall)
        cmd="$1"; shift
        ;;
    -h|--help)
        usage; exit 0
        ;;
    "")
        echo "Error: subcommand or target project directory is required." >&2
        usage
        exit 1
        ;;
    *)
        # Legacy invocation: harness-link.sh <target-dir> [options] == init
        cmd="init"
        ;;
esac

"cmd_$cmd" "$@"
