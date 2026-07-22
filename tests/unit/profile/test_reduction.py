from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agentharness.profile import (
    ProfileError,
    load_local_override_text,
    load_profile_candidate_text,
    load_profile_text,
)
from agentharness.profile.reduction import apply_local_override, find_reductions

from .test_loader import profile_yaml

_MUTATION_CODES = {
    "unknown_key": "profile.schema_invalid",
    "duplicate_id": "profile.duplicate_key",
    "invalid_gate": "profile.schema_invalid",
    "invalid_mode": "profile.schema_invalid",
    "noncanonical_path": "profile.noncanonical_path",
    "executable_substitution": "reduction.verifier_changed",
    "cache_substitution": "profile.schema_invalid",
    "runtime_substitution": "reduction.runtime_changed",
    "threshold_decrease": "reduction.threshold_decreased",
    "scope_narrowing": "reduction.scope_narrowed",
    "gate_removal": "reduction.gate_removed",
}


@settings(deadline=None)
@given(
    mutation=st.sampled_from(tuple(_MUTATION_CODES)),
    coverage=st.integers(min_value=1, max_value=100),
)
def test_generated_weakening_mutations_fail_with_stable_codes(
    mutation: str, coverage: int
) -> None:
    source = profile_yaml(coverage=coverage)
    replacements = {
        "unknown_key": ("project:\n", "unknown: true\nproject:\n"),
        "duplicate_id": (
            "requirements:\n  unit_testing:",
            "requirements:\n  unit_testing: {}\n  unit_testing:",
        ),
        "invalid_gate": ("[push, ci, completion]", "[deploy]"),
        "invalid_mode": ("mode: strict", "mode: permissive"),
        "noncanonical_path": (
            ".agentharness-policy/runtime.lock",
            ".agentharness-policy/../runtime.lock",
        ),
        "executable_substitution": ("command: [pytest]", "command: [other]"),
        "cache_substitution": (
            "    command: [pytest]",
            "    cache: /tmp/cache\n    command: [pytest]",
        ),
        "runtime_substitution": (
            ".agentharness-policy/runtime.lock",
            ".agentharness-policy/other.lock",
        ),
        "threshold_decrease": (
            f"minimum_coverage: {coverage}",
            f"minimum_coverage: {coverage - 1}",
        ),
        "scope_narrowing": ("include: [src/**]", "include: [src/core/**]"),
        "gate_removal": ("[push, ci, completion]", "[ci, completion]"),
    }
    old, new = replacements[mutation]
    mutated = source.replace(old, new, 1)
    expected = _MUTATION_CODES[mutation]
    if expected.startswith("profile."):
        with pytest.raises(ProfileError) as captured:
            load_profile_text(mutated)
        assert captured.value.code == expected
    else:
        base = load_profile_text(source)
        candidate = load_profile_text(mutated)
        assert expected in {
            finding.code for finding in find_reductions(base, candidate)
        }


@settings(deadline=None)
@given(st.integers(min_value=1, max_value=80))
def test_lowering_threshold_is_always_a_reduction(lower: int) -> None:
    base = load_profile_text(profile_yaml(coverage=81))
    candidate = load_profile_text(profile_yaml(coverage=lower))
    assert "reduction.threshold_decreased" in {
        finding.code for finding in find_reductions(base, candidate)
    }


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        (
            "requirements:\n  unit_testing:\n    provider: python\n    enabled: true",
            "requirements:\n  unit_testing:\n    provider: python\n    enabled: false",
            "reduction.requirement_disabled",
        ),
        ("mode: strict", "mode: warn", "reduction.bootstrap_mode_weakened"),
        ("[push, ci, completion]", "[ci, completion]", "reduction.gate_removed"),
        ("include: [src/**]", "include: [src/core/**]", "reduction.scope_narrowed"),
        ("exclude: []", "exclude: [src/legacy/**]", "reduction.scope_narrowed"),
        ("provider: python", "provider: core", "reduction.provider_changed"),
        ("command: [pytest]", "command: [other]", "reduction.verifier_changed"),
        (
            ".agentharness-policy/runtime.lock",
            ".agentharness-policy/other.lock",
            "reduction.runtime_changed",
        ),
    ],
)
def test_semantic_reductions_have_stable_codes(old: str, new: str, code: str) -> None:
    base = load_profile_text(profile_yaml())
    candidate = load_profile_text(profile_yaml().replace(old, new, 1))
    assert code in {finding.code for finding in find_reductions(base, candidate)}


