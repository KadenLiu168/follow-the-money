"""Durable publication of the manifest-led Feed bundle."""

from __future__ import annotations

import os
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..canonical import canonical_bytes, canonical_sha256, load_canonical_json
from ..schema import SchemaError
from .bundle import (
    MANIFEST_FILENAME,
    PREVIOUS_BUNDLE_MAJOR,
    BundleError,
    FeedBundle,
    artifact_relative_path,
    validate_bundle,
)
from .validate import assert_feed_identity, validate_feed


class PublishError(ValueError):
    """Feed publication failed (typed at the orchestration boundary)."""


@dataclass
class PublishResult:
    commit_durability_unknown: bool = False
    idempotent: bool = False
    manifest_replaced: bool = False
    retained: bool = False
    cleanup_failed: bool = False
    superseded_paths: tuple[str, ...] = ()


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
    if not parent.is_dir():
        raise PublishError(f"staging parent {parent} does not exist")
    tmp = parent / f".stage-{os.getpid()}-{secrets.token_hex(8)}"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view) :]
        finally:
            os.close(fd)
        _fsync_file(tmp)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    if not _same_device(tmp, parent):
        tmp.unlink()
        raise PublishError("staging file on a different device than parent")
    return tmp


def atomic_no_replace_rename(src: Path, dst: Path) -> None:
    """Create-only rename: refuse to overwrite an existing target."""
    try:
        os.link(src, dst)
        src.unlink()
    except FileExistsError as exc:
        raise PublishError(f"refusing to overwrite existing {dst}") from exc


def _bundle_key(bundle: FeedBundle) -> tuple[datetime, str]:
    try:
        cutoff = datetime.fromisoformat(bundle.cutoff)
    except ValueError as exc:
        raise PublishError("candidate manifest cutoff is invalid") from exc
    if cutoff.tzinfo is None:
        raise PublishError("candidate manifest cutoff must be timezone-aware")
    return cutoff.astimezone(UTC), bundle.content_digest


def _read_current_bundle(
    root: Path, *, allow_previous: bool = False
) -> tuple[FeedBundle | None, tuple[datetime, str] | None]:
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None, None
    try:
        validate_bundle(root, allow_previous=allow_previous)
    except (BundleError, OSError, TypeError, ValueError) as exc:
        raise PublishError(f"current Feed bundle is invalid: {exc}") from exc
    # Read the exact current physical inventory after validation. This lets
    # idempotence compare integrity rather than execution-audit timestamps.
    try:
        manifest = load_canonical_json(manifest_path.read_bytes(), where="current Feed manifest")
    except Exception as exc:
        raise PublishError(f"current Feed manifest is invalid: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PublishError("current Feed manifest is not an object")
    try:
        artifacts: dict[str, dict[str, object]] = {}
        artifact_bytes: dict[str, bytes] = {}
        for entry in manifest["artifacts"]:
            domain = entry["domain"]
            data = (root / entry["path"]).read_bytes()
            artifacts[domain] = load_canonical_json(data, where=f"current Feed artifact {domain}")
            artifact_bytes[domain] = data
        current = FeedBundle(
            manifest=manifest,
            artifacts=artifacts,
            manifest_bytes=manifest_path.read_bytes(),
            artifact_bytes=artifact_bytes,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise PublishError(f"current Feed bundle cannot be represented: {exc}") from exc
    return current, _bundle_key(current)


def _inventory_signature(bundle: FeedBundle) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            entry["domain"],
            entry["path"],
            entry["item_count"],
            entry["size_bytes"],
            entry["sha256"],
        )
        for entry in bundle.manifest["artifacts"]
    )


def _manifest_signature(bundle: FeedBundle) -> tuple[Any, ...]:
    return (
        bundle.run_id,
        bundle.content_digest,
        bundle.cutoff,
        _inventory_signature(bundle),
        canonical_bytes(bundle.manifest["bundle_schemas"]),
    )


def _candidate_action(
    root: Path, candidate: FeedBundle, *, allow_previous_current: bool = False
) -> tuple[str, FeedBundle | None]:
    current, current_key = _read_current_bundle(root, allow_previous=allow_previous_current)
    candidate_key = _bundle_key(candidate)
    if current is None:
        return "replace", None
    if current.manifest.get("schema_version") == PREVIOUS_BUNDLE_MAJOR:
        if not allow_previous_current:
            raise PublishError("previous Feed bundle requires bounded migration")
        return "replace", current
    assert current_key is not None
    if current_key > candidate_key:
        return "retain", current
    if current_key == candidate_key:
        if _manifest_signature(current) == _manifest_signature(candidate):
            return "idempotent", current
        raise PublishError("incompatible equal ownership in feed-manifest.json")
    return "replace", current


def _admit(deadline_at: float | None, monotonic: Callable[[], float]) -> None:
    if deadline_at is not None and monotonic() >= deadline_at:
        raise PublishError("pre_commit_deadline_exceeded: commit admission refused")


def _install_artifact(root: Path, domain: str, data: bytes) -> bool:
    target = root / artifact_relative_path(domain, load_canonical_json(data)["run_id"])
    if target.exists():
        try:
            if target.read_bytes() == data:
                return False
        except OSError as exc:
            raise PublishError(f"cannot inspect existing Feed artifact {target.name}") from exc
        raise PublishError(f"existing Feed artifact {target.name} has different bytes")
    stage = _stage_bytes(root, data)
    try:
        atomic_no_replace_rename(stage, target)
        return True
    finally:
        if stage.exists():
            stage.unlink()


