"""Unit tests for change range hashing."""

from __future__ import annotations

from agentharness.policy.change_range import (
    ChangedFile,
    _canonical_sort,
    _empty_range,
    _parse_diff_output,
)


class TestChangeRange:
    def test_empty_range_is_deterministic(self) -> None:
        r1 = _empty_range()
        r2 = _empty_range()
        assert r1.range_hash == r2.range_hash

    def test_different_files_produce_different_hash(self) -> None:
        files_a = [ChangedFile(path="src/a.py", status="M")]
        files_b = [ChangedFile(path="src/b.py", status="M")]
        import hashlib
        hash_a = hashlib.sha256(_canonical_sort(files_a).encode()).hexdigest()
        hash_b = hashlib.sha256(_canonical_sort(files_b).encode()).hexdigest()
        assert hash_a != hash_b

    def test_same_files_same_hash(self) -> None:
        files = [ChangedFile(path="src/a.py", status="M")]
        import hashlib
        h1 = hashlib.sha256(_canonical_sort(files).encode()).hexdigest()
        h2 = hashlib.sha256(_canonical_sort(files).encode()).hexdigest()
        assert h1 == h2

    def test_parse_diff_output(self) -> None:
        output = "M\tsrc/a.py\nA\tsrc/b.py\n"
        files = _parse_diff_output(output)
        assert len(files) == 2
        statuses = {f.status for f in files}
        assert "M" in statuses
        assert "A" in statuses
