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
