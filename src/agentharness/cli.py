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

    # GitHub sub-commands
    github_parser = subparsers.add_parser("github", add_help=False)
    github_sub = github_parser.add_subparsers(dest="github_command", required=True)

    # github protection plan
    gh_prot = github_sub.add_parser("protection", add_help=False)
    gh_prot_sub = gh_prot.add_subparsers(dest="prot_command", required=True)
    gh_plan = gh_prot_sub.add_parser("plan", add_help=False)
    gh_plan.add_argument("--repo", required=True, help="owner/repo")
    gh_plan.add_argument("--branch", default="main")
    gh_plan.add_argument("--json", action="store_true", dest="as_json")
    gh_apply = gh_prot_sub.add_parser("apply", add_help=False)
    gh_apply.add_argument("--repo", required=True, help="owner/repo")
    gh_apply.add_argument("--branch", default="main")
    gh_apply.add_argument(
        "--token-env", default="GITHUB_TOKEN", dest="token_env"
    )
    gh_apply.add_argument("--json", action="store_true", dest="as_json")

    # github completion check
    gh_comp = github_sub.add_parser("completion", add_help=False)
    gh_comp_sub = gh_comp.add_subparsers(dest="comp_command", required=True)
    gh_check = gh_comp_sub.add_parser("check", add_help=False)
    gh_check.add_argument("--repo", required=True)
    gh_check.add_argument("--pr", type=int, required=True)
    gh_check.add_argument("--expected-head", required=True)
    gh_check.add_argument(
        "--token-env", default="GITHUB_TOKEN", dest="token_env"
    )
    gh_check.add_argument("--json", action="store_true", dest="as_json")

    # profile sub-commands (AC-10)
    profile_parser = subparsers.add_parser("profile", add_help=False)
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)

    pf_validate = profile_sub.add_parser("validate", add_help=False)
    pf_validate.add_argument("file", type=Path, help="Profile YAML to validate")
    pf_validate.add_argument("--json", action="store_true", dest="as_json")

    pf_explain = profile_sub.add_parser("explain", add_help=False)
    pf_explain.add_argument("file", type=Path, help="Profile YAML to explain")
    pf_explain.add_argument("--json", action="store_true", dest="as_json")

    pf_preview = profile_sub.add_parser("preview", add_help=False)
    pf_preview.add_argument("file", type=Path, help="New profile YAML to preview")
    pf_preview.add_argument(
        "--current", type=Path, default=None, dest="current",
        help="Current profile for diff (default: .agentharness-profile.yaml)"
    )
    pf_preview.add_argument("--json", action="store_true", dest="as_json")

    pf_apply = profile_sub.add_parser("apply", add_help=False)
    pf_apply.add_argument("file", type=Path, help="Profile YAML to apply")
    pf_apply.add_argument(
        "--target", type=Path, default=None,
        help="Target file (default: .agentharness-profile.yaml)"
    )
    pf_apply.add_argument("--json", action="store_true", dest="as_json")

    # authority sub-commands
    authority_parser = subparsers.add_parser("authority", add_help=False)
    authority_parser.add_argument("--json", action="store_true", dest="as_json")
    authority_parser.add_argument("--target-dir", default=".", type=Path)

    authority_sub = authority_parser.add_subparsers(
        dest="authority_command", required=False
    )

    # check subcommand
    auth_check = authority_sub.add_parser("check", add_help=False)
    auth_check.add_argument(
        "--operation", required=True, help="Operation name to check"
    )
    auth_check.add_argument(
        "--target", default=None, help="Optional target (e.g., branch pattern)"
    )
    auth_check.add_argument("target_dir", nargs="?", default=".", type=Path)

    return parser


def execute_status() -> CommandResult:
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project is not configured.",
        remediation="Run 'agentharness bootstrap' to configure this project.",
        details={"state": "not_configured"},
    )


