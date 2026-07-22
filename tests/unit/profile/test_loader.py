from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agentharness.profile import (
    ProfileError,
    load_local_override_text,
    load_profile_text,
)
from agentharness.profile.loader import (
    MAX_PROFILE_BYTES,
    canonical_profile_bytes,
    profile_hash,
)
from agentharness.profile.schema import Profile


def profile_yaml(*, coverage: int = 80, gates: str = "[push, ci, completion]") -> str:
    return f"""
schema_version: 1
runtime:
  lock: .agentharness-policy/runtime.lock
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
    minimum_coverage: {coverage}
    scope:
      include: [src/**]
      exclude: []
    gates: {gates}
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


def test_loader_returns_frozen_typed_records() -> None:
    profile = load_profile_text(profile_yaml())
    assert isinstance(profile, Profile)
    assert profile.requirements[0].identifier == "unit_testing"
    with pytest.raises(FrozenInstanceError):
        profile.project.name = "changed"  # type: ignore[misc]


@settings(deadline=None)
@given(st.integers(min_value=0, max_value=100))
def test_semantically_equivalent_profiles_hash_identically(coverage: int) -> None:
    first = load_profile_text(profile_yaml(coverage=coverage))
    reordered = load_profile_text(
        profile_yaml(coverage=coverage, gates="[completion, push, ci]")
    )
    assert profile_hash(first) == profile_hash(reordered)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ("schema_version: 1\nschema_version: 1\n", "profile.duplicate_key"),
        ("base: &x {a: 1}\n", "profile.alias_forbidden"),
        ("base: &x {a: 1}\ncopy: *x\n", "profile.alias_forbidden"),
        ("value: !python/object:thing {}\n", "profile.tag_forbidden"),
        ("---\na: 1\n---\nb: 2\n", "profile.multiple_documents"),
        (
            "".join(f"{'  ' * depth}a:\n" for depth in range(40))
            + "  " * 40
            + "value: 1\n",
            "profile.too_deep",
        ),
        ("x" * (MAX_PROFILE_BYTES + 1), "profile.too_large"),
    ],
)
def test_bounded_yaml_rejects_unsafe_documents(payload: str, code: str) -> None:
    with pytest.raises(ProfileError) as captured:
        load_profile_text(payload)
    assert captured.value.code == code


@pytest.mark.parametrize(
    "path",
    [
        ".",
        "/tmp/runtime.lock",
        "./.agentharness-policy/runtime.lock",
        ".agentharness-policy/../runtime.lock",
        ".agentharness-policy\\runtime.lock",
        "C:/runtime.lock",
        ".agentharness-policy//runtime.lock",
        r'"bad\u0000.lock"',
        r'"bad\u0001.lock"',
        r'"bad\u007f.lock"',
        r'"bad\u0080.lock"',
        r'"bad\u009f.lock"',
    ],
)
def test_noncanonical_runtime_paths_are_rejected(path: str) -> None:
    with pytest.raises(ProfileError) as captured:
        load_profile_text(
            profile_yaml().replace(".agentharness-policy/runtime.lock", path)
        )
    assert captured.value.code == "profile.noncanonical_path"


def test_local_override_loader_accepts_only_typed_operational_hints() -> None:
    override = load_local_override_text(
        """schema_version: 1
