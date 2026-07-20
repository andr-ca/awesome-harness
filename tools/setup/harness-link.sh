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
#             since install; the target's selected profile and whether
#             its publish-authority flag is active (B5); whether the
#             recorded harness checkout's own validation commands still
#             exist. --json for machine-readable output (CI/scripting).
#             Does not run policy-conflict detection itself — points at
#             'python3 tools/verify-content-quality.py' instead (B7).
#   enforce-profile
#             Read .agentharness-profile and gate on it for real for a
#             detected Python (pytest --cov-fail-under), Go (go test +
#             go tool cover), or Vitest JS/TS project at the selected
#             tier's coverage_min; skips entirely if the tier doesn't
#             require tests. An unrecognized project type or JS runner
#             (Jest/Mocha) reports "not implemented yet" and exits 0
#             rather than falsely passing or blocking — pass --strict to
#             make that a failure instead (for a CI job that must cover
#             every project). Not wired into pre-push automatically;
#             invoke it explicitly, same as audit/doctor.
#   generate-clients
#             Run the client-adapter generators into the target so one
#             command produces the router/instruction files for the tools
#             it uses (--client codex|gemini|copilot|cursor|kilo|all).
#             Standalone, like enforce-profile; not yet wired into
#             init/update or tracked in state for uninstall (P1-01).
#   update    Re-sync an existing install to the current harness state.
#   uninstall Reverse everything 'init' recorded.
#
# All subcommands operate on a target project directory (default: '.').
# State is tracked in <target>/.agentharness-state.json, written by init and
# read by every other subcommand — a project not initialized through this
# CLI won't have one; run 'init' first.
#
# Install modes (--mode, init/update only):
#   copy       (default) Physically copy skill files into the target. No
#              dependency on this checkout persisting or staying at the
#              same path — portable across machines and safe to commit
#              and clone elsewhere. Content is a snapshot; re-run
#              'update' to pull in upstream changes.
#   link       Symlink skills from this harness checkout instead of
#              copying. Always current with zero re-sync step, but the
#              symlinks are absolute paths anchored to *this exact
#              checkout's location on this machine* — they break for
#              anyone who clones the target elsewhere, or if this
#              checkout moves (see issue #106). Use only when you're
#              actively co-developing the harness itself alongside a
#              project on the same machine; not recommended for
#              anything you'll commit and share.
#   submodule  Add this harness as a git submodule at <target>/.agentharness
#              (version-pinned in the target's own history) and symlink
#              skills from there instead of this checkout.
#   npm        Copy this checkout into <target>/.agentharness-pkg (a durable
#              local copy, gitignored) and symlink skills from there instead
#              of this checkout. This is what the npm/npx CLI shim
#              (bin/cli.js) defaults 'init'/'plan' to when no --mode is
#              given — its own HARNESS_DIR is an ephemeral npx cache/temp
#              extraction, so 'link' would silently break on cache cleanup.
#
# Migrating an existing --mode link install to --mode copy (or any other
# mode): just re-run init with the new --mode against the same target —
# it materializes the new mode's install fresh and re-records state,
# no uninstall step needed. See docs/INTEGRATION.md's "Migrating from
# link mode" section.
#
# Requires python3 (used for reading/writing the JSON state file).
# ============================================================================

set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_FILE_NAME=".agentharness-state.json"
PROFILE_FILE_NAME=".agentharness-profile"
GITIGNORE_MARKER="# --- Added by agentharness harness-link.sh ---"
SUBMODULE_PATH=".agentharness"
NPM_DURABLE_PATH=".agentharness-pkg"
# Every installed skill is mirrored under both directories: .claude/skills
# for Claude Code, .agents/skills for Codex CLI's real on-demand skill
# discovery (the Agent Skills open standard both clients now share — see
# tools/generate-agents-md.sh's header for the P0-06 rationale). Same
# source, same SKILL.md, two directories a client scans natively.
SKILL_DEST_SUBDIRS=(".claude/skills" ".agents/skills")

usage() {
    cat <<EOF
Usage: $(basename "$0") <subcommand> [target-project-dir] [OPTIONS]
       $(basename "$0") <target-project-dir> [OPTIONS]   (legacy: same as init)

Subcommands: init, plan, status, doctor, audit, audit-prs, enforce-profile, generate-clients, update, uninstall

init options:
  --mode link|copy|submodule|npm
                                Install mode (default: copy; the npm/npx
                                CLI shim defaults to npm instead — see
                                docs/INTEGRATION.md#method-4-npmnpx)
  --skills a,b,c               Comma-separated list of skills (default:
                                all; 'none' explicitly installs zero)
  --with-hook                   Install the trunk-protection hook (blocks
                                direct commits to trunk branches). Does NOT
                                enforce coverage on its own — see
                                --with-coverage-hook for that (P0-03).
  --with-coverage-hook          Like --with-hook, plus a generated
                                pre-push hook that runs 'enforce-profile'
                                against this project on every push
  --force                       Overwrite an existing, different core.hooksPath;
                                also auto-overwrite whole-file collisions
                                without prompting
  --profile prototype|internal|production
                                Write .agentharness-profile
  --dry-run                     Show the plan; change nothing (same as 'plan');
                                reports whole-file collisions without resolving
  --keep-existing               Auto-keep all whole-file collisions (do not
                                overwrite pre-existing surfaces)

update options:
  --yes                         Skip the confirmation prompt
  --force                       Auto-overwrite whole-file collisions without prompting
  --dry-run                     Show what would happen, make no changes
  --keep-existing               Auto-keep all whole-file collisions

uninstall options:
  --yes                         Skip the confirmation prompt

audit options:
  --json                        Machine-readable drift report (CI/scripting)

audit-prs options:
  (no options)                  Lists open PRs with stale unaddressed comments.
                                Exit 0 if none found; exit 1 if any flagged.

enforce-profile options:
  --strict                      Fail (non-zero) on a project type or test
                                runner enforcement doesn't support, instead
                                of the default non-blocking exit 0

generate-clients options:
  --client codex|gemini|copilot|cursor|kilo|all
                                Which client router/instruction files to
                                generate into the target (default: all).
                                Comma-separated list also accepted.
  --dry-run                       Show what would be created/updated/skipped; no files written.
  --force                         Overwrite pre-existing non-harness files (prints WARNING per file).

Examples:
  $(basename "$0") init ~/my-project --with-hook
  $(basename "$0") init ~/my-project --mode copy --skills committing,branching
  $(basename "$0") status ~/my-project
  $(basename "$0") doctor ~/my-project
  $(basename "$0") audit ~/my-project --json
  $(basename "$0") audit-prs
  $(basename "$0") enforce-profile ~/my-project
  $(basename "$0") enforce-profile ~/my-project --strict
  $(basename "$0") generate-clients ~/my-project --client copilot,cursor
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
    # $10=hooks_path(or "" — the exact core.hooksPath value this CLI actually
    #     set; only present when with_hook installation genuinely succeeded)
    # $11=coverage_hook(true/false — P0-03, whether the generated
    #     enforce-profile-calling pre-push script was actually installed)
    # $12=previous_hooks_path(or "" — the core.hooksPath value that existed
    #     before this install; restored on uninstall when present)
    local target="$1" mode="$2" skills_csv="$3" skills_filter="$4" with_hook="$5"
    local profile="$6" source_path="$7" source_revision="$8" source_remote="$9"
    local hooks_path="${10:-}" coverage_hook="${11:-false}" previous_hooks_path="${12:-}"
    local existing_installed_at=""
    if [ -f "$(state_path "$target")" ]; then
        existing_installed_at="$(state_field "$target" "installed_at" || true)"
    fi
    AH_MODE="$mode" AH_SKILLS_CSV="$skills_csv" AH_SKILLS_FILTER="$skills_filter" \
    AH_WITH_HOOK="$with_hook" AH_PROFILE="$profile" AH_SOURCE_PATH="$source_path" \
    AH_SOURCE_REVISION="$source_revision" AH_SOURCE_REMOTE="$source_remote" \
    AH_HOOKS_PATH="$hooks_path" AH_COVERAGE_HOOK="$coverage_hook" \
    AH_PREVIOUS_HOOKS_PATH="$previous_hooks_path" \
    AH_EXISTING_INSTALLED_AT="$existing_installed_at" \
    python3 - "$(state_path "$target")" <<'PYEOF'
import datetime
import json
import os
import sys
from pathlib import Path

path = sys.argv[1]
skills_csv = os.environ.get("AH_SKILLS_CSV", "")
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
existing_installed_at = os.environ.get("AH_EXISTING_INSTALLED_AT") or now

# Preserve v2 fields from existing state if present
v2_fields = {}
if Path(path).exists():
    try:
        existing = json.loads(Path(path).read_text())
        for field in ("managed_blocks", "collision_decisions", "overwritten_files"):
            if field in existing:
                v2_fields[field] = existing[field]
    except (OSError, json.JSONDecodeError):
        pass

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
    "hooks_path": os.environ.get("AH_HOOKS_PATH") or None,
    "previous_hooks_path": os.environ.get("AH_PREVIOUS_HOOKS_PATH") or None,
    "coverage_hook": os.environ.get("AH_COVERAGE_HOOK") == "true",
    "profile": os.environ.get("AH_PROFILE") or None,
    "installed_at": existing_installed_at,
    "updated_at": now,
}
# Merge in v2 fields if they exist
data.update(v2_fields)
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
}

# Repo-level install lock — excludes concurrent init/update runs against the
# SAME target repo (spec section 6). Distinct from tools/agent-lock.sh,
# which coordinates branches inside the harness repo itself; this lock lives
# inside the consumer's own repo and has no branch/feature concept.

install_lock_path() { echo "$1/.agentharness-install.lock"; }

acquire_install_lock() {
    local target="$1"
    local lock_dir
    lock_dir="$(install_lock_path "$target")"
    if ! mkdir "$lock_dir" 2>/dev/null; then
        echo "Error: another agentharness install/update is already in progress in $target (lock: $lock_dir)." >&2
        echo "If no other process is actually running, remove the lock directory manually and retry." >&2
        return 1
    fi
    echo "$$" > "$lock_dir/pid" 2>/dev/null || true
    return 0
}

