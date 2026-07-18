"""Preflight planning, collision classification, and crash-safe apply
for harness-link.sh's existing-surface integration. Orchestrates
block_installer.py; owns state schema v2. See
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md.
"""
from __future__ import annotations

import datetime
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import block_installer as bi  # noqa: E402

SCHEMA_VERSION = 2

_V2_LIST_FIELDS = ("managed_blocks", "overwritten_files", "collision_decisions")


def _fresh_v2_skeleton() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, **{k: [] for k in _V2_LIST_FIELDS}}


def load_state(path: Path) -> dict[str, Any]:
    """Load state, migrating v1 -> v2 in memory (schema migration policy
    tracked as F-12; this only adds the new v2 list fields, never
    rewrites v1 fields). Missing file returns a fresh v2 skeleton with
    no other fields — callers merge in mode/skills/etc. themselves."""
    path = Path(path)
    if not path.exists():
        return _fresh_v2_skeleton()
    data: dict[str, Any] = json.loads(path.read_text())
    if data.get("schema_version") == SCHEMA_VERSION:
        return data
    data["schema_version"] = SCHEMA_VERSION
    for f in _V2_LIST_FIELDS:
        data.setdefault(f, [])
    return data


def save_state(path: Path, data: dict[str, Any]) -> None:
    path = Path(path)
    path.write_text(json.dumps(data, indent=2) + "\n")


class Classification(Enum):
    CREATE = auto()               # nothing there yet, write it
    BLOCK_MANAGED = auto()        # supported instructions file: insert/replace block
    WHOLE_FILE_COLLISION = auto() # generated whole-file surface already occupied
    HARD_FAIL = auto()            # malformed markers, symlink, or non-regular file


def classify_path(path: Path, *, is_block_surface: bool) -> Classification:
    """Classify a target path per spec section 4's three-way rule.
    is_block_surface=True for CLAUDE.md/AGENTS.md/GEMINI.md/copilot
    files (block-managed); False for directory-style generated assets
    like .cursor/rules/*.mdc (whole-file collision candidates)."""
    path = Path(path)

    if path.is_symlink():
        return Classification.HARD_FAIL
    if path.exists() and not path.is_file():
        return Classification.HARD_FAIL

    if not path.exists():
        return (
            Classification.BLOCK_MANAGED
            if is_block_surface
            else Classification.CREATE
        )

    if is_block_surface:
        try:
            bi.find_blocks(path.read_text(), "core-instructions")
        except bi.MarkerError:
            return Classification.HARD_FAIL
        return Classification.BLOCK_MANAGED

    return Classification.WHOLE_FILE_COLLISION


def sha256_of_file(path: Path) -> str:
    return bi.sha256_bytes(Path(path).read_bytes())


def backup_path_for(target: Path, install_id: str) -> Path:
    return target.with_name(f"{target.name}.pre-agentharness.{install_id}")


def resolve_backup_path(
    target: Path,
    state: dict[str, Any],
    install_id: str,
    base_dir: Path,
) -> Path:
    """Collision-safe backup resolution (spec section 4):
    - reuse a state-owned backup if its recorded hash still matches its
      own on-disk content (it already holds true pre-harness bytes);
    - otherwise mint a new unique '<name>.pre-agentharness.<install_id>'
      path, generating a fresh suffix if that exact path is already
      occupied by something this state doesn't own — never overwritten.
    """
    rel = (
        str(target.relative_to(base_dir)) if target.is_absolute()
        else str(target)
    )
    for entry in state.get("overwritten_files", []):
        if entry["file"] != rel:
            continue
        backup_path: str = entry.get("backup", "")
        existing_backup = base_dir / backup_path
        # Compare against backup_sha256 (the hash of what the backup
        # itself holds — the pre-existing consumer content that was
        # copied into it), not written_sha256 (the hash of the harness
        # content written to the TARGET) — those are hashes of two
        # different files and would essentially never match.
        if (
            existing_backup.exists()
            and sha256_of_file(existing_backup) == entry.get("backup_sha256")
        ):
            return existing_backup

    candidate = backup_path_for(target, install_id)
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = backup_path_for(target, f"{install_id}-{suffix}")
    return candidate