presentation: {output_format: json, color: never}
performance: {concurrency: 4, timeout_seconds: 300}
"""
    )
    assert override.performance.concurrency == 4
    assert override.presentation.output_format == "json"


def test_parser_failures_do_not_expose_library_diagnostics() -> None:
    with pytest.raises(ProfileError) as captured:
        load_profile_text("schema_version: [unterminated")
    assert str(captured.value) == "invalid YAML document"
    assert "line" not in str(captured.value).lower()
    assert "column" not in str(captured.value).lower()


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-02-29T00:00:00Z",
        "2026-13-01T00:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T00:00:60Z",
        "2026-01-01T00:00:00+00:00",
    ],
)
def test_confirmed_at_must_be_a_real_canonical_utc_timestamp(timestamp: str) -> None:
    payload = profile_yaml().replace("2026-07-14T00:00:00Z", timestamp)
    with pytest.raises(ProfileError) as captured:
        load_profile_text(payload)
    assert captured.value.code == "profile.invalid_timestamp"


def test_leap_day_timestamp_is_accepted() -> None:
    profile = load_profile_text(
        profile_yaml().replace("2026-07-14T00:00:00Z", "2028-02-29T23:59:59Z")
    )
    assert profile.bootstrap.confirmed_at == "2028-02-29T23:59:59Z"


@pytest.mark.parametrize("value", [".nan", ".inf", "-.inf"])
def test_nonfinite_plugin_configuration_is_rejected(value: str) -> None:
    payload = profile_yaml().replace("config: {}", f"config: {{value: {value}}}")
    with pytest.raises(ProfileError) as captured:
        load_profile_text(payload)
    assert captured.value.code == "profile.nonfinite_number"


def test_canonical_profile_bytes_are_strict_json() -> None:
    canonical = canonical_profile_bytes(load_profile_text(profile_yaml()))
    assert b"NaN" not in canonical
    assert b"Infinity" not in canonical


def test_mapping_and_sequence_plugin_configurations_never_collide() -> None:
    mapping_profile = load_profile_text(
        profile_yaml().replace("config: {}", "config: {nested: {a: 1}}")
    )
    sequence_profile = load_profile_text(
        profile_yaml().replace("config: {}", "config: {nested: [[a, 1]]}")
    )
    assert mapping_profile != sequence_profile
    assert profile_hash(mapping_profile) != profile_hash(sequence_profile)


def test_oversized_yaml_integer_has_sanitized_stable_error() -> None:
    payload = profile_yaml().replace(
        "minimum_coverage: 80", "minimum_coverage: " + "9" * 5000
    )
    with pytest.raises(ProfileError) as captured:
        load_profile_text(payload)
    assert captured.value.code == "profile.invalid_yaml"
    assert str(captured.value) == "invalid YAML document"


@pytest.mark.parametrize(
    "replacement",
    [
        "\ud800",
        r'"\uD800"',
        r'"\uDFFF"',
    ],
)
def test_lone_surrogates_in_yaml_values_are_rejected(replacement: str) -> None:
    with pytest.raises(ProfileError) as captured:
        load_profile_text(
            profile_yaml().replace("name: example", f"name: {replacement}")
        )
    assert captured.value.code == "profile.invalid_unicode"


def test_lone_surrogates_in_yaml_mapping_keys_are_rejected() -> None:
    payload = profile_yaml().replace("config: {}", r'config: {"\uD800": value}')
    with pytest.raises(ProfileError) as captured:
        load_profile_text(payload)
    assert captured.value.code == "profile.invalid_unicode"


def test_canonicalization_rejects_surrogates_in_constructed_records() -> None:
    profile = load_profile_text(profile_yaml())
    invalid = replace(profile, project=replace(profile.project, name="\ud800"))
    with pytest.raises(ProfileError) as captured:
        canonical_profile_bytes(invalid)
    assert captured.value.code == "profile.invalid_unicode"


def test_review_signal_order_does_not_change_profile_hash() -> None:
    first_signals = """    expected_signals:
      - type: check
        name: zeta
        allowed_conclusions: [neutral, success]
      - type: review
        name: alpha
        allowed_conclusions: [success]
"""
    second_signals = """    expected_signals:
      - type: review
        name: alpha
        allowed_conclusions: [success]
      - type: check
        name: zeta
        allowed_conclusions: [success, neutral]
"""
    first = load_profile_text(
        profile_yaml().replace("    expected_signals: []\n", first_signals)
    )
    second = load_profile_text(
        profile_yaml().replace("    expected_signals: []\n", second_signals)
    )
    assert profile_hash(first) == profile_hash(second)


def test_duplicate_review_signal_identity_is_rejected() -> None:
    signals = """    expected_signals:
      - type: check
        name: review
        allowed_conclusions: [success]
      - type: check
        name: review
        allowed_conclusions: [neutral]
"""
    with pytest.raises(ProfileError) as captured:
        load_profile_text(profile_yaml().replace("    expected_signals: []\n", signals))
    assert captured.value.code == "profile.duplicate_signal"
