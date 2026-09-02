"""Auditable latest Feed publication (atomic, monotonic, serialized)."""

from __future__ import annotations

import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..canonical import canonical_bytes, canonical_sha256, load_canonical_json
from .validate import assert_feed_identity, validate_feed


class PublishError(ValueError):
    """Feed publication failed (typed at the orchestration boundary)."""


@dataclass
class PublishResult:
    latest_replaced: bool
    commit_durability_unknown: bool = False
    idempotent: bool = False


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _same_device(a: Path, b: Path) -> bool:
    return os.stat(a).st_dev == os.stat(b).st_dev


def _stage_bytes(parent: Path, data: bytes) -> Path:
    """Write bytes to an unpredictable same-parent/same-device staging file."""
    if not parent.exists():
        raise PublishError(f"staging parent {parent} does not exist")
    tmp = parent / f".stage-{os.getpid()}-{secrets.token_hex(8)}"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        _fsync_file(tmp)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
    if not _same_device(tmp, parent):
        tmp.unlink()
        raise PublishError("staging file on a different device than parent")
    return tmp


def _assert_canonical_feed_bytes(data: bytes, *, where: str) -> None:
    """Require bytes to equal the shared canonical JSON serialization."""
    try:
        parsed = load_canonical_json(data, where=where)
        if not isinstance(parsed, dict):
            raise PublishError(f"{where}: Feed must be an object")
        if canonical_bytes(parsed) != data:
            raise PublishError(f"{where}: not canonical Feed bytes")
    except PublishError:
        raise
    except Exception as exc:
        raise PublishError(f"{where}: not canonical Feed bytes: {exc}") from exc


def _ownership_key(data: bytes, *, where: str) -> tuple[datetime, str]:
    """Read the Feed ownership tuple from canonical JSON bytes."""
    try:
        feed = load_canonical_json(data, where=where)
        if not isinstance(feed, dict):
            raise TypeError("Feed must be an object")
        cutoff_value = feed.get("evidence_cutoff_at")
        if not isinstance(cutoff_value, str):
            raise TypeError("evidence_cutoff_at is missing")
        cutoff = datetime.fromisoformat(cutoff_value)
        if cutoff.tzinfo is None:
            raise ValueError("evidence_cutoff_at must be timezone-aware")
        digest = feed.get("content_digest")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("content_digest must be a 64-character hexadecimal string")
        if any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("content_digest must be lowercase hexadecimal")
        return cutoff.astimezone(UTC), digest
    except Exception as exc:
        raise PublishError(f"{where} ownership key invalid: {exc}") from exc


def _semantic_identity(data: bytes) -> tuple[str, datetime, str] | None:
    parsed = load_canonical_json(data, where="Feed")
    if not isinstance(parsed, dict) or not isinstance(parsed.get("run_id"), str):
        return None
    cutoff, digest = _ownership_key(data, where="Feed")
    return parsed["run_id"], cutoff, digest


def atomic_no_replace_rename(src: Path, dst: Path) -> None:
    """Create-only rename: refuse to overwrite an existing target."""
    try:
        os.link(src, dst)
        src.unlink()
    except FileExistsError as exc:
        raise PublishError(f"refusing to overwrite existing {dst}") from exc


def publish_feed(
    *,
    output_root: Path,
    cutoff: datetime,
    run_id: str,
    feed_bytes: bytes,
    latest_bytes: bytes | None = None,
    existing_latest_sha256: str | None = None,
    monotonic_now: Callable[[], float] | None = None,
    deadline_at: float | None = None,
) -> PublishResult:
    """Atomically publish one canonical candidate as ``latest.json``.

    ``latest_bytes`` remains an optional compatibility alias for callers that
    already pass the candidate twice; it is never a second product.
    """
    if latest_bytes is not None and latest_bytes != feed_bytes:
        raise PublishError("candidate/latest Feed bytes have incompatible ownership")
    _assert_canonical_feed_bytes(feed_bytes, where="candidate Feed")
    candidate_key = _ownership_key(feed_bytes, where="candidate Feed")
    if cutoff.tzinfo is None:
        raise PublishError("cutoff must be timezone-aware")
    if candidate_key[0] != cutoff.astimezone(UTC):
        raise PublishError("candidate Feed cutoff does not match publication cutoff")
    candidate = load_canonical_json(feed_bytes, where="candidate Feed")
    if isinstance(candidate, dict) and "run_id" in candidate and candidate.get("run_id") != run_id:
        raise PublishError("candidate Feed run_id does not match publication run")

    monotonic = monotonic_now or time.monotonic
    latest_path = Path(output_root) / "latest.json"
    candidate_identity = _semantic_identity(feed_bytes)

    def admit_commit() -> None:
        if deadline_at is not None and monotonic() >= deadline_at:
            raise PublishError("pre_commit_deadline_exceeded: commit admission refused")

    def latest_action() -> str:
        if existing_latest_sha256 is not None:
            if not latest_path.exists():
                raise PublishError(
                    "latest.json absent but ownership was declared (ownership mismatch)"
                )
            if canonical_sha256(latest_path.read_bytes()) != existing_latest_sha256:
                raise PublishError("latest.json changed during publication (ownership mismatch)")
        if not latest_path.exists():
            return "replace"
        current_bytes = latest_path.read_bytes()
        current_key = _ownership_key(current_bytes, where="current latest Feed")
        _assert_canonical_feed_bytes(current_bytes, where="current latest Feed")
        if candidate_identity is not None:
            try:
                current = load_canonical_json(current_bytes, where="current latest Feed")
                validate_feed(current)
                assert_feed_identity(current)
            except Exception as exc:
                raise PublishError(f"current latest Feed is invalid: {exc}") from exc
        if current_key > candidate_key:
            return "retain"
        if current_key == candidate_key:
            current_identity = _semantic_identity(current_bytes)
            if (
                candidate_identity is not None
                and current_identity is not None
                and current_identity == candidate_identity
            ):
                return "idempotent"
            if current_bytes != feed_bytes:
                raise PublishError("incompatible equal ownership in latest.json")
            return "idempotent"
        return "replace"

    action = latest_action()
    if action == "retain":
        return PublishResult(latest_replaced=False)
    if action == "idempotent":
        return PublishResult(latest_replaced=False, idempotent=True)

    stage = _stage_bytes(Path(output_root), feed_bytes)
    try:
        _fsync_dir(Path(output_root))
        admit_commit()
        # Re-check ownership immediately before the non-cancellable replace.
        action = latest_action()
        if action == "retain":
            return PublishResult(latest_replaced=False)
        if action == "idempotent":
            return PublishResult(latest_replaced=False, idempotent=True)
        os.replace(stage, latest_path)
        try:
            _fsync_dir(Path(output_root))
        except OSError:
            return PublishResult(
                latest_replaced=True,
                commit_durability_unknown=True,
            )
        return PublishResult(latest_replaced=True)
    finally:
        if stage.exists():
            stage.unlink()
