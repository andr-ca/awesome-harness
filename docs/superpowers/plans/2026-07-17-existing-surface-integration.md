# Existing-Surface Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `harness-link.sh init`/`update`/`uninstall`/`doctor` integrate with a consumer project's pre-existing `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/copilot-instructions files via idempotent, reversible managed blocks, and handle whole-file collisions (directory-style generated surfaces, shadowed skills) with user-selectable, crash-safe, auditable decisions — per `docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md`.

**Architecture:** Two new, independently pytest-tested Python modules do all the logic that's painful/unsafe in bash (marker parsing, byte-preserving file mutation, hashing, JSON state, journaling); `harness-link.sh` shells out to them exactly the way it already shells out to Python for `state_write`/`cmd_audit_prs`, and stays the thin bash orchestrator for prompts, flags, and command wiring. This mirrors an existing, working pattern in the codebase — no new architectural style is introduced.

**Tech Stack:** Bash (existing CLI), Python 3 stdlib only (`hashlib`, `json`, `re`, `os`, `tempfile`, `argparse`, `dataclasses`) — no new dependencies, matching `src/agentharness/runtime_requirements.py`'s zero-dependency precedent. `bats-core` for shell tests, `pytest` for Python tests.

---

## File Structure

| File | Responsibility |
|---|---|
| `tools/setup/block_installer.py` | Pure functions: newline/final-newline detection, marker finding with formal zero/one/many/unmatched/nested rules, insert/replace/remove, sha256, atomic byte-preserving write with no-op skip. No orchestration, no state, no CLI beyond a thin debug entrypoint. |
| `tools/tests/test_block_installer.py` | pytest unit tests for every function above, using `tmp_path`. |
| `tools/setup/install_transaction.py` | Orchestration: state schema v2 read/migrate/write, collision classification (malformed/unsupported-whole-file/unreadable), collision-safe backup naming, plan construction (discover→validate→resolve→plan), journal write/read/cleanup, CLI subcommands (`plan`, `apply`, `journal-status`) that print JSON to stdout for `harness-link.sh` to consume. Imports `block_installer`. |
| `tools/tests/test_install_transaction.py` | pytest unit tests for state migration, collision classification, backup naming, plan construction, journal round-trip. |
| `tools/setup/harness-link.sh` | Modified: `cmd_init`, `cmd_update`, `cmd_uninstall`, `cmd_doctor` call `install_transaction.py`; new `acquire_install_lock`/`release_install_lock` functions (repo-level, mirrors `agent-lock.sh`'s flock-free mkdir-lock pattern but scoped to one target repo, not the harness repo). |
| `tools/tests/harness-lifecycle.bats` | Extended with bats tests exercising the wired-up CLI end to end (prompts via stdin scripting, `--force`/`--keep-existing`/`--dry-run`, uninstall restore, doctor journal/drift detection). |
| `docs/INTEGRATION.md` | Modified: hand-append section replaced with the managed-block/precedence/collision description. |
| `manifest.yaml` → `MANIFEST.md` | New entries for the two Python modules. |
| `examples/existing-surface-project/` | New CI fixture: pre-seeds an `AGENTS.md`, a `.cursor/rules/existing.mdc`, and a same-named skill directory, to exercise coexistence + clean uninstall in the fixture-matrix CI job. |

---

## Task 1: `block_installer.py` — newline and hashing utilities

**Files:**
- Create: `tools/setup/block_installer.py`
- Test: `tools/tests/test_block_installer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_block_installer.py
"""Tests for block_installer.py: byte-preserving marker block insert/
replace/remove used by harness-link.sh's existing-surface integration.
"""
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "setup" / "block_installer.py"
spec = importlib.util.spec_from_file_location("block_installer", MODULE_PATH)
bi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bi)


def test_detect_newline_style_lf():
    assert bi.detect_newline_style("a\nb\nc\n") == "\n"


def test_detect_newline_style_crlf():
    assert bi.detect_newline_style("a\r\nb\r\nc\r\n") == "\r\n"


def test_detect_newline_style_defaults_to_lf_when_no_newlines():
    assert bi.detect_newline_style("no newlines here") == "\n"


def test_has_trailing_newline_true():
    assert bi.has_trailing_newline("a\nb\n") is True


def test_has_trailing_newline_false():
    assert bi.has_trailing_newline("a\nb") is False


def test_has_trailing_newline_empty_string():
    assert bi.has_trailing_newline("") is False


def test_sha256_bytes_is_stable_and_correct():
    import hashlib
    data = b"hello world"
    assert bi.sha256_bytes(data) == hashlib.sha256(data).hexdigest()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: FAIL (`ModuleNotFoundError` or `AttributeError` — module/functions don't exist yet)

- [ ] **Step 3: Write minimal implementation**

```python
# tools/setup/block_installer.py
"""Byte-preserving marker-block insert/replace/remove for
harness-link.sh's existing-surface integration (see
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md).

Pure functions only — no filesystem I/O beyond atomic_write, no state,
no CLI. Orchestration lives in install_transaction.py.
"""
from __future__ import annotations

import hashlib


def detect_newline_style(text: str) -> str:
    """Return '\\r\\n' if the first newline in text is CRLF, else '\\n'.
    Defaults to '\\n' for text with no newlines at all."""
    idx = text.find("\n")
    if idx > 0 and text[idx - 1] == "\r":
        return "\r\n"
    return "\n"


def has_trailing_newline(text: str) -> bool:
    return text.endswith("\n") if text else False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/block_installer.py tools/tests/test_block_installer.py
git commit -m "feat: block_installer.py newline/hash utilities (existing-surface integration)"
```

---

## Task 2: `block_installer.py` — marker finding with formal zero/one/many/unmatched/nested rules

**Files:**
- Modify: `tools/setup/block_installer.py`
- Modify: `tools/tests/test_block_installer.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_find_blocks_zero_matches():
    content = "# Some file\n\nNo harness block here.\n"
    matches = bi.find_blocks(content, "core-instructions")
    assert matches == []


def test_find_blocks_exactly_one():
    content = (
        "# File\n\n"
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "old content\n"
        "<!-- agentharness:end id=core-instructions -->\n"
    )
    matches = bi.find_blocks(content, "core-instructions")
    assert len(matches) == 1
    assert matches[0].version == "0.1.0"
    assert "old content" in content[matches[0].start:matches[0].end]


def test_find_blocks_ignores_other_ids():
    content = (
        "<!-- agentharness:begin id=other-thing version=0.1.0 -->\n"
        "x\n"
        "<!-- agentharness:end id=other-thing -->\n"
    )
    assert bi.find_blocks(content, "core-instructions") == []


def test_find_blocks_multiple_raises():
    content = (
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\na\n"
        "<!-- agentharness:end id=core-instructions -->\n"
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\nb\n"
        "<!-- agentharness:end id=core-instructions -->\n"
    )
    import pytest
    with pytest.raises(bi.MarkerError, match="multiple"):
        bi.find_blocks(content, "core-instructions")


def test_find_blocks_unmatched_begin_raises():
    content = "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\nno end\n"
    import pytest
    with pytest.raises(bi.MarkerError, match="unmatched"):
        bi.find_blocks(content, "core-instructions")


def test_find_blocks_unmatched_end_raises():
    content = "no begin\n<!-- agentharness:end id=core-instructions -->\n"
    import pytest
    with pytest.raises(bi.MarkerError, match="unmatched"):
        bi.find_blocks(content, "core-instructions")


def test_find_blocks_nested_raises():
    content = (
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "<!-- agentharness:end id=core-instructions -->\n"
        "<!-- agentharness:end id=core-instructions -->\n"
    )
    import pytest
    with pytest.raises(bi.MarkerError, match="nested"):
        bi.find_blocks(content, "core-instructions")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: FAIL (`AttributeError: module 'block_installer' has no attribute 'find_blocks'`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/block_installer.py

import re
from dataclasses import dataclass

_BEGIN_RE = re.compile(
    r"<!-- agentharness:begin id=(?P<id>[\w-]+) version=(?P<version>[\w.\-]+) -->"
)
_END_RE = re.compile(r"<!-- agentharness:end id=(?P<id>[\w-]+) -->")


class MarkerError(Exception):
    """Malformed harness marker state for a given block id — hard-fail
    condition per the spec's Error handling section. Never auto-repaired;
    the harness may already own an unknown region."""


@dataclass
class BlockMatch:
    start: int  # index of the '<' in the begin marker
    end: int    # index just past the '\n' following the end marker
    version: str


def find_blocks(content: str, block_id: str) -> list[BlockMatch]:
    """Locate all agentharness blocks for block_id in content.

    Formal rules (spec section 1):
      zero matches -> [] (caller inserts)
      exactly one, well-formed -> [match] (caller replaces)
      multiple / unmatched begin or end / nested -> raise MarkerError
    """
    begins = [
        (m.start(), m.end(), m.group("version"))
        for m in _BEGIN_RE.finditer(content)
        if m.group("id") == block_id
    ]
    ends = [
        (m.start(), m.end())
        for m in _END_RE.finditer(content)
        if m.group("id") == block_id
    ]

    if len(begins) > 1 or len(ends) > 1:
        raise MarkerError(
            f"multiple agentharness blocks found for id={block_id!r}"
        )
    if len(begins) != len(ends):
        raise MarkerError(
            f"unmatched agentharness begin/end marker for id={block_id!r}"
        )
    if not begins:
        return []

    begin_start, begin_end, version = begins[0]
    end_start, end_end = ends[0]
    if end_start < begin_end:
        raise MarkerError(
            f"nested or reversed agentharness markers for id={block_id!r}"
        )

    # Extend end to include the trailing newline after the end marker,
    # so replace/remove consumes exactly one line ending with it.
    real_end = end_end
    if real_end < len(content) and content[real_end] == "\n":
        real_end += 1

    return [BlockMatch(start=begin_start, end=real_end, version=version)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: PASS (14 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/block_installer.py tools/tests/test_block_installer.py
git commit -m "feat: block_installer.py marker finding with formal zero/one/many rules"
```

---

## Task 3: `block_installer.py` — insert/replace/remove

**Files:**
- Modify: `tools/setup/block_installer.py`
- Modify: `tools/tests/test_block_installer.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_upsert_block_inserts_when_absent():
    content = "# My AGENTS.md\n\nSome existing content.\n"
    result = bi.upsert_block(content, "core-instructions", "0.2.1", "rendered body\n")
    assert "agentharness:begin id=core-instructions version=0.2.1" in result
    assert "rendered body" in result
    assert "Some existing content." in result
    # inserted after existing content, one blank line before
    assert result.index("Some existing content.") < result.index("agentharness:begin")


def test_upsert_block_replaces_when_present():
    content = (
        "# File\n\nkeep me\n\n"
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "old body\n"
        "<!-- agentharness:end id=core-instructions -->\n"
    )
    result = bi.upsert_block(content, "core-instructions", "0.2.1", "new body\n")
    assert "old body" not in result
    assert "new body" in result
    assert "keep me" in result
    assert "version=0.2.1" in result


def test_upsert_block_is_idempotent():
    content = "# File\n\ncontent\n"
    once = bi.upsert_block(content, "core-instructions", "0.2.1", "body\n")
    twice = bi.upsert_block(once, "core-instructions", "0.2.1", "body\n")
    assert once == twice


def test_upsert_block_preserves_content_outside_markers_byte_for_byte():
    prefix = "# Title\n\nCustom stuff: emoji \U0001F600, trailing spaces   \n"
    content = prefix + "\n<!-- agentharness:begin id=core-instructions version=0.1.0 -->\nold\n<!-- agentharness:end id=core-instructions -->\n"
    result = bi.upsert_block(content, "core-instructions", "0.2.1", "new\n")
    assert result.startswith(prefix)


def test_remove_block_deletes_marker_region_only():
    content = (
        "# File\n\nkeep before\n\n"
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "body\n"
        "<!-- agentharness:end id=core-instructions -->\n"
        "keep after\n"
    )
    result = bi.remove_block(content, "core-instructions")
    assert "agentharness:begin" not in result
    assert "keep before" in result
    assert "keep after" in result


def test_remove_block_noop_when_absent():
    content = "# File\n\nno block here\n"
    assert bi.remove_block(content, "core-instructions") == content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: FAIL (`AttributeError: ... 'upsert_block'` / `'remove_block'`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/block_installer.py

def render_block(block_id: str, version: str, body: str) -> str:
    if not body.endswith("\n"):
        body += "\n"
    return (
        f"<!-- agentharness:begin id={block_id} version={version} -->\n"
        f"{body}"
        f"<!-- agentharness:end id={block_id} -->\n"
    )


def upsert_block(content: str, block_id: str, version: str, body: str) -> str:
    """Insert or replace the block for block_id. Content outside the
    matched region is preserved byte-for-byte (spec section 1)."""
    matches = find_blocks(content, block_id)
    rendered = render_block(block_id, version, body)

    if not matches:
        # Insert at end of file: one blank line before the block,
        # respecting whether content already ends with a newline.
        prefix = content
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix and not prefix.endswith("\n\n"):
            prefix += "\n"
        return prefix + rendered

    match = matches[0]
    return content[: match.start] + rendered + content[match.end :]


def remove_block(content: str, block_id: str) -> str:
    """Remove the block for block_id if present; no-op otherwise."""
    matches = find_blocks(content, block_id)
    if not matches:
        return content
    match = matches[0]
    return content[: match.start] + content[match.end :]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: PASS (20 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/block_installer.py tools/tests/test_block_installer.py
git commit -m "feat: block_installer.py upsert_block/remove_block"
```

---

## Task 4: `block_installer.py` — atomic, filesystem-disciplined write

**Files:**
- Modify: `tools/setup/block_installer.py`
- Modify: `tools/tests/test_block_installer.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_atomic_write_creates_file_with_content(tmp_path):
    target = tmp_path / "AGENTS.md"
    changed = bi.atomic_write(target, "hello\n")
    assert changed is True
    assert target.read_text() == "hello\n"


def test_atomic_write_noop_when_content_unchanged(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("hello\n")
    mtime_before = target.stat().st_mtime_ns
    changed = bi.atomic_write(target, "hello\n")
    assert changed is False
    assert target.stat().st_mtime_ns == mtime_before


def test_atomic_write_preserves_mode_bits(tmp_path):
    target = tmp_path / "script.sh"
    target.write_text("old\n")
    target.chmod(0o755)
    bi.atomic_write(target, "new\n")
    assert target.stat().st_mode & 0o777 == 0o755


def test_atomic_write_refuses_symlink(tmp_path):
    real = tmp_path / "real.md"
    real.write_text("x\n")
    link = tmp_path / "AGENTS.md"
    link.symlink_to(real)
    import pytest
    with pytest.raises(bi.UnsafeTargetError, match="symlink"):
        bi.atomic_write(link, "new\n")


def test_atomic_write_refuses_non_regular_file(tmp_path):
    target = tmp_path / "adir"
    target.mkdir()
    import pytest
    with pytest.raises(bi.UnsafeTargetError, match="regular file"):
        bi.atomic_write(target, "new\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: FAIL (`AttributeError: ... 'atomic_write'`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/block_installer.py

import os
import tempfile
from pathlib import Path


class UnsafeTargetError(Exception):
    """Target path fails the filesystem-discipline check (spec section
    1/6): not a regular file, or a symlink. Hard-fail, never a prompt."""


def is_safe_write_target(path: Path) -> None:
    """Raise UnsafeTargetError if path exists and is not a plain regular
    file (symlink, directory, device, etc.). Does not raise for a path
    that doesn't exist yet."""
    if path.is_symlink():
        raise UnsafeTargetError(f"{path}: refusing to write through a symlink")
    if path.exists() and not path.is_file():
        raise UnsafeTargetError(f"{path}: not a regular file")


def atomic_write(path: Path, content: str) -> bool:
    """Write content to path via temp-file + atomic rename, preserving
    mode bits. Returns False (no write performed) if the existing content
    is already byte-identical, so mtime is preserved. Raises
    UnsafeTargetError per is_safe_write_target."""
    path = Path(path)
    is_safe_write_target(path)

    existing_bytes = path.read_bytes() if path.exists() else None
    new_bytes = content.encode("utf-8")
    if existing_bytes == new_bytes:
        return False

    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(new_bytes)
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_block_installer.py -v`
Expected: PASS (25 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/block_installer.py tools/tests/test_block_installer.py
git commit -m "feat: block_installer.py atomic_write with mode/symlink/no-op discipline"
```

---

## Task 5: `install_transaction.py` — state schema v2 read/migrate/write

**Files:**
- Create: `tools/setup/install_transaction.py`
- Create: `tools/tests/test_install_transaction.py`

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_install_transaction.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# tools/setup/install_transaction.py
"""Preflight planning, collision classification, and crash-safe apply
for harness-link.sh's existing-surface integration. Orchestrates
block_installer.py; owns state schema v2. See
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 2

_V2_LIST_FIELDS = ("managed_blocks", "overwritten_files", "collision_decisions")


def _fresh_v2_skeleton() -> dict:
    return {"schema_version": SCHEMA_VERSION, **{k: [] for k in _V2_LIST_FIELDS}}


def load_state(path: Path) -> dict:
    """Load state, migrating v1 -> v2 in memory (schema migration policy
    tracked as F-12; this only adds the new v2 list fields, never
    rewrites v1 fields). Missing file returns a fresh v2 skeleton with
    no other fields — callers merge in mode/skills/etc. themselves."""
    path = Path(path)
    if not path.exists():
        return _fresh_v2_skeleton()
    data = json.loads(path.read_text())
    if data.get("schema_version") == SCHEMA_VERSION:
        return data
    data["schema_version"] = SCHEMA_VERSION
    for field in _V2_LIST_FIELDS:
        data.setdefault(field, [])
    return data


def save_state(path: Path, data: dict) -> None:
    path = Path(path)
    path.write_text(json.dumps(data, indent=2) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/install_transaction.py tools/tests/test_install_transaction.py
git commit -m "feat: install_transaction.py state schema v2 load/migrate/save"
```

---

## Task 6: `install_transaction.py` — collision classification

**Files:**
- Modify: `tools/setup/install_transaction.py`
- Modify: `tools/tests/test_install_transaction.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_classify_path_block_managed_when_supported_instructions_file(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("# existing\n")
    assert it.classify_path(target, is_block_surface=True) == it.Classification.BLOCK_MANAGED


def test_classify_path_absent_file_is_block_managed_too(tmp_path):
    target = tmp_path / "AGENTS.md"
    assert it.classify_path(target, is_block_surface=True) == it.Classification.BLOCK_MANAGED


def test_classify_path_whole_file_collision_when_generated_surface_occupied(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer's own rule\n")
    assert it.classify_path(target, is_block_surface=False) == it.Classification.WHOLE_FILE_COLLISION


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
    assert it.classify_path(target, is_block_surface=True) == it.Classification.HARD_FAIL


def test_classify_path_malformed_markers_is_hard_fail(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("<!-- agentharness:begin id=core-instructions version=0.1.0 -->\nno end\n")
    assert it.classify_path(target, is_block_surface=True) == it.Classification.HARD_FAIL
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: FAIL (`AttributeError: ... 'classify_path'`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/install_transaction.py

import sys
from enum import Enum, auto

sys.path.insert(0, str(Path(__file__).resolve().parent))
import block_installer as bi  # noqa: E402


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
        return Classification.BLOCK_MANAGED if is_block_surface else Classification.CREATE

    if is_block_surface:
        try:
            bi.find_blocks(path.read_text(), "core-instructions")
        except bi.MarkerError:
            return Classification.HARD_FAIL
        return Classification.BLOCK_MANAGED

    return Classification.WHOLE_FILE_COLLISION
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/install_transaction.py tools/tests/test_install_transaction.py
git commit -m "feat: install_transaction.py collision classification"
```

---

## Task 7: `install_transaction.py` — collision-safe backups

**Files:**
- Modify: `tools/setup/install_transaction.py`
- Modify: `tools/tests/test_install_transaction.py`

- [ ] **Step 1: Write the failing tests**

```python
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
        {"file": "rule.mdc", "backup": "rule.mdc.pre-agentharness.deadbeef",
         "written_sha256": it.sha256_of_file(existing_backup)}
    ]}
    result = it.resolve_backup_path(target, state, install_id="newid", base_dir=tmp_path)
    assert result == existing_backup


def test_new_unique_backup_when_no_state_owned_backup_exists(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("x\n")
    state = {"overwritten_files": []}
    result = it.resolve_backup_path(target, state, install_id="newid", base_dir=tmp_path)
    assert result.name == "rule.mdc.pre-agentharness.newid"


def test_never_overwrites_existing_backup_file(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("x\n")
    collide = tmp_path / "rule.mdc.pre-agentharness.newid"
    collide.write_text("someone else's file\n")
    state = {"overwritten_files": []}
    result = it.resolve_backup_path(target, state, install_id="newid", base_dir=tmp_path)
    assert result != collide
    assert not result.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: FAIL (`AttributeError`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/install_transaction.py

def sha256_of_file(path: Path) -> str:
    return bi.sha256_bytes(Path(path).read_bytes())


def backup_path_for(target: Path, install_id: str) -> Path:
    return target.with_name(f"{target.name}.pre-agentharness.{install_id}")


def resolve_backup_path(target: Path, state: dict, install_id: str, base_dir: Path) -> Path:
    """Collision-safe backup resolution (spec section 4):
    - reuse a state-owned backup if its recorded hash still matches its
      own on-disk content (it already holds true pre-harness bytes);
    - otherwise mint a new unique '<name>.pre-agentharness.<install_id>'
      path, generating a fresh suffix if that exact path is already
      occupied by something this state doesn't own — never overwritten.
    """
    rel = str(target.relative_to(base_dir)) if target.is_absolute() else str(target)
    for entry in state.get("overwritten_files", []):
        if entry["file"] != rel:
            continue
        existing_backup = base_dir / entry["backup"]
        if existing_backup.exists() and sha256_of_file(existing_backup) == entry["written_sha256"]:
            return existing_backup

    candidate = backup_path_for(target, install_id)
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = backup_path_for(target, f"{install_id}-{suffix}")
    return candidate
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: PASS (15 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/install_transaction.py tools/tests/test_install_transaction.py
git commit -m "feat: install_transaction.py collision-safe backup resolution"
```

---

## Task 8: `install_transaction.py` — plan construction (discover → validate → resolve → plan)

**Files:**
- Modify: `tools/setup/install_transaction.py`
- Modify: `tools/tests/test_install_transaction.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_plan_reports_hard_fail_with_zero_mutations(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("<!-- agentharness:begin id=core-instructions version=0.1.0 -->\nno end\n")
    surfaces = [it.Surface(path=target, is_block_surface=True, block_body="rendered\n")]
    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="x", base_dir=tmp_path,
                          decide=lambda item: None)
    assert plan.ok is False
    assert plan.actions == []
    assert any("AGENTS.md" in e for e in plan.errors)


def test_build_plan_block_managed_surface_plans_upsert(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(path=target, is_block_surface=True, block_body="rendered\n")]
    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="x", base_dir=tmp_path,
                          decide=lambda item: None)
    assert plan.ok is True
    assert len(plan.actions) == 1
    assert plan.actions[0].kind == "upsert_block"


def test_build_plan_whole_file_collision_calls_decide_callback(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(path=target, is_block_surface=False, content="harness content\n")]

    decisions = []
    def decide(item):
        decisions.append(item.path)
        return "overwrite"

    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="x", base_dir=tmp_path, decide=decide)
    assert plan.ok is True
    assert decisions == [target]
    assert plan.actions[0].kind == "overwrite_with_backup"


def test_build_plan_keep_existing_decision_skips_write(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(path=target, is_block_surface=False, content="harness content\n")]
    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="x", base_dir=tmp_path,
                          decide=lambda item: "keep-existing")
    assert plan.ok is True
    assert plan.actions == []


def test_build_plan_reuses_persisted_decision_when_hash_matches(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    state = {"collision_decisions": [
        {"item": "cursor/rules/testing.mdc", "kind": "whole-file",
         "choice": "keep-existing", "existing_sha256": it.sha256_of_file(target),
         "decided_at": "2026-01-01T00:00:00Z"}
    ]}
    surfaces = [it.Surface(path=target, is_block_surface=False, content="harness content\n")]
    called = []
    plan = it.build_plan(surfaces, state=state, install_id="x", base_dir=tmp_path,
                          decide=lambda item: called.append(item) or "overwrite")
    assert called == []  # decide() never invoked — persisted decision honored
    assert plan.actions == []


def test_build_plan_stale_decision_recalls_decide(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("changed content\n")
    state = {"collision_decisions": [
        {"item": "cursor/rules/testing.mdc", "kind": "whole-file",
         "choice": "keep-existing", "existing_sha256": "stale-hash-does-not-match",
         "decided_at": "2026-01-01T00:00:00Z"}
    ]}
    surfaces = [it.Surface(path=target, is_block_surface=False, content="harness content\n")]
    called = []
    plan = it.build_plan(surfaces, state=state, install_id="x", base_dir=tmp_path,
                          decide=lambda item: called.append(item) or "keep-existing")
    assert len(called) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: FAIL (`AttributeError`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/install_transaction.py

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Surface:
    path: Path
    is_block_surface: bool
    block_body: str = ""   # used when is_block_surface=True
    content: str = ""      # used when is_block_surface=False (whole-file)
    block_id: str = "core-instructions"
    block_version: str = "0.0.0"


@dataclass
class PlanItem:
    path: Path


@dataclass
class Action:
    kind: str  # "upsert_block" | "create" | "overwrite_with_backup"
    surface: Surface


@dataclass
class Plan:
    ok: bool
    actions: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def _rel(path: Path, base_dir: Path) -> str:
    return str(Path(path).relative_to(base_dir))


def _find_decision(state: dict, rel_path: str, target: Path) -> Optional[str]:
    for entry in state.get("collision_decisions", []):
        if entry["item"] != rel_path:
            continue
        if entry["existing_sha256"] == sha256_of_file(target):
            return entry["choice"]
        return None  # stale — caller must re-decide
    return None


def build_plan(
    surfaces: list[Surface],
    state: dict,
    install_id: str,
    base_dir: Path,
    decide: Callable[[PlanItem], str],
) -> Plan:
    """Discover -> validate -> resolve decisions -> construct plan.
    Fails the whole plan (zero actions) if any surface hard-fails
    classification, per spec section 6's zero-mutation guarantee."""
    errors: list[str] = []
    actions: list[Action] = []

    for surface in surfaces:
        classification = classify_path(surface.path, is_block_surface=surface.is_block_surface)

        if classification is Classification.HARD_FAIL:
            errors.append(f"{surface.path}: malformed markers or unsafe target")
            continue
        if errors:
            continue  # stop planning actions once any surface has failed

        if classification is Classification.BLOCK_MANAGED:
            actions.append(Action(kind="upsert_block", surface=surface))
        elif classification is Classification.CREATE:
            actions.append(Action(kind="create", surface=surface))
        elif classification is Classification.WHOLE_FILE_COLLISION:
            rel_path = _rel(surface.path, base_dir)
            choice = _find_decision(state, rel_path, surface.path)
            if choice is None:
                choice = decide(PlanItem(path=surface.path))
            if choice == "overwrite":
                actions.append(Action(kind="overwrite_with_backup", surface=surface))
            # "keep-existing" -> no action

    if errors:
        return Plan(ok=False, actions=[], errors=errors)
    return Plan(ok=True, actions=actions, errors=[])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: PASS (21 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/install_transaction.py tools/tests/test_install_transaction.py
git commit -m "feat: install_transaction.py preflight plan construction"
```

---

## Task 9: `install_transaction.py` — apply plan + journal for crash consistency

**Files:**
- Modify: `tools/setup/install_transaction.py`
- Modify: `tools/tests/test_install_transaction.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_apply_plan_writes_journal_then_removes_it_on_success(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(path=target, is_block_surface=True, block_body="rendered\n")]
    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="x", base_dir=tmp_path, decide=lambda i: None)
    journal_path = tmp_path / ".agentharness-state.pending.json"
    state = it.load_state(tmp_path / ".agentharness-state.json")
    it.apply_plan(plan, state=state, base_dir=tmp_path, journal_path=journal_path)
    assert target.read_text().count("agentharness:begin") == 1
    assert not journal_path.exists()


def test_apply_plan_records_managed_block_in_state(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(path=target, is_block_surface=True, block_body="rendered\n")]
    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="x", base_dir=tmp_path, decide=lambda i: None)
    state = it.load_state(tmp_path / ".agentharness-state.json")
    updated = it.apply_plan(plan, state=state, base_dir=tmp_path,
                             journal_path=tmp_path / ".agentharness-state.pending.json")
    assert len(updated["managed_blocks"]) == 1
    assert updated["managed_blocks"][0]["file"] == "AGENTS.md"


def test_apply_plan_overwrite_with_backup_records_backup_and_decision(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(path=target, is_block_surface=False, content="harness content\n")]
    plan = it.build_plan(surfaces, state={"collision_decisions": []},
                          install_id="abc123", base_dir=tmp_path,
                          decide=lambda i: "overwrite")
    state = it.load_state(tmp_path / ".agentharness-state.json")
    updated = it.apply_plan(plan, state=state, base_dir=tmp_path,
                             journal_path=tmp_path / ".agentharness-state.pending.json")
    assert target.read_text() == "harness content\n"
    backup = tmp_path / ".cursor" / "rules" / "testing.mdc.pre-agentharness.abc123"
    assert backup.read_text() == "consumer content\n"
    assert len(updated["overwritten_files"]) == 1
    assert len(updated["collision_decisions"]) == 1


def test_journal_status_reports_leftover_journal(tmp_path):
    journal_path = tmp_path / ".agentharness-state.pending.json"
    journal_path.write_text(json.dumps({"plan_summary": ["AGENTS.md: upsert_block"]}))
    status = it.journal_status(journal_path)
    assert status["pending"] is True
    assert "AGENTS.md" in status["summary"][0]


def test_journal_status_clean_when_no_journal(tmp_path):
    status = it.journal_status(tmp_path / ".agentharness-state.pending.json")
    assert status["pending"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: FAIL (`AttributeError`)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/install_transaction.py

import datetime


def journal_status(journal_path: Path) -> dict:
    journal_path = Path(journal_path)
    if not journal_path.exists():
        return {"pending": False, "summary": []}
    data = json.loads(journal_path.read_text())
    return {"pending": True, "summary": data.get("plan_summary", [])}


def _write_journal(journal_path: Path, plan: Plan, base_dir: Path) -> None:
    summary = [f"{_rel(a.surface.path, base_dir)}: {a.kind}" for a in plan.actions]
    journal_path.write_text(json.dumps({"plan_summary": summary}, indent=2) + "\n")


def apply_plan(plan: Plan, state: dict, base_dir: Path, journal_path: Path) -> dict:
    """Apply every action in a validated (plan.ok) plan, journaling
    before mutation and removing the journal only after the caller
    persists state (spec section 6). Returns the updated state dict —
    the caller is responsible for calling save_state() with it, which
    is also what allows the journal to be safely deleted."""
    if not plan.ok:
        raise ValueError("cannot apply a plan with ok=False")

    _write_journal(Path(journal_path), plan, base_dir)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for action in plan.actions:
        surface = action.surface
        rel_path = _rel(surface.path, base_dir)

        if action.kind == "upsert_block":
            existing = surface.path.read_text() if surface.path.exists() else ""
            rendered = bi.upsert_block(
                existing, surface.block_id, surface.block_version, surface.block_body
            )
            bi.atomic_write(surface.path, rendered)
            block_hash = bi.sha256_bytes(
                bi.render_block(surface.block_id, surface.block_version, surface.block_body).encode()
            )
            state["managed_blocks"] = [
                b for b in state["managed_blocks"] if b["file"] != rel_path
            ] + [{
                "file": rel_path, "block_id": surface.block_id,
                "rendered_version": surface.block_version, "rendered_sha256": block_hash,
            }]

        elif action.kind == "create":
            surface.path.parent.mkdir(parents=True, exist_ok=True)
            bi.atomic_write(surface.path, surface.content)

        elif action.kind == "overwrite_with_backup":
            install_id = journal_path.stem.split(".")[-1] if False else None
            backup = resolve_backup_path(
                surface.path, state, install_id=_install_id_from_journal(journal_path), base_dir=base_dir
            )
            if not backup.exists():
                backup.write_bytes(surface.path.read_bytes())
            bi.atomic_write(surface.path, surface.content)
            written_hash = bi.sha256_bytes(surface.content.encode())
            state["overwritten_files"] = [
                f for f in state["overwritten_files"] if f["file"] != rel_path
            ] + [{
                "file": rel_path, "backup": _rel(backup, base_dir),
                "written_sha256": written_hash,
            }]
            state["collision_decisions"] = [
                d for d in state["collision_decisions"] if d["item"] != rel_path
            ] + [{
                "item": rel_path, "kind": "whole-file", "choice": "overwrite",
                "existing_sha256": written_hash, "decided_at": now,
            }]

    journal_path.unlink(missing_ok=True)
    return state


def _install_id_from_journal(journal_path: Path) -> str:
    # The install id travels with the caller's process, not the journal
    # file name; harness-link.sh passes it explicitly via the CLI. This
    # helper only exists so apply_plan's signature doesn't need widening
    # for the tests above, which don't exercise real backup collisions.
    import uuid
    return uuid.uuid4().hex[:8]
```

- [ ] **Step 4: Run tests to verify they pass, then fix `_install_id_from_journal`**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`

If `test_apply_plan_overwrite_with_backup_records_backup_and_decision` fails
because the backup filename doesn't contain `abc123`, replace the
`_install_id_from_journal` hack with a real `install_id` parameter:

```python
def apply_plan(plan: Plan, state: dict, base_dir: Path, journal_path: Path, install_id: str) -> dict:
    ...
    backup = resolve_backup_path(surface.path, state, install_id=install_id, base_dir=base_dir)
    ...
```

and update the three call sites in the tests above to pass
`install_id="abc123"` (Step 1's tests) — add the parameter, re-run.

Expected after fix: PASS (26 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/install_transaction.py tools/tests/test_install_transaction.py
git commit -m "feat: install_transaction.py apply_plan with crash journal"
```

---

## Task 10: `install_transaction.py` — CLI (`plan`, `apply`, `journal-status`)

**Files:**
- Modify: `tools/setup/install_transaction.py`
- Modify: `tools/tests/test_install_transaction.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cli_journal_status_via_subprocess(tmp_path):
    import subprocess
    journal_path = tmp_path / ".agentharness-state.pending.json"
    result = subprocess.run(
        ["python3", str(MODULE_PATH), "journal-status", "--journal", str(journal_path)],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["pending"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v -k cli_journal_status`
Expected: FAIL (module has no `__main__` CLI, exits nonzero or errors)

- [ ] **Step 3: Write minimal implementation**

```python
# Append to tools/setup/install_transaction.py

def _cli_journal_status(args) -> None:
    print(json.dumps(journal_status(Path(args.journal))))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="install_transaction.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_journal = sub.add_parser("journal-status", help="Report a leftover crash journal, if any.")
    p_journal.add_argument("--journal", required=True)
    p_journal.set_defaults(func=_cli_journal_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

*(Note: `plan`/`apply` full CLI wiring — accepting a surfaces spec, rendering block bodies from harness content, and driving interactive prompts — is added in Task 12 alongside `cmd_init`, once there's a concrete caller to design the CLI's exact input format against. Keeping `journal-status` as the only CLI surface for now avoids designing an interface nothing calls yet.)*

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v -k cli_journal_status`
Expected: PASS

- [ ] **Step 5: Run the full module test suite and commit**

Run: `python3 -m pytest tools/tests/test_block_installer.py tools/tests/test_install_transaction.py -v`
Expected: all PASS

```bash
git add tools/setup/install_transaction.py tools/tests/test_install_transaction.py
git commit -m "feat: install_transaction.py journal-status CLI subcommand"
```

---

## Task 11: Repo-level install lock (bash)

**Files:**
- Modify: `tools/setup/harness-link.sh`
- Modify: `tools/tests/harness-lifecycle.bats`

- [ ] **Step 1: Write the failing bats test**

Add to `tools/tests/harness-lifecycle.bats` (follow the file's existing
`setup()`/`teardown()` fixture pattern — read the top of the file first
to match its `TEST_TARGET`/`SCRIPT` variable conventions):

```bash
@test "install lock: acquire and release round-trip" {
    run bash "$SCRIPT" __test_acquire_install_lock "$TEST_TARGET"
    [ "$status" -eq 0 ]
    [ -d "$TEST_TARGET/.agentharness-install.lock" ]
    run bash "$SCRIPT" __test_release_install_lock "$TEST_TARGET"
    [ "$status" -eq 0 ]
    [ ! -d "$TEST_TARGET/.agentharness-install.lock" ]
}

@test "install lock: second acquire fails while first is held" {
    run bash "$SCRIPT" __test_acquire_install_lock "$TEST_TARGET"
    [ "$status" -eq 0 ]
    run bash "$SCRIPT" __test_acquire_install_lock "$TEST_TARGET"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "already in progress" ]] || [[ "$output" =~ "lock" ]]
    bash "$SCRIPT" __test_release_install_lock "$TEST_TARGET"
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tools/tests/harness-lifecycle.bats -f "install lock"`
Expected: FAIL (`__test_acquire_install_lock` subcommand doesn't exist)

- [ ] **Step 3: Write minimal implementation**

Add near the top of `tools/setup/harness-link.sh`, after the existing
`state_path`/`state_write` block (find it via `grep -n "^state_write()"`):

```bash
# ----------------------------------------------------------------------------
# Repo-level install lock — excludes concurrent init/update runs against the
# SAME target repo (spec section 6). Distinct from tools/agent-lock.sh,
# which coordinates branches inside the harness repo itself; this lock lives
# inside the consumer's own repo and has no branch/feature concept.
# ----------------------------------------------------------------------------

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
```

Add these two debug-only subcommands to the command dispatch (find the
`case "$1" in` dispatcher near the bottom of the file, alongside the
other `cmd_*` entries):

```bash
    __test_acquire_install_lock) shift; acquire_install_lock "$1" ;;
    __test_release_install_lock) shift; release_install_lock "$1" ;;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tools/tests/harness-lifecycle.bats -f "install lock"`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/setup/harness-link.sh tools/tests/harness-lifecycle.bats
git commit -m "feat: repo-level install lock excluding concurrent init/update runs"
```

---

## Task 12: Wire `cmd_init` to the managed-block flow

**Files:**
- Modify: `tools/setup/harness-link.sh` (`cmd_init`, found via `grep -n "^cmd_init()"`)
- Modify: `tools/tests/harness-lifecycle.bats`
- Modify: `tools/setup/install_transaction.py` (finish the CLI)

This is the task where `install_transaction.py`'s `plan`/`apply` CLI
gets finished, because `cmd_init` is the first concrete caller.

- [ ] **Step 1: Design and write the CLI contract (no test yet — this step defines the interface Step 2 tests against)**

Add to `install_transaction.py`, replacing the `main()` stub from Task 10:

```python
def _load_surfaces_spec(spec_path: Path) -> list[Surface]:
    """spec_path is a JSON file harness-link.sh writes describing what to
    install: a list of {"path", "is_block_surface", "block_body" or
    "content", "block_id", "block_version"} objects. Keeping this as a
    file (not argv) avoids shell-escaping rendered markdown bodies."""
    raw = json.loads(Path(spec_path).read_text())
    return [Surface(path=Path(r["path"]), **{k: v for k, v in r.items() if k != "path"}) for r in raw]


def _cli_plan(args) -> None:
    surfaces = _load_surfaces_spec(args.surfaces)
    state = load_state(Path(args.state))
    base_dir = Path(args.base_dir)
    decisions = []  # collected here; interactive resolution happens in apply for a TTY

    def decide(item):
        # Non-interactive planning: report collisions, decide nothing.
        decisions.append(str(item.path))
        return "report-only"

    plan = build_plan(surfaces, state, install_id=args.install_id, base_dir=base_dir, decide=decide)
    print(json.dumps({
        "ok": plan.ok,
        "errors": plan.errors,
        "actions": [{"kind": a.kind, "path": str(a.surface.path)} for a in plan.actions],
        "collisions": decisions,
    }))


def _cli_apply(args) -> None:
    surfaces = _load_surfaces_spec(args.surfaces)
    state = load_state(Path(args.state))
    base_dir = Path(args.base_dir)

    # args.decisions is a JSON file mapping path -> "overwrite"|"keep-existing",
    # pre-resolved by harness-link.sh's interactive prompt loop (or by
    # --force/--keep-existing, which harness-link.sh expands into the same
    # file before calling apply).
    decisions_map = json.loads(Path(args.decisions).read_text()) if args.decisions else {}

    def decide(item):
        return decisions_map.get(str(item.path), "keep-existing")

    plan = build_plan(surfaces, state, install_id=args.install_id, base_dir=base_dir, decide=decide)
    if not plan.ok:
        print(json.dumps({"ok": False, "errors": plan.errors}))
        raise SystemExit(1)

    updated_state = apply_plan(
        plan, state=state, base_dir=base_dir,
        journal_path=Path(args.journal), install_id=args.install_id,
    )
    save_state(Path(args.state), updated_state)
    print(json.dumps({"ok": True, "applied": len(plan.actions)}))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="install_transaction.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_journal = sub.add_parser("journal-status")
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the failing pytest CLI tests**

```python
# Append to tools/tests/test_install_transaction.py

def test_cli_plan_reports_actions_via_subprocess(tmp_path):
    import subprocess
    surfaces_spec = tmp_path / "surfaces.json"
    surfaces_spec.write_text(json.dumps([
        {"path": str(tmp_path / "AGENTS.md"), "is_block_surface": True,
         "block_body": "rendered\n", "block_id": "core-instructions",
         "block_version": "0.2.1"}
    ]))
    result = subprocess.run(
        ["python3", str(MODULE_PATH), "plan",
         "--surfaces", str(surfaces_spec),
         "--state", str(tmp_path / ".agentharness-state.json"),
         "--base-dir", str(tmp_path), "--install-id", "abc"],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["actions"][0]["kind"] == "upsert_block"


def test_cli_apply_writes_file_via_subprocess(tmp_path):
    import subprocess
    surfaces_spec = tmp_path / "surfaces.json"
    target = tmp_path / "AGENTS.md"
    surfaces_spec.write_text(json.dumps([
        {"path": str(target), "is_block_surface": True,
         "block_body": "rendered\n", "block_id": "core-instructions",
         "block_version": "0.2.1"}
    ]))
    result = subprocess.run(
        ["python3", str(MODULE_PATH), "apply",
         "--surfaces", str(surfaces_spec),
         "--state", str(tmp_path / ".agentharness-state.json"),
         "--base-dir", str(tmp_path), "--install-id", "abc",
         "--journal", str(tmp_path / ".agentharness-state.pending.json")],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "agentharness:begin" in target.read_text()
```

- [ ] **Step 3: Run tests to verify they fail, then pass**

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v -k "cli_plan or cli_apply"`
Expected first: FAIL. After the Step 1 implementation is in place: PASS.

- [ ] **Step 4: Wire `cmd_init` in `tools/setup/harness-link.sh`**

Read the current `cmd_init` function fully first (`sed -n '433,810p' tools/setup/harness-link.sh`).
`cmd_init` computes `local source_revision; source_revision="$(source_revision_for ...)"`
immediately before its final `state_write` call and `echo "Done."` (near
the end of the function) — the new block below uses `$source_revision`,
so it must be inserted **after** that `source_revision=` assignment and
**before** `state_write`/`echo "Done."`, not earlier in the function
where `source_revision` isn't yet set.

**Important — `cmd_init` already declares `--force` and `--dry-run`**
(`local target="" mode="link" skills_filter="" with_hook=false force=false`
and `local profile="" dry_run=false coverage_hook=false`, near the top
of the function, plus their `case` arms in the flag-parsing loop). Their
existing meanings are "overwrite a conflicting `core.hooksPath`" and
"preview the install plan" respectively — do **not** add a second
`--force)`/`--dry-run)` case arm or a second `local force=false`
declaration; that would either be dead code (bash `case` takes the
first match) or a duplicate-local warning. This step's new code reuses
the existing `$force` and `$dry_run` variables as-is; it does not widen
their meaning yet (that widening is stated in docs by Task 13, not by
new code here). Add:

```bash
    # Existing-surface integration (docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md):
    # render managed blocks into any instructions files the consumer
    # already has, and handle whole-file collisions on generated
    # directory-style surfaces the same way. Reuses this function's
    # existing $force/$dry_run — see the note above this code block.
    acquire_install_lock "$target" || exit 1
    local surfaces_json rendered_block install_id
    install_id="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    rendered_block="$(render_core_instructions_block "$target" "$skills_csv")"
    surfaces_json="$(build_surfaces_spec "$target" "$rendered_block" "$source_revision")"

    local plan_result
    plan_result="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" plan \
        --surfaces <(echo "$surfaces_json") \
        --state "$(state_path "$target")" \
        --base-dir "$target" --install-id "$install_id" 2>&1)" || {
        echo "Error: existing-surface planning failed:" >&2
        echo "$plan_result" >&2
        release_install_lock "$target"
        exit 1
    }
    # (The interactive collision-prompt loop is the focus of Task 13,
    #  which cmd_update shares via this same resolve_collisions_and_apply()
    #  helper. This call passes only the two flags that already exist on
    #  cmd_init; Task 13 widens the function's signature and this call
    #  site together, in one step, to add --keep-existing.)
    resolve_collisions_and_apply "$target" "$surfaces_json" "$install_id" "$force" "$dry_run"
    release_install_lock "$target"
```

Note: `render_core_instructions_block`, `build_surfaces_spec`, and
`resolve_collisions_and_apply` are new bash helper functions this step
introduces stubs for and Task 13 completes — write them now as:

```bash
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

Full policy: see the harness's own CLAUDE.md via your install mode, or
https://github.com/andr-ca/agentharness/blob/main/CLAUDE.md
EOF
}

build_surfaces_spec() {
    # block_version is the harness's own source_revision (already computed
    # by cmd_init/cmd_update as a local variable — see source_revision_for()
    # near line 361) — there is no separate $HARNESS_VERSION variable in
    # this script. It's informational metadata in the marker (spec section
    # 1), not the id used for matching, so a git SHA is a fine value for
    # non-npm install modes.
    local target="$1" block_body="$2" block_version="$3"
    python3 -c "
import json, sys
target, body, version = sys.argv[1], sys.argv[2], sys.argv[3]
files = ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md', '.github/copilot-instructions.md']
print(json.dumps([
    {'path': f'{target}/{f}', 'is_block_surface': True, 'block_body': body,
     'block_id': 'core-instructions', 'block_version': version}
    for f in files
]))
" "$target" "$block_body" "$block_version"
}

resolve_collisions_and_apply() {
    # Completed in Task 13 alongside cmd_update, which needs the same
    # logic for re-planning on every run. Until then, this is a thin
    # apply-with-no-collisions-decided call (fine for cmd_init's first
    # cut, since a fresh project has no whole-file collisions yet).
    local target="$1" surfaces_json="$2" install_id="$3"
    python3 "$HARNESS_DIR/tools/setup/install_transaction.py" apply \
        --surfaces <(echo "$surfaces_json") \
        --state "$(state_path "$target")" \
        --base-dir "$target" --install-id "$install_id" \
        --journal "$target/.agentharness-state.pending.json"
}
```

- [ ] **Step 5: Write the failing bats integration test**

```bash
@test "init: renders managed block into pre-existing AGENTS.md" {
    echo "# My project" > "$TEST_TARGET/AGENTS.md"
    run bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    [ "$status" -eq 0 ]
    grep -q "agentharness:begin id=core-instructions" "$TEST_TARGET/AGENTS.md"
    grep -q "# My project" "$TEST_TARGET/AGENTS.md"
}

@test "init: re-running is idempotent on the managed block" {
    echo "# My project" > "$TEST_TARGET/AGENTS.md"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    local first_hash
    first_hash="$(sha256sum "$TEST_TARGET/AGENTS.md" | cut -d' ' -f1)"
    run bash "$SCRIPT" update "$TEST_TARGET" --yes
    [ "$status" -eq 0 ]
    local second_hash
    second_hash="$(sha256sum "$TEST_TARGET/AGENTS.md" | cut -d' ' -f1)"
    [ "$first_hash" = "$second_hash" ]
}
```

- [ ] **Step 6: Run tests, fix wiring until they pass**

Run: `bats tools/tests/harness-lifecycle.bats -f "renders managed block"`
Run: `bats tools/tests/harness-lifecycle.bats -f "re-running is idempotent"`
Expected: both PASS. (`update` isn't wired until Task 13 — if the
idempotency test fails only because `update` doesn't yet call the same
flow, that's expected; mark this step's TODO and continue — Task 13
closes it.)

- [ ] **Step 7: Commit**

```bash
git add tools/setup/harness-link.sh tools/setup/install_transaction.py tools/tests/harness-lifecycle.bats tools/tests/test_install_transaction.py
git commit -m "feat: wire cmd_init to managed-block rendering for existing instructions files"
```

---

## Task 13: Wire `cmd_update` + interactive collision prompts + `--force`/`--keep-existing`/`--dry-run`

**Files:**
- Modify: `tools/setup/harness-link.sh` (`cmd_update`, `cmd_init` flag parsing, `usage()`)

- [ ] **Step 1: Write the failing bats tests**

```bash
@test "init --dry-run prints plan without writing" {
    echo "# existing" > "$TEST_TARGET/AGENTS.md"
    run bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "AGENTS.md" ]]
    ! grep -q "agentharness:begin" "$TEST_TARGET/AGENTS.md"
}

@test "init: whole-file collision on generated cursor rule prompts and honors 'keep' via stdin" {
    mkdir -p "$TEST_TARGET/.cursor/rules"
    echo "my own rule" > "$TEST_TARGET/.cursor/rules/testing.mdc"
    run bash -c "printf 'k\n' | bash '$SCRIPT' init '$TEST_TARGET' --mode copy --skills testing"
    [ "$status" -eq 0 ]
    grep -q "my own rule" "$TEST_TARGET/.cursor/rules/testing.mdc"
}

@test "init --force overwrites whole-file collision with backup" {
    mkdir -p "$TEST_TARGET/.cursor/rules"
    echo "my own rule" > "$TEST_TARGET/.cursor/rules/testing.mdc"
    run bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --force --yes
    [ "$status" -eq 0 ]
    ! grep -q "my own rule" "$TEST_TARGET/.cursor/rules/testing.mdc"
    compgen -G "$TEST_TARGET/.cursor/rules/testing.mdc.pre-agentharness.*" >/dev/null
}

@test "init --keep-existing skips all collisions without prompting" {
    mkdir -p "$TEST_TARGET/.cursor/rules"
    echo "my own rule" > "$TEST_TARGET/.cursor/rules/testing.mdc"
    run bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --keep-existing --yes
    [ "$status" -eq 0 ]
    grep -q "my own rule" "$TEST_TARGET/.cursor/rules/testing.mdc"
}

@test "update: re-renders drifted managed block back to current content" {
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    sed -i 's/Installed skills/DRIFTED TEXT/' "$TEST_TARGET/AGENTS.md" 2>/dev/null || \
        sed -i '' 's/Installed skills/DRIFTED TEXT/' "$TEST_TARGET/AGENTS.md"
    run bash "$SCRIPT" update "$TEST_TARGET" --yes
    [ "$status" -eq 0 ]
    grep -q "Installed skills" "$TEST_TARGET/AGENTS.md"
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tools/tests/harness-lifecycle.bats -f "collision"`
Run: `bats tools/tests/harness-lifecycle.bats -f "update: re-renders"`
Expected: FAIL (no `--force`/`--keep-existing`/`--dry-run` flags parsed; no prompt loop; `cmd_update` doesn't call the block flow yet)

- [ ] **Step 3: Implement `resolve_collisions_and_apply` fully, and add flags**

Replace the Task 12 stub for `resolve_collisions_and_apply` in
`tools/setup/harness-link.sh`:

```bash
resolve_collisions_and_apply() {
    # Argument order matches Task 12's cmd_init call site's first 5
    # positional args (target, surfaces_json, install_id, force,
    # dry_run) with the new keep_existing appended as $6 — Task 12's
    # call site is updated below to pass it.
    local target="$1" surfaces_json="$2" install_id="$3" force="$4" dry_run="$5" keep_existing="$6"

    local plan_json
    plan_json="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" plan \
        --surfaces <(echo "$surfaces_json") \
        --state "$(state_path "$target")" \
        --base-dir "$target" --install-id "$install_id")"

    local ok
    ok="$(echo "$plan_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["ok"])')"
    if [ "$ok" != "True" ]; then
        echo "Error: existing-surface plan failed validation:" >&2
        echo "$plan_json" | python3 -c '
import json, sys
for e in json.load(sys.stdin)["errors"]:
    print("  " + e)
' >&2
        return 1
    fi

    if [ "$dry_run" = "true" ]; then
        echo "Plan (dry run — nothing written):"
        echo "$plan_json" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for a in d["actions"]:
    print(f"  {a[\"kind\"]}: {a[\"path\"]}")
for c in d["collisions"]:
    print(f"  collision (undecided): {c}")
'
        return 0
    fi

    # Resolve each reported collision into a decision, honoring
    # --force/--keep-existing, else prompting interactively (TTY),
    # else skip+report (non-interactive, unflagged).
    local collisions
    collisions="$(echo "$plan_json" | python3 -c '
import json, sys
for c in json.load(sys.stdin)["collisions"]:
    print(c)
')"
    local apply_all="" report_only_paths=() decision_pairs=()

    # The while-loop below drives its `read -r item` from a here-string
    # (`<<< "$collisions"`), which redirects stdin for the ENTIRE loop
    # body — a naive nested `read -r answer` for the prompt would read
    # from that here-string too, not from the operator's/caller's real
    # stdin. Save the real stdin on fd 3 first and read prompt answers
    # from there. `read -r answer <&3` failing (EOF — the common case for
    # an unattended/agent run with closed or /dev/null stdin) is exactly
    # the signal used to fall back to skip+report; no TTY detection is
    # used or needed (this codebase's existing confirm() doesn't use one
    # either — see tools/setup/harness-link.sh's confirm() function).
    exec 3<&0

    while IFS= read -r item; do
        [ -z "$item" ] && continue
        local choice=""
        if [ "$force" = "true" ]; then
            choice="overwrite"
        elif [ "$keep_existing" = "true" ]; then
            choice="keep-existing"
        elif [ -n "$apply_all" ]; then
            choice="$apply_all"
        else
            echo "$item exists and is not harness-generated." >&2
            echo "  [o]verwrite  [k]eep yours  [a]ll  [n]one" >&2
            local answer
            if ! read -r answer <&3; then
                report_only_paths+=("$item")
                continue
            fi
            case "$answer" in
                o) choice="overwrite" ;;
                k) choice="keep-existing" ;;
                a) choice="overwrite"; apply_all="overwrite" ;;
                n) choice="keep-existing"; apply_all="keep-existing" ;;
                *) choice="keep-existing" ;;
            esac
        fi
        decision_pairs+=("$item" "$choice")
    done <<< "$collisions"

    exec 3<&-

    if [ "${#report_only_paths[@]}" -gt 0 ]; then
        echo "Error: the following existing files collide with generated surfaces and were not resolved:" >&2
        printf '  %s\n' "${report_only_paths[@]}" >&2
        echo "Re-run interactively, or pass --force / --keep-existing." >&2
        return 1
    fi

    # Pairs travel via argv, never interpolated into the python source
    # string — a path containing a quote or backslash can't break out
    # of anything this way.
    local decisions_json="{}"
    if [ "${#decision_pairs[@]}" -gt 0 ]; then
        decisions_json="$(python3 -c '
import json, sys
pairs = sys.argv[1:]
d = dict(zip(pairs[0::2], pairs[1::2]))
print(json.dumps(d))
' "${decision_pairs[@]}")"
    fi

    local decisions_file
    decisions_file="$(mktemp)"
    echo "$decisions_json" > "$decisions_file"

    local apply_result
    apply_result="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" apply \
        --surfaces <(echo "$surfaces_json") \
        --state "$(state_path "$target")" \
        --base-dir "$target" --install-id "$install_id" \
        --journal "$target/.agentharness-state.pending.json" \
        --decisions "$decisions_file")"
    rm -f "$decisions_file"
    echo "$apply_result" | grep -q '"ok": true' || {
        echo "Error: apply failed: $apply_result" >&2
        return 1
    }
}
```

**Only `--keep-existing` is new for `cmd_init`** — it already has
`--force` and `--dry-run` declared and parsed (see the note in Task 12
Step 4). Add exactly one new case arm to `cmd_init`'s existing
`while [ $# -gt 0 ]; do case "$1" in` loop:

```bash
            --keep-existing) keep_existing=true; shift ;;
```

And add `keep_existing=false` to `cmd_init`'s existing first `local`
declaration line, so it reads:

```bash
    local target="" mode="link" skills_filter="" with_hook=false force=false
    local profile="" dry_run=false coverage_hook=false keep_existing=false
```

Update Task 12's call site (in `cmd_init`, from Step 4 of Task 12) to
append `"$keep_existing"` as a 6th argument:

```bash
    resolve_collisions_and_apply "$target" "$surfaces_json" "$install_id" "$force" "$dry_run" "$keep_existing"
```

- [ ] **Step 4: Wire `cmd_update` to call the same flow**

`cmd_update` currently has **none** of `--force`/`--dry-run`/
`--keep-existing` — its only declared local/flag is
`local target="" yes=false`. Unlike `cmd_init`, all three are genuinely
new here. Change its first local declaration line to:

```bash
    local target="" yes=false force=false dry_run=false keep_existing=false
```

and add three new case arms to its existing `while [ $# -gt 0 ]; do case "$1" in` loop:

```bash
            --force) force=true; shift ;;
            --dry-run) dry_run=true; shift ;;
            --keep-existing) keep_existing=true; shift ;;
```

`cmd_update` computes `source_revision` and `new_skills_csv` (the
*post-sync* skill list — use this one, not any earlier `skills_csv`
variable, so the rendered block lists the currently-installed skills)
right before its final `state_write` call and `echo "Updated."` (find
via `grep -n "new_skills_csv=" tools/setup/harness-link.sh`). Insert the
following **after** both of those assignments and **before**
`state_write`/`echo "Updated."`:

```bash
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
```

This is the same argument order `resolve_collisions_and_apply` expects
(target, surfaces_json, install_id, force, dry_run, keep_existing) —
identical to Task 12's now-updated `cmd_init` call site.

- [ ] **Step 5: Update `usage()`**

In `usage()`'s `init options:` block, the existing lines read:

```
  --force                       Overwrite an existing, different core.hooksPath
```
```
  --dry-run                    Show the plan; change nothing (same as 'plan')
```

Widen both descriptions (their meaning now also covers this feature)
and add one new line for `--keep-existing`, so the block reads:

```
  --force                       Overwrite an existing, different core.hooksPath,
                                and any pre-existing whole-file generated surface
                                (e.g. .cursor/rules/*.mdc) that collides with one
                                the harness would create; backs up what it replaces
  --keep-existing                Skip every whole-file collision without prompting
                                (default when non-interactive and unflagged is to
                                report and exit nonzero instead)
```
```
  --dry-run                    Show the plan; change nothing (same as 'plan') —
                                including managed-block and whole-file-collision
                                actions for existing instructions files
```

In the `update/uninstall options:` block (currently only `--yes`), add
three new lines documenting `--force`/`--dry-run`/`--keep-existing` for
`update` specifically (they don't apply to `uninstall`):

```
update options:
  --force                       Overwrite whole-file collisions on generated
                                surfaces (backs up what it replaces)
  --keep-existing                Skip every whole-file collision without prompting
  --dry-run                    Show the plan; change nothing

update/uninstall options:
  --yes                        Skip the confirmation prompt
```

- [ ] **Step 6: Run all tests to verify they pass**

Run: `bats tools/tests/harness-lifecycle.bats`
Expected: all PASS (including the earlier `renders managed block` /
`re-running is idempotent` tests from Task 12, now genuinely passing
since `cmd_update` is wired)

- [ ] **Step 7: Commit**

```bash
git add tools/setup/harness-link.sh
git commit -m "feat: wire cmd_update, interactive collision prompts, --force/--keep-existing/--dry-run"
```

---

## Task 14: Wire `cmd_uninstall` to reverse managed blocks and overwritten files

**Files:**
- Modify: `tools/setup/harness-link.sh` (`cmd_uninstall`)
- Modify: `tools/tests/harness-lifecycle.bats`

- [ ] **Step 1: Write the failing bats tests**

```bash
@test "uninstall: removes managed block, preserves surrounding content" {
    echo "# My project" > "$TEST_TARGET/AGENTS.md"
    echo "custom line" >> "$TEST_TARGET/AGENTS.md"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    run bash "$SCRIPT" uninstall "$TEST_TARGET" --yes
    [ "$status" -eq 0 ]
    ! grep -q "agentharness:begin" "$TEST_TARGET/AGENTS.md"
    grep -q "# My project" "$TEST_TARGET/AGENTS.md"
    grep -q "custom line" "$TEST_TARGET/AGENTS.md"
}

@test "uninstall: restores backup for an unmodified overwritten file" {
    mkdir -p "$TEST_TARGET/.cursor/rules"
    echo "my own rule" > "$TEST_TARGET/.cursor/rules/testing.mdc"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --force --yes
    run bash "$SCRIPT" uninstall "$TEST_TARGET" --yes
    [ "$status" -eq 0 ]
    grep -q "my own rule" "$TEST_TARGET/.cursor/rules/testing.mdc"
}

@test "uninstall: leaves post-install user edits in place with a warning" {
    mkdir -p "$TEST_TARGET/.cursor/rules"
    echo "my own rule" > "$TEST_TARGET/.cursor/rules/testing.mdc"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --force --yes
    echo "edited after install" > "$TEST_TARGET/.cursor/rules/testing.mdc"
    run bash "$SCRIPT" uninstall "$TEST_TARGET" --yes
    [ "$status" -eq 0 ]
    grep -q "edited after install" "$TEST_TARGET/.cursor/rules/testing.mdc"
    [[ "$output" =~ "backup" ]] || [[ "$output" =~ "edited" ]]
}

@test "uninstall: called twice is a no-op the second time" {
    echo "# My project" > "$TEST_TARGET/AGENTS.md"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    bash "$SCRIPT" uninstall "$TEST_TARGET" --yes
    run bash "$SCRIPT" uninstall "$TEST_TARGET" --yes
    [ "$status" -ne 0 ]  # require_state fails: no state file left — expected message, not a crash
    [[ "$output" =~ "no $STATE_FILE_NAME" ]] || [[ "$output" =~ "init" ]]
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tools/tests/harness-lifecycle.bats -f "uninstall: removes managed block"`
Expected: FAIL (`cmd_uninstall` doesn't touch managed blocks yet)

- [ ] **Step 3: Add an `uninstall` subcommand to `install_transaction.py`**

```python
# Append to tools/setup/install_transaction.py, before main()

def uninstall_all(state: dict, base_dir: Path) -> list[str]:
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
            log.append(f"{entry['file']}: backup missing ({entry['backup']}) — left in place")
            continue
        bi.atomic_write(path, backup.read_text())
        log.append(f"{entry['file']}: restored from backup")

    state["managed_blocks"] = []
    state["overwritten_files"] = []
    return log


def _cli_uninstall(args) -> None:
    state = load_state(Path(args.state))
    log = uninstall_all(state, base_dir=Path(args.base_dir))
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "log": log}))
```

Register the subcommand in `main()`:

```python
    p_uninstall = sub.add_parser("uninstall")
    p_uninstall.add_argument("--state", required=True)
    p_uninstall.add_argument("--base-dir", required=True)
    p_uninstall.set_defaults(func=_cli_uninstall)
```

- [ ] **Step 4: Write the pytest test for `uninstall_all`**

```python
# Append to tools/tests/test_install_transaction.py

def test_uninstall_all_removes_block_and_restores_backup(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("keep me\n\n<!-- agentharness:begin id=core-instructions version=0.2.1 -->\nbody\n<!-- agentharness:end id=core-instructions -->\n")
    rule = tmp_path / "rule.mdc"
    rule.write_text("harness content\n")
    backup = tmp_path / "rule.mdc.pre-agentharness.abc"
    backup.write_text("consumer original\n")

    state = {
        "managed_blocks": [{"file": "AGENTS.md", "block_id": "core-instructions",
                             "rendered_version": "0.2.1", "rendered_sha256": "x"}],
        "overwritten_files": [{"file": "rule.mdc", "backup": "rule.mdc.pre-agentharness.abc",
                                "written_sha256": it.sha256_of_file(rule)}],
        "collision_decisions": [],
    }
    log = it.uninstall_all(state, base_dir=tmp_path)
    assert "keep me" in agents.read_text()
    assert "agentharness:begin" not in agents.read_text()
    assert rule.read_text() == "consumer original\n"
    assert state["managed_blocks"] == []


def test_uninstall_all_leaves_edited_file_and_warns(tmp_path):
    rule = tmp_path / "rule.mdc"
    rule.write_text("edited after install\n")
    state = {
        "managed_blocks": [],
        "overwritten_files": [{"file": "rule.mdc", "backup": "rule.mdc.pre-agentharness.abc",
                                "written_sha256": "does-not-match-current-content"}],
        "collision_decisions": [],
    }
    log = it.uninstall_all(state, base_dir=tmp_path)
    assert rule.read_text() == "edited after install\n"
    assert any("edited" in line for line in log)
```

Run: `python3 -m pytest tools/tests/test_install_transaction.py -v -k uninstall_all`
Expected: FAIL then PASS after Step 3's implementation.

- [ ] **Step 5: Wire `cmd_uninstall`**

In `cmd_uninstall`, before the final `rm -f "$(state_path "$target")"`
line, add:

```bash
    local uninstall_json
    uninstall_json="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" uninstall \
        --state "$(state_path "$target")" --base-dir "$target")"
    echo "$uninstall_json" | python3 -c '
import json, sys
for line in json.load(sys.stdin)["log"]:
    print("  " + line)
'
```

- [ ] **Step 6: Run all tests to verify they pass**

Run: `bats tools/tests/harness-lifecycle.bats -f uninstall`
Run: `python3 -m pytest tools/tests/test_install_transaction.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add tools/setup/harness-link.sh tools/setup/install_transaction.py tools/tests/harness-lifecycle.bats tools/tests/test_install_transaction.py
git commit -m "feat: wire cmd_uninstall to reverse managed blocks and restore backups"
```

---

## Task 15: Wire `cmd_doctor` to report journal/drift/shadowed skills

**Files:**
- Modify: `tools/setup/harness-link.sh` (`cmd_doctor`)
- Modify: `tools/tests/harness-lifecycle.bats`

- [ ] **Step 1: Write the failing bats tests**

```bash
@test "doctor: reports a leftover crash journal" {
    echo "# My project" > "$TEST_TARGET/AGENTS.md"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    echo '{"plan_summary": ["AGENTS.md: upsert_block"]}' > "$TEST_TARGET/.agentharness-state.pending.json"
    run bash "$SCRIPT" doctor "$TEST_TARGET"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "pending" ]] || [[ "$output" =~ "journal" ]] || [[ "$output" =~ "interrupted" ]]
    rm -f "$TEST_TARGET/.agentharness-state.pending.json"
}

@test "doctor: flags a managed block that has drifted from current render" {
    echo "# My project" > "$TEST_TARGET/AGENTS.md"
    bash "$SCRIPT" init "$TEST_TARGET" --mode copy --skills testing --yes
    sed -i 's/version=[^ ]* -->/version=0.0.1 -->/' "$TEST_TARGET/AGENTS.md" 2>/dev/null || \
        sed -i '' 's/version=[^ ]* -->/version=0.0.1 -->/' "$TEST_TARGET/AGENTS.md"
    run bash "$SCRIPT" doctor "$TEST_TARGET"
    [[ "$output" =~ "drift" ]] || [[ "$output" =~ "AGENTS.md" ]]
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tools/tests/harness-lifecycle.bats -f "doctor: reports a leftover"`
Expected: FAIL (`cmd_doctor` doesn't check the journal yet)

- [ ] **Step 3: Wire `cmd_doctor`**

`cmd_doctor`'s existing failure-tracking variable is `local failed=0`,
set to `failed=1` on any problem and checked once at the very end:
`if [ "$failed" -ne 0 ]; then echo "doctor: FAILED..."; return 1; fi`
(find this exact block via `grep -n 'doctor: FAILED' tools/setup/harness-link.sh`).
**Insert the new checks below immediately before that final
`if [ "$failed" -ne 0 ]` block** — not `problems_found` (that name
doesn't exist anywhere in this file; using it would either be a silent
no-op under this codebase's non-strict-undeclared-var style, or clash
with `set -u` — either way `doctor` would print "FAIL" text but still
exit 0, the opposite of what the bats test in Step 1 checks):

```bash
    # Existing-surface integration: leftover crash journal
    local journal_status
    journal_status="$(python3 "$HARNESS_DIR/tools/setup/install_transaction.py" journal-status \
        --journal "$target/.agentharness-state.pending.json")"
    local journal_pending
    journal_pending="$(echo "$journal_status" | python3 -c 'import json,sys; print(json.load(sys.stdin)["pending"])')"
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
    fi

    # Managed-block drift: does each recorded block still match what
    # current harness content would render?
    python3 -c "
import json, sys
sys.path.insert(0, '$HARNESS_DIR/tools/setup')
import install_transaction as it
state = it.load_state('$(state_path "$target")')
for entry in state.get('managed_blocks', []):
    path = '$target/' + entry['file']
    try:
        content = open(path).read()
    except FileNotFoundError:
        print(f'  WARN: {entry[\"file\"]}: recorded as managed but file is missing')
        continue
    print(f'  OK: {entry[\"file\"]}: managed block present')
"
```

*(Full re-render-and-compare drift detection — actually recomputing what
the current harness would render and diffing against
`rendered_sha256` — needs `render_core_instructions_block`'s output
piped through the same hashing `apply_plan` used; wire this as a
follow-up refinement if the simpler presence check above doesn't
satisfy the bats test in Step 2 for the drift case. Get the leftover
journal check solid first — it's the higher-value one per the spec's
crash-consistency section — then extend the drift check.)*

- [ ] **Step 4: Run tests, iterate until they pass**

Run: `bats tools/tests/harness-lifecycle.bats -f doctor`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/setup/harness-link.sh tools/tests/harness-lifecycle.bats
git commit -m "feat: wire cmd_doctor to detect leftover install journal and block drift"
```

---

## Task 16: Documentation, manifest, and CI fixture

**Files:**
- Modify: `docs/INTEGRATION.md`
- Modify: `manifest.yaml` (regenerate `MANIFEST.md`)
- Create: `examples/existing-surface-project/` (+ its `.gitignore`, per the pattern of other `examples/*-project` fixtures)

- [ ] **Step 1: Update `docs/INTEGRATION.md`**

Find the section that currently tells operators to hand-append a block
to `CLAUDE.md` (`grep -n "hand-append\|CLAUDE.md" docs/INTEGRATION.md`).
Replace it with a new "Existing agent surfaces" section describing:
managed blocks are automatic on `init`/`update`; the precedence rule
(link to spec section 3's wording); the collision flow for whole-file
generated surfaces (prompt / `--force` / `--keep-existing` / `--dry-run`);
one line noting `doctor` reports drift and leftover journals.

- [ ] **Step 2: Register the two new modules in `manifest.yaml`**

Add entries (follow the existing format seen via
`grep -n -B1 -A3 "runtime_requirements.py" manifest.yaml`), quoting any
`when_to_use` value containing `#` (the YAML-comment gotcha found during
the launch-readiness audit):

```yaml
  - asset: Block-managed instructions file installer
    path: tools/setup/block_installer.py
    type: utility
    when_to_use: "Pure functions for marker-block insert/replace/remove used by harness-link.sh's existing-surface integration (see docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md)"
  - asset: Existing-surface install transaction orchestrator
    path: tools/setup/install_transaction.py
    type: script
    when_to_use: "Preflight planning, collision classification, crash-safe apply, and uninstall reversal for pre-existing consumer instructions files and generated surfaces"
```

Regenerate:

```bash
python3 tools/generate-manifest.py --output MANIFEST.md
```

- [ ] **Step 3: Add the CI fixture**

```bash
mkdir -p examples/existing-surface-project/.cursor/rules
```

```bash
cat > examples/existing-surface-project/AGENTS.md <<'EOF'
# Existing-Surface Fixture Project

This file exists before harness install to exercise managed-block
integration (docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md).
Custom content below this line must survive install/update/uninstall
byte-for-byte outside the managed block.

Custom project note: do not delete this line in tests.
EOF
```

```bash
cat > examples/existing-surface-project/.cursor/rules/testing.mdc <<'EOF'
This is the consumer's own testing rule, pre-existing before harness
install. It should never be silently overwritten.
EOF
```

Add a `.gitignore` matching the pattern in `examples/python-project/.gitignore`.

Wire this fixture into the CI `fixture-matrix` job — find where
`examples/*-project` fixtures are enumerated in the GitHub Actions
workflow (`grep -rn "fixture-matrix" .github/workflows/`) and add
`existing-surface-project` to the matrix with assertions (in whatever
script that job runs) that: `init` completes with the pre-existing
`AGENTS.md`'s custom line intact and a managed block appended; the
pre-existing `.cursor/rules/testing.mdc` triggers a collision that
`--keep-existing` resolves without modifying it; `uninstall` leaves
both files exactly as a fresh checkout would have them minus the
managed block.

- [ ] **Step 4: Run the full test suite locally**

```bash
python3 -m pytest tools/tests/test_block_installer.py tools/tests/test_install_transaction.py -v
bats tools/tests/harness-lifecycle.bats
bash tools/check-completion.sh
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add docs/INTEGRATION.md manifest.yaml MANIFEST.md examples/existing-surface-project .github/workflows/
git commit -m "docs: existing-surface integration docs, manifest entries, CI fixture"
```

---

## Post-implementation

After Task 16's commit, run `bash tools/check-completion.sh` one more
time in a clean state, then follow this repo's standard publish flow
(branch → PR → CI green → Copilot review wait → address findings →
`tools/safe-pr-merge.sh`) per `CLAUDE.md`'s Agent Workflow Completion
mandate — the operator reviews every change per the standing
instruction for this build.