def _cleanup_created(root: Path, paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
    try:
        _fsync_dir(root)
    except OSError:
        pass


def _cleanup_artifacts(root: Path, active: set[str]) -> tuple[bool, tuple[str, ...]]:
    failed = False
    deleted: list[str] = []
    for path in root.iterdir():
        if not path.is_file() or not re.fullmatch(
            r"feed-(?:[a-z_]+)-[0-9a-f]{32}\.json", path.name
        ):
            continue
        if path.name in active:
            continue
        try:
            path.unlink()
            deleted.append(path.name)
        except OSError:
            failed = True
    if not failed:
        try:
            _fsync_dir(root)
        except OSError:
            failed = True
    return failed, tuple(deleted)


def publish_bundle(
    *,
    output_root: Path,
    bundle: FeedBundle,
    cutoff: datetime,
    run_id: str,
    existing_manifest_sha256: str | None = None,
    monotonic_now: Callable[[], float] | None = None,
    deadline_at: float | None = None,
    allow_previous_current: bool = False,
) -> PublishResult:
    """Install immutable typed artifacts, then atomically activate the manifest."""
    root = Path(output_root)
    if not root.is_dir():
        raise PublishError(f"Feed product root does not exist: {root}")
    if cutoff.tzinfo is None:
        raise PublishError("cutoff must be timezone-aware")
    try:
        candidate_cutoff = datetime.fromisoformat(bundle.cutoff)
    except ValueError as exc:
        raise PublishError("candidate manifest cutoff is invalid") from exc
    if candidate_cutoff.tzinfo is None or candidate_cutoff.astimezone(UTC) != cutoff.astimezone(
        UTC
    ):
        raise PublishError("candidate manifest cutoff does not match publication cutoff")
    if bundle.run_id != run_id:
        raise PublishError("candidate manifest run_id does not match publication run")
    if bundle.manifest.get("pipeline", {}).get("status") not in {"healthy", "degraded"}:
        raise PublishError("candidate Feed pipeline status is not publishable")
    try:
        validate_bundle(root, manifest=bundle.manifest, manifest_bytes=bundle.manifest_bytes)
    except (BundleError, OSError, TypeError, ValueError) as exc:
        # Candidate files are not active yet; validate the logical candidate
        # directly when its final files have not been installed.
        from .bundle import reconstruct_feed

        try:
            from .dedupe import item_total_order_key

            candidate_items = sorted(
                (item for artifact in bundle.artifacts.values() for item in artifact["items"]),
                key=item_total_order_key,
            )
            candidate_feed = reconstruct_feed(bundle.manifest, candidate_items)
            validate_feed(candidate_feed)
            assert_feed_identity(candidate_feed)
        except (BundleError, OSError, SchemaError, TypeError, ValueError) as inner:
            raise PublishError(f"candidate Feed bundle is invalid: {inner}") from exc

    monotonic = monotonic_now or time.monotonic

    def assert_manifest_ownership() -> None:
        if existing_manifest_sha256 is None:
            return
        manifest_path = root / MANIFEST_FILENAME
        if (
            not manifest_path.exists()
            or canonical_sha256(manifest_path.read_bytes()) != existing_manifest_sha256
        ):
            raise PublishError("feed-manifest.json changed during publication (ownership mismatch)")

    assert_manifest_ownership()
    action, _current = _candidate_action(
        root, bundle, allow_previous_current=allow_previous_current
    )
    if action == "retain":
        return PublishResult(retained=True)
    if action == "idempotent":
        return PublishResult(idempotent=True)

    created: list[Path] = []
    try:
        for domain in bundle.artifacts:
            if _install_artifact(root, domain, bundle.artifact_bytes[domain]):
                created.append(root / artifact_relative_path(domain, bundle.run_id))
        _fsync_dir(root)
        # Validate the candidate against the installed final artifact paths;
        # this catches path/inventory races before the activation point.
        validate_bundle(root, manifest=bundle.manifest, manifest_bytes=bundle.manifest_bytes)
        manifest_stage = _stage_bytes(root, bundle.manifest_bytes)
        try:
            _admit(deadline_at, monotonic)
            assert_manifest_ownership()
            candidate_action, _current = _candidate_action(
                root, bundle, allow_previous_current=allow_previous_current
            )
            if candidate_action == "retain":
                _cleanup_created(root, created)
                return PublishResult(retained=True)
            if candidate_action == "idempotent":
                _cleanup_created(root, created)
                return PublishResult(idempotent=True)
            os.replace(manifest_stage, root / MANIFEST_FILENAME)
            try:
                _fsync_dir(root)
            except OSError:
                return PublishResult(
                    manifest_replaced=True,
                    commit_durability_unknown=True,
                )
        finally:
            if manifest_stage.exists():
                manifest_stage.unlink()
    except PublishError:
        _cleanup_created(root, created)
        raise
    except (OSError, ValueError) as exc:
        _cleanup_created(root, created)
        raise PublishError(str(exc)) from exc

    active = {entry["path"] for entry in bundle.manifest["artifacts"]}
    cleanup_failed, superseded_paths = _cleanup_artifacts(root, active)
    return PublishResult(
        manifest_replaced=True,
        cleanup_failed=cleanup_failed,
        superseded_paths=superseded_paths,
    )


# Explicit name for callers that use the product noun rather than operation.
publish_feed_bundle = publish_bundle
