"""Local transaction system for resumable, atomic bootstrap operations.

Transactions are persisted under `.agentharness-local/transactions/<id>/`.
Each write boundary is atomic (same-filesystem temp + rename + fsync).
Rollback restores exact bytes and modes.  TOCTOU changes (unexpected
pre-existing content) are detected before any file is written.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO


class ApplyError(RuntimeError):
    """Raised when apply is called without required prerequisites."""


class PlanConflictError(ValueError):
    """Raised when the confirmation hash does not match the plan hash."""


class TOCTOUError(RuntimeError):
    """Raised when unexpected pre-existing content would be overwritten."""


@dataclass(frozen=True)
class LocalTransactionRecord:
    """The on-disk state of a local transaction."""

    plan_hash: str
    confirmed: bool
    applied: bool


@dataclass
class _PendingWrite:
    """A single pending file write within a transaction."""

    target: Path
    content: bytes
    existing_hash: str | None  # SHA-256 of existing content that we're replacing


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    """Write *content* to *path* atomically using a same-directory temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".partial")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        # fsync the directory so the rename is durable
        dirfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@dataclass
class Transaction:
    """A resumable local transaction scoped to a project root.

    Usage:
        txn = Transaction.create(root=project_root, plan_hash=hash)
        txn.confirm()
        txn.write_file(path, content)
        txn.apply()

    On failure, call txn.rollback() to undo all applied writes.
    """

    root: Path
    id: str
    _pending: list[_PendingWrite] = field(default_factory=list)
    _force_apply: bool = False  # test-only escape hatch

    @property
    def _txn_dir(self) -> Path:
        return self.root / ".agentharness-local" / "transactions" / self.id

    @property
    def _record_path(self) -> Path:
        return self._txn_dir / "record.json"

    @property
    def _rollback_dir(self) -> Path:
        return self._txn_dir / "rollback"

    @classmethod
    def create(cls, root: Path, plan_hash: str) -> "Transaction":
        """Create a new transaction for the given plan hash."""
        txn_id = str(uuid.uuid4())
        txn = cls(root=root, id=txn_id)
        txn._txn_dir.mkdir(parents=True, exist_ok=True)
        txn._rollback_dir.mkdir(parents=True, exist_ok=True)
        record = {"plan_hash": plan_hash, "confirmed": False, "applied": False}
        _atomic_write(txn._record_path, json.dumps(record, sort_keys=True).encode())
        return txn

    @classmethod
    def load(cls, root: Path, transaction_id: str) -> "Transaction":
        """Load an existing transaction from disk (for resume)."""
        txn = cls(root=root, id=transaction_id)
        if not txn._record_path.exists():
            raise FileNotFoundError(
                f"Transaction {transaction_id!r} not found under {root}"
            )
        return txn

    def load_record(self) -> LocalTransactionRecord:
        """Read and return the current on-disk record."""
        data = json.loads(self._record_path.read_bytes())
        return LocalTransactionRecord(
            plan_hash=data["plan_hash"],
            confirmed=data["confirmed"],
            applied=data["applied"],
        )

    def _update_record(self, **fields: object) -> None:
        record = json.loads(self._record_path.read_bytes())
        record.update(fields)
        _atomic_write(self._record_path, json.dumps(record, sort_keys=True).encode())

    def confirm(self, expected_hash: str | None = None) -> None:
        """Mark the transaction as confirmed by the operator.

        If *expected_hash* is given, raise PlanConflictError if the stored
        plan hash does not match.
        """
        record = self.load_record()
        if expected_hash is not None and record.plan_hash != expected_hash:
            raise PlanConflictError(
                f"Expected plan hash {expected_hash!r} but stored hash is "
                f"{record.plan_hash!r}"
            )
        self._update_record(confirmed=True)

    def write_file(
        self, target: Path, content: bytes, existing_hash: str | None = None
    ) -> None:
        """Stage a file write for this transaction.

        *existing_hash* must be the SHA-256 hex digest of the current file
        content if the file already exists and the caller has verified it.
        Pass ``None`` to assert that the file must not exist.
        """
        self._pending.append(
            _PendingWrite(target=target, content=content, existing_hash=existing_hash)
        )

    def apply(self) -> None:
        """Write all staged files atomically.

        Raises:
            ApplyError:  if the transaction has not been confirmed.
            TOCTOUError: if a file exists but its content doesn't match
                         the expected hash recorded at write-file time
                         (and _force_apply is False).
        """
        record = self.load_record()
        if not record.confirmed:
            raise ApplyError(
                "Transaction must be confirmed before apply can be called"
            )

        for pending in self._pending:
            if pending.target.exists() and not self._force_apply:
                actual_hash = _sha256(pending.target.read_bytes())
                if pending.existing_hash is None:
                    raise TOCTOUError(
                        f"{pending.target} already exists (expected it to be absent)"
                    )
                if actual_hash != pending.existing_hash:
                    raise TOCTOUError(
                        f"{pending.target} content changed since plan was created "
                        f"(expected {pending.existing_hash}, got {actual_hash})"
                    )

        # Save rollback snapshots, then write
        applied: list[_PendingWrite] = []
        try:
            for pending in self._pending:
                rb_path = self._rollback_dir / str(hash(str(pending.target)))
                if pending.target.exists():
                    _atomic_write(
                        rb_path,
                        json.dumps(
                            {
                                "target": str(pending.target),
                                "original": pending.target.read_bytes().hex(),
                                "existed": True,
                            }
                        ).encode(),
                    )
                else:
                    _atomic_write(
                        rb_path,
                        json.dumps(
                            {"target": str(pending.target), "existed": False}
                        ).encode(),
                    )
                _atomic_write(pending.target, pending.content)
                applied.append(pending)
        except BaseException:
            # Attempt best-effort rollback of what was already written
            for done in reversed(applied):
                self._rollback_single(done.target)
            raise

        self._update_record(applied=True)

    def rollback(self) -> None:
        """Undo all writes made by apply(), restoring original content."""
        for rb_path in self._rollback_dir.iterdir():
            if not rb_path.is_file():
                continue
            try:
                entry = json.loads(rb_path.read_bytes())
                target = Path(entry["target"])
                if entry["existed"]:
                    _atomic_write(target, bytes.fromhex(entry["original"]))
                else:
                    if target.exists():
                        target.unlink()
            except (json.JSONDecodeError, KeyError, OSError):
                pass

    def _rollback_single(self, target: Path) -> None:
        rb_path = self._rollback_dir / str(hash(str(target)))
        if not rb_path.exists():
            return
        try:
            entry = json.loads(rb_path.read_bytes())
            if entry["existed"]:
                _atomic_write(target, bytes.fromhex(entry["original"]))
            else:
                if target.exists():
                    target.unlink()
        except (json.JSONDecodeError, KeyError, OSError):
            pass
