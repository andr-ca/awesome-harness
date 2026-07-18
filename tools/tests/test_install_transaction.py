"""Tests for install_transaction.py: state schema v2, collision
classification, backups, preflight plan construction, and the crash
journal used by harness-link.sh's existing-surface integration.
"""
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "setup" / "install_transaction.py"
spec = importlib.util.spec_from_file_location("install_transaction", MODULE_PATH)
it = importlib.util.module_from_spec(spec)
sys.modules["install_transaction"] = it
spec.loader.exec_module(it)


def test_load_state_migrates_v1_to_v2(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    state_path.write_text(json.dumps({"version": 1, "mode": "link", "skills": []}))
    data = it.load_state(state_path)
    assert data["schema_version"] == 2
    assert data["managed_blocks"] == []
    assert data["overwritten_files"] == []
    assert data["collision_decisions"] == []
    # v1 fields survive untouched
    assert data["mode"] == "link"


def test_load_state_missing_file_returns_fresh_v2_skeleton(tmp_path):
    data = it.load_state(tmp_path / "does-not-exist.json")
    assert data["schema_version"] == 2
    assert data["managed_blocks"] == []


def test_load_state_already_v2_is_passthrough(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    original = {
        "schema_version": 2, "mode": "link", "skills": [],
        "managed_blocks": [{"file": "AGENTS.md", "block_id": "core-instructions",
                             "rendered_version": "0.2.1", "rendered_sha256": "abc"}],
        "overwritten_files": [], "collision_decisions": [],
    }
    state_path.write_text(json.dumps(original))
    assert it.load_state(state_path) == original


def test_save_state_writes_valid_json(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    data = it.load_state(state_path)
    data["mode"] = "link"
    it.save_state(state_path, data)
    reloaded = json.loads(state_path.read_text())
    assert reloaded["mode"] == "link"
    assert reloaded["schema_version"] == 2


def test_classify_path_block_managed_when_supported_instructions_file(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("# existing\n")
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.BLOCK_MANAGED


def test_classify_path_absent_file_is_block_managed_too(tmp_path):
    target = tmp_path / "AGENTS.md"
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.BLOCK_MANAGED


def test_classify_path_whole_file_collision_when_generated_surface_occupied(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer's own rule\n")
    result = it.classify_path(target, is_block_surface=False)
    assert result == it.Classification.WHOLE_FILE_COLLISION


def test_classify_path_absent_whole_file_surface_is_no_collision(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    assert it.classify_path(target, is_block_surface=False) == it.Classification.CREATE


def test_classify_path_symlink_is_hard_fail(tmp_path):
    real = tmp_path / "real.md"
    real.write_text("x\n")
    link = tmp_path / "AGENTS.md"
    link.symlink_to(real)
    assert it.classify_path(link, is_block_surface=True) == it.Classification.HARD_FAIL


def test_classify_path_directory_is_hard_fail(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.mkdir()
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.HARD_FAIL


def test_classify_path_malformed_markers_is_hard_fail(tmp_path):
    target = tmp_path / "AGENTS.md"
    content = (
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "no end\n"
    )
    target.write_text(content)
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.HARD_FAIL


def test_backup_path_for_creates_unique_suffix(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("x\n")
    backup = it.backup_path_for(target, install_id="a1b2c3")
    assert backup.name == "testing.mdc.pre-agentharness.a1b2c3"


def test_reuse_existing_state_owned_backup_when_hash_matches(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("original\n")
    existing_backup = tmp_path / "rule.mdc.pre-agentharness.deadbeef"
    existing_backup.write_text("original\n")
    state = {"overwritten_files": [
        {"file": "rule.mdc",
         "backup": "rule.mdc.pre-agentharness.deadbeef",
         "written_sha256": it.sha256_of_file(existing_backup)}
    ]}
    result = it.resolve_backup_path(
        target, state, install_id="newid", base_dir=tmp_path
    )
    assert result == existing_backup


def test_new_unique_backup_when_no_state_owned_backup_exists(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("x\n")
    state = {"overwritten_files": []}
    result = it.resolve_backup_path(
        target, state, install_id="newid", base_dir=tmp_path
    )
    assert result.name == "rule.mdc.pre-agentharness.newid"


def test_never_overwrites_existing_backup_file(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("x\n")
    collide = tmp_path / "rule.mdc.pre-agentharness.newid"
    collide.write_text("someone else's file\n")
    state = {"overwritten_files": []}
    result = it.resolve_backup_path(
        target, state, install_id="newid", base_dir=tmp_path
    )
    assert result != collide
    assert not result.exists()


def test_build_plan_reports_hard_fail_with_zero_mutations(tmp_path):
    target = tmp_path / "AGENTS.md"
    content = (
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "no end\n"
    )
    target.write_text(content)
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path,
        decide=lambda item: None
    )
    assert plan.ok is False
    assert plan.actions == []
    assert any("AGENTS.md" in e for e in plan.errors)


def test_build_plan_block_managed_surface_plans_upsert(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path,
        decide=lambda item: None
    )
    assert plan.ok is True
    assert len(plan.actions) == 1
    assert plan.actions[0].kind == "upsert_block"


def test_build_plan_whole_file_collision_calls_decide_callback(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]

    decisions = []
    def decide(item):
        decisions.append(item.path)
        return "overwrite"

    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=decide
    )
    assert plan.ok is True
    assert decisions == [target]
    assert plan.actions[0].kind == "overwrite_with_backup"


def test_build_plan_keep_existing_decision_skips_write(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path,
        decide=lambda item: "keep-existing"
    )
    assert plan.ok is True
    assert plan.actions == []


def test_build_plan_reuses_persisted_decision_when_hash_matches(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    state = {"collision_decisions": [
        {"item": ".cursor/rules/testing.mdc", "kind": "whole-file",
         "choice": "keep-existing",
         "existing_sha256": it.sha256_of_file(target),
         "decided_at": "2026-01-01T00:00:00Z"}
    ]}
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    called = []
    plan = it.build_plan(
        surfaces, state=state, install_id="x", base_dir=tmp_path,
        decide=lambda item: called.append(item) or "overwrite"
    )
    # decide() never invoked — persisted decision honored
    assert called == []
    assert plan.actions == []


def test_build_plan_stale_decision_recalls_decide(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("changed content\n")
    state = {"collision_decisions": [
        {"item": ".cursor/rules/testing.mdc", "kind": "whole-file",
         "choice": "keep-existing",
         "existing_sha256": "stale-hash-does-not-match",
         "decided_at": "2026-01-01T00:00:00Z"}
    ]}
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    called = []
    it.build_plan(
        surfaces, state=state, install_id="x", base_dir=tmp_path,
        decide=lambda item: called.append(item) or "keep-existing"
    )
    assert len(called) == 1


def test_apply_plan_writes_journal_then_removes_it_on_success(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=lambda i: None
    )
    journal_path = tmp_path / ".agentharness-state.pending.json"
    state = it.load_state(tmp_path / ".agentharness-state.json")
    it.apply_plan(
        plan, state=state, base_dir=tmp_path, journal_path=journal_path,
        install_id="x"
    )
    assert target.read_text().count("agentharness:begin") == 1
    assert not journal_path.exists()


def test_apply_plan_records_managed_block_in_state(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=lambda i: None
    )
    state = it.load_state(tmp_path / ".agentharness-state.json")
    updated = it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="x"
    )
    assert len(updated["managed_blocks"]) == 1
    assert updated["managed_blocks"][0]["file"] == "AGENTS.md"


def test_apply_plan_overwrite_with_backup_records_backup_and_decision(
    tmp_path
):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="abc123", base_dir=tmp_path,
        decide=lambda i: "overwrite"
    )
    state = it.load_state(tmp_path / ".agentharness-state.json")
    updated = it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="abc123"
    )
    assert target.read_text() == "harness content\n"
    backup = tmp_path / ".cursor" / "rules" / "testing.mdc.pre-agentharness.abc123"
    assert backup.read_text() == "consumer content\n"
    assert len(updated["overwritten_files"]) == 1
    assert len(updated["collision_decisions"]) == 1


def test_journal_status_reports_leftover_journal(tmp_path):
    journal_path = tmp_path / ".agentharness-state.pending.json"
    journal_path.write_text(
        json.dumps(
            {"plan_summary": ["AGENTS.md: upsert_block"]}
        )
    )
    status = it.journal_status(journal_path)
    assert status["pending"] is True
    assert "AGENTS.md" in status["summary"][0]


def test_journal_status_clean_when_no_journal(tmp_path):
    status = it.journal_status(
        tmp_path / ".agentharness-state.pending.json"
    )
    assert status["pending"] is False


def test_cli_journal_status_via_subprocess(tmp_path):
    import subprocess

    journal_path = tmp_path / ".agentharness-state.pending.json"
    result = subprocess.run(
        [
            "python3",
            str(MODULE_PATH),
            "journal-status",
            "--journal",
            str(journal_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["pending"] is False


def test_rel_handles_relative_paths(tmp_path):
    # Regression test: _rel() should handle both absolute and relative paths
    # without raising ValueError (matches resolve_backup_path() behavior)
    rel_path = Path("cursor/rules/testing.mdc")
    result = it._rel(rel_path, tmp_path)
    assert result == "cursor/rules/testing.mdc"
    # Also verify absolute paths still work
    abs_path = tmp_path / "AGENTS.md"
    result = it._rel(abs_path, tmp_path)
    assert result == "AGENTS.md"


def test_cli_plan_reports_actions_via_subprocess(tmp_path):
    import subprocess

    surfaces_spec = tmp_path / "surfaces.json"
    surfaces_spec.write_text(
        json.dumps([
            {
                "path": str(tmp_path / "AGENTS.md"),
                "is_block_surface": True,
                "block_body": "rendered\n",
                "block_id": "core-instructions",
                "block_version": "0.2.1",
            }
        ])
    )
    result = subprocess.run(
        [
            "python3",
            str(MODULE_PATH),
            "plan",
            "--surfaces",
            str(surfaces_spec),
            "--state",
            str(tmp_path / ".agentharness-state.json"),
            "--base-dir",
            str(tmp_path),
            "--install-id",
            "abc",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["actions"][0]["kind"] == "upsert_block"


def test_cli_apply_writes_file_via_subprocess(tmp_path):
    import subprocess

    surfaces_spec = tmp_path / "surfaces.json"
    target = tmp_path / "AGENTS.md"
    surfaces_spec.write_text(
        json.dumps([
            {
                "path": str(target),
                "is_block_surface": True,
                "block_body": "rendered\n",
                "block_id": "core-instructions",
                "block_version": "0.2.1",
            }
        ])
    )
    result = subprocess.run(
        [
            "python3",
            str(MODULE_PATH),
            "apply",
            "--surfaces",
            str(surfaces_spec),
            "--state",
            str(tmp_path / ".agentharness-state.json"),
            "--base-dir",
            str(tmp_path),
            "--install-id",
            "abc",
            "--journal",
            str(tmp_path / ".agentharness-state.pending.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "agentharness:begin" in target.read_text()


def test_apply_plan_creates_parent_dirs_for_upsert_block(tmp_path):
    # Regression test: upsert_block should create parent directories
    # (e.g., .github/) if they don't exist yet
    target = tmp_path / ".github" / "copilot-instructions.md"
    assert not (tmp_path / ".github").exists()
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=lambda i: None
    )
    state = it.load_state(tmp_path / ".agentharness-state.json")
    it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="x"
    )
    assert target.exists()
    assert "agentharness:begin" in target.read_text()
