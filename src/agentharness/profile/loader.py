from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from importlib import resources
from math import isfinite
from pathlib import PurePosixPath
from typing import Any, cast
from unicodedata import category

import fastjsonschema  # type: ignore[import-untyped]
import yaml
from yaml.constructor import ConstructorError
from yaml.tokens import AliasToken, AnchorToken, TagToken

from agentharness.profile.schema import (
    Bootstrap,
    BootstrapMode,
    Completion,
    FrozenMapping,
    FrozenSequence,
    FrozenValue,
    Gate,
    LocalOverride,
    PerformanceOverride,
    Plugin,
    PresentationOverride,
    Profile,
    ProfileError,
    Project,
    Protection,
    Requirement,
    RequirementReductionProtection,
    Reviews,
    ReviewSignal,
    Runtime,
    Scope,
    WaiverProtection,
    Workflow,
)

MAX_PROFILE_BYTES = 1_048_576
MAX_PROFILE_DEPTH = 32
_DRIVE_PATH = re.compile(r"^[A-Za-z]:")


class _UniqueSafeLoader(yaml.SafeLoader):
    pass


# Keep timestamps as source strings so schema validation is deterministic.
_UniqueSafeLoader.yaml_implicit_resolvers = {
    key: [item for item in values if item[0] != "tag:yaml.org,2002:timestamp"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _construct_mapping(
    loader: _UniqueSafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as error:
            raise ConstructorError(
                None, None, "mapping key must be scalar", key_node.start_mark
            ) from error
        if duplicate:
            raise ConstructorError(
                None, None, f"duplicate key: {key}", key_node.start_mark
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _load_yaml(payload: str | bytes, *, prefix: str) -> Mapping[str, object]:
    try:
        encoded = payload.encode("utf-8") if isinstance(payload, str) else payload
    except UnicodeEncodeError as error:
        raise ProfileError(
            f"{prefix}.invalid_unicode", "Unicode surrogate code points are forbidden"
        ) from error
    if len(encoded) > MAX_PROFILE_BYTES:
        raise ProfileError(f"{prefix}.too_large", "YAML document exceeds 1 MiB")
    try:
        text = encoded.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProfileError(f"{prefix}.invalid_yaml", "YAML must be UTF-8") from error
    try:
        for token in yaml.scan(text):
            if isinstance(token, (AliasToken, AnchorToken)):
                raise ProfileError(
                    f"{prefix}.alias_forbidden",
                    "YAML aliases and anchors are forbidden",
                )
            if isinstance(token, TagToken):
                raise ProfileError(
                    f"{prefix}.tag_forbidden", "explicit YAML tags are forbidden"
                )
        nodes = list(yaml.compose_all(text, Loader=_UniqueSafeLoader))
        if len(nodes) != 1:
            raise ProfileError(
                f"{prefix}.multiple_documents", "exactly one YAML document is allowed"
            )
        _check_node_depth(nodes[0], depth=1, prefix=prefix)
        value = yaml.load(text, Loader=_UniqueSafeLoader)
    except ProfileError:
        raise
    except ConstructorError as error:
        if "duplicate key" in str(error):
            raise ProfileError(
                f"{prefix}.duplicate_key", "duplicate YAML mapping key"
            ) from error
        raise ProfileError(f"{prefix}.invalid_yaml", "invalid YAML document") from error
    except (yaml.YAMLError, RecursionError, ValueError) as error:
        raise ProfileError(f"{prefix}.invalid_yaml", "invalid YAML document") from error
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ProfileError(
            f"{prefix}.schema_invalid", "document must be a string-keyed object"
        )
    _check_depth(value, depth=1, prefix=prefix)
    _check_json_domain(value, prefix=prefix)
    return value


def _check_node_depth(node: yaml.Node | None, *, depth: int, prefix: str) -> None:
    if node is None:
        return
    if depth > MAX_PROFILE_DEPTH:
        raise ProfileError(
            f"{prefix}.too_deep", f"YAML nesting exceeds {MAX_PROFILE_DEPTH}"
        )
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            _check_node_depth(key, depth=depth + 1, prefix=prefix)
            _check_node_depth(value, depth=depth + 1, prefix=prefix)
    elif isinstance(node, yaml.SequenceNode):
        for value in node.value:
            _check_node_depth(value, depth=depth + 1, prefix=prefix)


def _check_depth(value: object, *, depth: int, prefix: str) -> None:
    if depth > MAX_PROFILE_DEPTH:
        raise ProfileError(
            f"{prefix}.too_deep", f"YAML nesting exceeds {MAX_PROFILE_DEPTH}"
        )
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _check_depth(key, depth=depth + 1, prefix=prefix)
            _check_depth(nested, depth=depth + 1, prefix=prefix)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            _check_depth(nested, depth=depth + 1, prefix=prefix)


def _check_json_domain(value: object, *, prefix: str) -> None:
    if isinstance(value, str) and any(
        category(character) == "Cs" for character in value
    ):
        raise ProfileError(
            f"{prefix}.invalid_unicode", "Unicode surrogate code points are forbidden"
        )
    if isinstance(value, float) and not isfinite(value):
        raise ProfileError(
            f"{prefix}.nonfinite_number", "non-finite numbers are forbidden"
        )
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ProfileError(
                f"{prefix}.schema_invalid", "all object keys must be strings"
            )
        for nested in value.values():
            _check_json_domain(nested, prefix=prefix)
        for key in value:
            _check_json_domain(key, prefix=prefix)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            _check_json_domain(nested, prefix=prefix)


def _validate(document: Mapping[str, object], schema_name: str, prefix: str) -> None:
    try:
        schema_text = (
            resources.files("agentharness.schemas")
            .joinpath(schema_name)
            .read_text(encoding="utf-8")
        )
        schema = json.loads(schema_text)
        fastjsonschema.compile(schema)(document)
    except (fastjsonschema.JsonSchemaException, OSError, json.JSONDecodeError) as error:
        raise ProfileError(
            f"{prefix}.schema_invalid", f"document does not match {schema_name}"
        ) from error


def _mapping(value: object) -> Mapping[str, Any]:
    assert isinstance(value, Mapping)
    return cast(Mapping[str, Any], value)


def _utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ProfileError(
            "profile.invalid_timestamp", "confirmed_at must be a valid UTC timestamp"
        ) from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ProfileError(
            "profile.invalid_timestamp", "confirmed_at must use canonical UTC form"
        )
    return value


def _canonical_path(value: str, field: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or value == "."
        or any(category(character) in {"Cc", "Cs"} for character in value)
        or value.startswith(("/", "./"))
        or "\\" in value
        or "//" in value
        or _DRIVE_PATH.match(value)
        or any(part in {".", "..", ""} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ProfileError(
            "profile.noncanonical_path",
            f"{field} must be a canonical repository-relative POSIX path",
        )
    return value


def _canonical_scope_path(value: str, field: str) -> str:
    return _canonical_path(value, field)


def _freeze(value: object) -> FrozenValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return FrozenSequence(tuple(_freeze(item) for item in value))
    if isinstance(value, Mapping):
        return FrozenMapping(
            tuple(sorted((str(key), _freeze(nested)) for key, nested in value.items()))
        )
    raise ProfileError(
        "profile.schema_invalid", "unsupported plugin configuration value"
    )


def _load_profile_text(payload: str | bytes, *, require_active: bool) -> Profile:
    document = _load_yaml(payload, prefix="profile")
    _validate(document, "profile-v1.json", "profile")
    runtime = _mapping(document["runtime"])
    project = _mapping(document["project"])
    bootstrap = _mapping(document["bootstrap"])
    plugins_doc = _mapping(document["plugins"])
    requirements_doc = _mapping(document["requirements"])
    workflow_doc = _mapping(document["workflow"])
    reviews_doc = _mapping(workflow_doc["reviews"])
    completion_doc = _mapping(workflow_doc["completion"])
    protection_doc = _mapping(document["protection"])
    reductions_doc = _mapping(protection_doc["requirement_reductions"])
    waivers_doc = _mapping(protection_doc["waivers"])
    if require_active:
        _validate_active_invariants(reductions_doc, waivers_doc)

    plugins = tuple(
        Plugin(
            identifier=identifier,
            enabled=bool(config["enabled"]),
            version=str(config["version"]),
            config=cast(FrozenMapping, _freeze(_mapping(config["config"]))),
        )
        for identifier, raw_config in sorted(plugins_doc.items())
        for config in (_mapping(raw_config),)
    )
    enabled_plugins = {plugin.identifier for plugin in plugins if plugin.enabled}
    requirements: list[Requirement] = []
    for identifier, raw_config in sorted(requirements_doc.items()):
        config = _mapping(raw_config)
        provider = str(config["provider"])
        if provider != "core" and provider not in enabled_plugins:
            message = (
                f"requirement {identifier} uses disabled or missing provider {provider}"
            )
            raise ProfileError(
                "profile.provider_unavailable",
                message,
            )
        scope_doc = _mapping(config.get("scope", {}))
        requirements.append(
            Requirement(
                identifier=identifier,
                provider=provider,
                enabled=bool(config["enabled"]),
                gates=tuple(
                    sorted(
                        (Gate(str(gate)) for gate in config["gates"]),
                        key=lambda gate: gate.value,
                    )
                ),
                tool=str(config["tool"]) if "tool" in config else None,
                command=tuple(str(item) for item in config.get("command", [])),
                standard=str(config["standard"]) if "standard" in config else None,
                checks=tuple(sorted(str(item) for item in config.get("checks", []))),
                minimum_coverage=int(config["minimum_coverage"])
                if "minimum_coverage" in config
                else None,
                minimum_score=int(config["minimum_score"])
                if "minimum_score" in config
                else None,
                required_for=tuple(
                    sorted(str(item) for item in config.get("required_for", []))
                ),
                scope=Scope(
                    include=tuple(
                        sorted(
                            _canonical_scope_path(
                                str(item), f"requirements.{identifier}.scope.include"
                            )
                            for item in scope_doc.get("include", [])
                        )
                    ),
                    exclude=tuple(
                        sorted(
                            _canonical_scope_path(
                                str(item), f"requirements.{identifier}.scope.exclude"
                            )
                            for item in scope_doc.get("exclude", [])
                        )
                    ),
                ),
            )
        )
    unsorted_signals = tuple(
        ReviewSignal(
            type=str(signal["type"]),
            name=str(signal["name"]),
            allowed_conclusions=tuple(
                sorted(str(item) for item in signal["allowed_conclusions"])
            ),
        )
        for raw_signal in reviews_doc["expected_signals"]
        for signal in (_mapping(raw_signal),)
    )
    signal_identities = [(signal.type, signal.name) for signal in unsorted_signals]
    if len(signal_identities) != len(set(signal_identities)):
        raise ProfileError(
            "profile.duplicate_signal",
            "review signal type and name must form a unique identity",
        )
    signals = tuple(
        sorted(
            unsorted_signals,
            key=lambda signal: (
                signal.type,
                signal.name,
                signal.allowed_conclusions,
            ),
        )
    )
    return Profile(
        schema_version=1,
        runtime=Runtime(_canonical_path(str(runtime["lock"]), "runtime.lock")),
        project=Project(str(project["name"]), str(project["rigor"])),
        bootstrap=Bootstrap(
            BootstrapMode(str(bootstrap["mode"])),
            _utc_timestamp(str(bootstrap["confirmed_at"])),
            bool(bootstrap["existing_checks_are_required"]),
        ),
        plugins=plugins,
        requirements=tuple(requirements),
        workflow=Workflow(
            reviews=Reviews(
                signals,
                int(reviews_doc["timeout_seconds"]),
                int(reviews_doc["stabilization_seconds"]),
            ),
            completion=Completion(
                bool(completion_doc["require_clean_tree"]),
                bool(completion_doc["require_committed_changes"]),
                str(completion_doc["publication"]),
                bool(completion_doc["require_current_ci"]),
                bool(completion_doc["require_resolved_reviews"]),
            ),
        ),
        protection=Protection(
            str(protection_doc["provider"]),
            str(protection_doc["default_branch"]),
            RequirementReductionProtection(
                tuple(sorted(str(item) for item in reductions_doc["codeowners"])),
                bool(reductions_doc["require_codeowner_approval"]),
                int(reductions_doc["minimum_total_approvals"]),
            ),
            WaiverProtection(
                bool(waivers_doc["require_expiry"]), bool(waivers_doc["require_reason"])
            ),
        ),
    )


def _validate_active_invariants(
    reductions: Mapping[str, Any], waivers: Mapping[str, Any]
) -> None:
    if (
        not reductions["codeowners"]
        or not reductions["require_codeowner_approval"]
        or reductions["minimum_total_approvals"] < 1
    ):
        raise ProfileError(
            "profile.reduction_protection_invalid",
            "active profiles must protect requirement reductions",
        )
    if not waivers["require_expiry"] or not waivers["require_reason"]:
        raise ProfileError(
            "profile.waiver_protection_invalid",
            "active profiles must require waiver expiry and reason",
        )


def load_profile_text(payload: str | bytes) -> Profile:
    """Load a structurally valid profile that satisfies activation invariants."""

    return _load_profile_text(payload, require_active=True)


def load_profile_candidate_text(payload: str | bytes) -> Profile:
    """Load a typed policy-change candidate for semantic reduction analysis.

    Candidate loading validates the complete structural schema and typed boundary but
    deliberately defers activation-only protection invariants to policy review.
    """

    return _load_profile_text(payload, require_active=False)


def load_local_override_text(payload: str | bytes) -> LocalOverride:
    document = _load_yaml(payload, prefix="override")
    _validate(document, "local-override-v1.json", "override")
    presentation = _mapping(document.get("presentation", {}))
    performance = _mapping(document.get("performance", {}))
    return LocalOverride(
        schema_version=1,
        presentation=PresentationOverride(
            str(presentation["output_format"])
            if "output_format" in presentation
            else None,
            str(presentation["color"]) if "color" in presentation else None,
        ),
        performance=PerformanceOverride(
            int(performance["concurrency"]) if "concurrency" in performance else None,
            int(performance["timeout_seconds"])
            if "timeout_seconds" in performance
            else None,
        ),
    )


def _json_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, FrozenMapping):
        return {key: _json_value(nested) for key, nested in value.entries}
    if isinstance(value, FrozenSequence):
        return [_json_value(item) for item in value.items]
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _json_value(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def canonical_profile_bytes(profile: Profile) -> bytes:
    try:
        return json.dumps(
            _json_value(profile),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except UnicodeEncodeError as error:
        raise ProfileError(
            "profile.invalid_unicode", "Unicode surrogate code points are forbidden"
        ) from error


def profile_hash(profile: Profile) -> str:
    return hashlib.sha256(canonical_profile_bytes(profile)).hexdigest()
