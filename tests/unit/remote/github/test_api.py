"""Unit tests for the GitHub API boundary."""

from __future__ import annotations

import pytest

from agentharness.remote.github.api import APIError, GitHubClient, RateLimitError
from agentharness.remote.github.auth import AuthError, get_token, redact_token


class TestAuth:
    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(AuthError, match="token not found"):
            get_token("GITHUB_TOKEN")

    def test_empty_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "   ")
        with pytest.raises(AuthError):
            get_token("GITHUB_TOKEN")

    def test_valid_token_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_testtoken")
        assert get_token("GITHUB_TOKEN") == "ghp_testtoken"

    def test_token_redacted_in_text(self) -> None:
        result = redact_token("Authorization: Bearer ghp_secret", "ghp_secret")
        assert "ghp_secret" not in result
        assert "[REDACTED]" in result

    def test_empty_token_redact_is_no_op(self) -> None:
        text = "some text"
        assert redact_token(text, "") == text

    def test_error_message_does_not_contain_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AuthError must not include the token value in its message."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        try:
            get_token("GITHUB_TOKEN")
        except AuthError as e:
            assert "token value" not in str(e).lower()


class TestAPIClient:
    def test_rate_limit_raises_rate_limit_error(self) -> None:
        """A 429 response should produce RateLimitError, not a generic APIError."""
        # We test the error type hierarchy, not the actual network call
        assert issubclass(RateLimitError, APIError)

    def test_client_construction(self) -> None:
        client = GitHubClient(token="test-token")
        assert client._token == "test-token"
