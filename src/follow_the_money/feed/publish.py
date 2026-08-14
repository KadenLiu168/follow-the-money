"""Auditable Feed publication (atomic, monotonic, serialized).

Design sections 2/4:

- Each validated run writes a create-only ``feeds/daily/YYYY-MM-DD/<run_id>.json``
  (date = cutoff in Asia/Shanghai) before atomically replacing
  ``feeds/latest.json``.
- Staging is an unpredictable sibling under the final parent on the same
  device; bytes are written create-only, flushed and file-``fsync``ed; the
  staging directory is ``fsync``ed.
- Dated artifacts commit with a platform atomic no-replace primitive; latest
  commits from a same-directory temp by atomic replace only after ownership
  validation; each rename is followed by parent-directory ``fsync``.
- Candidates must be the shared ``canonical_bytes()`` serialization of their
  validated Feed.
- Byte-identical reruns and runs whose semantic ``run_id``/``content_digest``
  match an existing valid dated artifact are idempotent no-ops: the first
  immutable dated bytes are retained and any ``latest.json`` repair or
  replacement uses those retained bytes. Same-path semantic mismatches and
  invalid existing artifacts fail closed.
"""

from __future__ import annotations

import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..canonical import canonical_bytes, canonical_sha256, load_canonical_json
from .validate import assert_feed_identity, validate_feed


class PublishError(ValueError):
    """Feed publication failed (typed at the orchestration boundary)."""


@dataclass
class PublishResult:
    dated_path: Path | None
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
    """Require ``data`` to be exactly the canonical serialization of its
    decoded Feed object (the only bytes Feed artifacts may publish)."""
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
    """Read the validated Feed ownership tuple from canonical JSON bytes."""
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


def atomic_no_replace_rename(src: Path, dst: Path) -> None:
    """Create-only rename: refuse to overwrite an existing target."""
    try:
        os.link(src, dst)  # atomic no-replace via hard link (POSIX)
        src.unlink()
    except FileExistsError as exc:
        raise PublishError(f"refusing to overwrite existing {dst}") from exc


