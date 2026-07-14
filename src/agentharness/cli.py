import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from typing import Never, TextIO

from agentharness.errors import CommandUsageError
from agentharness.models import (
    CommandResult,
    JsonValue,
    Outcome,
    ResultCode,
    SupportedJsonValue,
)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise CommandUsageError from None


def create_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(prog="agentharness", add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status", add_help=False)
    status_parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def execute_status() -> CommandResult:
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project is not configured.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"state": "not_configured"},
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
        result = execute_status()
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
    return 0
