"""Tests for block_installer.py: byte-preserving marker block insert/
replace/remove used by harness-link.sh's existing-surface integration.
"""
import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "setup" / "block_installer.py"
spec = importlib.util.spec_from_file_location("block_installer", MODULE_PATH)
bi = importlib.util.module_from_spec(spec)
sys.modules["block_installer"] = bi
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
