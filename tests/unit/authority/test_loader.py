"""Tests for authority contract loading and backward compatibility."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from agentharness.authority import AuthorityError, Operation
from agentharness.authority.loader import load_contract_text, load_effective_authority


class TestLoadContractText:
    """Test loading a contract from JSON text."""

    def test_valid_minimal_contract(self) -> None:
        """Minimal valid contract loads."""
        payload = json.dumps(
            {
                "schema_version": 1,
                "grants": [],
                "revoked": [],
            }
        )
        contract = load_contract_text(payload)
        assert contract.schema_version == 1
        assert len(contract.grants) == 0
        assert len(contract.revoked) == 0

    def test_contract_with_single_grant(self) -> None:
        """Contract with a single grant loads."""
        payload = json.dumps(
            {
                "schema_version": 1,
                "grants": [
                    {
                        "operations": ["push"],
                        "target": "main",
                        "expires": "2026-07-23T00:00:00Z",
                        "granted_by": "operator",
                    }
                ],
                "revoked": [],
            }
        )
        contract = load_contract_text(payload)
        assert len(contract.grants) == 1
        grant = contract.grants[0]
        assert grant.operations == (Operation.PUSH,)
        assert grant.target == "main"
        assert grant.expires == "2026-07-23T00:00:00Z"
        assert grant.granted_by == "operator"

    def test_contract_with_multiple_operations(self) -> None:
        """Grant with multiple operations loads."""
        payload = json.dumps(
            {
                "schema_version": 1,
                "grants": [
                    {
                        "operations": ["push", "commit", "pr-create"],
                    }
                ],
                "revoked": [],
            }
        )
        contract = load_contract_text(payload)
        grant = contract.grants[0]
        assert len(grant.operations) == 3
        assert Operation.PUSH in grant.operations
        assert Operation.COMMIT in grant.operations
        assert Operation.PR_CREATE in grant.operations

    def test_contract_with_revocations(self) -> None:
        """Contract with revoked operations loads."""
        payload = json.dumps(
            {
                "schema_version": 1,
                "grants": [{"operations": ["push", "commit"]}],
                "revoked": ["push"],
            }
        )
        contract = load_contract_text(payload)
        assert "push" in contract.revoked
        assert len(contract.revoked) == 1

    def test_grant_without_optional_fields(self) -> None:
        """Grant without optional fields (target, expires, granted_by) loads."""
        payload = json.dumps(
            {
                "schema_version": 1,
                "grants": [{"operations": ["push"]}],
                "revoked": [],
            }
        )
        contract = load_contract_text(payload)
        grant = contract.grants[0]
        assert grant.target is None
        assert grant.expires is None
        assert grant.granted_by is None

    def test_bytes_payload(self) -> None:
        """Bytes payload is handled."""
        payload = json.dumps(
            {
                "schema_version": 1,
                "grants": [],
                "revoked": [],
            }
        ).encode("utf-8")
        contract = load_contract_text(payload)
        assert contract.schema_version == 1

    def test_invalid_json_raises_error(self) -> None:
        """Invalid JSON raises AuthorityError."""
        with pytest.raises(AuthorityError) as exc_info:
            load_contract_text("not valid json")
        assert exc_info.value.code == "authority.invalid_json"

    def test_non_object_payload_raises_error(self) -> None:
        """Non-object JSON raises AuthorityError."""
        with pytest.raises(AuthorityError) as exc_info:
            load_contract_text("[]")
        assert exc_info.value.code == "authority.schema_invalid"

    def test_missing_required_fields_raises_error(self) -> None:
        """Missing required fields (grants, revoked) raises error."""
        with pytest.raises(AuthorityError) as exc_info:
            load_contract_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "grants": [],
                        # missing "revoked"
                    }
                )
            )
        assert exc_info.value.code == "authority.schema_invalid"

    def test_wrong_schema_version_raises_error(self) -> None:
        """Wrong schema version raises error."""
        with pytest.raises(AuthorityError) as exc_info:
            load_contract_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "grants": [],
                        "revoked": [],
                    }
                )
            )
        assert exc_info.value.code == "authority.schema_invalid"

    def test_invalid_operation_name_raises_error(self) -> None:
        """Invalid operation name raises error."""
        with pytest.raises(AuthorityError) as exc_info:
            load_contract_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "grants": [{"operations": ["invalid-op"]}],
                        "revoked": [],
                    }
                )
            )
        assert exc_info.value.code == "authority.schema_invalid"

    def test_invalid_utf8_raises_error(self) -> None:
        """Invalid UTF-8 bytes raise error."""
        with pytest.raises(AuthorityError) as exc_info:
            load_contract_text(b"\xff\xfe")
        assert exc_info.value.code == "authority.invalid_utf8"


class TestLoadEffectiveAuthority:
    """Test loading effective authority with backward compatibility."""

    def test_authority_json_takes_precedence_over_flag(self) -> None:
        """If both .agentharness-authority.json and flag exist, contract wins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create both the contract file and the flag
            contract_data = {
                "schema_version": 1,
                "grants": [{"operations": ["push"], "target": "fix/*"}],
                "revoked": [],
            }
            (repo_root / ".agentharness-authority.json").write_text(
                json.dumps(contract_data)
            )
            (repo_root / ".agentharness-publish-mode").touch()

            # Should load the contract, not the flag
            contract = load_effective_authority(repo_root)
            assert len(contract.grants) == 1
            assert contract.grants[0].target == "fix/*"

    def test_flag_backward_compatibility_grants_all_ops(self) -> None:
        """If only flag exists, it grants all 8 operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".agentharness-publish-mode").touch()

            contract = load_effective_authority(repo_root)
            assert len(contract.grants) == 1

            grant = contract.grants[0]
            assert len(grant.operations) == 8
            assert Operation.PUSH in grant.operations
            assert Operation.COMMIT in grant.operations
            assert Operation.PR_CREATE in grant.operations
            assert Operation.PR_MERGE in grant.operations
            assert Operation.ISSUE_CREATE in grant.operations
            assert Operation.FS_WRITE_OUTSIDE_REPO in grant.operations
            assert Operation.EXTERNAL_MESSAGE in grant.operations
            assert Operation.DESTRUCTIVE_FS in grant.operations

    def test_flag_backward_compatibility_no_target_or_expiry(self) -> None:
        """Flag-based grant has no target or expiry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".agentharness-publish-mode").touch()

            contract = load_effective_authority(repo_root)
            grant = contract.grants[0]
            assert grant.target is None
            assert grant.expires is None

    def test_empty_directory_returns_empty_contract(self) -> None:
        """No files means no grants."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract = load_effective_authority(repo_root)
            assert len(contract.grants) == 0
            assert len(contract.revoked) == 0

    def test_malformed_contract_raises_error(self) -> None:
        """Malformed contract file raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".agentharness-authority.json").write_text(
                "not valid json"
            )

            with pytest.raises(AuthorityError):
                load_effective_authority(repo_root)

    def test_contract_file_takes_precedence_over_missing_flag(self) -> None:
        """Contract file is used even if flag file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_data = {
                "schema_version": 1,
                "grants": [{"operations": ["commit"]}],
                "revoked": [],
            }
            (repo_root / ".agentharness-authority.json").write_text(
                json.dumps(contract_data)
            )

            contract = load_effective_authority(repo_root)
            assert len(contract.grants) == 1
            assert Operation.COMMIT in contract.grants[0].operations

    def test_multiple_grants_in_contract(self) -> None:
        """Contract with multiple grants loads all of them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            contract_data = {
                "schema_version": 1,
                "grants": [
                    {"operations": ["push"], "target": "fix/*"},
                    {"operations": ["commit"], "target": None},
                ],
                "revoked": [],
            }
            (repo_root / ".agentharness-authority.json").write_text(
                json.dumps(contract_data)
            )

            contract = load_effective_authority(repo_root)
            assert len(contract.grants) == 2


class TestBackwardCompatibilityScenarios:
    """Real-world backward compatibility scenarios."""

    def test_existing_publish_mode_flag_still_works(self) -> None:
        """Existing projects with just the flag still work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            # Old-style: just the flag file
            (repo_root / ".agentharness-publish-mode").touch()

            # Should still load and grant all operations
            contract = load_effective_authority(repo_root)
            assert len(contract.grants) == 1
            assert len(contract.grants[0].operations) == 8

    def test_migration_from_flag_to_contract(self) -> None:
        """Operator can migrate from flag to contract by creating the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Start with flag
            (repo_root / ".agentharness-publish-mode").touch()
            contract1 = load_effective_authority(repo_root)
            assert len(contract1.grants[0].operations) == 8

            # Migrate: create contract file (which takes precedence)
            contract_data = {
                "schema_version": 1,
                "grants": [{"operations": ["push"], "target": "fix/*"}],
                "revoked": [],
            }
            (repo_root / ".agentharness-authority.json").write_text(
                json.dumps(contract_data)
            )

            contract2 = load_effective_authority(repo_root)
            assert len(contract2.grants) == 1
            assert contract2.grants[0].target == "fix/*"
