#!/usr/bin/env python3
"""
Config loader with environment variable interpolation.

Loads YAML configuration files and interpolates environment variables
using the ${VAR_NAME:-default_value} syntax.

Usage:
    from config_loader import load_config
    config = load_config('config/logging.yaml')

Environment variable substitution:
    ${LOGGING_LEVEL}           → value of LOGGING_LEVEL env var (error if not set)
    ${LOGGING_LEVEL:-INFO}     → value of LOGGING_LEVEL or "INFO" if not set
    ${LOG_PATH:-./logs}        → value of LOG_PATH or "./logs" if not set
"""

import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover — defensive; PyYAML is a required dependency
    raise ImportError(
        "PyYAML is required for config_loader. Install with: pip install pyyaml"
    ) from e


def find_env_var_placeholders(value: str):
    """
    Scan a string for ${VAR_NAME} / ${VAR_NAME:-default} placeholders.

    A regex can't correctly find the closing '}' when a default value
    itself contains braces (e.g. ${LOG_FILENAME:-app-{date}.log} — a
    non-greedy `.*?}` stops at the first '}', truncating the default to
    "app-{date"). This scans character-by-character instead, tracking
    brace depth inside the default so nested '{'/'}' pairs don't end the
    placeholder early.

    Yields (start, end, var_name, default_value) tuples, where `end` is
    the index just past the placeholder's closing '}' and `default_value`
    is None if no ':-' was present.
    """
    i = 0
    n = len(value)
    while i < n:
        if value[i:i + 2] != "${":
            i += 1
            continue

        start = i
        j = i + 2
        name_start = j
        while j < n and value[j] not in ":}":
            j += 1
        var_name = value[name_start:j]

        default_value = None
        if j < n and value[j] == ":" and value[j + 1:j + 2] == "-":
            j += 2
            default_start = j
            depth = 0
            while j < n and not (value[j] == "}" and depth == 0):
                if value[j] == "{":
                    depth += 1
                elif value[j] == "}":
                    depth -= 1
                j += 1
            default_value = value[default_start:j]

        if j >= n or value[j] != "}":
            raise ValueError(
                f"Malformed environment variable placeholder starting at "
                f"position {start} in {value!r}: missing closing '}}'"
            )

        yield start, j + 1, var_name, default_value
        i = j + 1


def interpolate_env_vars(value: str) -> str:
    """
    Interpolate environment variables in a string.

    Supports the syntax: ${VAR_NAME} or ${VAR_NAME:-default_value}
    - ${VAR_NAME}: Require the env var to be set; error if missing
    - ${VAR_NAME:-default}: Use default if env var not set. The default
      may itself contain literal '{' / '}' characters (e.g. a date
      format placeholder) without being mistaken for the closing brace.

    Args:
        value: String potentially containing env var placeholders

    Returns:
        String with environment variables substituted

    Raises:
        ValueError: If a required env var is not set, or a placeholder
            is malformed (missing closing '}')
    """
    pieces = []
    cursor = 0
    for start, end, var_name, default_value in find_env_var_placeholders(value):
        pieces.append(value[cursor:start])

        env_value = os.environ.get(var_name)
        if env_value is not None:
            pieces.append(env_value)
        elif default_value is not None:
            pieces.append(default_value)
        else:
            raise ValueError(
                f"Required environment variable '{var_name}' not set and no default provided"
            )

        cursor = end

    pieces.append(value[cursor:])
    return "".join(pieces)


def process_config_value(value: Any) -> Any:
    """
    Recursively process config values, interpolating environment variables.

    Handles strings, lists, dicts, and nested structures.

    Args:
        value: Config value (can be any YAML type)

    Returns:
        Processed value with env vars interpolated
    """
    if isinstance(value, str):
        return interpolate_env_vars(value)
    elif isinstance(value, dict):
        return {k: process_config_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [process_config_value(item) for item in value]
    else:
        # Numbers, booleans, None — pass through unchanged
        return value


def load_config(config_path: str) -> Any:
    """
    Load YAML configuration file with environment variable interpolation.

    Args:
        config_path: Path to YAML config file

    Returns:
        Parsed configuration with env vars interpolated. Typically a dict,
        but reflects whatever type the YAML document's root actually is
        (list, string, number, etc.) — same as yaml.safe_load.

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValueError: If required env vars are not set
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    # Process all values to interpolate environment variables
    return process_config_value(config)


def main(argv=None) -> int:
    """CLI entrypoint. Extracted from `__main__` so tests can call it
    in-process (subprocess-invoked code isn't visible to coverage.py
    without extra setup, and this is simpler and faster than that).

    Resolved values (including anything pulled from the environment,
    which may be secrets) are never printed by default — only
    --show-config opts into that.
    """
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        print(
            f"Usage: {argv[0]} <config_file> [--show-env-vars] [--show-config]",
            file=sys.stderr,
        )
        return 1

    config_file = argv[1]
    show_env_vars = "--show-env-vars" in argv
    show_config = "--show-config" in argv

    try:
        config = load_config(config_file)

        if show_env_vars:
            print("Environment variables referenced:")
            with open(config_file) as f:
                content = f.read()
            for _, _, var_name, _default_value in find_env_var_placeholders(content):
                # A var with neither an env value nor a default would have
                # already raised inside load_config() above, so by this
                # point every placeholder is one or the other.
                if os.environ.get(var_name) is not None:
                    status = "set (from environment)"
                else:
                    status = "not set, using default"
                print(f"  {var_name}: {status}")
            print()

        if show_config:
            import json

            print(json.dumps(config, indent=2))
        else:
            print(f"OK: {config_file} loaded and interpolated successfully.")
            print("(pass --show-config to print the resolved config — may include secrets)")
        return 0
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover — entry point, all logic is in main() and tested there
    sys.exit(main())
