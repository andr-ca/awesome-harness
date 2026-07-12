#!/usr/bin/env python3
"""
Tests for config_loader.py — environment variable interpolation in YAML configs.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# config_loader.py lives alongside this test file, which isn't on sys.path
# when pytest is invoked from the repo root (or anywhere else).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_loader import interpolate_env_vars, load_config, main, process_config_value  # noqa: E402


class TestInterpolateEnvVars:
    """Tests for direct env var interpolation."""

    def test_simple_substitution(self):
        """${VAR} is replaced with env var value."""
        os.environ["TEST_VAR"] = "hello"
        result = interpolate_env_vars("prefix-${TEST_VAR}-suffix")
        assert result == "prefix-hello-suffix"

    def test_substitution_with_default(self):
        """${VAR:-default} uses default if env var not set."""
        os.environ.pop("MISSING_VAR", None)
        result = interpolate_env_vars("value: ${MISSING_VAR:-fallback}")
        assert result == "value: fallback"

    def test_substitution_prefers_env_var(self):
        """${VAR:-default} uses env var if set, ignoring default."""
        os.environ["TEST_VAR"] = "actual"
        result = interpolate_env_vars("${TEST_VAR:-default}")
        assert result == "actual"

    def test_multiple_substitutions(self):
        """Multiple ${VAR} in one string are all replaced."""
        os.environ["VAR1"] = "a"
        os.environ["VAR2"] = "b"
        result = interpolate_env_vars("${VAR1}/${VAR2}")
        assert result == "a/b"

    def test_default_containing_braces_is_not_truncated(self):
        """${VAR:-app-{date}.log} keeps the literal braces in the default.

        Regression test: a naive non-greedy regex stops at the first '}',
        which truncates this to "app-{date" and leaves ".log}" dangling —
        exactly the pattern logging.yaml.example uses for its filename.
        """
        os.environ.pop("LOG_FILENAME", None)
        result = interpolate_env_vars("${LOG_FILENAME:-app-{date}.log}")
        assert result == "app-{date}.log"

    def test_env_var_overrides_default_containing_braces(self):
        """A set env var still wins over a brace-containing default."""
        os.environ["LOG_FILENAME"] = "custom.log"
        result = interpolate_env_vars("${LOG_FILENAME:-app-{date}.log}")
        assert result == "custom.log"

    def test_missing_required_var_raises_error(self):
        """${VAR} without default raises error if var not set."""
        os.environ.pop("UNDEFINED_VAR", None)
        with pytest.raises(ValueError, match="UNDEFINED_VAR"):
            interpolate_env_vars("${UNDEFINED_VAR}")

    def test_no_substitution_needed(self):
        """Strings without ${...} are returned unchanged."""
        result = interpolate_env_vars("just a string")
        assert result == "just a string"

    def test_malformed_placeholder_missing_closing_brace_raises(self):
        """A placeholder with no closing '}' raises a clear ValueError."""
        with pytest.raises(ValueError, match="missing closing"):
            interpolate_env_vars("${UNCLOSED")


class TestProcessConfigValue:
    """Tests for recursive config processing."""

    def test_string_value(self):
        """String values are interpolated."""
        os.environ["TEST"] = "value"
        result = process_config_value("${TEST}")
        assert result == "value"

    def test_dict_value(self):
        """Dict values are recursively processed."""
        os.environ["KEY"] = "val"
        config = {"nested": {"var": "${KEY}"}}
        result = process_config_value(config)
        assert result == {"nested": {"var": "val"}}

    def test_list_value(self):
        """List values are recursively processed."""
        os.environ["ITEM"] = "x"
        config = ["${ITEM}", "static"]
        result = process_config_value(config)
        assert result == ["x", "static"]

    def test_number_value(self):
        """Numbers pass through unchanged."""
        assert process_config_value(42) == 42
        assert process_config_value(3.14) == 3.14

    def test_boolean_value(self):
        """Booleans pass through unchanged."""
        assert process_config_value(True) is True
        assert process_config_value(False) is False

    def test_none_value(self):
        """None passes through unchanged."""
        assert process_config_value(None) is None

    def test_complex_nested_structure(self):
        """Complex nested structures are fully processed."""
        os.environ["ENV_VAR"] = "production"
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "env": "${ENV_VAR:-dev}",
            },
            "services": [
                {"name": "auth", "env": "${ENV_VAR}"},
                {"name": "api", "port": 8080},
            ],
        }
        result = process_config_value(config)
        assert result["database"]["env"] == "production"
        assert result["services"][0]["env"] == "production"
        assert result["services"][1]["port"] == 8080


class TestLoadConfig:
    """Tests for loading and processing config files."""

    def test_load_yaml_config(self):
        """Can load and process a YAML config file."""
        os.environ["LOG_LEVEL"] = "DEBUG"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "logging": {
                            "level": "${LOG_LEVEL:-INFO}",
                            "format": "json",
                        }
                    }
                )
            )

            config = load_config(str(config_path))
            assert config["logging"]["level"] == "DEBUG"
            assert config["logging"]["format"] == "json"

    def test_missing_config_file_raises_error(self):
        """FileNotFoundError raised for missing config file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_uses_defaults_when_env_vars_not_set(self):
        """Defaults are used when environment variables aren't set."""
        os.environ.pop("UNDEFINED_VAR", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "setting": "${UNDEFINED_VAR:-default_value}",
                    }
                )
            )

            config = load_config(str(config_path))
            assert config["setting"] == "default_value"

    def test_empty_yaml_file(self):
        """Empty YAML file loads as empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("")

            config = load_config(str(config_path))
            assert config == {}


class TestCLI:
    """Tests for main(), the CLI entrypoint used by `python config_loader.py`.

    Calls main() directly (in-process) rather than via subprocess: it's
    faster, and subprocess-invoked code isn't visible to coverage.py
    without extra sitecustomize/COVERAGE_PROCESS_START configuration.
    main() takes argv explicitly for exactly this reason.
    """

    def _config_with_secret(self, tmpdir):
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(
            yaml.dump({"service": {"name": "myapp", "secret": "${API_KEY}"}})
        )
        return str(config_path)

    def _config_with_secret_and_default(self, tmpdir):
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "service": {
                        "name": "myapp",
                        "secret": "${API_KEY}",
                        "region": "${REGION:-us-east-1}",
                    }
                }
            )
        )
        return str(config_path)

    def test_no_args_prints_usage_and_returns_nonzero(self, capsys):
        exit_code = main(["config_loader.py"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "Usage" in captured.err

    def test_defaults_to_sys_argv_when_called_with_no_argument(self, monkeypatch, capsys):
        """main() with no argv falls back to sys.argv (the real CLI path)."""
        monkeypatch.setattr(sys, "argv", ["config_loader.py"])
        exit_code = main()
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "Usage" in captured.err

    def test_missing_config_file_errors_and_returns_nonzero(self, capsys):
        exit_code = main(["config_loader.py", "/nonexistent/config.yaml"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "ERROR" in captured.err

    def test_default_output_does_not_leak_secret(self, capsys):
        os.environ["API_KEY"] = "sk-super-secret-value"
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = self._config_with_secret(tmpdir)
            exit_code = main(["config_loader.py", config_file])
            captured = capsys.readouterr()
            assert exit_code == 0
            assert "loaded and interpolated successfully" in captured.out
            assert "sk-super-secret-value" not in captured.out

    def test_show_env_vars_reports_status_not_value(self, capsys):
        os.environ["API_KEY"] = "sk-super-secret-value"
        os.environ.pop("REGION", None)
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = self._config_with_secret_and_default(tmpdir)
            exit_code = main(["config_loader.py", config_file, "--show-env-vars"])
            captured = capsys.readouterr()
            assert exit_code == 0
            assert "API_KEY: set (from environment)" in captured.out
            assert "REGION: not set, using default" in captured.out
            assert "sk-super-secret-value" not in captured.out

    def test_show_config_prints_resolved_value(self, capsys):
        os.environ["API_KEY"] = "sk-super-secret-value"
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = self._config_with_secret(tmpdir)
            exit_code = main(["config_loader.py", config_file, "--show-config"])
            captured = capsys.readouterr()
            assert exit_code == 0
            assert "sk-super-secret-value" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
