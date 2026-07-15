"""Tests for Tasks 3-7 of Slice 4.

Covers documentation, changelog, integrations, agents, and operations.
"""

from __future__ import annotations

from pathlib import Path

from agentharness.integrations.agents import (
    find_canonical_source,
    list_generated_clients,
)
from agentharness.integrations.files import (
    MergeStrategy,
    plan_create,
    plan_managed_block,
)
from agentharness.integrations.managed_block import apply_managed_block
from agentharness.integrations.structured_merge import merge_json_keys
from agentharness.plugins.core.changelog import (
    ChangelogStrategy,
    detect_changelog_policy,
)
from agentharness.plugins.core.documentation import (
    DocStrategy,
    detect_documentation_policy,
)


class TestDocumentationPolicy:
    def test_readme_only(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\n")
        result = detect_documentation_policy(tmp_path)
        assert result.strategy == DocStrategy.README_ONLY

    def test_sphinx_detected(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "conf.py").write_text("project = 'test'\n")
        result = detect_documentation_policy(tmp_path)
        assert result.strategy == DocStrategy.SPHINX

    def test_absent(self, tmp_path: Path) -> None:
        result = detect_documentation_policy(tmp_path)
        assert result.strategy == DocStrategy.ABSENT


class TestChangelogPolicy:
    def test_keepachangelog_detected(self, tmp_path: Path) -> None:
        content = "# Changelog\nFormat loosely follows [Keep a Changelog].\n"
        (tmp_path / "CHANGELOG.md").write_text(content)
        result = detect_changelog_policy(tmp_path)
        assert result.strategy == ChangelogStrategy.KEEPACHANGELOG

    def test_monolithic_without_keepachangelog(self, tmp_path: Path) -> None:
        (tmp_path / "CHANGELOG.md").write_text("# Changes\n## v1.0\n- Something\n")
        result = detect_changelog_policy(tmp_path)
        assert result.strategy == ChangelogStrategy.MONOLITHIC

    def test_absent(self, tmp_path: Path) -> None:
        result = detect_changelog_policy(tmp_path)
        assert result.strategy == ChangelogStrategy.ABSENT


class TestFileOwnership:
    def test_plan_create(self) -> None:
        plan = plan_create("new.txt", b"hello")
        assert plan.strategy == MergeStrategy.CREATE
        assert plan.content_hash is not None

    def test_plan_managed_block(self) -> None:
        plan = plan_managed_block("config.yaml", "my-block", b"key: value")
        assert plan.strategy == MergeStrategy.MANAGED_BLOCK


class TestManagedBlock:
    def test_insert_new_block(self) -> None:
        result = apply_managed_block("", "my-id", "content here")
        assert "BEGIN AGENTHARNESS-MANAGED: my-id" in result
        assert "content here" in result

    def test_replace_existing_block(self) -> None:
        existing = (
            "prefix\n# BEGIN AGENTHARNESS-MANAGED: x\nold\n"
            "# END AGENTHARNESS-MANAGED: x\nsuffix"
        )
        result = apply_managed_block(existing, "x", "new content")
        assert "old" not in result
        assert "new content" in result
        assert "prefix" in result
        assert "suffix" in result


class TestStructuredMerge:
    def test_adds_keys_to_empty(self) -> None:
        result = merge_json_keys("", {"key": "value"})
        import json
        assert json.loads(result)["key"] == "value"

    def test_preserves_unrelated_keys(self) -> None:
        existing = '{"a": 1, "b": 2}'
        result = merge_json_keys(existing, {"c": 3})
        import json
        data = json.loads(result)
        assert data["a"] == 1
        assert data["b"] == 2
        assert data["c"] == 3

    def test_updates_existing_key(self) -> None:
        existing = '{"a": 1}'
        result = merge_json_keys(existing, {"a": 99})
        import json
        assert json.loads(result)["a"] == 99


class TestAgentIntegration:
    def test_find_canonical_source(self, tmp_path: Path) -> None:
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("# Source\n")
        source = find_canonical_source(tmp_path)
        assert source == claude

    def test_missing_source_returns_none(self, tmp_path: Path) -> None:
        assert find_canonical_source(tmp_path) is None


class TestGeneratedIntegrations:
    def test_generated_clients_listed(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Agents\n")
        clients = list_generated_clients(tmp_path)
        assert any(c.name == "AGENTS.md" for c in clients)


class TestProfileOperations:
    def test_explain_profile_returns_rationale(self) -> None:
        from agentharness.policy.compiler import PolicyRequirement, compile_policy
        from agentharness.policy.results import GateKind
        from agentharness.policy.scope import PathExpression, ScopeExpression
        from agentharness.profile.operations import explain_profile

        req = PolicyRequirement(
            requirement_id="req.test",
            gate=GateKind.COMMIT,
            capability_id="cap.test",
            mode="strict",
            scope=ScopeExpression(includes=[PathExpression("src/**")]),
        )
        policy = compile_policy([req])
        explanations = explain_profile(policy)
        assert len(explanations) == 1
        assert explanations[0].requirement_id == "req.test"
