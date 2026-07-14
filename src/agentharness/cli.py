import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Never, TextIO

from agentharness.errors import CommandUsageError
from agentharness.models import (
    CommandResult,
    JsonValue,
    Outcome,
    ResultCode,
    SupportedJsonValue,
)
from agentharness.runtime_upgrade import (
    UpgradePlanningError,
    load_upgrade_request,
    plan_upgrade,
)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise CommandUsageError from None


def create_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(prog="agentharness", add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status", add_help=False)
    status_parser.add_argument("--json", action="store_true", dest="as_json")
    runtime_parser = subparsers.add_parser("runtime", add_help=False)
    runtime_subparsers = runtime_parser.add_subparsers(
        dest="runtime_command", required=True
    )
    plan_upgrade_parser = runtime_subparsers.add_parser(
        "plan-upgrade", add_help=False
    )
    plan_upgrade_parser.add_argument("--base-lock", type=Path, required=True)
    plan_upgrade_parser.add_argument("--request", type=Path, required=True)
    plan_upgrade_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def execute_status() -> CommandResult:
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project is not configured.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"state": "not_configured"},
    )


def execute_runtime_plan_upgrade(
    request_path: Path, trusted_base_lock: Path
) -> CommandResult:
    try:
        plan = plan_upgrade(
            load_upgrade_request(
                request_path,
                trusted_base_lock=trusted_base_lock,
            )
        )
    except UpgradePlanningError:
        return CommandResult(
            code=ResultCode.RUNTIME_UPGRADE_REJECTED,
            outcome=Outcome.ERROR,
            summary="Runtime upgrade is not admissible under the base lock.",
            remediation=(
                "Inspect the base-authoritative upgrade evidence and keep the "
                "base lock."
            ),
        )
    return CommandResult(
        code=ResultCode.RUNTIME_UPGRADE_PLANNED,
        outcome=Outcome.SUCCESS,
        summary="Runtime upgrade is admissible under the base lock.",
        remediation="Review and commit the protected runtime lock diff.",
        details={
            "evaluator_core_version": plan.evaluator.core_version,
            "candidate_core_version": plan.candidate.core_version,
            "candidate_schema_version": plan.candidate.schema_version,
            "contracts": plan.contracts,
            "lock_diff": plan.lock_diff,
        },
    )


def _to_json_value(value: SupportedJsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _to_json_value(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    return value


def result_to_dict(result: CommandResult) -> dict[str, JsonValue]:
    return {
        "schema_version": result.schema_version,
        "code": result.code.value,
        "outcome": result.outcome.value,
        "summary": result.summary,
        "remediation": result.remediation,
        "details": {
            key: _to_json_value(value) for key, value in result.details.items()
        },
    }


def render_json(result: CommandResult) -> str:
    return json.dumps(result_to_dict(result), allow_nan=False, sort_keys=True)


def render_human(result: CommandResult) -> str:
    return f"{result.outcome.value}: {result.summary}\nNext: {result.remediation}"


def main(argv: Sequence[str] | None = None, output: TextIO | None = None) -> int:
    destination = output if output is not None else sys.stdout
    try:
        arguments = create_parser().parse_args(argv)
        if arguments.command == "status":
            result = execute_status()
        else:
            result = execute_runtime_plan_upgrade(
                arguments.request,
                arguments.base_lock,
            )
    except CommandUsageError:
        result = CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary="The command is invalid.",
            remediation="Run 'agentharness status' to inspect this project.",
        )
        print(render_human(result), file=destination)
        return 2

    rendered = render_json(result) if arguments.as_json else render_human(result)
    print(rendered, file=destination)
    return 0 if result.outcome is Outcome.SUCCESS else 1