def test_requirement_and_gate_removal_are_reductions() -> None:
    base = load_profile_text(profile_yaml())
    prefix, remainder = profile_yaml().split("requirements:\n", 1)
    _, suffix = remainder.split("workflow:\n", 1)
    candidate = load_profile_text(
        prefix
        + "requirements:\n  documentation:\n"
        + "    provider: core\n    enabled: true\n"
        + "    checks: [readme_present]\n    gates: [ci]\n"
        + "workflow:\n"
        + suffix
    )
    codes = {finding.code for finding in find_reductions(base, candidate)}
    assert "reduction.requirement_removed" in codes


def test_allowed_override_is_applied_without_mutating_policy() -> None:
    profile = load_profile_text(profile_yaml())
    override = load_local_override_text(
        "schema_version: 1\nperformance: {concurrency: 2, timeout_seconds: 60}\n"
    )
    effective = apply_local_override(
        profile, override, verifier_max_timeout_seconds=120
    )
    assert effective.profile is profile
    assert effective.performance.timeout_seconds == 60


def test_timeout_must_remain_within_verifier_bound() -> None:
    profile = load_profile_text(profile_yaml())
    override = load_local_override_text(
        "schema_version: 1\nperformance: {timeout_seconds: 121}\n"
    )
    with pytest.raises(ProfileError) as captured:
        apply_local_override(profile, override, verifier_max_timeout_seconds=120)
    assert captured.value.code == "override.timeout_exceeds_bound"


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("rigor: production", "rigor: internal", "reduction.rigor_weakened"),
        (
            "existing_checks_are_required: true",
            "existing_checks_are_required: false",
            "reduction.bootstrap_weakened",
        ),
        (
            "required_for: [feature, fix]",
            "required_for: [feature]",
            "reduction.scope_narrowed",
        ),
        (
            "require_committed_changes: true",
            "require_committed_changes: false",
            "reduction.completion_weakened",
        ),
        (
            "require_resolved_reviews: true",
            "require_resolved_reviews: false",
            "reduction.completion_weakened",
        ),
        (
            "publication: follow_publish_authority",
            "publication: local_only",
            "reduction.completion_weakened",
        ),
        (
            "codeowners: ['@maintainers']",
            "codeowners: ['@other']",
            "reduction.protection_codeowners_changed",
        ),
        (
            "provider: github\n  default_branch: main",
            "provider: gitlab\n  default_branch: main",
            "reduction.protection_identity_changed",
        ),
        (
            "default_branch: main",
            "default_branch: trunk",
            "reduction.protection_identity_changed",
        ),
        (
            "version: 1.0.0",
            "version: 1.0.1",
            "reduction.plugin_identity_changed",
        ),
        (
            "config: {}",
            "config: {mode: strict}",
            "reduction.plugin_identity_changed",
        ),
    ],
)
def test_all_protected_policy_surfaces_are_classified(
    old: str, new: str, code: str
) -> None:
    source = profile_yaml().replace(
        "command: [pytest]\n",
        "command: [pytest]\n    required_for: [feature, fix]\n",
    )
    base = load_profile_text(source)
    candidate = load_profile_text(source.replace(old, new, 1))
    assert code in {finding.code for finding in find_reductions(base, candidate)}