def execute_github_protection_plan(repo: str, branch: str) -> CommandResult:
    """Read current branch protection and compare to desired plan (read-only)."""
    from agentharness.remote.github.models import ProtectionPlan, ProtectionState
    from agentharness.remote.github.protection import plan_protection

    plan = ProtectionPlan(
        branch=branch,
        require_reviews=True,
        required_approvals=1,
        dismiss_stale_reviews=True,
        require_code_owner_reviews=True,
        required_contexts=["CI"],
    )

    # Try to read the current state without writing anything.
    current: ProtectionState | None = None
    try:
        from agentharness.remote.github.api import GitHubClient
        from agentharness.remote.github.auth import get_token
        token = get_token("GITHUB_TOKEN")
        owner, name = (repo.split("/", 1) if "/" in repo else (repo, repo))
        client = GitHubClient(token=token)
        path = f"/repos/{owner}/{name}/branches/{branch}/protection"
        raw = client.get(path)
        reviews = raw.get("required_pull_request_reviews") or {}
        checks = raw.get("required_status_checks") or {}
        current = ProtectionState(
            branch=branch,
            is_protected=True,
            required_approvals=reviews.get("required_approving_review_count", 0),
            dismiss_stale_reviews=reviews.get("dismiss_stale_reviews", False),
            require_code_owner_reviews=reviews.get("require_code_owner_reviews", False),
            required_contexts=checks.get("contexts", []),
        )
    except Exception:  # noqa: BLE001
        pass  # token unavailable or not yet protected — treat as unprotected

    result = plan_protection(plan, current=current)
    status = "applied" if result.matches_plan else "not yet applied"
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"Protection plan for {repo}/{branch}: {status}.",
        remediation=(
            ""
            if result.matches_plan
            else f"Run 'agentharness github protection apply --repo {repo}' to apply."
        ),
        details={
            "repo": repo,
            "branch": branch,
            "matches_plan": result.matches_plan,
            "required_approvals": plan.required_approvals,
        },
    )


def execute_github_protection_apply(
    repo: str,
    branch: str,
    token_env: str,
) -> CommandResult:
    """Apply and read back branch protection for *repo*/*branch*."""
    from agentharness.remote.github.api import APIError, GitHubClient
    from agentharness.remote.github.auth import AuthError, get_token
    from agentharness.remote.github.models import ProtectionPlan
    from agentharness.remote.github.protection import apply_protection

    try:
        token = get_token(token_env)
    except AuthError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=str(e),
            remediation=f"Set ${token_env} to a GitHub token with repo scope.",
            details={},
        )

    owner, name = (repo.split("/", 1) if "/" in repo else (repo, repo))
    plan = ProtectionPlan(
        branch=branch,
        require_reviews=True,
        required_approvals=1,
        dismiss_stale_reviews=True,
        require_code_owner_reviews=True,
        required_contexts=["CI"],
    )
    client = GitHubClient(token=token)
    try:
        reconcile = apply_protection(client, owner, name, plan)
    except APIError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"GitHub API error while applying protection: {e}",
            remediation="Check that the token has repo admin permissions.",
            details={},
        )

    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS if reconcile.matches_plan else Outcome.ERROR,
        summary=(
            "Branch protection applied and verified."
            if reconcile.matches_plan
            else "Branch protection applied but read-back did not match plan."
        ),
        remediation=(
            "Protection is active."
            if reconcile.matches_plan
            else "Re-run with --json to inspect the discrepancy."
        ),
        details={
            "repo": repo,
            "branch": branch,
            "matches_plan": reconcile.matches_plan,
        },
    )


def execute_github_completion_check(
    repo: str,
    pr_number: int,
    expected_head: str,
    token_env: str,
) -> CommandResult:
    """Check the completion gate for a pull request."""
    from agentharness.remote.github.api import APIError, GitHubClient
    from agentharness.remote.github.auth import AuthError, get_token
    from agentharness.remote.github.completion import evaluate_completion
    from agentharness.remote.github.models import PRState
    from agentharness.remote.github.reviews import extract_signals

    try:
        token = get_token(token_env)
    except AuthError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=str(e),
            remediation=f"Set ${token_env} to a GitHub token.",
            details={},
        )

    owner, name = (repo.split("/", 1) if "/" in repo else (repo, repo))
    client = GitHubClient(token=token)
    try:
        pr_data = client.get(f"/repos/{owner}/{name}/pulls/{pr_number}")
        checks_data = client.get(
            f"/repos/{owner}/{name}/commits/{pr_data['head']['sha']}/check-runs"
        )
    except APIError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"GitHub API error: {e}",
            remediation="Check that the token has repo read permissions.",
            details={},
        )

    runs = checks_data.get("check_runs", [])
    passing = [r["name"] for r in runs if r["conclusion"] == "success"]
    failing = [r["name"] for r in runs if r["conclusion"] not in ("success", None)]
    pr = PRState(
        number=pr_number,
        head_sha=pr_data["head"]["sha"],
        is_draft=pr_data.get("draft", False),
        review_decision=pr_data.get("review_decision"),
        unresolved_threads=0,  # would require graphql query
        passing_checks=passing,
        failing_checks=failing,
    )
    signals = extract_signals(pr)
    decision = evaluate_completion(signals, expected_head)

    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS if decision.is_complete else Outcome.ERROR,
        summary=(
            "PR is ready to complete."
            if decision.is_complete
            else f"PR is blocked: {'; '.join(decision.blocking_reasons)}"
        ),
        remediation=(
            "Merge when ready."
            if decision.is_complete
            else "Address the blocking reasons before merging."
        ),
        details={
            "pr": pr_number,
            "head_sha": pr.head_sha,
            "is_complete": decision.is_complete,
            "blocking_reasons": list(decision.blocking_reasons),
        },
    )


