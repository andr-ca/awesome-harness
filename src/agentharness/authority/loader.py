"""Loader for authority contracts with backward-compatibility support."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

import fastjsonschema  # type: ignore[import-untyped]

from agentharness.authority import AuthorityError, Contract, Grant, Operation


def _validate(document: dict[str, Any], schema_name: str, prefix: str) -> None:
    """Validate a document against a JSON schema."""
    try:
        schema_text = (
            resources.files("agentharness.schemas")
            .joinpath(schema_name)
            .read_text(encoding="utf-8")
        )
        schema = json.loads(schema_text)
        fastjsonschema.compile(schema)(document)
    except (fastjsonschema.JsonSchemaException, OSError, json.JSONDecodeError) as error:
        raise AuthorityError(
            f"{prefix}.schema_invalid", f"document does not match {schema_name}"
        ) from error


def load_contract_text(payload: str | bytes) -> Contract:
    """Load and validate a JSON authority contract."""
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    except UnicodeDecodeError as error:
        raise AuthorityError(
            "authority.invalid_utf8", "Contract must be UTF-8 encoded"
        ) from error

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise AuthorityError(
            "authority.invalid_json", "Contract must be valid JSON"
        ) from error

    if not isinstance(document, dict):
        raise AuthorityError(
            "authority.schema_invalid", "Contract must be a JSON object"
        )

    _validate(document, "authority-v1.json", "authority")

    # Parse grants
    grants: list[Grant] = []
    for grant_doc in document.get("grants", []):
        assert isinstance(grant_doc, dict)
        operations = tuple(
            Operation(op) for op in grant_doc.get("operations", [])
        )
        grant = Grant(
            operations=operations,
            target=grant_doc.get("target"),
            expires=grant_doc.get("expires"),
            granted_by=grant_doc.get("granted_by"),
        )
        grants.append(grant)

    return Contract(
        schema_version=1,
        grants=tuple(grants),
        revoked=tuple(document.get("revoked", [])),
    )


def load_effective_authority(repo_root: Path) -> Contract:
    """Load the effective authority contract with backward compatibility.

    Precedence:
    1. If .agentharness-authority.json exists, use it (new contract model)
    2. Else if .agentharness-publish-mode flag exists, treat as grant of ALL 8
       operations, any target, no expiry (backward compat)
    3. Else return a contract with no grants (default deny)
    """
    contract_path = repo_root / ".agentharness-authority.json"
    publish_mode_path = repo_root / ".agentharness-publish-mode"

    # Try to load the contract file
    if contract_path.exists():
        try:
            text = contract_path.read_text(encoding="utf-8")
            return load_contract_text(text)
        except (OSError, ValueError) as error:
            raise AuthorityError(
                "authority.load_failed",
                f"Failed to load authority contract from {contract_path}: {error}",
            ) from error

    # Fall back to publish-mode flag (backward compat)
    if publish_mode_path.exists():
        # Grant all 8 operations, any target, no expiry
        all_ops: list[Operation] = [op for op in Operation]
        grant = Grant(
            operations=tuple(all_ops),
            target=None,
            expires=None,
            granted_by=".agentharness-publish-mode flag",
        )
        return Contract(
            schema_version=1,
            grants=(grant,),
            revoked=(),
        )

    # No grant source present — return empty contract (default deny)
    return Contract(
        schema_version=1,
        grants=(),
        revoked=(),
    )