@dataclass
class Surface:
    path: Path
    is_block_surface: bool
    block_body: str = ""
    content: str = ""
    block_id: str = "core-instructions"
    block_version: str = "0.0.0"


@dataclass
class PlanItem:
    path: Path


@dataclass
class Action:
    kind: str
    surface: Surface


@dataclass
class Plan:
    ok: bool
    actions: list[Action] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    collision_decisions: list[dict[str, Any]] = field(default_factory=list)


def _rel(path: Path, base_dir: Path) -> str:
    path = Path(path)
    return str(path.relative_to(base_dir)) if path.is_absolute() else str(path)


def _find_decision(
    state: dict[str, Any], rel_path: str, target: Path
) -> str | None:
    for entry in state.get("collision_decisions", []):
        if entry["item"] != rel_path:
            continue
        existing_sha = entry.get("existing_sha256")
        if existing_sha == sha256_of_file(target):
            choice: str | None = entry.get("choice")
            return choice
        return None  # stale — caller must re-decide
    return None


def build_plan(
    surfaces: list[Surface],
    state: dict[str, Any],
    install_id: str,
    base_dir: Path,
    decide: Callable[[PlanItem], str],
) -> Plan:
    """Discover -> validate -> resolve decisions -> construct plan.
    Fails the whole plan (zero actions) if any surface hard-fails
    classification, per spec section 6's zero-mutation guarantee."""
    errors: list[str] = []
    actions: list[Action] = []
    collision_decisions: list[dict[str, Any]] = []

    for surface in surfaces:
        classification = classify_path(
            surface.path, is_block_surface=surface.is_block_surface
        )

        if classification is Classification.HARD_FAIL:
            errors.append(
                f"{surface.path}: malformed markers or unsafe target"
            )
            continue
        if errors:
            continue  # stop planning actions once any surface has failed

        if classification is Classification.BLOCK_MANAGED:
            actions.append(Action(kind="upsert_block", surface=surface))
        elif classification is Classification.CREATE:
            actions.append(Action(kind="create", surface=surface))
        elif classification is Classification.WHOLE_FILE_COLLISION:
            rel_path = _rel(surface.path, base_dir)
            persisted_choice = _find_decision(state, rel_path, surface.path)
            if persisted_choice is not None:
                choice = persisted_choice
                # Already recorded and still valid (hash matched) — no
                # new collision_decisions entry needed.
            else:
                # Capture the hash of what's on disk RIGHT NOW, before
                # any mutation — this is the pre-existing consumer
                # content that caused the collision, which is what a
                # later run's staleness check must compare against.
                # Capturing it here (at plan time) rather than in
                # apply_plan means it's correct for BOTH "overwrite"
                # (where apply_plan is about to replace the file with
                # harness content) and "keep-existing" (where nothing
                # ever gets written, so there'd be nothing to capture
                # later).
                pre_existing_hash = sha256_of_file(surface.path)
                choice = decide(PlanItem(path=surface.path))
                collision_decisions.append({
                    "item": rel_path,
                    "kind": "whole-file",
                    "choice": choice,
                    "existing_sha256": pre_existing_hash,
                    "decided_at": datetime.datetime.now(
                        datetime.UTC
                    ).isoformat(),
                })
            if choice == "overwrite":
                actions.append(
                    Action(kind="overwrite_with_backup", surface=surface)
                )
            # "keep-existing" -> no action, but the decision above is
            # still persisted so a later run doesn't re-ask.

    if errors:
        return Plan(ok=False, actions=[], errors=errors)
    return Plan(
        ok=True,
        actions=actions,
        errors=[],
        collision_decisions=collision_decisions,
    )


def journal_status(journal_path: Path) -> dict[str, Any]:
    journal_path = Path(journal_path)
    if not journal_path.exists():
        return {"pending": False, "summary": []}
    data: dict[str, Any] = json.loads(journal_path.read_text())
    return {"pending": True, "summary": data.get("plan_summary", [])}


def _write_journal(journal_path: Path, plan: Plan, base_dir: Path) -> None:
    summary = [
        f"{_rel(a.surface.path, base_dir)}: {a.kind}" for a in plan.actions
    ]
    journal_path.write_text(
        json.dumps({"plan_summary": summary}, indent=2) + "\n"
    )


