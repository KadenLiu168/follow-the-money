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
- Same run ID + digest is an idempotent no-op; an existing path with
  incompatible content fails.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..canonical import canonical_sha256


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
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    if not _same_device(tmp, parent):
        tmp.unlink()
        raise PublishError("staging file on a different device than parent")
    return tmp


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
    digest = canonical_sha256(feed_bytes)
    asia = cutoff.astimezone(ZoneInfo("Asia/Shanghai"))
    date_dir = output_root / "daily" / asia.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    dated = date_dir / f"{run_id}.json"

    if dated.exists():
        existing = dated.read_bytes()
        if canonical_sha256(existing) == digest:
            # Same run ID + digest: idempotent. After a crash the dated commit
            # may exist while latest is absent/stale; complete latest without
            # re-publishing the dated artifact.
            latest_path = output_root / "latest.json"
            latest_replaced = False
            if not latest_path.exists() or canonical_sha256(latest_path.read_bytes()) != digest:
                if (
                    latest_path.exists()
                    and existing_latest_sha256 is not None
                    and canonical_sha256(latest_path.read_bytes()) != existing_latest_sha256
                ):
                    raise PublishError("latest.json changed during recovery (ownership mismatch)")
                latest_stage = _stage_bytes(output_root, latest_bytes)
                try:
                    os.replace(latest_stage, latest_path)
                    try:
                        _fsync_dir(output_root)
                    except OSError:
                        pass  # durability unknown handled by caller contract
                finally:
                    if latest_stage.exists():
                        latest_stage.unlink()
                latest_replaced = True
            return PublishResult(dated_path=dated, latest_replaced=latest_replaced, idempotent=True)
        raise PublishError(f"existing dated path {dated} has incompatible content")

    # Stage both artifacts as unpredictable siblings.
    feed_stage = _stage_bytes(date_dir, feed_bytes)
    latest_stage = _stage_bytes(output_root, latest_bytes)
    durability_unknown = False
    try:
        _fsync_dir(date_dir)
        _fsync_dir(output_root)
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
        if existing_latest_sha256 is not None:
            latest_path = output_root / "latest.json"
            if latest_path.exists():
                current = canonical_sha256(latest_path.read_bytes())
                if current != existing_latest_sha256:
                    # Stale externally prepared candidate: do not replace.
                    raise PublishError(
                        "latest.json changed during publication (ownership mismatch)"
                    )
            else:
                raise PublishError(
                    "latest.json absent but ownership was declared (ownership mismatch)"
                )
        os.replace(latest_stage, output_root / "latest.json")
        try:
            _fsync_dir(output_root)
        except OSError:
            durability_unknown = True
    except PublishError:
        for p in (feed_stage, latest_stage):
            if p.exists():
                p.unlink()
        raise
    finally:
        for p in (feed_stage, latest_stage):
            if p.exists():
                p.unlink()
    return PublishResult(
        dated_path=dated, latest_replaced=True, commit_durability_unknown=durability_unknown
    )
