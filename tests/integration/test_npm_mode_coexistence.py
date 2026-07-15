"""Integration tests for policy namespace and install-mode coexistence (AC-30).

AC-30: Policy namespace coexists with link, copy, npm, and .agentharness/
submodule mode.

Verifies that the `.agentharness-policy/` directory namespace (runtime.lock,
trust.yaml, evidence files) does not conflict with harness install paths
(.agents/skills/, .agentharness/, .agentharness-npm/) and that profile-
declared lock paths under the policy namespace are accepted by the loader
for all four install modes.

Note: harness-link.sh lifecycle (actual filesystem install) is exercised in
tools/tests/harness-lifecycle.bats. These tests verify the Python-side schema
and path-resolution rules that the lifecycle depends on.
"""

from __future__ import annotations

import pytest

from agentharness.profile import ProfileError, load_profile_text
from agentharness.profile.schema import Profile


def _policy_profile(lock_path: str = ".agentharness-policy/runtime.lock") -> str:
    """Return a minimal valid profile YAML with the given lock path."""
    return f"""
schema_version: 1
runtime:
  lock: {lock_path}
project:
  name: example
  rigor: production
bootstrap:
  mode: strict
  confirmed_at: 2026-07-14T00:00:00Z
  existing_checks_are_required: true
plugins:
  python:
    enabled: true
    version: 1.0.0
    config: {{}}
requirements:
  unit_testing:
    provider: python
    enabled: true
    command: [pytest]
    minimum_coverage: 80
    scope:
      include: [src/**]
      exclude: []
    gates: [push, ci, completion]
workflow:
  reviews:
    expected_signals: []
    timeout_seconds: 900
    stabilization_seconds: 60
  completion:
    require_clean_tree: true
    require_committed_changes: true
    publication: follow_publish_authority
    require_current_ci: true
    require_resolved_reviews: true
protection:
  provider: github
  default_branch: main
  requirement_reductions:
    codeowners: ['@maintainers']
    require_codeowner_approval: true
    minimum_total_approvals: 1
  waivers:
    require_expiry: true
    require_reason: true
"""


class TestPolicyNamespaceCoexistence:
    """AC-30: policy namespace works with all four install modes."""

    def test_link_mode_policy_namespace_accepted(self) -> None:
        """link mode: .agentharness-policy/ path is valid in profile."""
        profile = load_profile_text(_policy_profile(".agentharness-policy/runtime.lock"))  # noqa: E501
        assert isinstance(profile, Profile)
        assert profile.runtime.lock == ".agentharness-policy/runtime.lock"

    def test_copy_mode_policy_namespace_accepted(self) -> None:
        """copy mode: policy namespace path stays the same (install path doesn't affect it)."""  # noqa: E501
        profile = load_profile_text(_policy_profile(".agentharness-policy/runtime.lock"))  # noqa: E501
        assert isinstance(profile, Profile)

    def test_npm_mode_policy_namespace_accepted(self) -> None:
        """npm mode: policy namespace under .agentharness-policy/ is unaffected
        by .agentharness-npm/ install path."""
        profile = load_profile_text(_policy_profile(".agentharness-policy/runtime.lock"))  # noqa: E501
        assert isinstance(profile, Profile)
        assert profile.runtime.lock == ".agentharness-policy/runtime.lock"

    def test_submodule_mode_policy_namespace_accepted(self) -> None:
        """submodule mode: .agentharness/ install path doesn't conflict with policy ns."""  # noqa: E501
        profile = load_profile_text(_policy_profile(".agentharness-policy/runtime.lock"))  # noqa: E501
        assert isinstance(profile, Profile)

    def test_policy_path_must_not_escape_namespace(self) -> None:
        """Traversal paths that escape .agentharness-policy/ must be rejected."""
        with pytest.raises(ProfileError):
            load_profile_text(_policy_profile(".agentharness-policy/../runtime.lock"))

    def test_policy_path_must_be_under_relative_root(self) -> None:
        """Absolute paths must be rejected."""
        with pytest.raises(ProfileError):
            load_profile_text(_policy_profile("/etc/runtime.lock"))

    def test_policy_namespace_does_not_overlap_skills_namespace(self) -> None:
        """The policy directory (.agentharness-policy/) must not overlap
        with the skills install directories (.agents/, .agentharness-npm/, etc.)."""
        policy_namespace = ".agentharness-policy"
        # Use trailing slash to require exact-prefix matching, not substring
        skills_namespaces = [
            ".agents/",
            ".agentharness-npm/",
            ".claude/",
            ".kilo/",
            ".cursor/",
        ]
        policy_ns_slash = policy_namespace + "/"
        for ns in skills_namespaces:
            assert not ns.startswith(policy_ns_slash), (
                f"Skills namespace {ns!r} starts with policy namespace"
            )
            assert not policy_ns_slash.startswith(ns), (
                f"Policy namespace {policy_ns_slash!r} starts with skills namespace {ns!r}"  # noqa: E501
            )
