"""Byte-preserving marker-block insert/replace/remove for
harness-link.sh's existing-surface integration (see
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md).

Pure functions only — no filesystem I/O beyond atomic_write, no state,
no CLI. Orchestration lives in install_transaction.py.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


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

    if len(begins) != len(ends):
        raise MarkerError(
            f"unmatched agentharness begin/end marker for id={block_id!r}"
        )
    if not begins:
        return []

    if len(begins) > 1:
        # Multiple blocks: check if they're nested or just multiple independent
        if begins[1][0] < ends[0][0]:
            raise MarkerError(
                f"nested or reversed agentharness markers for id={block_id!r}"
            )
        else:
            raise MarkerError(
                f"multiple agentharness blocks found for id={block_id!r}"
            )

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