def test_plugin_removal_and_disablement_are_protected_reductions() -> None:
    base = load_profile_text(profile_yaml())
    disabled_source = (
        profile_yaml()
        .replace(
            "requirements:\n  unit_testing:\n    provider: python",
            "requirements:\n  unit_testing:\n    provider: core",
        )
        .replace("enabled: true", "enabled: false", 1)
    )
    disabled = load_profile_text(disabled_source)
    assert "reduction.plugin_disabled" in {
        finding.code for finding in find_reductions(base, disabled)
    }

    removed_source = (
        profile_yaml()
        .replace(
            "plugins:\n  python:\n    enabled: true\n"
            "    version: 1.0.0\n    config: {}",
            "plugins:\n  core_plugin:\n    enabled: true\n"
            "    version: 1.0.0\n    config: {}",
        )
        .replace("provider: python", "provider: core", 1)
    )
    removed = load_profile_text(removed_source)
    assert "reduction.plugin_removed" in {
        finding.code for finding in find_reductions(base, removed)
    }


def test_weak_codeowner_candidate_is_parsed_and_classified() -> None:
    base = load_profile_text(profile_yaml())
    candidate = load_profile_candidate_text(
        profile_yaml()
        .replace(
            "require_codeowner_approval: true",
            "require_codeowner_approval: false",
        )
        .replace("minimum_total_approvals: 1", "minimum_total_approvals: 0")
    )
    assert "reduction.protection_weakened" in {
        finding.code for finding in find_reductions(base, candidate)
    }


def test_weak_waiver_candidate_is_parsed_and_classified() -> None:
    base = load_profile_text(profile_yaml())
    candidate = load_profile_candidate_text(
        profile_yaml()
        .replace("require_expiry: true", "require_expiry: false")
        .replace("require_reason: true", "require_reason: false")
    )
    assert "reduction.waiver_weakened" in {
        finding.code for finding in find_reductions(base, candidate)
    }


def test_codeowner_addition_is_protected_under_any_matching_semantics() -> None:
    base = load_profile_text(profile_yaml())
    candidate = load_profile_candidate_text(
        profile_yaml().replace(
            "codeowners: ['@maintainers']",
            "codeowners: ['@maintainers', '@platform']",
        )
    )
    assert "reduction.protection_codeowners_changed" in {
        finding.code for finding in find_reductions(base, candidate)
    }


def test_stabilization_window_decrease_is_a_reduction() -> None:
    base = load_profile_text(profile_yaml())
    candidate = load_profile_candidate_text(
        profile_yaml().replace("stabilization_seconds: 60", "stabilization_seconds: 59")
    )
    assert "reduction.review_window_weakened" in {
        finding.code for finding in find_reductions(base, candidate)
    }


@pytest.mark.parametrize("timeout", [1, 901])
def test_review_timeout_identity_change_is_protected(timeout: int) -> None:
    base = load_profile_text(profile_yaml())
    candidate = load_profile_candidate_text(
        profile_yaml().replace("timeout_seconds: 900", f"timeout_seconds: {timeout}")
    )
    assert "reduction.review_window_changed" in {
        finding.code for finding in find_reductions(base, candidate)
    }


def test_plugin_config_json_kind_change_is_an_identity_reduction() -> None:
    base = load_profile_text(
        profile_yaml().replace("config: {}", "config: {nested: {a: 1}}")
    )
    candidate = load_profile_candidate_text(
        profile_yaml().replace("config: {}", "config: {nested: [[a, 1]]}")
    )
    assert "reduction.plugin_identity_changed" in {
        finding.code for finding in find_reductions(base, candidate)
    }


