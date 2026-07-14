import subprocess
import sys
from pathlib import Path

from agentharness.cli import main

EXPECTED_STATUS_JSON = (
    '{"code": "status_available", "details": {"state": "not_configured"}, '
    '"outcome": "success", "remediation": "Run \'agentharness bootstrap\' to '
    'configure this project.", "schema_version": 1, '
    '"summary": "Project is not configured."}\n'
)


def test_status_json_has_stable_result_shape(capsys):
    exit_code = main(["status", "--json"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (0, EXPECTED_STATUS_JSON, "")


def test_status_human_output_states_project_is_not_configured(capsys):
    exit_code = main(["status"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (
        0,
        "success: Project is not configured.\n"
        "Next: Run 'agentharness bootstrap' to configure this project.\n",
        "",
    )


def test_module_entry_point_emits_stable_status_json():
    project_root = Path(__file__).parents[2]
    completed = subprocess.run(
        [sys.executable, "-m", "agentharness", "status", "--json"],
        cwd=project_root,
        env={"PYTHONPATH": str(project_root / "src")},
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        0,
        EXPECTED_STATUS_JSON,
        "",
    )


def test_invalid_command_is_safe(capsys, monkeypatch):
    secret = "credential-value-that-must-not-leak"
    monkeypatch.setenv("AGENTHARNESS_TOKEN", secret)

    exit_code = main(["unknown-command"])

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert exit_code == 2
    assert "Traceback" not in output
    assert secret not in output
