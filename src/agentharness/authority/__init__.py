"""Scoped authority contract — declarative, expiring, revocable operation grants."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AuthorityError(ValueError):
    """A stable, operator-safe authority validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class Operation(StrEnum):
    """Valid operations that can be granted."""

    COMMIT = "commit"
    PUSH = "push"
    PR_CREATE = "pr-create"
    PR_MERGE = "pr-merge"
    ISSUE_CREATE = "issue-create"
    FS_WRITE_OUTSIDE_REPO = "fs-write-outside-repo"
    EXTERNAL_MESSAGE = "external-message"
    DESTRUCTIVE_FS = "destructive-fs"


@dataclass(frozen=True, slots=True)
class Grant:
    """A single grant of operations with optional target and expiry."""

    operations: tuple[Operation, ...]
    target: str | None = None
    expires: str | None = None
    granted_by: str | None = None


@dataclass(frozen=True, slots=True)
class Contract:
    """The effective authority contract: grants and revocations."""

    schema_version: int
    grants: tuple[Grant, ...]
    revoked: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Decision:
    """The result of an authority decision: allow or refuse."""

    allowed: bool
    reason: str | None = None
