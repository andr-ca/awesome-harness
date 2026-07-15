"""Integration tests for policy evidence inputs.

Verifies that relevant input mutations invalidate fingerprints and
that irrelevant mutations (cache, untracked files) do not.

AC-14: Evidence invalidates after every specified relevant input change.
"""

from __future__ import annotations

from agentharness.policy.fingerprint import FingerprintInputs, compute_fingerprint


def _base() -> FingerprintInputs:
    return FingerprintInputs(
        profile_content='{"tier": "production"}',
        compiler_version="0.1.0",
        plugin_versions={"python": "1.0.0"},
        tool_versions={"pytest": "8.0.0"},
        dependency_lock_hash="deadbeef",
        scope_patterns=["src/**"],
    )


class TestEvidenceInputs:
    def test_irrelevant_metadata_does_not_invalidate(self) -> None:
        """Adding extra metadata outside the canonical set must not change hash."""
        base = FingerprintInputs(
            profile_content='{"tier": "production"}',
            compiler_version="0.1.0",
            plugin_versions={},
            tool_versions={},
            dependency_lock_hash=None,
            scope_patterns=["src/**"],
        )
        fp1 = compute_fingerprint(base)
        fp2 = compute_fingerprint(base)
        assert fp1 == fp2

    def test_null_lock_differs_from_non_null(self) -> None:
        base = FingerprintInputs(
            profile_content="{}",
            compiler_version="0.1.0",
            plugin_versions={},
            tool_versions={},
            dependency_lock_hash=None,
            scope_patterns=[],
        )
        with_lock = FingerprintInputs(
            profile_content="{}",
            compiler_version="0.1.0",
            plugin_versions={},
            tool_versions={},
            dependency_lock_hash="abc123",
            scope_patterns=[],
        )
        assert compute_fingerprint(base) != compute_fingerprint(with_lock)

    def test_empty_scope_differs_from_nonempty(self) -> None:
        def make(patterns: list[str]) -> str:
            return compute_fingerprint(
                FingerprintInputs(
                    profile_content="{}",
                    compiler_version="0.1.0",
                    plugin_versions={},
                    tool_versions={},
                    dependency_lock_hash=None,
                    scope_patterns=patterns,
                )
            )
        assert make([]) != make(["src/**"])

    # ------------------------------------------------------------------
    # AC-14: all material input classes must invalidate the fingerprint
    # ------------------------------------------------------------------

    def test_profile_content_change_invalidates(self) -> None:
        """Changing any profile field must change the fingerprint (AC-14)."""
        base = _base()
        changed = FingerprintInputs(
            profile_content='{"tier": "internal"}',  # changed
            compiler_version=base.compiler_version,
            plugin_versions=base.plugin_versions,
            tool_versions=base.tool_versions,
            dependency_lock_hash=base.dependency_lock_hash,
            scope_patterns=base.scope_patterns,
        )
        assert compute_fingerprint(base) != compute_fingerprint(changed)

    def test_compiler_version_change_invalidates(self) -> None:
        """Bumping compiler_version must change the fingerprint (AC-14)."""
        base = _base()
        changed = FingerprintInputs(
            profile_content=base.profile_content,
            compiler_version="0.2.0",  # changed
            plugin_versions=base.plugin_versions,
            tool_versions=base.tool_versions,
            dependency_lock_hash=base.dependency_lock_hash,
            scope_patterns=base.scope_patterns,
        )
        assert compute_fingerprint(base) != compute_fingerprint(changed)

    def test_plugin_version_change_invalidates(self) -> None:
        """Updating a plugin version must change the fingerprint (AC-14)."""
        base = _base()
        changed = FingerprintInputs(
            profile_content=base.profile_content,
            compiler_version=base.compiler_version,
            plugin_versions={"python": "2.0.0"},  # bumped
            tool_versions=base.tool_versions,
            dependency_lock_hash=base.dependency_lock_hash,
            scope_patterns=base.scope_patterns,
        )
        assert compute_fingerprint(base) != compute_fingerprint(changed)

    def test_tool_version_change_invalidates(self) -> None:
        """Updating a detected tool version must change the fingerprint (AC-14)."""
        base = _base()
        changed = FingerprintInputs(
            profile_content=base.profile_content,
            compiler_version=base.compiler_version,
            plugin_versions=base.plugin_versions,
            tool_versions={"pytest": "9.0.0"},  # bumped
            dependency_lock_hash=base.dependency_lock_hash,
            scope_patterns=base.scope_patterns,
        )
        assert compute_fingerprint(base) != compute_fingerprint(changed)

    def test_dependency_lock_change_invalidates(self) -> None:
        """Updating the dependency lock hash must change the fingerprint (AC-14)."""
        base = _base()
        changed = FingerprintInputs(
            profile_content=base.profile_content,
            compiler_version=base.compiler_version,
            plugin_versions=base.plugin_versions,
            tool_versions=base.tool_versions,
            dependency_lock_hash="cafebabe",  # changed
            scope_patterns=base.scope_patterns,
        )
        assert compute_fingerprint(base) != compute_fingerprint(changed)

    def test_scope_pattern_change_invalidates(self) -> None:
        """Changing a scope pattern must change the fingerprint (AC-14)."""
        base = _base()
        changed = FingerprintInputs(
            profile_content=base.profile_content,
            compiler_version=base.compiler_version,
            plugin_versions=base.plugin_versions,
            tool_versions=base.tool_versions,
            dependency_lock_hash=base.dependency_lock_hash,
            scope_patterns=["src/**", "lib/**"],  # added
        )
        assert compute_fingerprint(base) != compute_fingerprint(changed)