def apply_plan(
    plan: Plan,
    state: dict[str, Any],
    base_dir: Path,
    journal_path: Path,
    install_id: str,
) -> dict[str, Any]:
    """Apply every action in a validated (plan.ok) plan, journaling
    before mutation. Returns the updated state dict — the caller is
    responsible for calling save_state() with it, and ONLY THEN
    deleting journal_path (this function deliberately does not delete
    it — see spec section 6's crash-consistency requirement: the
    journal must survive a crash between this returning and the
    caller's save_state() call, so a leftover journal always means
    "state may not reflect what's on disk," never "state is fine, some
    other unrelated file happened to still exist.")."""
    if not plan.ok:
        raise ValueError("cannot apply a plan with ok=False")

    _write_journal(Path(journal_path), plan, base_dir)

    for action in plan.actions:
        surface = action.surface
        rel_path = _rel(surface.path, base_dir)

        if action.kind == "upsert_block":
            surface.path.parent.mkdir(parents=True, exist_ok=True)
            existing = (
                surface.path.read_text() if surface.path.exists() else ""
            )
            rendered = bi.upsert_block(
                existing,
                surface.block_id,
                surface.block_version,
                surface.block_body,
            )
            bi.atomic_write(surface.path, rendered)
            block_hash = bi.sha256_bytes(
                bi.render_block(
                    surface.block_id,
                    surface.block_version,
                    surface.block_body,
                ).encode()
            )
            state["managed_blocks"] = [
                b for b in state["managed_blocks"] if b["file"] != rel_path
            ] + [{
                "file": rel_path,
                "block_id": surface.block_id,
                "rendered_version": surface.block_version,
                "rendered_sha256": block_hash,
            }]

        elif action.kind == "create":
            surface.path.parent.mkdir(parents=True, exist_ok=True)
            bi.atomic_write(surface.path, surface.content)

        elif action.kind == "overwrite_with_backup":
            backup = resolve_backup_path(
                surface.path,
                state,
                install_id=install_id,
                base_dir=base_dir,
            )
            if not backup.exists():
                backup.write_bytes(surface.path.read_bytes())
            backup_hash = sha256_of_file(backup)
            bi.atomic_write(surface.path, surface.content)
            written_hash = bi.sha256_bytes(surface.content.encode())
            state["overwritten_files"] = [
                f for f in state["overwritten_files"] if f["file"] != rel_path
            ] + [{
                "file": rel_path,
                "backup": _rel(backup, base_dir),
                "written_sha256": written_hash,
                "backup_sha256": backup_hash,
            }]

    # Collision decisions (both "overwrite" and "keep-existing") were
    # already captured at plan time in plan.collision_decisions, using
    # the pre-existing file's hash — merge them in here rather than
    # recomputing anything from post-mutation state.
    for decision in plan.collision_decisions:
        item = decision["item"]
        state["collision_decisions"] = [
            d for d in state["collision_decisions"] if d["item"] != item
        ] + [decision]

    return state


def _load_surfaces_spec(spec_path: Path) -> list[Surface]:
    """spec_path is a JSON file harness-link.sh writes describing what to
    install: a list of {"path", "is_block_surface", "block_body" or
    "content", "block_id", "block_version"} objects. Keeping this as a
    file (not argv) avoids shell-escaping rendered markdown bodies."""
    raw = json.loads(Path(spec_path).read_text())
    return [
        Surface(
            path=Path(r["path"]),
            **{k: v for k, v in r.items() if k != "path"},
        )
        for r in raw
    ]


