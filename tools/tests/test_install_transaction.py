"""Tests for install_transaction.py: state schema v2, collision
classification, backups, preflight plan construction, and the crash
journal used by harness-link.sh's existing-surface integration.
"""
import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "setup" / "install_transaction.py"
spec = importlib.util.spec_from_file_location("install_transaction", MODULE_PATH)
it = importlib.util.module_from_spec(spec)
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