def execute_profile_validate(file: Path) -> CommandResult:
    """Validate a profile YAML file against the schema (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        profile = load_profile_text(file.read_text(encoding="utf-8"))
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary=f"Profile is valid (schema_version={profile.schema_version}).",
            remediation="",
            details={
                "file": str(file),
                "schema_version": profile.schema_version,
                "requirement_count": len(profile.requirements),
                "rigor": profile.project.rigor,
            },
        )
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile validation failed: {e}",
            remediation="Fix the YAML schema errors and retry.",
            details={"file": str(file), "error": str(e)},
        )


def execute_profile_explain(file: Path) -> CommandResult:
    """Show all requirements with capability/mode/gates (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        profile = load_profile_text(file.read_text(encoding="utf-8"))
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Could not parse profile: {e}",
            remediation="Run 'agentharness profile validate <file>' to diagnose.",
            details={"file": str(file), "error": str(e)},
        )
    reqs: list[dict[str, object]] = [
        {
            "id": r.identifier,
            "provider": r.provider,
            "enabled": r.enabled,
            "gates": [str(g) for g in r.gates],
            "minimum_coverage": getattr(r, "minimum_coverage", None),
        }
        for r in profile.requirements
    ]
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"{len(reqs)} requirement(s) in {file}",
        remediation="",
        details={
            "file": str(file),
            "requirements": reqs,  # type: ignore[dict-item]
        }
    )


def execute_profile_preview(file: Path, current: Path | None) -> CommandResult:
    """Show what diff a profile apply would make (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        load_profile_text(file.read_text(encoding="utf-8"))
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Incoming profile is invalid: {e}",
            remediation="Fix the YAML and retry.",
            details={"file": str(file), "error": str(e)},
        )
    current_path = current or Path(".agentharness-profile.yaml")
    if not current_path.exists():
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary=(
                f"No current profile at {current_path}"
                " — applying would create a new profile."
            ),
            remediation="",
            details={
                "current_file": str(current_path),
                "incoming_file": str(file),
                "diff": "new_file",
            },
        )
    current_text = current_path.read_text(encoding="utf-8")
    incoming_text = file.read_text(encoding="utf-8")
    if current_text == incoming_text:
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="No changes — incoming profile is identical to current.",
            remediation="",
            details={
                "current_file": str(current_path),
                "incoming_file": str(file),
                "diff": "no_change",
            },
        )
    import difflib
    diff_lines: list[str] = list(
        difflib.unified_diff(
            current_text.splitlines(),
            incoming_text.splitlines(),
            fromfile=str(current_path),
            tofile=str(file),
            lineterm="",
        )
    )
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"{len(diff_lines)} diff line(s) between current and incoming profile.",
        remediation="Run 'agentharness profile apply <file>' to apply.",
        details={
            "current_file": str(current_path),
            "incoming_file": str(file),
            "diff": "changed",
            "diff_lines": diff_lines,  # type: ignore[dict-item]
        },
    )


def execute_profile_apply(file: Path, target: Path | None) -> CommandResult:
    """Write the profile to the target path (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        load_profile_text(file.read_text(encoding="utf-8"))
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile validation failed — not applied: {e}",
            remediation="Fix the YAML errors before applying.",
            details={"file": str(file), "error": str(e)},
        )
    target_path = target or Path(".agentharness-profile.yaml")
    try:
        target_path.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Could not write profile to {target_path}: {e}",
            remediation="Check file system permissions.",
            details={"target": str(target_path), "error": str(e)},
        )
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"Profile applied to {target_path}.",
        remediation="",
        details={"source": str(file), "target": str(target_path)},
    )


