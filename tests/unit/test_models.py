import json
from dataclasses import FrozenInstanceError

import pytest

from agentharness import errors, models
from agentharness.cli import render_json
from agentharness.models import CommandResult, Outcome, ResultCode


def test_result_validation_error_is_a_stable_validation_type():
    assert issubclass(errors.ResultValidationError, TypeError)


def test_json_boundary_constants_are_explicit_and_interoperable():
    assert (
        models.MAX_JSON_NESTING_DEPTH,
        models.MIN_JSON_INTEGER,
        models.MAX_JSON_INTEGER,
    ) == (64, -(2**63), (2**63) - 1)


def test_command_result_is_immutable():
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project bootstrap status is available.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"state": "not_configured"},
    )

    with pytest.raises(FrozenInstanceError):
        result.summary = "changed"


def test_command_result_details_are_immutable():
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project bootstrap status is available.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"state": "not_configured"},
    )

    with pytest.raises(TypeError):
        result.details["state"] = "changed"


def test_command_result_copies_nested_input_before_freezing():
    details = {"profile": {"checks": ["lint"]}}
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project bootstrap status is available.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details=details,
    )

    details["profile"]["checks"].append("test")
    details["profile"]["mode"] = "changed"

    assert '"details": {"profile": {"checks": ["lint"]}}' in render_json(result)


def test_command_result_nested_mappings_are_immutable():
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project bootstrap status is available.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"profile": {"checks": ["lint"]}},
    )

    with pytest.raises(TypeError):
        result.details["profile"]["mode"] = "changed"


def test_command_result_nested_sequences_are_immutable():
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project bootstrap status is available.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"profile": {"checks": ["lint"]}},
    )

    with pytest.raises(TypeError):
        result.details["profile"]["checks"][0] = "changed"


@pytest.mark.parametrize(
    "unsupported",
    [{"set values"}, float("nan"), float("inf"), float("-inf")],
)
def test_command_result_rejects_non_json_values(unsupported):
    with pytest.raises(errors.ResultValidationError, match="Unsupported JSON value"):
        CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="Project bootstrap status is available.",
            remediation="Run 'agentharness bootstrap' to configure this project.",
            details={"unsupported": unsupported},
        )


def test_command_result_rejects_non_string_mapping_keys():
    with pytest.raises(
        errors.ResultValidationError, match="JSON object keys must be strings"
    ):
        CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="Project bootstrap status is available.",
            remediation="Run 'agentharness bootstrap' to configure this project.",
            details={1: "unsupported"},
        )


def test_command_result_rejects_cyclic_sequence():
    cyclic: list[object] = []
    cyclic.append(cyclic)

    with pytest.raises(errors.ResultValidationError, match="cyclic JSON value"):
        CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="Project is not configured.",
            remediation="Run 'agentharness bootstrap' to configure this project.",
            details={"cyclic": cyclic},
        )


def test_command_result_rejects_cyclic_mapping():
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic

    with pytest.raises(errors.ResultValidationError, match="cyclic JSON value"):
        CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="Project is not configured.",
            remediation="Run 'agentharness bootstrap' to configure this project.",
            details={"cyclic": cyclic},
        )


def test_command_result_rejects_excessive_nesting():
    nested: object = "leaf"
    for _ in range(models.MAX_JSON_NESTING_DEPTH):
        nested = [nested]

    with pytest.raises(errors.ResultValidationError, match="maximum JSON nesting"):
        CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="Project is not configured.",
            remediation="Run 'agentharness bootstrap' to configure this project.",
            details={"nested": nested},
        )


@pytest.mark.parametrize(
    "unsupported",
    [models.MIN_JSON_INTEGER - 1, models.MAX_JSON_INTEGER + 1],
)
def test_command_result_rejects_out_of_range_integers(unsupported):
    with pytest.raises(errors.ResultValidationError, match="64-bit range"):
        CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="Project is not configured.",
            remediation="Run 'agentharness bootstrap' to configure this project.",
            details={"unsupported": unsupported},
        )


def test_command_result_integer_boundaries_round_trip_through_json():
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project is not configured.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={
            "minimum": models.MIN_JSON_INTEGER,
            "maximum": models.MAX_JSON_INTEGER,
            "finite_float": 1.25,
        },
    )

    assert json.loads(render_json(result))["details"] == {
        "finite_float": 1.25,
        "maximum": models.MAX_JSON_INTEGER,
        "minimum": models.MIN_JSON_INTEGER,
    }


def test_command_result_maximum_nesting_round_trips_through_json():
    nested: object = "leaf"
    for _ in range(models.MAX_JSON_NESTING_DEPTH - 1):
        nested = [nested]
    result = CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project is not configured.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"nested": nested},
    )

    assert json.loads(render_json(result))["details"] == {"nested": nested}