@settings(deadline=None)
@given(
    require_owner=st.booleans(),
    approvals=st.integers(min_value=0, max_value=2),
    require_expiry=st.booleans(),
    require_reason=st.booleans(),
    add_owner=st.booleans(),
    stabilization=st.integers(min_value=0, max_value=59),
)
def test_generated_structural_candidates_classify_nested_policy_changes(
    require_owner: bool,
    approvals: int,
    require_expiry: bool,
    require_reason: bool,
    add_owner: bool,
    stabilization: int,
) -> None:
    source = profile_yaml()
    candidate_source = (
        source.replace(
            "require_codeowner_approval: true",
            f"require_codeowner_approval: {str(require_owner).lower()}",
        )
        .replace("minimum_total_approvals: 1", f"minimum_total_approvals: {approvals}")
        .replace(
            "require_expiry: true", f"require_expiry: {str(require_expiry).lower()}"
        )
        .replace(
            "require_reason: true", f"require_reason: {str(require_reason).lower()}"
        )
        .replace("stabilization_seconds: 60", f"stabilization_seconds: {stabilization}")
    )
    if add_owner:
        candidate_source = candidate_source.replace(
            "codeowners: ['@maintainers']",
            "codeowners: ['@maintainers', '@generated']",
        )
    base = load_profile_text(source)
    candidate = load_profile_candidate_text(candidate_source)
    codes = {finding.code for finding in find_reductions(base, candidate)}
    assert "reduction.review_window_weakened" in codes
    if not require_owner or approvals == 0:
        assert "reduction.protection_weakened" in codes
    if not require_expiry or not require_reason:
        assert "reduction.waiver_weakened" in codes
    if add_owner:
        assert "reduction.protection_codeowners_changed" in codes


def test_review_signal_removal_and_change_are_reductions() -> None:
    signal = (
        "    expected_signals:\n"
        "      - type: check\n"
        "        name: review\n"
        "        allowed_conclusions: [success, neutral]"
    )
    base_source = profile_yaml().replace("    expected_signals: []", signal)
    base = load_profile_text(base_source)
    removed = load_profile_text(profile_yaml())
    changed = load_profile_text(base_source.replace("[success, neutral]", "[success]"))
    assert "reduction.review_signal_removed" in {
        finding.code for finding in find_reductions(base, removed)
    }
    assert "reduction.review_signal_changed" in {
        finding.code for finding in find_reductions(base, changed)
    }


def test_empty_include_means_unbounded_scope() -> None:
    bounded = load_profile_text(profile_yaml())
    unbounded = load_profile_text(
        profile_yaml().replace("include: [src/**]", "include: []")
    )
    assert "reduction.scope_narrowed" not in {
        finding.code for finding in find_reductions(bounded, unbounded)
    }
    assert "reduction.scope_narrowed" in {
        finding.code for finding in find_reductions(unbounded, bounded)
    }


@settings(deadline=None)
@given(
    rigor_pair=st.sampled_from(
        [
            ("production", "internal"),
            ("production", "prototype"),
            ("internal", "prototype"),
        ]
    ),
    removed=st.sets(
        st.sampled_from(["push", "ci", "completion"]), min_size=1, max_size=2
    ),
    coverage=st.integers(min_value=1, max_value=100),
)
def test_generated_valid_policy_variants_preserve_reduction_invariants(
    rigor_pair: tuple[str, str], removed: set[str], coverage: int
) -> None:
    strong, weak = rigor_pair
    base_source = profile_yaml(coverage=coverage).replace(
        "rigor: production", f"rigor: {strong}"
    )
    candidate_source = base_source.replace(f"rigor: {strong}", f"rigor: {weak}")
    remaining = [gate for gate in ("push", "ci", "completion") if gate not in removed]
    if remaining:
        candidate_source = candidate_source.replace(
            "[push, ci, completion]", f"[{', '.join(remaining)}]"
        )
    base = load_profile_text(base_source)
    candidate = load_profile_text(candidate_source)
    codes = {finding.code for finding in find_reductions(base, candidate)}
    assert "reduction.rigor_weakened" in codes
    if remaining != ["push", "ci", "completion"]:
        assert "reduction.gate_removed" in codes
