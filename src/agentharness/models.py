from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

from agentharness import RESULT_SCHEMA_VERSION
from agentharness.errors import ResultValidationError

MAX_JSON_NESTING_DEPTH = 64
MIN_JSON_INTEGER = -(2**63)
MAX_JSON_INTEGER = (2**63) - 1

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | Mapping[str, JsonValue]
type FrozenJsonValue = (
    JsonScalar | tuple[FrozenJsonValue, ...] | Mapping[str, FrozenJsonValue]
)
type SupportedJsonValue = JsonValue | FrozenJsonValue


def _freeze_mapping(
    value: Mapping[str, SupportedJsonValue],
    *,
    depth: int,
    active_containers: set[int],
) -> Mapping[str, FrozenJsonValue]:
    _enter_container(value, depth, active_containers)
    try:
        frozen: dict[str, FrozenJsonValue] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ResultValidationError("JSON object keys must be strings")
            frozen[key] = _freeze_json(
                nested_value,
                depth=depth + 1,
                active_containers=active_containers,
            )
        return MappingProxyType(frozen)
    finally:
        active_containers.remove(id(value))


def _enter_container(
    value: object, depth: int, active_containers: set[int]
) -> None:
    if depth > MAX_JSON_NESTING_DEPTH:
        raise ResultValidationError(
            f"maximum JSON nesting depth is {MAX_JSON_NESTING_DEPTH}"
        )
    identity = id(value)
    if identity in active_containers:
        raise ResultValidationError("cyclic JSON value is not supported")
    active_containers.add(identity)


def _freeze_sequence(
    value: list[JsonValue] | tuple[FrozenJsonValue, ...],
    *,
    depth: int,
    active_containers: set[int],
) -> tuple[FrozenJsonValue, ...]:
    _enter_container(value, depth, active_containers)
    try:
        return tuple(
            _freeze_json(
                item,
                depth=depth + 1,
                active_containers=active_containers,
            )
            for item in value
        )
    finally:
        active_containers.remove(id(value))


def _freeze_json(
    value: SupportedJsonValue,
    *,
    depth: int,
    active_containers: set[int],
) -> FrozenJsonValue:
    if isinstance(value, float):
        if not isfinite(value):
            raise ResultValidationError("Unsupported JSON value: non-finite float")
        return value
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        if not MIN_JSON_INTEGER <= value <= MAX_JSON_INTEGER:
            raise ResultValidationError(
                "JSON integer must be within the signed 64-bit range"
            )
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(
            value,
            depth=depth,
            active_containers=active_containers,
        )
    if isinstance(value, (list, tuple)):
        return _freeze_sequence(
            value,
            depth=depth,
            active_containers=active_containers,
        )
    raise ResultValidationError(f"Unsupported JSON value: {type(value).__name__}")


class ResultCode(StrEnum):
    STATUS_AVAILABLE = "status_available"
    INVALID_COMMAND = "invalid_command"


class Outcome(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True, slots=True, init=False)
class CommandResult:
    code: ResultCode
    outcome: Outcome
    summary: str
    remediation: str
    details: Mapping[str, FrozenJsonValue]
    schema_version: int

    def __init__(
        self,
        code: ResultCode,
        outcome: Outcome,
        summary: str,
        remediation: str,
        details: Mapping[str, SupportedJsonValue] | None = None,
        schema_version: int = RESULT_SCHEMA_VERSION,
    ) -> None:
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "remediation", remediation)
        details_value = details if details is not None else {}
        object.__setattr__(
            self,
            "details",
            _freeze_mapping(details_value, depth=1, active_containers=set()),
        )
        object.__setattr__(self, "schema_version", schema_version)