release_install_lock() {
    local target="$1"
    rm -rf "$(install_lock_path "$target")"
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
#
# Used by 'update' (upstream skill removal between install and update is
# legitimate drift, not a typo, so update tolerates it and just skips) and by
# 'init'/'plan' AFTER validate_skills_filter has already confirmed every name
# is valid — at that point this never actually skips anything for init, it's
# just the shared resolution logic.
resolve_wanted_skills() {
    local skills_src_root="$1" filter="$2"
    [ "$filter" = "none" ] && return 0
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

# Hard-fail validator for init/plan (P0-04): a typo or path-traversal attempt
# in an explicit --skills list used to be silently dropped, producing a
# "successful" install with zero skills and no way for automation to tell
# that apart from a real, intentional empty install. Checked BEFORE any
# filesystem mutation — an invalid name aborts the whole command, atomically.
# An explicit filter of exactly "none" is the one sanctioned way to request
# zero skills; anything else that resolves to nothing is treated as an error.
validate_skills_filter() {
    local skills_src_root="$1" filter="$2"
    [ "$filter" = "none" ] && return 0
    [ -z "$filter" ] && return 0
    local wanted=()
    IFS=',' read -ra wanted <<< "$filter"
    local bad=0
    for skill in "${wanted[@]}"; do
        case "$skill" in
            */*|.*|'')
                echo "Error: invalid skill name: '$skill' (must be a plain directory name, no path separators or leading dot)" >&2
                bad=1
                continue
                ;;
        esac
        if [ ! -d "$skills_src_root/.claude/skills/$skill" ]; then
            echo "Error: unknown skill: '$skill' (no directory under .claude/skills/)" >&2
            bad=1
        fi
    done
    return "$bad"
}

# ----------------------------------------------------------------------------
# npm durable source (P0-02)
# ----------------------------------------------------------------------------

# Copies HARNESS_DIR into <target>/$NPM_DURABLE_PATH, excluding .git — the
# npm-installed package tree HARNESS_DIR points at when invoked via the npm
# CLI shim has already been pruned to package.json's "files" allowlist by npm
# itself, so this is a small, self-contained copy, not the whole dev repo.
copy_npm_durable_source() {
    local target="$1"
    local dst="${target:?copy_npm_durable_source: target must not be empty}/$NPM_DURABLE_PATH"
    rm -rf "$dst"
    mkdir -p "$dst"
    # Exclude the durable-copy directory itself from the tar source: if
    # 'target' is HARNESS_DIR or a subdirectory of it (e.g. dogfooding this
    # harness's own repo as an init target), the freshly-created, empty
    # $dst would otherwise sit inside the tree being read, and get read
    # back into itself mid-stream. Compute the exclude path relative to
    # HARNESS_DIR (not just "./$NPM_DURABLE_PATH", which only matches when
    # target IS HARNESS_DIR) so a target that's a subdirectory of
    # HARNESS_DIR is covered too.
    local tar_exclude="./$NPM_DURABLE_PATH"
    case "$dst" in
        "$HARNESS_DIR"/*)
            tar_exclude="./${dst#"$HARNESS_DIR"/}"
            ;;
    esac
    # Explicitly exclude sensitive/ephemeral files that npm pack's "files"
    # allowlist has already pruned from a registry tarball but that may
    # exist in a dev-checkout source (where this copy runs via 'npm mode').
    # Without these excludes, an untracked .env* or a cache directory
    # would silently land in every consumer's .agentharness-pkg/.
    (cd "$HARNESS_DIR" && tar cf -         --exclude=.git         --exclude="$tar_exclude"         --exclude=".env"         --exclude=".env.*"         --exclude="*.env"         --exclude="node_modules"         --exclude=".cache"         --exclude="__pycache__"         --exclude="*.pyc"         --exclude=".worktrees"         .) | (cd "$dst" && tar xf -)
}

# Prefers package.json's version (meaningful for an npm-distributed source —
# "0.2.0" tells a consumer far more than a git SHA they can't independently
# look up) and falls back to a git revision for link/copy/submodule modes,
# whose skills_src_root is a real git checkout.
source_revision_for() {
    local src_root="$1" mode="$2"
    if [ "$mode" = "npm" ] && [ -f "$src_root/package.json" ]; then
        # Pass src_root as argv, not interpolated into the Python source —
        # a path containing a quote or backslash would otherwise break out
        # of the embedded string literal.
        python3 -c "
import json, sys
with open(sys.argv[1] + '/package.json') as f:
    print(json.load(f)['version'])
" "$src_root" 2>/dev/null && return
    fi
    git -C "$src_root" rev-parse HEAD 2>/dev/null || echo unknown
}

# ----------------------------------------------------------------------------
# Coverage-aware pre-push hook (P0-03, opt-in via --with-coverage-hook)
# ----------------------------------------------------------------------------
#
# --with-hook alone only ever installed trunk-protection for a consumer —
# the shared pre-push script this harness uses for ITSELF is hardcoded to
# test agentharness's own suites and deliberately no-ops for any other repo
# (see .github/hooks/pre-push's own comments). Calling that combination
# "coverage hooks" in docs/CLI output was therefore never accurate for a
# consumer. This generates a real, consumer-owned pre-push script instead —
# unlike prevent-trunk-commit/pre-commit (universal, safe to copy verbatim),
# this one is written fresh per install because it has to call
# 'enforce-profile' against THIS target, using a harness-link.sh path that's
# only known at install time.
#
# A marker string ("agentharness generated coverage hook") lets doctor
# confirm the file at $target/.github/hooks/pre-push is genuinely this
# generated script and not something else that happens to share the name.
COVERAGE_HOOK_MARKER="# agentharness generated coverage hook — do not hand-edit, regenerate with 'init --with-coverage-hook'"

generate_coverage_pre_push() {
    local target="$1" harness_link_path="$2"
    # %q-quote the path before embedding it in the GENERATED script's
    # HARNESS_LINK=... assignment (unquoted on the left so %q's own
    # quoting, only added when actually needed, is what governs it) — an
    # unescaped path containing shell metacharacters (e.g. a checkout
    # directory renamed to include "$(...)") would otherwise be evaluated
    # as a command when the hook later runs.
    local harness_link_quoted
    printf -v harness_link_quoted '%q' "$harness_link_path"
    cat > "$target/.github/hooks/pre-push" <<EOF
#!/bin/bash
$COVERAGE_HOOK_MARKER
set -euo pipefail

TARGET_ROOT="\$(git rev-parse --show-toplevel)"
HARNESS_LINK=$harness_link_quoted

if [ ! -f "\$HARNESS_LINK" ]; then
    echo "agentharness coverage hook: harness-link.sh not found at \$HARNESS_LINK" >&2
    echo "(the recorded harness source may have moved or been deleted — run 'doctor' to check, or re-run 'init --with-coverage-hook' to regenerate this hook)." >&2
    exit 1
fi

exec bash "\$HARNESS_LINK" enforce-profile "\$TARGET_ROOT"
EOF
    chmod +x "$target/.github/hooks/pre-push"
}

# Managed-block rendering and collision handling — renders core-instructions
# block into existing instructions files and handles whole-file collisions
# on directory-style generated surfaces. Wired into cmd_init (Task 12) and
# cmd_update (Task 13).

render_core_instructions_block() {
    local target="$1" skills_csv="$2"
    local skills_list
    skills_list="$(echo "$skills_csv" | tr ',' '\n' | sed 's/^/- /')"
    cat <<EOF
This project uses [agentharness](https://github.com/andr-ca/agentharness)
for engineering policies (git conventions, testing, review workflow).

**Precedence:** harness-enforced constraints (hooks, completion gate)
cannot be weakened by this file's instructions; this file's own
instructions take precedence over harness *defaults* everywhere else.

Installed skills:
$skills_list

If a skill above looks empty, missing, or won't load, this install may
be broken (e.g. a moved/renamed harness checkout, or a fresh clone of
a project that used \`--mode link\` — see issue #106) — run
\`harness-link.sh doctor <this-project-path>\` from the harness
checkout to check, and \`$STATE_FILE_NAME\` in this project to see how
it was installed.

**Git conventions** (from the \`branching\`/\`committing\` skills above —
stated here directly so they hold even if a skill is unreadable): never
commit directly to a trunk branch (\`main\`/\`master\`/\`release/*\`);
create a feature branch first (\`git checkout -b <type>/<short-description>\`);
open a PR for review before merging into the trunk branch.

**PR merge checklist:** never merge on green CI alone. Wait for
automated review (e.g. GitHub Copilot) to post *or* its check-run to
reach a completed state before proceeding; reply to every review
comment (issue-level and inline) with what you did about it; then
watch the post-merge CI run on the base branch to an actual terminal
state — "pushed"/"merged" and "verified green" are different claims,
only the second means done. If this checkout has agentharness's own
\`tools/safe-pr-merge.sh\` available (see its INTEGRATION.md section),
prefer it over doing these steps by hand — it enforces the sequence.

Full policy: see the harness's own CLAUDE.md via your install mode, or
https://github.com/andr-ca/agentharness/blob/main/CLAUDE.md
EOF
}

build_surfaces_spec() {
    local target="$1" block_body="$2" block_version="$3"
    python3 -c "
import json, sys
target, body, version = sys.argv[1], sys.argv[2], sys.argv[3]
block_files = ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md', '.github/copilot-instructions.md']
print(json.dumps([
    {'path': f'{target}/{f}', 'is_block_surface': True, 'block_body': body,
     'block_id': 'core-instructions', 'block_version': version}
    for f in block_files
]))
" "$target" "$block_body" "$block_version"
}

resolve_collisions_and_apply() {
    local target="$1" surfaces_json="$2" install_id="$3" force="$4" dry_run="$5" keep_existing="$6"

    # Step 1: Plan the installation (identifies collisions)
    local plan_result
    plan_result="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" plan \
        --surfaces <(echo "$surfaces_json") \
        --state "$(state_path "$target")" \
        --base-dir "$target" --install-id "$install_id" 2>&1)" || {
        echo "Error: existing-surface planning failed:" >&2
        echo "$plan_result" >&2
        return 1
    }

    # Extract the collisions list from the plan result
    local collisions
    collisions="$(echo "$plan_result" | python3 -c "
import json, sys
plan = json.load(sys.stdin)
collisions = plan.get('collisions', [])
for c in collisions:
    print(c)
" 2>/dev/null)"

    # --dry-run must never call 'apply' — regardless of whether there
    # are any collisions. This check used to live only inside the
    # collisions branch below, which meant the common case (a plan with
    # zero whole-file collisions, e.g. just the four block-managed
    # instructions files) fell through to the unconditional "no
    # collisions, just apply" branch further down and silently mutated
    # the target even under --dry-run.
    if [ "$dry_run" = true ]; then
        if [ -n "$collisions" ]; then
            echo "  File collisions (would prompt for resolution in normal mode):"
            echo "$collisions" | sed 's/^/    - /'
        fi
        echo "$plan_result" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for a in d["actions"]:
    kind = a["kind"]
    path = a["path"]
    print(f"  {kind}: {path}")
'
        return 0
    fi

    # If there are collisions, resolve them
    if [ -n "$collisions" ]; then
        # Build the decisions map based on user preferences
        local decisions_json="{}"
        local collision_count=0
        local report_only_paths=()

        # Set up fd 3 for reading prompts (stdin in the main shell context)
        exec 3<&0

        # Process each collision
        while IFS= read -r collision_path; do
            [ -z "$collision_path" ] && continue
            collision_count=$((collision_count + 1))

            local decision
            if [ "$force" = true ]; then
                decision="overwrite"
            elif [ "$keep_existing" = true ]; then
                decision="keep-existing"
            else
                # Interactive prompt via fd 3
                local reply
                if ! read -u 3 -r -p "Collision: $collision_path — [o]verwrite/[k]eep/[a]ll-overwrite/[n]one? " reply 2>/dev/null; then
                    # EOF on stdin in non-interactive mode without --force/--keep-existing:
                    # collect the path and report error after loop
                    report_only_paths+=("$collision_path")
                    continue
                fi
                case "$reply" in
                    o|overwrite) decision="overwrite" ;;
                    k|keep) decision="keep-existing" ;;
                    a|all)
                        decision="overwrite"
                        force=true  # Switch to --force mode for remaining collisions
                        ;;
                    n|none)
                        decision="keep-existing"
                        keep_existing=true  # Switch to --keep-existing mode
                        ;;
                    *)
                        echo "Invalid choice. Using default (keep-existing)."
                        decision="keep-existing"
                        ;;
                esac
            fi

            # Add the decision to the JSON map
            decisions_json="$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
data[sys.argv[2]] = sys.argv[3]
print(json.dumps(data))
" "$decisions_json" "$collision_path" "$decision")"
        done <<< "$collisions"

        # Close fd 3
        exec 3<&-

        # If there are unresolved collisions from EOF, report and fail
        if [ "${#report_only_paths[@]}" -gt 0 ]; then
            echo "Error: stdin closed without resolving collisions. Use --force, --keep-existing, or provide responses interactively:" >&2
            printf '  - %s\n' "${report_only_paths[@]}" >&2
            return 1
        fi

        if [ "$collision_count" -gt 0 ]; then
            echo "  Resolved $collision_count collision(s)"
        fi

        # Write decisions to a temporary file for apply
        local decisions_file
        decisions_file="$(mktemp)"
        echo "$decisions_json" > "$decisions_file"

        # Step 2: Apply the installation with the decisions
        local apply_result
        apply_result="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" apply \
            --surfaces <(echo "$surfaces_json") \
            --state "$(state_path "$target")" \
            --base-dir "$target" --install-id "$install_id" \
            --journal "$target/.agentharness-state.pending.json" \
            --decisions "$decisions_file" 2>&1)" || {
            echo "Error: existing-surface apply failed:" >&2
            echo "$apply_result" >&2
            rm -f "$decisions_file"
            return 1
        }

        rm -f "$decisions_file"
    else
        # No collisions, just apply
        local apply_result
        apply_result="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" apply \
            --surfaces <(echo "$surfaces_json") \
            --state "$(state_path "$target")" \
            --base-dir "$target" --install-id "$install_id" \
            --journal "$target/.agentharness-state.pending.json" 2>&1)" || {
            echo "Error: existing-surface apply failed:" >&2
            echo "$apply_result" >&2
            return 1
        }
    fi

    return 0
}

# Print a visibility note if init/update left untracked files behind
# (issue #88): a fresh install can write dozens of files (skills,
# generated instruction docs, state files) straight into the target's
# working tree, and nothing about the process stages or commits them.
# Left silent, that content is invisible to every other clone, PR, or CI
# run of the consumer's own repo until someone happens to run 'git
# status' — this is a message only, deliberately not an auto-'git add':
# silently staging is its own footgun (surprising diffs, or sweeping in
# unrelated pre-existing untracked files this run didn't create).
warn_if_untracked() {
    local target="$1"
    local dry_run="$2"

    if [ "$dry_run" = true ]; then
        return 0
    fi

    if ! git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        return 0
    fi

    local untracked_count
    untracked_count="$(git -C "$target" status --porcelain --untracked-files=all 2>/dev/null | grep -c '^??' || true)"

    if [ "${untracked_count:-0}" -gt 0 ]; then
        echo ""
        echo "Note: $untracked_count untracked file(s) in $target after this install."
        echo "  Skills, generated instruction docs, and state files just written here"
        echo "  aren't part of your repo's history until committed — review with"
        echo "  'git status' and 'git add' them, or they stay invisible to every"
        echo "  other clone, PR, and CI run of this repo."
    fi
}

# ----------------------------------------------------------------------------
# init / plan
# ----------------------------------------------------------------------------

cmd_init() {
    local target="" mode="copy" skills_filter="" with_hook=false force=false
    local profile="" dry_run=false coverage_hook=false keep_existing=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --mode) mode="$2"; shift 2 ;;
            --skills) skills_filter="$2"; shift 2 ;;
            --with-hook) with_hook=true; shift ;;
            --with-coverage-hook) with_hook=true; coverage_hook=true; shift ;;
            --force) force=true; shift ;;
            --profile) profile="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            --keep-existing) keep_existing=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *)
                if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; usage; exit 1; fi
                shift
                ;;
        esac
    done
    target="${target:-.}"

    case "$mode" in
        link|copy|submodule|npm) ;;
        *) echo "Error: --mode must be link, copy, submodule, or npm (got: $mode)" >&2; exit 1 ;;
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

    # P0-04: validate before any mutation (including before the dry-run
    # branch below, so 'plan' reports the same failure 'init' would rather
    # than silently planning an empty install). For submodule mode this is
    # only a first pass against HARNESS_DIR, not the final word — the
    # submodule's pinning can fall back to the remote's default branch (see
    # below) when this checkout's exact commit isn't reachable, which can
    # leave the submodule with a different skill set than HARNESS_DIR. A
    # second validation runs after the submodule/npm source is finalized,
    # against whatever skills_src_root actually ends up being.
    if ! validate_skills_filter "$skills_src_root" "$skills_filter"; then
        echo "Error: one or more requested skill names are invalid or unknown — aborting before making any changes." >&2
        echo "Use --skills none to explicitly install zero skills." >&2
        exit 1
    fi

    if [ "$dry_run" = true ]; then
        echo "Plan for 'init' on $target (mode: $mode):"
        echo "  Skills to install:"
        resolve_wanted_skills "$skills_src_root" "$skills_filter" | sed 's/^/    - /'
        echo "  .gitignore: merge $HARNESS_DIR/.github/.gitignore.template (additive)"
        if [ "$coverage_hook" = true ]; then
            echo "  Hook: install trunk-protection + a generated coverage-aware pre-push hook (real files under .github/hooks, regardless of --mode)"
        elif [ "$with_hook" = true ]; then
            echo "  Hook: install trunk-protection hook only — not coverage (mode: $mode; see --with-coverage-hook)"
        fi
        [ -n "$profile" ] && echo "  Profile: write $PROFILE_FILE_NAME = $profile"
        echo "  Managed blocks: update CLAUDE.md, AGENTS.md, GEMINI.md, .github/copilot-instructions.md"
        echo "  State: write $target/$STATE_FILE_NAME"
        echo "(dry run — nothing was changed)"
        return 0
    fi

    echo "Initializing agentharness ($HARNESS_DIR) into $target (mode: $mode)"

    local submodule_newly_added=false
    if [ "$mode" = "submodule" ]; then
        if ! git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            echo "Error: --mode submodule requires $target to be a git repo." >&2
            exit 1
        fi
        # The submodule remote defaults to this checkout's own 'origin',
        # but AGENTHARNESS_SUBMODULE_REMOTE overrides it — used by the
        # hermetic tests to point at a local bare clone instead of the
        # network origin (P1-05), and usable by a consumer who wants to
        # pin against a mirror rather than the canonical remote.
        local harness_remote
        harness_remote="${AGENTHARNESS_SUBMODULE_REMOTE:-$(git -C "$HARNESS_DIR" remote get-url origin 2>/dev/null || true)}"
        if [ -z "$harness_remote" ]; then
            echo "Error: --mode submodule requires this harness checkout to have an 'origin' remote (or AGENTHARNESS_SUBMODULE_REMOTE set)." >&2
            exit 1
        fi
        if [ ! -e "$target/$SUBMODULE_PATH/.git" ]; then
            git -C "$target" submodule add "$harness_remote" "$SUBMODULE_PATH"
            submodule_newly_added=true
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

    # P0-02: 'npm' mode exists for the npx/npm install path, whose default
    # HARNESS_DIR is an npx cache/temp extraction — not a durable, user-owned
    # location. Rather than symlink into that ephemeral path (the original
    # bug: a later cache cleanup silently breaks every installed skill),
    # copy HARNESS_DIR into a durable, version-pinned directory inside the
    # consumer itself, then symlink skills from THAT — same mechanics as
    # submodule mode's "durable local copy, then link from it" pattern, just
    # populated by a plain file copy instead of a git clone (an npx-invoked
    # HARNESS_DIR is frequently not its own git repo at all).
    if [ "$mode" = "npm" ]; then
        copy_npm_durable_source "$target"
        skills_src_root="$target/$NPM_DURABLE_PATH"
        hooks_src_dir="$target/$NPM_DURABLE_PATH/.github/hooks"
    fi

    # Second validation pass (Copilot review, PR #19): the first pass above
    # ran against HARNESS_DIR before skills_src_root could have changed. For
    # submodule mode specifically, a fallback to the remote's default branch
    # (see the comment above) can leave the submodule with a different skill
    # set than HARNESS_DIR had — re-checking here against the now-final
    # skills_src_root is what actually keeps P0-04's atomicity guarantee
    # true for every mode, not just the modes where skills_src_root never
    # changes after the first check.
    if ! validate_skills_filter "$skills_src_root" "$skills_filter"; then
        echo "Error: one or more requested skill names are invalid or unknown in the resolved source ($skills_src_root)." >&2
        echo "For --mode submodule, this can happen when the submodule's pin fell back to the remote's default branch instead of this checkout's exact commit — check the messages above." >&2
        # Roll back whatever this invocation itself just created, so a
        # failed init really does leave nothing behind (P0-04's atomicity
        # guarantee applies to this check's own failure path too, not just
        # to the checks that ran before any mutation).
        if [ "$mode" = "npm" ]; then
            rm -rf "${target:?}/${NPM_DURABLE_PATH:?}"
            echo "  Rolled back: removed the durable npm copy this run created." >&2
        elif [ "$mode" = "submodule" ] && [ "$submodule_newly_added" = true ]; then
            git -C "$target" submodule deinit -f -- "$SUBMODULE_PATH" 2>/dev/null || true
            git -C "$target" rm -f "$SUBMODULE_PATH" 2>/dev/null || true
            rm -rf "${target:?}/.git/modules/${SUBMODULE_PATH:?}"
            echo "  Rolled back: removed the submodule this run added." >&2
        fi
        exit 1
    fi

    # ------------------------------------------------------------------
    # 1. Skills
    # ------------------------------------------------------------------
    local linked_skills=()

    while IFS= read -r skill; do
        linked_skills+=("$skill")
        for dest_subdir in "${SKILL_DEST_SUBDIRS[@]}"; do
            local skills_dst="$target/$dest_subdir"
            mkdir -p "$skills_dst"
            local src="$skills_src_root/.claude/skills/$skill"
            local dst="$skills_dst/$skill"
            case "$mode" in
                link|submodule|npm)
                    if [ -L "$dst" ]; then
                        rm "$dst"
                    elif [ -e "$dst" ]; then
                        echo "  Skipping $skill ($dest_subdir): $dst exists and is not a symlink (not overwriting)" >&2
                        continue
                    fi
                    ln -s "$src" "$dst"
                    echo "  Linked skill: $skill ($dest_subdir)"
                    ;;
                copy)
                    rm -rf "$dst"
                    cp -rL "$src" "$dst"
                    echo "  Copied skill: $skill ($dest_subdir)"
                    ;;
            esac
        done
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
    # installed_hooks_path is the source of truth for what state_write records
    # (P0-01): it's only ever set on a branch that actually wrote
    # core.hooksPath, never from the --with-hook flag's intent alone. A
    # declined install (conflicting existing hooksPath, no --force) must
    # record with_hook=false — otherwise doctor/uninstall later believe the
    # harness owns a hook path it never touched, and uninstall would
    # unconditionally unset a config value that predates this install.
    local installed_hooks_path=""
    if [ "$with_hook" = true ]; then
        if ! git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            echo "  --with-hook requested but $target is not a git repo — skipping." >&2
            with_hook=false
            coverage_hook=false
        else
            local hooks_path
            # --with-coverage-hook needs a real, consumer-owned pre-push
            # script (P0-03) — it can't be the harness's own shared/symlinked
            # pre-push (that one is hardcoded to test agentharness itself and
            # deliberately no-ops for any other repo). So coverage_hook forces
            # real-file hook installation into target/.github/hooks the same
            # way --mode copy already does, regardless of what --mode is.
            if [ "$mode" = "copy" ] || [ "$coverage_hook" = true ]; then
                hooks_path="$target/.github/hooks"
            else
                hooks_path="$hooks_src_dir"
            fi
            # Decide whether this install will actually own core.hooksPath
            # BEFORE writing any hook files (Copilot review): generating/
            # copying files first and only then discovering a conflicting
            # existing core.hooksPath left real filesystem side effects
            # behind on a declined install, even though with_hook/
            # coverage_hook were correctly recorded as false.
            local existing_hooks_path existing_hooks_abs
            existing_hooks_path="$(git -C "$target" config --get core.hooksPath 2>/dev/null || true)"
            existing_hooks_abs="$existing_hooks_path"
            # core.hooksPath may be recorded as a relative path (git resolves
            # it relative to the work tree root at run time) — comparing that
            # raw string against our always-absolute $hooks_path would treat
            # an equivalent, already-correct hooksPath as a conflict. Resolve
            # it to an absolute path first (Copilot review).
            if [ -n "$existing_hooks_path" ]; then
                case "$existing_hooks_path" in
                    /*) ;;
                    # $target is already an absolute, canonicalized path
                    # (resolved via cd+pwd earlier in cmd_init), so plain
                    # concatenation is enough for the realistic case (a
                    # plain relative path with no './'/'../' segments) —
                    # don't require the directory to already exist (a
                    # cd-based resolution would silently fall through to
                    # the raw string on a brand-new repo's first install,
                    # since .github/hooks doesn't exist yet at that point).
                    *) existing_hooks_abs="$target/$existing_hooks_path" ;;
                esac
                # Normalize away './'/trailing-slash/'..' differences (e.g.
                # "./.github/hooks" or "$target/.github/hooks/") that would
                # otherwise still fail this string comparison even though
                # git resolves them to the same directory (Copilot review,
                # round 4). Pure string manipulation — no filesystem access,
                # so it works whether or not the directory already exists.
                existing_hooks_abs="$(python3 -c "import os.path, sys; print(os.path.normpath(sys.argv[1]))" "$existing_hooks_abs")"
                hooks_path="$(python3 -c "import os.path, sys; print(os.path.normpath(sys.argv[1]))" "$hooks_path")"
            fi
            if [ -n "$existing_hooks_abs" ] && [ "$existing_hooks_abs" != "$hooks_path" ] && [ "$force" != true ]; then
                echo "  --with-hook requested but $target already has a different core.hooksPath set:" >&2
                echo "    $existing_hooks_path" >&2
                echo "  Not overwriting — rerun with --force, or 'git -C $target config --unset core.hooksPath' first." >&2
                echo "  Recording with_hook=false — this install does not own $target's hook configuration." >&2
                with_hook=false
                coverage_hook=false
            else
                if [ "$mode" = "copy" ] || [ "$coverage_hook" = true ]; then
                    mkdir -p "$target/.github/hooks"
                    cp "$hooks_src_dir/prevent-trunk-commit" "$hooks_src_dir/pre-commit" "$hooks_src_dir/pre-merge-commit" "$target/.github/hooks/"
                    if [ "$coverage_hook" = true ]; then
                        generate_coverage_pre_push "$target" "$skills_src_root/tools/setup/harness-link.sh"
                        echo "  Generated a coverage-aware pre-push hook (calls 'enforce-profile' on every push)"
                    else
                        cp "$hooks_src_dir/pre-push" "$target/.github/hooks/"
                    fi
                fi
                if [ -n "$existing_hooks_abs" ] && [ "$existing_hooks_abs" != "$hooks_path" ]; then
                    git -C "$target" config core.hooksPath "$hooks_path"
                    echo "  Overwrote existing core.hooksPath ($existing_hooks_path) with agentharness hooks (--force)"
                else
                    git -C "$target" config core.hooksPath "$hooks_path"
                    if [ "$coverage_hook" = true ]; then
                        echo "  Installed trunk-protection + coverage-aware pre-push hooks (core.hooksPath)"
                    else
                        echo "  Installed trunk-protection hook (core.hooksPath) — not coverage, see --with-coverage-hook"
                    fi
                fi
                installed_hooks_path="$hooks_path"
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
    # 4a. File placement analysis
    # Analyze the project's top-level structure and generate
    # .agentharness-guarded-paths.json so pre-commit hooks and AI agents
    # know which directories and root files are off-limits for new
    # unannounced files. Requires Python 3 and tools/analyze_structure.py
    # in the harness source; silently skips if either is absent.
    # ------------------------------------------------------------------
    local analyze_script="$HARNESS_DIR/tools/analyze_structure.py"
    local guarded_paths_dst="$target/.agentharness-guarded-paths.json"
    if [ ! -f "$guarded_paths_dst" ] && command -v python3 >/dev/null 2>&1 && [ -f "$analyze_script" ]; then
        if python3 "$analyze_script" "$target" --output "$guarded_paths_dst" 2>/dev/null; then
            echo "  Generated .agentharness-guarded-paths.json (file placement policy)"
        else
            echo "  Warning: failed to analyze project structure — .agentharness-guarded-paths.json not created." >&2
        fi
    elif [ -f "$guarded_paths_dst" ]; then
        echo "  .agentharness-guarded-paths.json already exists — not overwriting"
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
    source_revision="$(source_revision_for "$skills_src_root" "$mode")"
    local source_remote
    source_remote="$(git -C "$skills_src_root" remote get-url origin 2>/dev/null || true)"
    local skills_csv
    skills_csv="$(IFS=,; echo "${linked_skills[*]}")"

    # Existing-surface integration (docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md):
    # render managed blocks into any instructions files the consumer
    # already has, and handle whole-file collisions on generated
    # directory-style surfaces the same way. Reuses this function's
    # existing $force/$dry_run.
    acquire_install_lock "$target" || exit 1
    local surfaces_json rendered_block install_id
    install_id="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    rendered_block="$(render_core_instructions_block "$target" "$skills_csv")"
    surfaces_json="$(build_surfaces_spec "$target" "$rendered_block" "$source_revision")"

    resolve_collisions_and_apply "$target" "$surfaces_json" "$install_id" "$force" "$dry_run" "$keep_existing" || {
        release_install_lock "$target"
        exit 1
    }
    release_install_lock "$target"

    # Pass the pre-install hooks path so uninstall can restore it (F-05)
    state_write "$target" "$mode" "$skills_csv" "$skills_filter" "$with_hook" \
        "$profile" "$skills_src_root" "$source_revision" "$source_remote" "$installed_hooks_path" "$coverage_hook" \
        "${existing_hooks_path:-}"

    warn_if_untracked "$target" "$dry_run"

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
    local hooks_path
    hooks_path="$(state_field "$target" hooks_path 2>/dev/null || echo "(none)")"
    [ "$hooks_path" = "None" ] && hooks_path="(none)"
    echo "  hooks_path:    $hooks_path"
    echo "  coverage_hook: $(state_field "$target" coverage_hook 2>/dev/null || echo "false")"
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

    # issue #88: an install can leave every skill file untracked by git,
    # invisible to clones/PRs/CI, with nothing in doctor's other checks
    # (which only look at the working tree) ever catching it. Soft-warn,
    # not fail — a "copy" install outside a git repo, or a project that
    # deliberately gitignores skills like a local cache, are legitimate.
    local in_git_repo=false
    git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1 && in_git_repo=true

    local skills_csv
    skills_csv="$(state_field "$target" skills)"
    IFS=',' read -ra skills <<< "$skills_csv"
    for skill in "${skills[@]}"; do
        [ -z "$skill" ] && continue
        for dest_subdir in "${SKILL_DEST_SUBDIRS[@]}"; do
            local dir="$target/$dest_subdir/$skill"
            if [ ! -e "$dir/SKILL.md" ]; then
                echo "  ✗ $skill: SKILL.md not found at $dir" >&2
                failed=1
                continue
            fi
            echo "  ✓ $skill: SKILL.md present ($dest_subdir)"
            local broken=0
            while IFS= read -r link; do
                if [ ! -e "$link" ]; then
                    echo "  ✗ $skill: broken bundled-resource link: $link" >&2
                    failed=1
                    broken=1
                fi
            done < <(find -L "$dir" -type l 2>/dev/null)
            [ "$broken" -eq 0 ] && echo "  ✓ $skill: bundled resources resolve ($dest_subdir)"

            # Check the skill directory itself, not "$dir/SKILL.md" — in
            # symlink modes (link/npm/submodule) the skill dir is itself a
            # symlink, and git tracks the symlink as its own entry rather
            # than anything path-appended past it, so a path ending in
            # /SKILL.md never matches even when the symlink is committed.
            if [ "$in_git_repo" = true ] && ! git -C "$target" ls-files --error-unmatch \
                "$dest_subdir/$skill" >/dev/null 2>&1; then
                echo "  (warn) $skill: $dir is untracked by git ($dest_subdir) — invisible to clones, PRs, and CI until committed"
            fi
        done
    done

    local with_hook
    with_hook="$(state_field "$target" with_hook)"
    if [ "$with_hook" = "true" ]; then
        # Compare against the exact path this CLI recorded, not just "is
        # something set" (P0-01) — a repo that later points core.hooksPath
        # somewhere else entirely would otherwise read as healthy.
        local recorded_hooks_path actual_hooks_path
        recorded_hooks_path="$(state_field "$target" hooks_path 2>/dev/null || echo "")"
        [ "$recorded_hooks_path" = "None" ] && recorded_hooks_path=""
        actual_hooks_path="$(git -C "$target" config --get core.hooksPath 2>/dev/null || true)"
        if [ -z "$recorded_hooks_path" ]; then
            echo "  ✗ with_hook is recorded true, but no hooks_path was recorded (older state, or install never actually applied it) — rerun 'init --with-hook' to re-record" >&2
            failed=1
        elif [ -z "$actual_hooks_path" ]; then
            echo "  ✗ with_hook is recorded true ($recorded_hooks_path), but core.hooksPath is unset" >&2
            failed=1
        elif [ "$actual_hooks_path" != "$recorded_hooks_path" ]; then
            echo "  ✗ core.hooksPath has changed since install (recorded: $recorded_hooks_path, actual: $actual_hooks_path)" >&2
            failed=1
        else
            echo "  ✓ core.hooksPath set ($actual_hooks_path)"

            # Check that both pre-commit and pre-merge-commit hook files exist.
            # Git only falls back to pre-commit for merge commits under certain
            # conditions; when the fallback fails, merge commits to trunk bypass
            # protection entirely (see issue #76 for detailed analysis).
            local pre_commit_path="$actual_hooks_path/pre-commit"
            local pre_merge_commit_path="$actual_hooks_path/pre-merge-commit"
            if [ -x "$pre_commit_path" ] && [ ! -x "$pre_merge_commit_path" ]; then
                echo "  ✗ pre-commit hook exists but pre-merge-commit is missing — merge commits to trunk branches may bypass protection (see issue #76 for details)" >&2
                failed=1
            elif [ -x "$pre_commit_path" ] && [ -x "$pre_merge_commit_path" ]; then
                echo "  ✓ both pre-commit and pre-merge-commit hooks present"
            fi
        fi

        # P0-03: a coverage-hook install's pre-push MUST be the generated
        # script, not the harness's own agentharness-specific one (that one
        # would just no-op for this consumer, silently enforcing nothing).
        local coverage_hook
        coverage_hook="$(state_field "$target" coverage_hook 2>/dev/null || echo "false")"
        if [ "$coverage_hook" = "true" ]; then
            local pre_push_path="$target/.github/hooks/pre-push"
            if [ ! -x "$pre_push_path" ]; then
                echo "  ✗ coverage_hook is recorded true, but $pre_push_path is missing or not executable" >&2
                failed=1
            elif ! grep -qF "$COVERAGE_HOOK_MARKER" "$pre_push_path"; then
                echo "  ✗ $pre_push_path exists but isn't the generated coverage hook (marker missing) — hand-edited or overwritten?" >&2
                failed=1
            else
                echo "  ✓ coverage-aware pre-push hook present and generated by this CLI"
            fi
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

    # Existing-surface integration: leftover crash journal
    local journal_status
    if journal_status="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" journal-status \
        --journal "$target/.agentharness-state.pending.json" 2>&1)"; then
        local journal_pending
        journal_pending="$(echo "$journal_status" | python3 -c 'import json,sys; print(json.load(sys.stdin)["pending"])' 2>/dev/null || echo "")"
        if [ "$journal_pending" = "True" ]; then
            echo "  ✗ an install/update was interrupted mid-apply (pending journal found)." >&2
            echo "$journal_status" | python3 -c '
import json, sys
for s in json.load(sys.stdin)["summary"]:
    print("    " + s)
'
            echo "    Recovery: re-run '\''init'\''/'\''update'\'' to complete the interrupted apply, or" >&2
            echo "    inspect .agentharness-state.pending.json and remove it if safe." >&2
            failed=1
        elif [ -z "$journal_pending" ]; then
            echo "  ✗ could not parse journal-status output — the pending journal file may be corrupted." >&2
            echo "$journal_status" >&2
            failed=1
        fi
    else
        echo "  ✗ journal-status check itself failed to run:" >&2
        echo "$journal_status" >&2
        failed=1
    fi

    # Managed-block drift: does the block currently on disk still match
    # what was recorded (by hash) when it was last installed/updated?
    python3 -c "
import hashlib
import sys
sys.path.insert(0, '$HARNESS_DIR/tools/setup')
import install_transaction as it
import block_installer as bi

state = it.load_state('$(state_path "$target")')
any_drift = False
for entry in state.get('managed_blocks', []):
    path = '$target/' + entry['file']
    try:
        content = open(path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f'  WARN: {entry[\"file\"]}: recorded as managed but file is missing')
        continue
    try:
        matches = bi.find_blocks(content, entry['block_id'])
    except bi.MarkerError:
        print(f'  WARN: {entry[\"file\"]}: malformed markers, cannot verify drift')
        any_drift = True
        continue
    if len(matches) != 1:
        print(f'  WARN: {entry[\"file\"]}: expected one managed block, found {len(matches)}')
        any_drift = True
        continue
    m = matches[0]
    current_block_text = content[m.start:m.end]
    current_hash = bi.sha256_bytes(current_block_text.encode('utf-8'))
    if current_hash != entry.get('rendered_sha256'):
        print(f'  drift: {entry[\"file\"]}: on-disk managed block does not match last-recorded render (hand-edited, or a version bump is pending — re-run update)')
        any_drift = True
    else:
        print(f'  OK: {entry[\"file\"]}: managed block matches last-recorded render')
sys.exit(1 if any_drift else 0)
" || failed=1

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
    local target="" json=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --json) json=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; exit 1; fi; shift ;;
        esac
    done
    target="${target:-.}"
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

    local not_installed=() no_longer_available=()
    for name in "${available[@]}"; do
        if ! printf '%s\n' "${installed[@]}" | grep -qxF "$name"; then
            not_installed+=("$name")
        fi
    done
    for name in "${installed[@]}"; do
        [ -z "$name" ] && continue
        if ! printf '%s\n' "${available[@]}" | grep -qxF "$name"; then
            no_longer_available+=("$name")
        fi
    done

    local source_rev current_rev rev_comparable=false commits_since=""
    source_rev="$(state_field "$target" source.revision)"
    current_rev="$(git -C "$source_path" rev-parse HEAD 2>/dev/null || echo unknown)"
    if [ "$current_rev" != "$source_rev" ] && [ "$current_rev" != "unknown" ] && git -C "$source_path" cat-file -e "$source_rev" 2>/dev/null; then
        rev_comparable=true
        commits_since="$(git -C "$source_path" log --oneline "$source_rev..$current_rev" -- .claude/skills patterns languages 2>/dev/null | head -20 || true)"
    fi

    # B5: expanded audit scope, reusing B1/B4/B7 rather than building new
    # detection logic for each.
    #
    # unsafe-authority: is the *audited target's own* .agentharness-
    # publish-mode flag (B1) present — same file, same directory scope
    # enforce-profile (B4) already reads its profile file from.
    local publish_mode_active=false
    [ -f "$target/.agentharness-publish-mode" ] && publish_mode_active=true

    # selected-profile: same file/precedence enforce-profile (B4) uses.
    local selected_profile="none (defaults to production)"
    if [ -f "$target/$PROFILE_FILE_NAME" ]; then
        selected_profile="$(tr -d '[:space:]' < "$target/$PROFILE_FILE_NAME")"
    fi

    # validation-commands: does the *recorded harness checkout's* own
    # tooling still exist where docs claim it does — catches a doc
    # referencing a script that was renamed/deleted upstream. Checked
    # against source_path (the harness), not target (the consumer
    # project), matching how skill availability above is also computed
    # from source_path.
    local validation_cmds=(
        "tools/check.sh"
        "tools/setup/harness-link.sh"
        "tools/verify-manifest.sh"
        "tools/verify-content-quality.py"
        "tools/generate-agents-md.sh"
        "tools/generate-manifest.py"
    )
    local validation_report=""
    local cmd_path full exists executable
    for cmd_path in "${validation_cmds[@]}"; do
        full="$source_path/$cmd_path"
        exists="false"; executable="false"
        [ -e "$full" ] && exists="true"
        [ -x "$full" ] && executable="true"
        validation_report+="$cmd_path|$exists|$executable"$'\n'
    done

    # --json (P2-01, expanded for P2-01/B5): machine-readable form of the
    # same drift this subcommand already computes, for CI or scripted
    # consumption instead of parsing the human-readable text below.
    if [ "$json" = true ]; then
        python3 - "$target" "$source_path" "$source_rev" "$current_rev" "$rev_comparable" \
            "$(printf '%s\n' "${not_installed[@]}")" "$(printf '%s\n' "${no_longer_available[@]}")" \
            "$commits_since" "$publish_mode_active" "$selected_profile" "$validation_report" <<'PYEOF'
import json
import sys

target, source_path, source_rev, current_rev, rev_comparable = sys.argv[1:6]
not_installed_raw, no_longer_available_raw, commits_raw = sys.argv[6:9]
publish_mode_active, selected_profile, validation_raw = sys.argv[9:12]


def lines(s):
    return [line for line in s.split("\n") if line]


not_installed = lines(not_installed_raw)
no_longer_available = lines(no_longer_available_raw)

validation_commands = []
for line in lines(validation_raw):
    cmd_path, exists, executable = line.split("|")
    validation_commands.append({
        "command": cmd_path,
        "exists": exists == "true",
        "executable": executable == "true",
    })

print(json.dumps({
    "target": target,
    "source_path": source_path,
    "source_revision": source_rev,
    "current_revision": current_rev,
    "revision_comparable": rev_comparable == "true",
    "available_not_installed": not_installed,
    "installed_not_available": no_longer_available,
    "drift": bool(not_installed or no_longer_available),
    "commits_since_install": lines(commits_raw),
    "publish_mode_active": publish_mode_active == "true",
    "selected_profile": selected_profile,
    "validation_commands": validation_commands,
}, indent=2))
PYEOF
        return
    fi

    echo "Skill drift for $target:"
    local found_drift=0
    for name in "${not_installed[@]}"; do
        echo "  + available upstream, not installed: $name"
        found_drift=1
    done
    for name in "${no_longer_available[@]}"; do
        echo "  - installed, no longer available upstream: $name"
        found_drift=1
    done
    [ "$found_drift" -eq 0 ] && echo "  (none)"

    echo ""
    if [ "$rev_comparable" = true ]; then
        echo "Commits in source since install ($source_rev..$current_rev):"
        printf '%s\n' "$commits_since"
    else
        echo "Source revision unchanged or not comparable ($source_rev)."
    fi

    echo ""
    echo "Selected profile: $selected_profile"
    echo "Publish-authority flag active: $publish_mode_active"

    echo ""
    echo "Validation commands (in the recorded harness checkout):"
    while IFS='|' read -r v_path v_exists v_executable; do
        [ -z "$v_path" ] && continue
        if [ "$v_exists" != "true" ]; then
            echo "  ✗ MISSING: $v_path"
        elif [ "$v_executable" != "true" ]; then
            echo "  ⚠ $v_path (exists, not executable)"
        else
            echo "  ✓ $v_path"
        fi
    done <<< "$validation_report"

    echo ""
    echo "Policy-conflict check: run 'python3 tools/verify-content-quality.py' in the harness checkout (not duplicated here — see B7)."
}

# ----------------------------------------------------------------------------
# enforce-profile (B4, extended for JS/TS) — makes .agentharness-profile do
# something mechanical instead of being a lookup table nothing reads.
# Never falsely blocks or falsely passes something it can't actually
# check — a project type (or, within JS/TS, a test runner) this doesn't
# recognize gets a clear "not implemented yet" and exit 0, not a silent
# pass framed as a real check. Reads the profile file directly (works for
# any project with one, not just projects initialized via this CLI's
# `init --profile`) and always falls back to production (fail-safe) for a
# missing or unrecognized profile, matching patterns/profiles/README.md's
# documented precedence rule.
# ----------------------------------------------------------------------------

profile_field() {
    # $1=profile.yaml path $2=field name under the top-level 'tests:' key
    awk -v field="$2" '
        /^tests:/ { intests=1; next }
        intests && $0 ~ "^  " field ":" { print $2; exit }
        /^[a-zA-Z]/ { intests=0 }
    ' "$1"
}

# JS/TS + Go runner adapters (B4 was Python-only; P1-02 extends
# enforcement to Go and one mainstream JS runner, Vitest, plus a
# --strict mode so CI can fail on "unsupported" instead of quietly
# passing). The guiding rule is unchanged: only run a check this repo
# can invoke and parse deterministically with no guessing —
#   * Python  → pytest + pytest-cov (`--cov-fail-under`)
#   * Go      → `go test -coverprofile` + `go tool cover -func` total
#   * JS/TS   → Node's built-in `node --test` OR Vitest's
#               `coverage-summary.json` (both stable, machine-readable)
# Anything else (Jest, Mocha, an unrecognized project type) gets an
# honest "not implemented yet". By default that is a non-blocking exit 0
# (never a false pass framed as a real check); under --strict it is a
# failure, so a CI job can require that every project it runs against is
# actually one enforcement understands.

# In non-strict mode an unsupported project/runner is a clean exit 0
# (the explanatory message is already printed); under --strict it fails,
# so CI can require full coverage of the projects it gates.
unsupported_exit() {
    if [ "$1" = true ]; then
        echo "  (--strict) failing because profile enforcement is not implemented for this project/runner." >&2
        return 1
    fi
    return 0
}

# Go: `go test -coverprofile` writes a merged profile across ./...; `go
# tool cover -func` prints a final `total:` line whose last field is the
# statement-coverage percentage — stable across Go versions and needs no
# third-party tooling.
enforce_go_profile() {
    local target="$1" profile_name="$2" coverage_min="$3"

    if ! command -v go >/dev/null 2>&1; then
        echo "Error: go not available — cannot enforce the '$profile_name' tier's test requirement for this Go project." >&2
        return 1
    fi

    echo "  Go project detected; tests.required: true, coverage_min: ${coverage_min:-none}"

    if [ -z "$coverage_min" ]; then
        (cd "$target" && go test ./...)
        return
    fi

    local profile_tmp
    profile_tmp="$(mktemp)"
    if ! (cd "$target" && go test -covermode=set -coverprofile="$profile_tmp" ./...); then
        rm -f "$profile_tmp"
        return 1
    fi

    # `go tool cover` must run from inside the module so it can resolve
    # the package paths recorded in the profile (otherwise: "package X is
    # not in std"). Guarded with `if !` so a parse failure is handled
    # here, not aborted by `set -e`.
    local cover_out
    if ! cover_out="$(cd "$target" && go tool cover -func="$profile_tmp" 2>/dev/null)"; then
        rm -f "$profile_tmp"
        echo "Error: 'go tool cover' failed on the coverage profile — cannot enforce coverage_min=$coverage_min." >&2
        return 1
    fi
    rm -f "$profile_tmp"

    local pct
    pct="$(echo "$cover_out" | awk '/^total:/ {gsub(/%/,"",$NF); print $NF}')"
    if [ -z "$pct" ]; then
        echo "Error: could not parse a total coverage percentage from 'go tool cover' — cannot enforce coverage_min=$coverage_min (no tests?)." >&2
        return 1
    fi
    if awk -v pct="$pct" -v min="$coverage_min" 'BEGIN { exit !(pct < min) }'; then
        echo "Coverage $pct% is below the '$profile_name' tier's minimum of $coverage_min%."
        return 1
    fi
    echo "  Coverage $pct% meets the '$profile_name' tier's minimum of $coverage_min%."
}

# Node's built-in test runner: `--experimental-test-coverage` prints an
# "all files" summary row whose second pipe-delimited column is the line
# percentage.
enforce_js_node_test() {
    local target="$1" profile_name="$2" coverage_min="$3"

    echo "  JS/TS project detected (Node built-in test runner); tests.required: true, coverage_min: ${coverage_min:-none}"

    local coverage_output
    if ! coverage_output="$(cd "$target" && node --test --experimental-test-coverage 2>&1)"; then
        echo "$coverage_output"
        return 1
    fi
    echo "$coverage_output"

    if [ -z "$coverage_min" ]; then
        return 0
    fi

    local pct
    pct="$(echo "$coverage_output" | grep "all files" | awk -F'|' '{gsub(/[^0-9.]/,"",$2); print $2}')"
    if [ -z "$pct" ]; then
        echo "Error: could not parse a coverage percentage from the test run — cannot enforce coverage_min=$coverage_min." >&2
        return 1
    fi

    if awk -v pct="$pct" -v min="$coverage_min" 'BEGIN { exit !(pct < min) }'; then
        echo "Coverage $pct% is below the '$profile_name' tier's minimum of $coverage_min%."
        return 1
    fi
    echo "  Coverage $pct% meets the '$profile_name' tier's minimum of $coverage_min%."
}

# Vitest: `--coverage.reporter=json-summary` writes
# coverage/coverage-summary.json, whose `total.lines.pct` is a stable,
# machine-readable number (no scraping of human-formatted terminal
# output). Uses the project's own local vitest binary when present, else
# npx --no-install (never silently pulls vitest from the network).
enforce_js_vitest_profile() {
    local target="$1" profile_name="$2" coverage_min="$3"

    echo "  JS/TS project detected (Vitest); tests.required: true, coverage_min: ${coverage_min:-none}"

    local -a runner
    if [ -x "$target/node_modules/.bin/vitest" ]; then
        runner=("$target/node_modules/.bin/vitest")
    elif command -v npx >/dev/null 2>&1; then
        runner=(npx --no-install vitest)
    else
        echo "Error: vitest not found (no node_modules/.bin/vitest and no npx) — cannot enforce the '$profile_name' tier's test requirement." >&2
        return 1
    fi

    local out
    if ! out="$(cd "$target" && "${runner[@]}" run --coverage --coverage.enabled --coverage.reporter=json-summary 2>&1)"; then
        echo "$out"
        return 1
    fi
    echo "$out"

    if [ -z "$coverage_min" ]; then
        return 0
    fi

    local summary="$target/coverage/coverage-summary.json"
    if [ ! -f "$summary" ]; then
        echo "Error: Vitest produced no coverage/coverage-summary.json (is @vitest/coverage-v8 installed and coverage enabled?) — cannot enforce coverage_min=$coverage_min." >&2
        return 1
    fi
    local pct
    pct="$(node -p "require(process.argv[1]).total.lines.pct" "$summary" 2>/dev/null)"
    if [ -z "$pct" ]; then
        echo "Error: could not parse total line coverage from coverage-summary.json — cannot enforce coverage_min=$coverage_min." >&2
        return 1
    fi

    if awk -v pct="$pct" -v min="$coverage_min" 'BEGIN { exit !(pct < min) }'; then
        echo "Coverage $pct% is below the '$profile_name' tier's minimum of $coverage_min%."
        return 1
    fi
    echo "  Coverage $pct% meets the '$profile_name' tier's minimum of $coverage_min%."
}

# Dispatch a JS/TS project to the right runner adapter by reading its
# package.json `scripts.test`. $target is passed as an argv argument, not
# interpolated into the JS source string — avoids both module-resolution
# pitfalls (a relative path like "my-project" would otherwise be treated
# as a package name, not a file path, unless it starts with ./ or /) and
# string-injection risk from unusual path characters (quotes, etc.).
enforce_js_ts_profile() {
    local target="$1" profile_name="$2" coverage_min="$3" strict="$4"

    if ! command -v node >/dev/null 2>&1; then
        echo "Error: node not available — cannot enforce the '$profile_name' tier's test requirement for this JS/TS project." >&2
        return 1
    fi

    local test_script
    test_script="$(node -p "(require(process.argv[1] + '/package.json').scripts || {}).test || ''" "$target" 2>/dev/null)"

    if [ -z "$test_script" ]; then
        echo "Error: no 'test' script defined in package.json — cannot enforce the '$profile_name' tier's test requirement." >&2
        return 1
    fi

    case "$test_script" in
        *"node --test"*|*"node:test"*)
            enforce_js_node_test "$target" "$profile_name" "$coverage_min" ;;
        *vitest*)
            enforce_js_vitest_profile "$target" "$profile_name" "$coverage_min" ;;
        *)
            echo "  JS/TS project detected, but its 'test' script ('$test_script') isn't Node's built-in test runner or Vitest — profile enforcement currently supports \`node --test\` and Vitest (v1 scope). See ROADMAP.md."
            unsupported_exit "$strict" ;;
    esac
}

# ----------------------------------------------------------------------------
# audit-prs — list open PRs with stale unaddressed review comments
# ----------------------------------------------------------------------------

cmd_audit_prs() {
    # Lists open PRs carrying stale unaddressed review feedback: a
    # top-level comment with no reply that is newer than the PR's last
    # commit, or older than 24h. One line per flagged PR; exit 1 if any
    # (so it can gate), 0 otherwise.

    if ! command -v gh >/dev/null 2>&1; then
        echo "Error: 'gh' CLI not found. Install GitHub CLI to use audit-prs." >&2
        return 1
    fi

    local repo
    repo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
    if [ -z "$repo" ]; then
        echo "Error: could not resolve a GitHub repository from the current directory." >&2
        return 1
    fi

    AH_AUDIT_REPO="$repo" python3 - <<'PY'
import json, os, subprocess, sys
from datetime import datetime, timedelta, timezone

repo = os.environ["AH_AUDIT_REPO"]


def gh(*args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


prs_raw = gh("pr", "list", "-R", repo, "--state", "open",
             "--json", "number,title,author")
prs = json.loads(prs_raw) if prs_raw else []
if not prs:
    print("No open PRs found.")
    sys.exit(0)

now = datetime.now(timezone.utc)
flagged = 0
for pr in prs:
    num = str(pr["number"])
    author = pr["author"]["login"]
    view_raw = gh("pr", "view", num, "-R", repo, "--json", "comments,commits")
    if view_raw is None:
        continue
    view = json.loads(view_raw)
    commits = view.get("commits", [])
    last_commit = ts(commits[-1]["committedDate"]) if commits else None

    unanswered = []

    # Issue-level comments have no threading; the reply convention is a
    # later comment from the PR author.
    comments = view.get("comments", [])
    author_times = [ts(c["createdAt"]) for c in comments
                    if c["author"]["login"] == author]
    last_author = max(author_times) if author_times else None
    for c in comments:
        if c["author"]["login"] == author:
            continue
        created = ts(c["createdAt"])
        if last_author is None or created > last_author:
            unanswered.append(created)

    # Inline review comments thread via in_reply_to_id.
    inline_raw = gh("api", f"repos/{repo}/pulls/{num}/comments?per_page=100")
    inline = json.loads(inline_raw) if inline_raw else []
    replied_to = {c.get("in_reply_to_id") for c in inline if c.get("in_reply_to_id")}
    for c in inline:
        if c.get("in_reply_to_id") is None and c["id"] not in replied_to:
            unanswered.append(ts(c["created_at"]))

    stale = [t for t in unanswered
             if (last_commit is not None and t > last_commit)
             or (now - t > timedelta(hours=24))]
    if stale:
        oldest_hours = int((now - min(stale)).total_seconds() // 3600)
        title = pr["title"]
        print(f'#{num} "{title}" - {len(stale)} unanswered comment(s), '
              f"oldest {oldest_hours}h")
        flagged += 1

if flagged:
    print(f"Found {flagged} PR(s) with stale unaddressed comments.")
    sys.exit(1)
print("No PRs with stale unaddressed comments found.")
PY
}

cmd_enforce_profile() {
    local target="" strict=false
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit 0 ;;
            --strict) strict=true; shift ;;
            *) if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; exit 1; fi; shift ;;
        esac
    done
    target="${target:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"

    local profile_name="production"
    if [ -f "$target/$PROFILE_FILE_NAME" ]; then
        profile_name="$(tr -d '[:space:]' < "$target/$PROFILE_FILE_NAME")"
    fi

    local profile_yaml="$HARNESS_DIR/patterns/profiles/$profile_name.yaml"
    if [ ! -f "$profile_yaml" ]; then
        echo "Warning: unrecognized profile '$profile_name' from $PROFILE_FILE_NAME — falling back to production (fail-safe, never silently relaxes enforcement)." >&2
        profile_name="production"
        profile_yaml="$HARNESS_DIR/patterns/profiles/production.yaml"
    fi

    echo "enforce-profile: $target"
    echo "  selected profile: $profile_name"

    local tests_required coverage_min
    tests_required="$(profile_field "$profile_yaml" required)"
    coverage_min="$(profile_field "$profile_yaml" coverage_min)"
    [ "$coverage_min" = "null" ] && coverage_min=""

    if [ "$tests_required" != "true" ]; then
        echo "  tests.required: false at '$profile_name' tier — nothing to enforce, skipping."
        return 0
    fi

    if [ -f "$target/pyproject.toml" ] || [ -f "$target/setup.py" ] || [ -f "$target/requirements.txt" ]; then
        if ! python3 -m pytest --version >/dev/null 2>&1; then
            echo "Error: pytest not available — cannot enforce the '$profile_name' tier's test requirement." >&2
            return 1
        fi

        echo "  Python project detected; tests.required: true, coverage_min: ${coverage_min:-none}"
        local pytest_args=(-q)
        if [ -n "$coverage_min" ]; then
            pytest_args+=("--cov=$target" "--cov-branch" "--cov-fail-under=$coverage_min")
        fi
        (cd "$target" && python3 -m pytest "${pytest_args[@]}")
        return
    fi

    if [ -f "$target/go.mod" ]; then
        enforce_go_profile "$target" "$profile_name" "$coverage_min"
        return
    fi

    if [ -f "$target/package.json" ]; then
        enforce_js_ts_profile "$target" "$profile_name" "$coverage_min" "$strict"
        return
    fi

    echo "  Profile enforcement isn't implemented yet for this project type — see ROADMAP.md."
    unsupported_exit "$strict"
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
    local target="" yes=false force=false dry_run=false keep_existing=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --yes) yes=true; shift ;;
            --force) force=true; shift ;;
            --dry-run) dry_run=true; shift ;;
            --keep-existing) keep_existing=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) if [ -z "$target" ]; then target="$1"; else echo "Unexpected argument: $1" >&2; exit 1; fi; shift ;;
        esac
    done
    target="${target:-.}"
    [ -d "$target" ] && target="$(cd "$target" && pwd)"
    require_state "$target"

    local mode source_path skills_filter with_hook profile hooks_path coverage_hook
    mode="$(state_field "$target" mode)"
    source_path="$(state_field "$target" source.path)"
    skills_filter="$(state_field "$target" skills_filter 2>/dev/null || echo "")"
    [ "$skills_filter" = "None" ] && skills_filter=""
    with_hook="$(state_field "$target" with_hook)"
    # update never touches hooks — carry the previously recorded path/flag
    # through unchanged (P0-01/P0-03: this must stay in sync with whatever
    # init/doctor last verified, not silently reset just because update
    # doesn't ask).
    hooks_path="$(state_field "$target" hooks_path 2>/dev/null || echo "")"
    [ "$hooks_path" = "None" ] && hooks_path=""
    coverage_hook="$(state_field "$target" coverage_hook 2>/dev/null || echo "false")"
    profile="$(state_field "$target" profile 2>/dev/null || echo "")"
    [ "$profile" = "None" ] && profile=""

    # P0-02: 'npm' mode's whole point is that source_path (the durable local
    # copy) must NOT be diffed against its own prior self to detect
    # upstream changes — refresh it from HARNESS_DIR (this exact invocation
    # of the currently-running package) FIRST, so 'current' below reflects
    # whatever version of agentharness-toolkit this update was actually run
    # with, not whatever was durably copied at install time.
    if [ "$mode" = "npm" ]; then
        echo "  Refreshing durable npm source from the currently running package ($HARNESS_DIR)..."
        copy_npm_durable_source "$target"
    fi

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

    if [ "$dry_run" = true ]; then
        # --dry-run must never mutate: skip skill sync, .gitignore merge,
        # and state_write entirely, and pass dry_run through to the
        # managed-block/collision flow too (parity with 'init --dry-run').
        # source_revision/new_skills_csv aren't computed yet at this point
        # in the function (that happens later, only on the real-apply
        # path) — compute local equivalents from what's already available
        # ($source_path, $current) instead of reusing those names early.
        local dry_run_source_revision dry_run_skills_csv
        dry_run_source_revision="$(source_revision_for "$source_path" "$mode")"
        dry_run_skills_csv="$(IFS=,; echo "${current[*]}")"

        acquire_install_lock "$target" || exit 1
        local surfaces_json rendered_block install_id
        install_id="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
        rendered_block="$(render_core_instructions_block "$target" "$dry_run_skills_csv")"
        surfaces_json="$(build_surfaces_spec "$target" "$rendered_block" "$dry_run_source_revision")"
        resolve_collisions_and_apply "$target" "$surfaces_json" "$install_id" "$force" "$dry_run" "$keep_existing" || {
            release_install_lock "$target"
            exit 1
        }
        release_install_lock "$target"
        echo "(dry run — nothing was changed)"
        return 0
    fi

    if [ "${#to_add[@]}" -eq 0 ] && [ "${#to_remove[@]}" -eq 0 ] && [ "${#to_refresh[@]}" -eq 0 ]; then
        # Preserve the original "(nothing to do)" wording several existing
        # tests assert on. We still fall through to the unconditional
        # managed-block flow below (outside this if/else) to catch drifted
        # blocks even when no skills changed — that flow is idempotent
        # (atomic_write no-ops on unchanged content) and silent when
        # there's nothing to fix, so it doesn't contradict this message.
        echo "  (nothing to do)"
    else
        confirm "$yes" "Apply this update?" || { echo "Aborted."; return 1; }

        for name in "${to_remove[@]}"; do
            for dest_subdir in "${SKILL_DEST_SUBDIRS[@]}"; do
                local dst="$target/$dest_subdir/$name"
                if [ -L "$dst" ] || [ -d "$dst" ]; then
                    rm -rf "$dst"
                fi
            done
            echo "  Removed: $name"
        done

        for name in "${current[@]}"; do
            for dest_subdir in "${SKILL_DEST_SUBDIRS[@]}"; do
                mkdir -p "$target/$dest_subdir"
                local src="$source_path/.claude/skills/$name"
                local dst="$target/$dest_subdir/$name"
                case "$mode" in
                    link|submodule|npm)
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
    fi

    local source_revision
    source_revision="$(source_revision_for "$source_path" "$mode")"
    local source_remote
    source_remote="$(git -C "$source_path" remote get-url origin 2>/dev/null || true)"
    local new_skills_csv
    new_skills_csv="$(IFS=,; echo "${current[*]}")"

    # Existing-surface integration: same as cmd_init
    acquire_install_lock "$target" || exit 1
    local surfaces_json rendered_block install_id
    install_id="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    rendered_block="$(render_core_instructions_block "$target" "$new_skills_csv")"
    surfaces_json="$(build_surfaces_spec "$target" "$rendered_block" "$source_revision")"
    resolve_collisions_and_apply "$target" "$surfaces_json" "$install_id" "$force" "$dry_run" "$keep_existing" || {
        release_install_lock "$target"
        exit 1
    }
    release_install_lock "$target"

    state_write "$target" "$mode" "$new_skills_csv" "$skills_filter" "$with_hook" \
        "$profile" "$source_path" "$source_revision" "$source_remote" "$hooks_path" "$coverage_hook"

    warn_if_untracked "$target" false

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
    [ "$mode" = "npm" ] && [ -e "$target/$NPM_DURABLE_PATH" ] && echo "  - the $NPM_DURABLE_PATH durable source copy"
    echo "  - $STATE_FILE_NAME"

    confirm "$yes" "Proceed with uninstall?" || { echo "Aborted."; return 1; }

    for name in "${installed[@]}"; do
        [ -z "$name" ] && continue
        for dest_subdir in "${SKILL_DEST_SUBDIRS[@]}"; do
            local dst="$target/$dest_subdir/$name"
            if [ -L "$dst" ] || [ -d "$dst" ]; then
                rm -rf "$dst"
            fi
        done
        echo "  Removed skill: $name"
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
        # Only unset core.hooksPath if it still holds exactly what this CLI
        # installed (P0-01) — if the recorded path is missing (older state)
        # or the user/another tool has since repointed it, unsetting would
        # destroy configuration this install never owned.
        local recorded_hooks_path actual_hooks_path
        recorded_hooks_path="$(state_field "$target" hooks_path 2>/dev/null || echo "")"
        [ "$recorded_hooks_path" = "None" ] && recorded_hooks_path=""
        actual_hooks_path="$(git -C "$target" config --get core.hooksPath 2>/dev/null || true)"
        if [ -z "$recorded_hooks_path" ]; then
            echo "  core.hooksPath: no hooks_path was recorded for this install — leaving core.hooksPath ($actual_hooks_path) untouched" >&2
        elif [ "$actual_hooks_path" = "$recorded_hooks_path" ]; then
            # Restore the pre-install hooks path if one was recorded; unset otherwise
            local previous_hooks_path
            previous_hooks_path="$(state_field "$target" previous_hooks_path 2>/dev/null || echo "")"
            [ "$previous_hooks_path" = "None" ] && previous_hooks_path=""
            if [ -n "$previous_hooks_path" ]; then
                git -C "$target" config core.hooksPath "$previous_hooks_path" 2>/dev/null || true
                echo "  Restored core.hooksPath to previous value: $previous_hooks_path"
            else
                git -C "$target" config --unset core.hooksPath 2>/dev/null || true
                echo "  Unset core.hooksPath (no previous value was recorded)"
            fi
            # Both --mode copy and a coverage-hook install (P0-03) write
            # real, consumer-owned hook files at $target/.github/hooks/
            # (unlike link/submodule/npm's symlink-to-the-shared-dir case,
            # which has nothing here to remove) — clean those up too, but
            # only in this verified-still-ours branch, same ownership
            # guard as the config unset above. Copilot review: this used
            # to only fire when coverage_hook=true, leaving a plain
            # '--mode copy --with-hook' install's copied
            # prevent-trunk-commit/pre-commit/pre-push files behind.
            if [ "$recorded_hooks_path" = "$target/.github/hooks" ]; then
                local coverage_hook
                coverage_hook="$(state_field "$target" coverage_hook 2>/dev/null || echo "false")"
                rm -f "$target/.github/hooks/pre-push" "$target/.github/hooks/pre-commit" "$target/.github/hooks/pre-merge-commit" "$target/.github/hooks/prevent-trunk-commit"
                rmdir "$target/.github/hooks" 2>/dev/null || true
                rmdir "$target/.github" 2>/dev/null || true
                if [ "$coverage_hook" = "true" ]; then
                    echo "  Removed the generated coverage-aware pre-push hook"
                else
                    echo "  Removed the copied hook files"
                fi
            fi
        else
            echo "  core.hooksPath has changed since install (recorded: $recorded_hooks_path, actual: $actual_hooks_path) — leaving it untouched" >&2
        fi
    fi

    [ -f "$target/$PROFILE_FILE_NAME" ] && rm -f "$target/$PROFILE_FILE_NAME" && echo "  Removed $PROFILE_FILE_NAME"

    if [ "$mode" = "submodule" ] && [ -e "$target/$SUBMODULE_PATH/.git" ]; then
        git -C "$target" submodule deinit -f "$SUBMODULE_PATH" 2>/dev/null || true
        rm -rf "$target/.git/modules/$SUBMODULE_PATH"
        git -C "$target" rm -f "$SUBMODULE_PATH" 2>/dev/null || rm -rf "${target:?}/${SUBMODULE_PATH:?}"
        echo "  Removed the $SUBMODULE_PATH submodule"
    fi

    if [ "$mode" = "npm" ] && [ -e "$target/$NPM_DURABLE_PATH" ]; then
        rm -rf "${target:?}/${NPM_DURABLE_PATH:?}"
        echo "  Removed the $NPM_DURABLE_PATH durable source copy"
    fi

    local uninstall_json
    uninstall_json="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" uninstall \
        --state "$(state_path "$target")" --base-dir "$target")"
    echo "$uninstall_json" | python3 -c '
import json, sys
for line in json.load(sys.stdin)["log"]:
    print("  " + line)
'

    rm -f "$(state_path "$target")"
    echo "Uninstalled."
}

# ----------------------------------------------------------------------------
# generate-clients (P1-01, first increment)
# ----------------------------------------------------------------------------
#
# Run this repo's client-adapter generators against a consumer project, so
# a single command produces the routing/instruction files for the agentic
# tools it uses — instead of the per-generator manual steps in
# docs/INTEGRATION.md. Ships standalone (same posture as enforce-profile):
# it does NOT yet wire generation into init/update or record generated
# files in state for uninstall — that managed-block lifecycle integration
# is the larger, still-open part of P1-01 (see ROADMAP.md). Claude Code
# isn't a target here: CLAUDE.md is the hand-authored source every one of
# these files is generated *from*, not something to generate.

# _gc_is_harness_generated FILE
# Returns 0 if FILE contains the harness provenance marker, 1 otherwise.
_gc_is_harness_generated() {
    local f="$1"
    [ -f "$f" ] && grep -qE "Generated (from|by) .*(generate-|agentharness)" "$f" 2>/dev/null
}

# _gc_check_file FILE LABEL DRY_RUN FORCE
# Checks whether FILE can be safely written.
# Returns 0 if safe (or dry-run); 1 if should be skipped.
_gc_check_file() {
    local f="$1" label="$2" dry_run="$3" force="$4"
    if [ ! -f "$f" ]; then
        [ "$dry_run" = true ] && echo "  [dry-run] would create: $label"
        return 0
    fi
    if _gc_is_harness_generated "$f"; then
        [ "$dry_run" = true ] && echo "  [dry-run] would update (harness-owned): $label"
        return 0
    fi
    if [ "$force" = true ]; then
        # Only warn during actual writes, not during dry-run (no-op path)
        [ "$dry_run" = false ] && echo "  WARNING: overwriting non-harness file with --force: $label" >&2
        [ "$dry_run" = true ] && echo "  [dry-run] would overwrite (--force): $label"
        return 0
    fi
    echo "  SKIP: $label already exists and was not created by this harness." >&2
    echo "        Use --force to overwrite, or delete it first." >&2
    return 1
}

cmd_generate_clients() {
    local target="" clients="all" dry_run=false force=false
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit 0 ;;
            --dry-run) dry_run=true; shift ;;
            --force)   force=true; shift ;;
            --client|--clients)
                if [ -z "${2:-}" ]; then
                    echo "Error: --client requires a value (codex, gemini, copilot, cursor, kilo, or all)." >&2
                    exit 1
                fi
                clients="$2"; shift 2 ;;
            *) if [ -z "$target" ]; then target="$1"; shift; else echo "Unexpected argument: $1" >&2; exit 1; fi ;;
        esac
    done
    target="${target:-.}"
    if [ ! -d "$target" ]; then
        echo "Error: target '$target' is not a directory." >&2
        exit 1
    fi
    target="$(cd "$target" && pwd)"

    local selected
    if [ "$clients" = all ]; then
        selected="codex gemini copilot cursor kilo"
    else
        selected="${clients//,/ }"
    fi

    local gen="$HARNESS_DIR/tools"
    local -a client_list
    read -ra client_list <<< "$selected"

    [ "$dry_run" = true ] && echo "generate-clients: --dry-run mode (no files will be written)"
    echo "generate-clients: $target"

    local skipped=0
    local c
    for c in "${client_list[@]}"; do
        case "$c" in
            codex)
                if _gc_check_file "$target/AGENTS.md" "AGENTS.md" "$dry_run" "$force"; then
                    [ "$dry_run" = false ] && bash "$gen/generate-agents-md.sh" "$HARNESS_DIR" --output "$target/AGENTS.md"
                    echo "  codex/opencode/zed -> AGENTS.md"
                else
                    skipped=$((skipped+1))
                fi ;;
            gemini)
                if _gc_check_file "$target/GEMINI.md" "GEMINI.md" "$dry_run" "$force"; then
                    [ "$dry_run" = false ] && bash "$gen/generate-gemini-md.sh" "$HARNESS_DIR" --output "$target/GEMINI.md"
                    echo "  gemini/antigravity -> GEMINI.md"
                else
                    skipped=$((skipped+1))
                fi ;;
            copilot)
                # Guard primary file and also check for non-harness .github/instructions/ files
                local copilot_ok=true
                if ! _gc_check_file "$target/.github/copilot-instructions.md" ".github/copilot-instructions.md" "$dry_run" "$force"; then
                    copilot_ok=false
                fi
                if [ "$copilot_ok" = true ] && [ -d "$target/.github/instructions" ]; then
                    local inst_file
                    for inst_file in "$target/.github/instructions/"*.instructions.md; do
                        [ -f "$inst_file" ] || continue
                        if ! _gc_is_harness_generated "$inst_file" && [ "$force" != true ]; then
                            echo "  SKIP: .github/instructions/$(basename "$inst_file") exists and is not harness-generated. Use --force." >&2
                            copilot_ok=false
                            break
                        fi
                    done
                fi
                if [ "$copilot_ok" = true ]; then
                    [ "$dry_run" = false ] && bash "$gen/generate-copilot-instructions.sh" "$HARNESS_DIR" --output-dir "$target"
                    echo "  copilot -> .github/copilot-instructions.md (+ .github/instructions/)"
                else
                    skipped=$((skipped+1))
                fi ;;
            cursor)
                # Guard all .cursor/rules/*.mdc to avoid overwriting user's custom rules
                local cursor_ok=true
                if [ -d "$target/.cursor/rules" ]; then
                    local mdc_file
                    for mdc_file in "$target/.cursor/rules/"*.mdc; do
                        [ -f "$mdc_file" ] || continue
                        if ! _gc_is_harness_generated "$mdc_file" && [ "$force" != true ]; then
                            echo "  SKIP: .cursor/rules/$(basename "$mdc_file") exists and is not harness-generated. Use --force." >&2
                            cursor_ok=false
                            break
                        fi
                    done
                fi
                if [ "$cursor_ok" = true ]; then
                    [ "$dry_run" = false ] && bash "$gen/generate-cursor-rules.sh" "$HARNESS_DIR" --output-dir "$target"
                    echo "  cursor -> .cursor/rules/"
                else
                    skipped=$((skipped+1))
                fi ;;
            kilo)
                if _gc_check_file "$target/.kilo/rules/agentharness.md" ".kilo/rules/agentharness.md" "$dry_run" "$force"; then
                    [ "$dry_run" = false ] && mkdir -p "$target/.kilo/rules" && bash "$gen/generate-kilo-rules.sh" "$HARNESS_DIR" --output "$target/.kilo/rules/agentharness.md"
                    echo "  kilo -> .kilo/rules/agentharness.md"
                else
                    skipped=$((skipped+1))
                fi ;;
            *)
                echo "Error: unknown client '${c}' (valid: codex, gemini, copilot, cursor, kilo, all)." >&2
                exit 1 ;;
        esac
    done

    if [ "$skipped" -gt 0 ]; then
        echo "generate-clients: $skipped file(s) skipped (pre-existing non-harness files). Use --force to overwrite."
    fi
    echo "generate-clients: done"
}


# ----------------------------------------------------------------------------
# Dispatch
# ----------------------------------------------------------------------------
#
# Guarded so this file can be `source`d for its functions (list_available_
# skills, state_field, etc. — see tools/generate-agents-md.sh) without also
# triggering the CLI dispatch below.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        __test_acquire_install_lock)
            shift; acquire_install_lock "$1"; exit $?
            ;;
        __test_release_install_lock)
            shift; release_install_lock "$1"; exit $?
            ;;
        __test_resolve_collisions_and_apply)
            shift; resolve_collisions_and_apply "$@"; exit $?
            ;;
        init|plan|status|doctor|audit|audit-prs|enforce-profile|generate-clients|update|uninstall)
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

    # cmd_$cmd would break for "enforce-profile" and "audit-prs" (hyphens
    # don't match underscore-named functions) — translate explicitly instead
    # of renaming the functions to something inconsistent with the rest.
    case "$cmd" in
        enforce-profile) cmd_fn="cmd_enforce_profile" ;;
        audit-prs) cmd_fn="cmd_audit_prs" ;;
        generate-clients) cmd_fn="cmd_generate_clients" ;;
        *) cmd_fn="cmd_$cmd" ;;
    esac
    "$cmd_fn" "$@"
fi