def execute_authority_check(
    operation: str, target: str | None, target_dir: Path
) -> CommandResult:
    """Check if an operation is authorized."""
    from agentharness.authority.loader import load_effective_authority
    from agentharness.authority.operations import decide

    repo_root = target_dir.resolve()
    try:
        contract = load_effective_authority(repo_root)
    except ValueError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Failed to load authority contract: {e}",
            remediation="Check the authority contract file and try again.",
            details={"repo_root": str(repo_root), "error": str(e)},
        )

    decision = decide(contract, operation, target)
    if decision.allowed:
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary=f"Operation '{operation}' is authorized.",
            remediation="",
            details={"operation": operation, "target": target, "allowed": True},
        )
    else:
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.ERROR,
            summary=f"Operation '{operation}' is not authorized: {decision.reason}",
            remediation="Request appropriate authority or contact the operator.",
            details={
                "operation": operation,
                "target": target,
                "allowed": False,
                "reason": decision.reason,
            },
        )


def execute_authority_info(as_json: bool, target_dir: Path) -> CommandResult:
    """Display or report the effective authority."""
    from datetime import UTC, datetime

    from agentharness.authority.loader import load_effective_authority

    repo_root = target_dir.resolve()
    try:
        contract = load_effective_authority(repo_root)
    except ValueError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Failed to load authority contract: {e}",
            remediation="Check the authority contract file.",
            details={"repo_root": str(repo_root), "error": str(e)},
        )

    # Determine the source of authority
    contract_path = repo_root / ".agentharness-authority.json"
    flag_path = repo_root / ".agentharness-publish-mode"
    if contract_path.exists():
        source = "contract"
    elif flag_path.exists():
        source = "flag"
    else:
        source = "none"

    # Build operations list with details
    operations_granted: list[dict[str, object]] = []
    now = datetime.now(UTC)

    for grant in contract.grants:
        for op in grant.operations:
            status = "active"
            reason = None
            if op.value in contract.revoked:
                status = "revoked"
                reason = "revoked"
            elif grant.expires:
                try:
                    if grant.expires.endswith("Z"):
                        expires_str = grant.expires.rstrip("Z") + "+00:00"
                    else:
                        expires_str = grant.expires
                    expires_dt = datetime.fromisoformat(expires_str)
                    if now >= expires_dt:
                        status = "expired"
                        reason = f"expired at {grant.expires}"
                except (ValueError, TypeError):
                    status = "invalid"
                    reason = "invalid expiry format"

            operations_granted.append(
                {
                    "operation": op.value,
                    "target": grant.target,
                    "expires": grant.expires,
                    "granted_by": grant.granted_by,
                    "status": status,
                    "reason": reason,
                }
            )

    details = {
        "source": source,
        "schema_version": contract.schema_version,
        "operations_granted": operations_granted,
        "revoked": list(contract.revoked),
    }

    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"Authority source: {source}",
        remediation="",
        details=details,
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
        elif arguments.command == "github":
            result = _dispatch_github(arguments)
        elif arguments.command == "profile":
            result = _dispatch_profile(arguments)
        elif arguments.command == "authority":
            result = _dispatch_authority(arguments)
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

    as_json = getattr(arguments, "as_json", False)
    rendered = render_json(result) if as_json else render_human(result)
    print(rendered, file=destination)
    return 0 if result.outcome is Outcome.SUCCESS else 1


def _dispatch_github(arguments: argparse.Namespace) -> CommandResult:
    """Route github sub-commands."""
    if arguments.github_command == "protection":
        if arguments.prot_command == "plan":
            return execute_github_protection_plan(arguments.repo, arguments.branch)
        if arguments.prot_command == "apply":
            return execute_github_protection_apply(
                arguments.repo,
                arguments.branch,
                arguments.token_env,
            )
    if arguments.github_command == "completion":
        if arguments.comp_command == "check":
            return execute_github_completion_check(
                arguments.repo,
                arguments.pr,
                arguments.expected_head,
                arguments.token_env,
            )
    raise CommandUsageError

def _dispatch_profile(arguments: argparse.Namespace) -> CommandResult:
    """Route profile sub-commands (AC-10)."""
    if arguments.profile_command == "validate":
        return execute_profile_validate(arguments.file)
    if arguments.profile_command == "explain":
        return execute_profile_explain(arguments.file)
    if arguments.profile_command == "preview":
        return execute_profile_preview(arguments.file, arguments.current)
    if arguments.profile_command == "apply":
        return execute_profile_apply(arguments.file, arguments.target)
    raise CommandUsageError


def _dispatch_authority(arguments: argparse.Namespace) -> CommandResult:
    """Route authority sub-commands."""
    if arguments.authority_command == "check":
        return execute_authority_check(
            arguments.operation, arguments.target, arguments.target_dir
        )
    # Default: show authority info
    target_dir = arguments.target_dir
    as_json = arguments.as_json
    return execute_authority_info(as_json, target_dir)