def publish_feed(
    *,
    output_root: Path,
    cutoff: datetime,
    run_id: str,
    feed_bytes: bytes,
    latest_bytes: bytes,
    existing_latest_sha256: str | None = None,
    monotonic_now: Callable[[], float] | None = None,
    deadline_at: float | None = None,
) -> PublishResult:
    """Serialize dated (no-replace) then latest (atomic replace) publication.

    ``cutoff`` must be timezone-aware UTC; the dated path uses the cutoff date
    in Asia/Shanghai.

    Durability contract: a rename that has already committed is never rolled
    back. If the dated directory cannot be fsynced after its commit, the
    dated artifact is retained, ``latest`` is not updated, and the result is
    typed ``commit_durability_unknown``. A failure after latest replacement
    likewise retains both artifacts without making a false durability claim.
    """
    candidate_key = _ownership_key(feed_bytes, where="candidate Feed")
    latest_key = _ownership_key(latest_bytes, where="latest Feed")
    if candidate_key != latest_key or feed_bytes != latest_bytes:
        raise PublishError("candidate/latest Feed bytes have incompatible ownership")
    _assert_canonical_feed_bytes(feed_bytes, where="candidate Feed")
    _assert_canonical_feed_bytes(latest_bytes, where="latest Feed")

    digest = canonical_sha256(feed_bytes)
    monotonic = monotonic_now or time.monotonic
    asia = cutoff.astimezone(ZoneInfo("Asia/Shanghai"))
    date_dir = output_root / "daily" / asia.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    dated = date_dir / f"{run_id}.json"

    def latest_action(latest_path: Path, candidate_bytes: bytes) -> str:
        """Return replace, retain, or same for the serialized latest owner."""
        candidate_owner = _ownership_key(candidate_bytes, where="latest Feed")
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
        if current_key > candidate_owner:
            return "retain"
        if current_key == candidate_owner:
            if current_bytes != candidate_bytes:
                raise PublishError("incompatible equal ownership in latest.json")
            return "same"
        return "replace"

    def admit_commit() -> None:
        if deadline_at is not None and monotonic() >= deadline_at:
            raise PublishError("pre_commit_deadline_exceeded: commit admission refused")

    def recover_latest(retained: bytes) -> PublishResult:
        """Complete or repair latest from the retained immutable dated bytes.

        Used for both byte-identical reruns and semantic-identity idempotent
        reruns after a crash where the dated commit exists but latest is
        absent or owned by an older identity.
        """
        latest_path = output_root / "latest.json"
        latest_replaced = False
        durability_unknown = False
        action = latest_action(latest_path, retained)
        if action == "replace":
            recovery_stage = _stage_bytes(output_root, retained)
            try:
                _fsync_dir(output_root)
                admit_commit()
                os.replace(recovery_stage, latest_path)
                try:
                    _fsync_dir(output_root)
                except OSError:
                    durability_unknown = True
            finally:
                if recovery_stage.exists():
                    recovery_stage.unlink()
            latest_replaced = True
        return PublishResult(
            dated_path=dated,
            latest_replaced=latest_replaced,
            commit_durability_unknown=durability_unknown,
            idempotent=True,
        )

    def same_semantic_identity(existing: bytes) -> bool:
        """Whether the existing dated bytes are a valid canonical Feed with
        the candidate's semantic ``run_id``/``content_digest`` at the same
        cutoff. Invalid or mismatched existing content returns False (the
        caller fails closed); it never overwrites the immutable artifact."""
        try:
            feed = load_canonical_json(existing, where="existing dated Feed")
            if not isinstance(feed, dict):
                return False
            validate_feed(feed)
            assert_feed_identity(feed)
            if feed.get("run_id") != run_id:
                return False
            if feed.get("content_digest") != candidate_key[1]:
                return False
            existing_cutoff = datetime.fromisoformat(feed["evidence_cutoff_at"])
            if existing_cutoff.tzinfo is None:
                return False
            return existing_cutoff.astimezone(UTC) == candidate_key[0]
        except (TypeError, ValueError, KeyError):
            return False

    if dated.exists():
        existing = dated.read_bytes()
        if canonical_sha256(existing) == digest:
            # Same run ID + digest: idempotent. After a crash the dated commit
            # may exist while latest is absent/stale; complete latest without
            # re-publishing the dated artifact.
            return recover_latest(existing)
        if same_semantic_identity(existing):
            # Same semantic identity with different excluded audit bytes:
            # the first immutable dated artifact is the audit record for this
            # semantic run; retain it and use its bytes for latest repair.
            return recover_latest(existing)
        raise PublishError(f"existing dated path {dated} has incompatible content")

    # Stage both artifacts as unpredictable siblings.
    feed_stage: Path | None = None
    latest_stage: Path | None = None
    durability_unknown = False
    try:
        feed_stage = _stage_bytes(date_dir, feed_bytes)
        latest_stage = _stage_bytes(output_root, latest_bytes)
        _fsync_dir(date_dir)
        _fsync_dir(output_root)
        admit_commit()
        # Dated: atomic no-replace. After the rename commits, a parent fsync
        # failure is durability-unknown, never a rollback.
        atomic_no_replace_rename(feed_stage, dated)
        try:
            _fsync_dir(date_dir)
        except OSError:
            durability_unknown = True
            return PublishResult(
                dated_path=dated,
                latest_replaced=False,
                commit_durability_unknown=True,
            )
        # Latest: ownership validation then atomic replace.
        action = latest_action(output_root / "latest.json", latest_bytes)
        latest_replaced = False
        if action == "replace":
            os.replace(latest_stage, output_root / "latest.json")
            latest_replaced = True
            try:
                _fsync_dir(output_root)
            except OSError:
                durability_unknown = True
    except PublishError:
        for p in (feed_stage, latest_stage):
            if p is not None and p.exists():
                p.unlink()
        raise
    finally:
        for p in (feed_stage, latest_stage):
            if p is not None and p.exists():
                p.unlink()
    return PublishResult(
        dated_path=dated,
        latest_replaced=latest_replaced,
        commit_durability_unknown=durability_unknown,
        idempotent=action == "same",
    )