def uninstall_all(state: dict[str, Any], base_dir: Path) -> list[str]:
    """Reverse every managed block and overwritten file recorded in
    state, per the spec's per-file-class uninstall semantics. Returns a
    list of human-readable log lines for harness-link.sh to print."""
    log: list[str] = []

    for entry in state.get("managed_blocks", []):
        path = base_dir / entry["file"]
        if not path.exists():
            log.append(f"{entry['file']}: no longer exists, nothing to remove")
            continue
        content = path.read_text()
        removed = bi.remove_block(content, entry["block_id"])
        if removed != content:
            bi.atomic_write(path, removed)
            log.append(f"{entry['file']}: removed managed block")
        else:
            log.append(f"{entry['file']}: block not found, nothing to remove")

    for entry in state.get("overwritten_files", []):
        path = base_dir / entry["file"]
        backup = base_dir / entry["backup"]
        if not path.exists():
            log.append(f"{entry['file']}: deleted since install, nothing to restore")
            continue
        current_hash = sha256_of_file(path)
        if current_hash != entry["written_sha256"]:
            log.append(
                f"{entry['file']}: edited since install — left in place; "
                f"backup available at {entry['backup']}"
            )
            continue
        if not backup.exists():
            msg = f"{entry['file']}: backup missing ({entry['backup']}) — left in place"
            log.append(msg)
            continue
        bi.atomic_write(path, backup.read_text())
        log.append(f"{entry['file']}: restored from backup")

    state["managed_blocks"] = []
    state["overwritten_files"] = []
    return log


def _cli_uninstall(args: Any) -> None:
    state = load_state(Path(args.state))
    log = uninstall_all(state, base_dir=Path(args.base_dir))
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "log": log}))


def _cli_journal_status(args: Any) -> None:
    print(json.dumps(journal_status(Path(args.journal))))


def _cli_plan(args: Any) -> None:
    surfaces = _load_surfaces_spec(args.surfaces)
    state = load_state(Path(args.state))
    base_dir = Path(args.base_dir)
    decisions: list[str] = []

    def decide(item: PlanItem) -> str:
        decisions.append(str(item.path))
        return "report-only"

    plan = build_plan(
        surfaces,
        state,
        install_id=args.install_id,
        base_dir=base_dir,
        decide=decide,
    )
    print(
        json.dumps({
            "ok": plan.ok,
            "errors": plan.errors,
            "actions": [
                {"kind": a.kind, "path": str(a.surface.path)}
                for a in plan.actions
            ],
            "collisions": decisions,
        })
    )


def _cli_apply(args: Any) -> None:
    surfaces = _load_surfaces_spec(args.surfaces)
    state = load_state(Path(args.state))
    base_dir = Path(args.base_dir)

    decisions_map: dict[str, str] = {}
    if args.decisions:
        decisions_map = json.loads(Path(args.decisions).read_text())

    def decide(item: PlanItem) -> str:
        return decisions_map.get(str(item.path), "keep-existing")

    plan = build_plan(
        surfaces,
        state,
        install_id=args.install_id,
        base_dir=base_dir,
        decide=decide,
    )
    if not plan.ok:
        print(json.dumps({"ok": False, "errors": plan.errors}))
        raise SystemExit(1)

    journal_path = Path(args.journal)
    updated_state = apply_plan(
        plan,
        state=state,
        base_dir=base_dir,
        journal_path=journal_path,
        install_id=args.install_id,
    )
    save_state(Path(args.state), updated_state)
    # Only delete the journal after state has actually been persisted —
    # if the process crashes between apply_plan() returning and this
    # line, the journal must still be here for 'doctor' to find.
    journal_path.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "applied": len(plan.actions)}))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="install_transaction.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_journal = sub.add_parser(
        "journal-status", help="Report a leftover crash journal, if any."
    )
    p_journal.add_argument("--journal", required=True)
    p_journal.set_defaults(func=_cli_journal_status)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--surfaces", required=True)
    p_plan.add_argument("--state", required=True)
    p_plan.add_argument("--base-dir", required=True)
    p_plan.add_argument("--install-id", required=True)
    p_plan.set_defaults(func=_cli_plan)

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--surfaces", required=True)
    p_apply.add_argument("--state", required=True)
    p_apply.add_argument("--base-dir", required=True)
    p_apply.add_argument("--install-id", required=True)
    p_apply.add_argument("--journal", required=True)
    p_apply.add_argument("--decisions", default=None)
    p_apply.set_defaults(func=_cli_apply)

    p_uninstall = sub.add_parser("uninstall")
    p_uninstall.add_argument("--state", required=True)
    p_uninstall.add_argument("--base-dir", required=True)
    p_uninstall.set_defaults(func=_cli_uninstall)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
