"""Private repository-native deployment boundary for the scheduled Feed."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..canonical import load_canonical_json
from ..config.model import AppConfig, RatePolicy
from ..providers.lock import LOCK_FILENAME
from ..providers.rate import (
    PERSISTENCE_MARKER,
    REGISTRY_FILENAME,
    RateRegistry,
    RateStateError,
    _atomic_write,
)
from ..schema import SchemaError
from .bundle import (
    DOMAINS,
    LEGACY_FILENAME,
    MANIFEST_FILENAME,
    BundleError,
    artifact_relative_path,
    build_bundle,
    load_feed,
    validate_bundle,
)
from .checkpoint import (
    CHECKPOINT_FILENAME,
    FeedCheckpoint,
    PreviousSuccess,
    read_checkpoint,
    write_checkpoint,
)
from .publish import publish_bundle
from .validate import assert_feed_identity, validate_feed

LEASE_FILENAME = "feed-run-lease.json"
LEASE_VERSION = "1"
LEASE_STATES = frozenset({"bootstrap", "in_progress", "success", "failure"})
LEASE_FIELDS = frozenset(
    {
        "version",
        "deployment_run_id",
        "state",
        "armed_at",
        "finished_at",
        "feed_start_not_after",
        "recovery_not_before",
    }
)
_RUNTIME_DURABLE_NAMES = frozenset(
    {PERSISTENCE_MARKER, REGISTRY_FILENAME, LEASE_FILENAME, CHECKPOINT_FILENAME}
)
_RUNTIME_TRANSIENT_NAMES = frozenset({LOCK_FILENAME, "feed-status.json", ".feed-exit-code"})
_LAYOUT_EMPTY = "empty"
_LAYOUT_NEW = "new"
_LAYOUT_LEGACY = "legacy"

_DIAGNOSTIC_FIELD_LIMIT = 256
_DIAGNOSTIC_REPORT_LIMIT = 4096
_DIAGNOSTIC_UNAVAILABLE = "Feed failure diagnostics unavailable"
_DIAGNOSTIC_PROVIDER_FIELDS = (
    "provider_id",
    "state",
    "availability",
    "availability_reason",
    "upstream_http_status",
    "affected_coverage_groups",
    "error",
    "attempted",
    "fetched",
    "accepted",
    "rejected",
)
_DIAGNOSTIC_COUNTER_FIELDS = frozenset({"attempted", "fetched", "accepted", "rejected"})
_MARKDOWN_SPECIAL = frozenset("\\`*_{}[]()#+-.!|<>~")


class DeploymentError(ValueError):
    """Hosted deployment state failed closed."""


@dataclass(frozen=True)
class DeploymentLease:
    version: str
    deployment_run_id: str
    state: str
    armed_at: datetime
    finished_at: datetime | None
    feed_start_not_after: datetime | None
    recovery_not_before: datetime


@dataclass(frozen=True)
class DeploymentPreparation:
    mode: str
    lease: DeploymentLease
    paths: tuple[Path, ...]


GitRunner = Callable[[list[str]], str]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DeploymentError("deployment clock must be timezone-aware")
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    return (
        None
        if value is None
        else _utc(value).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _parse_time(value: object, field: str, *, required: bool) -> datetime | None:
    if value is None:
        if required:
            raise DeploymentError(f"lease {field} is required")
        return None
    if not isinstance(value, str):
        raise DeploymentError(f"lease {field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DeploymentError(f"lease {field} must be an ISO-8601 UTC timestamp") from exc
    return _utc(parsed)


def read_lease(path: Path, *, expected_run_id: str | None = None) -> DeploymentLease:
    try:
        raw = json.loads(Path(path).read_bytes())
    except (OSError, ValueError) as exc:
        raise DeploymentError(f"cannot read lease: {path}") from exc
    if not isinstance(raw, dict):
        raise DeploymentError("lease must be a JSON object")
    unknown = set(raw) - LEASE_FIELDS
    missing = LEASE_FIELDS - set(raw)
    if unknown:
        raise DeploymentError(f"unknown lease fields: {sorted(unknown)}")
    if missing:
        raise DeploymentError(f"missing lease fields: {sorted(missing)}")
    if raw["version"] != LEASE_VERSION:
        raise DeploymentError(f"unknown lease version: {raw['version']!r}")
    run_id = raw["deployment_run_id"]
    state = raw["state"]
    if not isinstance(run_id, str) or not run_id.strip():
        raise DeploymentError("lease deployment_run_id must be non-empty")
    if not isinstance(state, str) or state not in LEASE_STATES:
        raise DeploymentError(f"unknown lease state: {state!r}")
    if expected_run_id is not None and run_id != expected_run_id:
        raise DeploymentError("lease deployment_run_id does not match this run")

    armed_at = _parse_time(raw["armed_at"], "armed_at", required=True)
    finished_at = _parse_time(
        raw["finished_at"], "finished_at", required=state in {"success", "failure"}
    )
    feed_start = _parse_time(
        raw["feed_start_not_after"],
        "feed_start_not_after",
        required=state in {"in_progress", "success", "failure"},
    )
    recovery = _parse_time(raw["recovery_not_before"], "recovery_not_before", required=True)
    assert armed_at is not None and recovery is not None
    if state == "bootstrap" and (finished_at is not None or feed_start is not None):
        raise DeploymentError("bootstrap lease has terminal or armed fields")
    if state == "in_progress" and finished_at is not None:
        raise DeploymentError("in_progress lease has finished_at")
    if feed_start is not None and feed_start < armed_at:
        raise DeploymentError("lease feed_start_not_after precedes armed_at")
    if recovery < armed_at or (feed_start is not None and recovery < feed_start):
        raise DeploymentError("lease recovery_not_before is inconsistent")
    if finished_at is not None and finished_at < armed_at:
        raise DeploymentError("lease finished_at precedes armed_at")
    return DeploymentLease(
        version=LEASE_VERSION,
        deployment_run_id=run_id,
        state=state,
        armed_at=armed_at,
        finished_at=finished_at,
        feed_start_not_after=feed_start,
        recovery_not_before=recovery,
    )


def write_lease(path: Path, lease: DeploymentLease) -> None:
    read_lease_bytes = {
        "version": lease.version,
        "deployment_run_id": lease.deployment_run_id,
        "state": lease.state,
        "armed_at": _iso(lease.armed_at),
        "finished_at": _iso(lease.finished_at),
        "feed_start_not_after": _iso(lease.feed_start_not_after),
        "recovery_not_before": _iso(lease.recovery_not_before),
    }
    if lease.version != LEASE_VERSION or lease.state not in LEASE_STATES:
        raise DeploymentError("cannot write unsupported lease")
    _atomic_write(
        Path(path),
        json.dumps(read_lease_bytes, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )


def _scope_policies(config: AppConfig) -> dict[str, RatePolicy]:
    policies: dict[str, RatePolicy] = {}
    for provider in config.providers:
        policy = provider.rate_policy
        if not provider.enabled or policy is None or policy.unlimited:
            continue
        previous = policies.get(policy.scope_id)
        if previous is not None and previous != policy:
            raise DeploymentError(f"rate scope {policy.scope_id!r} has inconsistent policies")
        policies[policy.scope_id] = policy
    return policies


def _validate_deployment_compatibility(config: AppConfig) -> None:
    if config.rate_registry.version != LEASE_VERSION:
        raise DeploymentError("unsupported RateRegistry version for hosted deployment")
    if config.rate_registry.schema_file != REGISTRY_FILENAME:
        raise DeploymentError("hosted deployment requires the authoritative RateRegistry file")
    if config.feed.pre_commit_deadline_seconds <= 0:
        raise DeploymentError("pre_commit_deadline_seconds must be positive")


def _cooldown_seconds(config: AppConfig) -> int:
    hours = config.rate_registry.crash_cooldown_hours
    if not isinstance(hours, int) or hours <= 0:
        raise DeploymentError("crash_cooldown_hours must be positive")
    return hours * 3600


def _validate_recovery_envelope(config: AppConfig, policies: Iterable[RatePolicy]) -> int:
    cooldown = _cooldown_seconds(config)
    for policy in policies:
        if policy.refill_period_seconds > cooldown or policy.minimum_interval_seconds > cooldown:
            raise DeploymentError(f"rate scope {policy.scope_id!r} exceeds recovery envelope")
    return cooldown


def _validate_existing_state(
    root: Path, config: AppConfig, policies: dict[str, RatePolicy]
) -> RateRegistry:
    marker = root / PERSISTENCE_MARKER
    registry = RateRegistry(root)
    if not marker.is_file() or not registry.registry_path.is_file():
        raise DeploymentError("established deployment state is missing marker or registry")
    try:
        registry_payload = load_canonical_json(
            registry.registry_path.read_bytes(), where=str(registry.registry_path)
        )
        if not isinstance(registry_payload, dict) or registry_payload.get("root_identity") != str(
            root.resolve()
        ):
            raise DeploymentError("rate registry root_identity is inconsistent")
        scope_ids = registry.registered_scope_ids()
        expected_scope_names = {registry.scope_path(scope_id).name for scope_id in scope_ids}
        actual_scope_names = {path.name for path in root.glob("scope-*.json")}
        if actual_scope_names != expected_scope_names:
            raise DeploymentError("rate scope files are missing/partial or orphaned")
        for scope_id in scope_ids:
            state = registry.read_active_scope(scope_id)
            policy = policies.get(scope_id)
            if policy is not None and (
                state.capacity != str(policy.capacity)
                or state.refill_period_seconds != policy.refill_period_seconds
                or state.minimum_interval_seconds != policy.minimum_interval_seconds
            ):
                raise DeploymentError(f"rate scope {scope_id!r} policy is incompatible")
    except DeploymentError:
        raise
    except RateStateError as exc:
        raise DeploymentError(str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise DeploymentError("rate registry is invalid") from exc
    return registry


def _runtime_entries(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        return ()
    if not root.is_dir():
        raise DeploymentError(f"runtime state root is not a directory: {root}")
    try:
        return tuple(sorted(root.iterdir(), key=lambda path: path.name))
    except OSError as exc:
        raise DeploymentError(f"cannot inspect runtime state root {root}: {exc}") from exc


def _is_transient_runtime_path(path: Path) -> bool:
    name = path.name
    return (
        name in _RUNTIME_TRANSIENT_NAMES
        or name.startswith(".stage-")
        or ".tmp-" in name
        or name.endswith(".tmp")
    )


def _assert_no_unknown_runtime_entries(root: Path, expected: set[str]) -> None:
    unexpected = [
        path.name
        for path in _runtime_entries(root)
        if path.name not in expected and not _is_transient_runtime_path(path)
    ]
    if unexpected:
        raise DeploymentError(f"unsupported runtime state paths: {sorted(unexpected)}")


def _assert_no_partial_bundle(product_root: Path) -> None:
    root = Path(product_root)
    if not root.exists() or (root / MANIFEST_FILENAME).exists():
        return
    try:
        partial = [
            path.name
            for path in root.iterdir()
            if path.is_file() and re.fullmatch(r"feed-(?:[a-z_]+)-[0-9a-f]{32}\.json", path.name)
        ]
    except OSError as exc:
        raise DeploymentError(f"cannot inspect Feed product root {root}") from exc
    if partial:
        raise DeploymentError("partial Feed bundle has artifacts without feed-manifest.json")


def _validate_new_layout(
    runtime_root: Path,
    config: AppConfig,
    policies: dict[str, RatePolicy],
    *,
    product_root: Path | None = None,
) -> tuple[RateRegistry, DeploymentLease]:
    runtime_root = Path(runtime_root)
    required = set(_RUNTIME_DURABLE_NAMES)
    expected = required | {path.name for path in runtime_root.glob("scope-*.json")}
    _assert_no_unknown_runtime_entries(runtime_root, expected)
    missing = sorted(name for name in required if not (runtime_root / name).is_file())
    if missing:
        raise DeploymentError(f"partial deployment state is missing durable files: {missing}")
    registry = _validate_existing_state(runtime_root, config, policies)
    lease = read_lease(runtime_root / LEASE_FILENAME)
    read_checkpoint(runtime_root / CHECKPOINT_FILENAME)
    # A present manifest is authoritative; otherwise validate the supported
    # legacy product before allowing any future Provider work.
    if product_root is not None:
        product_root = Path(product_root)
        _assert_no_partial_bundle(product_root)
        if (product_root / MANIFEST_FILENAME).exists() or (product_root / LEGACY_FILENAME).exists():
            try:
                load_feed(product_root)
            except BundleError as exc:
                raise DeploymentError(str(exc)) from exc
    return registry, lease


def _legacy_paths(root: Path, registry: RateRegistry) -> tuple[Path, ...]:
    return (
        root / PERSISTENCE_MARKER,
        root / REGISTRY_FILENAME,
        *(
            root / registry.scope_path(scope_id).name
            for scope_id in registry.registered_scope_ids()
        ),
        root / LEASE_FILENAME,
    )


def _checkpoint_from_latest(product_root: Path) -> FeedCheckpoint:
    """Read current product identity, preferring the active manifest."""
    root = Path(product_root)
    manifest_path = root / MANIFEST_FILENAME
    latest_path = root / LEGACY_FILENAME
    try:
        if manifest_path.exists():
            raw = validate_bundle(root)
        elif latest_path.exists():
            if not latest_path.is_file():
                raise DeploymentError("legacy latest Feed is not a regular file")
            raw = load_canonical_json(latest_path.read_bytes(), where="legacy latest.json")
            if not isinstance(raw, dict):
                raise DeploymentError("legacy latest Feed must be an object")
            validate_feed(raw)
            assert_feed_identity(raw)
        else:
            return FeedCheckpoint(previous_success=None)
        if raw.get("pipeline", {}).get("status") not in {"healthy", "degraded"}:
            raise DeploymentError("current Feed is not a successful Feed")
        cutoff = raw.get("evidence_cutoff_at")
        run_id = raw.get("run_id")
        if not isinstance(cutoff, str) or not isinstance(run_id, str):
            raise DeploymentError("current Feed identity is incomplete")
        return FeedCheckpoint(previous_success=PreviousSuccess(cutoff, run_id))
    except DeploymentError:
        raise
    except (OSError, SchemaError, BundleError, TypeError, ValueError) as exc:
        label = "Feed manifest" if manifest_path.exists() else "legacy latest Feed"
        raise DeploymentError(f"{label} is invalid") from exc


def _validate_legacy_layout(
    product_root: Path, config: AppConfig, policies: dict[str, RatePolicy]
) -> tuple[RateRegistry, DeploymentLease]:
    _assert_no_partial_bundle(product_root)
    registry = _validate_existing_state(product_root, config, policies)
    if (product_root / CHECKPOINT_FILENAME).exists():
        raise DeploymentError("legacy runtime state contains unsupported checkpoint")
    lease = read_lease(product_root / LEASE_FILENAME)
    _checkpoint_from_latest(product_root)
    return registry, lease


def classify_layout(
    product_root: Path,
    runtime_state_root: Path,
    config: AppConfig,
) -> str:
    """Classify repository runtime state without creating or changing files."""
    product_root = Path(product_root)
    runtime_state_root = Path(runtime_state_root)
    if product_root.resolve() == runtime_state_root.resolve():
        raise DeploymentError("Feed product and runtime-state roots must be distinct")
    policies = _scope_policies(config)
    state_entries = _runtime_entries(runtime_state_root)
    legacy_entries = _runtime_entries(product_root)
    state_names = {path.name for path in state_entries}
    legacy_names = {path.name for path in legacy_entries}
    state_authoritative = bool(
        state_names & _RUNTIME_DURABLE_NAMES
        or any(name.startswith("scope-") and name.endswith(".json") for name in state_names)
    )
    legacy_authoritative = bool(
        legacy_names & _RUNTIME_DURABLE_NAMES
        or any(name.startswith("scope-") and name.endswith(".json") for name in legacy_names)
    )
    state_unknown = [
        path.name
        for path in state_entries
        if not _is_transient_runtime_path(path)
        and path.name not in _RUNTIME_DURABLE_NAMES
        and not (path.name.startswith("scope-") and path.name.endswith(".json"))
    ]
    if state_unknown:
        raise DeploymentError(f"unsupported or partial runtime state layout: {state_unknown}")
    if state_authoritative and legacy_authoritative:
        raise DeploymentError("mixed old and new runtime layouts are not accepted")
    if state_authoritative:
        _validate_new_layout(runtime_state_root, config, policies)
        return _LAYOUT_NEW
    if legacy_authoritative:
        _validate_legacy_layout(product_root, config, policies)
        return _LAYOUT_LEGACY
    if any(not _is_transient_runtime_path(path) for path in state_entries):
        raise DeploymentError("unsupported or partial runtime state layout")
    return _LAYOUT_EMPTY


def _copy_exact(source: Path, target: Path) -> None:
    try:
        _atomic_write(target, source.read_bytes(), no_replace=True)
    except (OSError, RateStateError) as exc:
        raise DeploymentError(f"cannot relocate {source} to {target}") from exc


def _assert_legacy_checkpoint_matches(product_root: Path, runtime_root: Path) -> None:
    legacy_checkpoint = _checkpoint_from_latest(product_root)
    checkpoint = read_checkpoint(Path(runtime_root) / CHECKPOINT_FILENAME)
    if legacy_checkpoint.previous_success != checkpoint.previous_success:
        raise DeploymentError("legacy latest Feed and checkpoint do not match")


def migrate_legacy_feed(product_root: Path) -> tuple[Path, ...]:
    """Split and activate legacy ``latest.json`` without Provider work."""
    product_root = Path(product_root)
    manifest_path = product_root / MANIFEST_FILENAME
    if manifest_path.exists():
        try:
            validate_bundle(product_root)
        except BundleError as exc:
            raise DeploymentError(f"existing Feed manifest is invalid: {exc}") from exc
        return (manifest_path,)
    _assert_no_partial_bundle(product_root)
    latest_path = product_root / LEGACY_FILENAME
    if not latest_path.exists():
        return ()
    try:
        raw = load_canonical_json(latest_path.read_bytes(), where="legacy latest.json")
        if not isinstance(raw, dict):
            raise DeploymentError("legacy latest Feed must be an object")
        validate_feed(raw)
        assert_feed_identity(raw)
        bundle = build_bundle(raw)
        cutoff = datetime.fromisoformat(bundle.cutoff)
        publication = publish_bundle(
            output_root=product_root,
            bundle=bundle,
            cutoff=cutoff,
            run_id=bundle.run_id,
        )
        if publication.commit_durability_unknown:
            raise DeploymentError("Feed bundle migration durability is unknown")
        if not (publication.manifest_replaced or publication.idempotent):
            raise DeploymentError("Feed bundle migration ownership was not accepted")
    except DeploymentError:
        raise
    except (OSError, BundleError, SchemaError, TypeError, ValueError) as exc:
        raise DeploymentError("legacy latest Feed migration failed") from exc
    return (manifest_path,) + tuple(
        product_root / artifact_relative_path(domain, bundle.run_id) for domain in DOMAINS
    )


def migrate_legacy_state(
    product_root: Path,
    runtime_state_root: Path,
    config: AppConfig,
) -> tuple[Path, ...]:
    """Relocate one validated legacy runtime layout without network access."""
    product_root = Path(product_root)
    runtime_state_root = Path(runtime_state_root)
    policies = _scope_policies(config)
    registry, _lease = _validate_legacy_layout(product_root, config, policies)
    legacy_paths = _legacy_paths(product_root, registry)
    checkpoint = _checkpoint_from_latest(product_root)
    runtime_state_root.mkdir(parents=True, exist_ok=True)

    _copy_exact(product_root / PERSISTENCE_MARKER, runtime_state_root / PERSISTENCE_MARKER)
    try:
        registry_payload = load_canonical_json(
            (product_root / REGISTRY_FILENAME).read_bytes(), where="legacy rate registry"
        )
        if not isinstance(registry_payload, dict):
            raise DeploymentError("legacy rate registry must be an object")
        registry_payload["root_identity"] = str(runtime_state_root.resolve())
        _atomic_write(
            runtime_state_root / REGISTRY_FILENAME,
            json.dumps(registry_payload, sort_keys=True).encode("utf-8"),
            no_replace=True,
        )
    except (OSError, RateStateError, TypeError, ValueError) as exc:
        raise DeploymentError("cannot relocate legacy rate registry") from exc
    for scope_id in registry.registered_scope_ids():
        _copy_exact(
            registry.scope_path(scope_id),
            runtime_state_root / registry.scope_path(scope_id).name,
        )
    _copy_exact(product_root / LEASE_FILENAME, runtime_state_root / LEASE_FILENAME)
    try:
        write_checkpoint(runtime_state_root / CHECKPOINT_FILENAME, checkpoint)
    except (OSError, ValueError) as exc:
        raise DeploymentError("cannot seed relocated Feed checkpoint") from exc

    new_registry, _new_lease = _validate_new_layout(
        runtime_state_root, config, policies, product_root=product_root
    )
    new_paths = _durable_paths(runtime_state_root, new_registry)
    new_paths += (runtime_state_root / CHECKPOINT_FILENAME,)
    for path in legacy_paths:
        try:
            path.unlink()
        except OSError as exc:
            raise DeploymentError(f"cannot remove legacy runtime path {path}") from exc
    return new_paths + legacy_paths


def _durable_paths(root: Path, registry: RateRegistry) -> tuple[Path, ...]:
    marker = root / PERSISTENCE_MARKER
    if not marker.is_file():
        raise RateStateError("deployment persistence marker is missing")
    scope_ids = registry.registered_scope_ids()
    for scope_id in scope_ids:
        registry.read_active_scope(scope_id)
    lease = root / LEASE_FILENAME
    if not lease.is_file():
        raise RateStateError("deployment lease is missing")
    return (
        marker,
        root / REGISTRY_FILENAME,
        *(registry.scope_path(scope_id) for scope_id in scope_ids),
        lease,
    )


def allowlisted_paths(root: Path) -> tuple[Path, ...]:
    """Return only repository-backed state named by the registry and lease."""
    root = Path(root)
    registry = RateRegistry(root)
    try:
        return _durable_paths(root, registry)
    except RateStateError as exc:
        raise DeploymentError(str(exc)) from exc


def prepare_deployment(
    product_root: Path,
    runtime_state_root: Path,
    config: AppConfig,
    *,
    deployment_run_id: str,
    now: Callable[[], datetime],
) -> DeploymentPreparation:
    product_root = Path(product_root)
    runtime_state_root = Path(runtime_state_root)
    current = _utc(now())
    _validate_deployment_compatibility(config)
    policies = _scope_policies(config)
    cooldown = _validate_recovery_envelope(config, policies.values())
    layout = classify_layout(product_root, runtime_state_root, config)

    if layout == _LAYOUT_EMPTY:
        runtime_state_root.mkdir(parents=True, exist_ok=True)
        registry = RateRegistry(runtime_state_root)
        try:
            registry.ensure_registry(now=now)
            for policy in policies.values():
                registry.initialize_scope(
                    policy.scope_id,
                    policy.capacity,
                    policy.refill_period_seconds,
                    policy.minimum_interval_seconds,
                    now=now,
                )
        except (OSError, RateStateError) as exc:
            raise DeploymentError(str(exc)) from exc
        lease = DeploymentLease(
            version=LEASE_VERSION,
            deployment_run_id=deployment_run_id,
            state="bootstrap",
            armed_at=current,
            finished_at=None,
            feed_start_not_after=None,
            recovery_not_before=current + timedelta(seconds=cooldown),
        )
        try:
            write_lease(runtime_state_root / LEASE_FILENAME, lease)
            write_checkpoint(
                runtime_state_root / CHECKPOINT_FILENAME,
                FeedCheckpoint(previous_success=None),
            )
        except (OSError, RateStateError, ValueError) as exc:
            raise DeploymentError("cannot persist bootstrap deployment state") from exc
        return DeploymentPreparation(
            "bootstrap",
            lease,
            _durable_paths(runtime_state_root, registry)
            + (runtime_state_root / CHECKPOINT_FILENAME,),
        )

    if layout == _LAYOUT_LEGACY:
        paths = migrate_legacy_state(product_root, runtime_state_root, config)
        # This is a zero-network migration-only step. Keep latest.json until
        # the generated-state commit stages its deletion atomically with the
        # newly activated bundle.
        paths += migrate_legacy_feed(product_root)
        lease = read_lease(runtime_state_root / LEASE_FILENAME)
        return DeploymentPreparation("migration", lease, paths)

    registry, lease = _validate_new_layout(
        runtime_state_root, config, policies, product_root=product_root
    )
    if (
        not (product_root / MANIFEST_FILENAME).exists()
        and (product_root / LEGACY_FILENAME).exists()
    ):
        _assert_legacy_checkpoint_matches(product_root, runtime_state_root)
        migrate_legacy_feed(product_root)
        return DeploymentPreparation(
            "migration",
            lease,
            _migration_allowlisted_paths(product_root, runtime_state_root),
        )
    if lease.deployment_run_id == deployment_run_id:
        raise DeploymentError("deployment_run_id has already been used")
    if lease.state in {"bootstrap", "in_progress"} and current < lease.recovery_not_before:
        raise DeploymentError("recovery_not_before has not elapsed")

    registered = set(registry.registered_scope_ids())
    try:
        for scope_id, policy in policies.items():
            if scope_id not in registered:
                registry.initialize_scope(
                    scope_id,
                    policy.capacity,
                    policy.refill_period_seconds,
                    policy.minimum_interval_seconds,
                    now=now,
                )
    except (OSError, RateStateError) as exc:
        raise DeploymentError(str(exc)) from exc

    feed_start = current + timedelta(seconds=config.feed.pre_commit_deadline_seconds)
    armed = DeploymentLease(
        version=LEASE_VERSION,
        deployment_run_id=deployment_run_id,
        state="in_progress",
        armed_at=current,
        finished_at=None,
        feed_start_not_after=feed_start,
        recovery_not_before=feed_start
        + timedelta(seconds=config.feed.pre_commit_deadline_seconds + cooldown),
    )
    try:
        write_lease(runtime_state_root / LEASE_FILENAME, armed)
    except (OSError, RateStateError, ValueError) as exc:
        raise DeploymentError("cannot persist armed deployment lease") from exc
    return DeploymentPreparation("armed", armed, _durable_paths(runtime_state_root, registry))


def assert_feed_admitted(
    root: Path, *, deployment_run_id: str, now: datetime | Callable[[], datetime]
) -> DeploymentLease:
    lease = read_lease(Path(root) / LEASE_FILENAME, expected_run_id=deployment_run_id)
    if lease.state != "in_progress" or lease.feed_start_not_after is None:
        raise DeploymentError("deployment is not armed for Feed execution")
    current = _utc(now() if callable(now) else now)
    if current > lease.feed_start_not_after:
        raise DeploymentError("feed_start_not_after has elapsed")
    return lease


def _read_success_status(status_path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(status_path).read_bytes())
    except (OSError, ValueError) as exc:
        raise DeploymentError("successful Feed status is missing or corrupt") from exc
    if (
        not isinstance(raw, dict)
        or raw.get("status") not in {"healthy", "degraded"}
        or not isinstance(raw.get("run_id"), str)
        or not raw["run_id"]
        or not isinstance(raw.get("evidence_cutoff_at"), str)
    ):
        raise DeploymentError("successful Feed status is invalid")
    return raw


def _feed_paths(product_root: Path, raw: dict[str, Any]) -> tuple[Path, ...]:
    if "dated_relative_path" in raw:
        raise DeploymentError("Feed status dated_relative_path is unsupported")
    relative = raw.get("manifest_relative_path")
    if relative != MANIFEST_FILENAME:
        raise DeploymentError("Feed status manifest_relative_path is invalid")
    root_resolved = product_root.resolve()
    candidate = (product_root / relative).resolve()
    if not candidate.is_relative_to(root_resolved) or not candidate.is_file():
        raise DeploymentError("Feed status manifest_relative_path is outside or missing")
    if candidate.stat().st_size == 0:
        raise DeploymentError("Feed status manifest_relative_path is empty")
    try:
        feed = validate_bundle(product_root)
        if (
            feed.get("run_id") != raw["run_id"]
            or feed.get("evidence_cutoff_at") != raw["evidence_cutoff_at"]
        ):
            raise DeploymentError(
                "Feed product manifest_relative_path does not match successful status"
            )
        manifest = load_canonical_json(candidate.read_bytes(), where=str(candidate))
        paths = (candidate,) + tuple(
            product_root / entry["path"] for entry in manifest["artifacts"]
        )
        for path in paths[1:]:
            resolved = path.resolve()
            if not resolved.is_relative_to(root_resolved) or not resolved.is_file():
                raise DeploymentError("Feed artifact inventory contains an outside or missing path")
        superseded = raw.get("superseded_relative_paths", [])
        if not isinstance(superseded, list) or any(
            not isinstance(relative, str) for relative in superseded
        ):
            raise DeploymentError("Feed status superseded_relative_paths is invalid")
        active_names = {path.name for path in paths[1:]}
        for relative in superseded:
            relative_path = Path(relative)
            if (
                relative_path.name != relative
                or "/" in relative
                or "\\" in relative
                or re.fullmatch(r"feed-(?:[a-z_]+)-[0-9a-f]{32}\.json", relative) is None
                or relative in active_names
            ):
                raise DeploymentError("Feed status superseded_relative_paths is invalid")
            superseded_path = (product_root / relative_path).resolve()
            if not superseded_path.is_relative_to(root_resolved) or superseded_path.exists():
                raise DeploymentError("superseded Feed artifact is not a deletion")
        return paths + tuple(product_root / relative for relative in superseded)
    except DeploymentError:
        raise
    except (OSError, BundleError, SchemaError, TypeError, ValueError, KeyError) as exc:
        raise DeploymentError("Feed product manifest is invalid") from exc


def finalize_deployment(
    product_root: Path,
    runtime_state_root: Path,
    *,
    deployment_run_id: str,
    feed_succeeded: bool,
    status_path: Path,
    now: Callable[[], datetime],
) -> tuple[Path, ...]:
    product_root = Path(product_root)
    runtime_state_root = Path(runtime_state_root)
    lease_path = runtime_state_root / LEASE_FILENAME
    lease = read_lease(lease_path, expected_run_id=deployment_run_id)
    if lease.state != "in_progress":
        raise DeploymentError("only an in_progress lease can be finalized")
    status = _read_success_status(status_path) if feed_succeeded else None
    feed_paths = _feed_paths(product_root, status) if status is not None else ()
    finished_at = _utc(now())
    if finished_at < lease.armed_at:
        raise DeploymentError("finalization clock precedes lease arming")
    registry = RateRegistry(runtime_state_root)
    try:
        durable = _durable_paths(runtime_state_root, registry)
    except RateStateError as exc:
        raise DeploymentError(str(exc)) from exc
    checkpoint_path = runtime_state_root / CHECKPOINT_FILENAME
    if feed_succeeded:
        if status is None:
            raise DeploymentError("successful Feed status is missing")
        try:
            checkpoint = read_checkpoint(checkpoint_path)
        except (OSError, ValueError) as exc:
            raise DeploymentError("successful Feed checkpoint is missing or corrupt") from exc
        previous = checkpoint.previous_success
        if previous is None or (
            previous.run_id != status["run_id"]
            or previous.evidence_cutoff_at != status["evidence_cutoff_at"]
        ):
            raise DeploymentError("successful Feed status and checkpoint do not match")
    terminal = DeploymentLease(
        version=LEASE_VERSION,
        deployment_run_id=lease.deployment_run_id,
        state="success" if feed_succeeded else "failure",
        armed_at=lease.armed_at,
        finished_at=finished_at,
        feed_start_not_after=lease.feed_start_not_after,
        recovery_not_before=lease.recovery_not_before,
    )
    try:
        write_lease(lease_path, terminal)
    except (OSError, RateStateError, ValueError) as exc:
        raise DeploymentError("cannot persist terminal deployment lease") from exc
    if feed_succeeded:
        return durable + (checkpoint_path,) + feed_paths
    return durable


def _default_git(repo_root: Path) -> GitRunner:
    def run(args: list[str]) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise DeploymentError(f"git {' '.join(args)} failed") from exc
        return completed.stdout

    return run


def refresh_repository(repo_root: Path, *, git: GitRunner | None = None) -> None:
    runner = git or _default_git(Path(repo_root))
    runner(["fetch", "origin", "main"])
    runner(["merge", "--ff-only", "origin/main"])


def _relative_allowed(repo_root: Path, paths: Iterable[Path]) -> list[str]:
    root = Path(repo_root).resolve()
    relative: list[str] = []
    for path in paths:
        candidate = Path(path).resolve()
        if not candidate.is_relative_to(root):
            raise DeploymentError(f"generated path is outside repository: {path}")
        relative.append(str(candidate.relative_to(root)))
    return sorted(set(relative))


def publish_generated_state(
    repo_root: Path,
    paths: Iterable[Path],
    *,
    message: str,
    git: GitRunner | None = None,
) -> None:
    runner = git or _default_git(Path(repo_root))
    allowed = _relative_allowed(repo_root, paths)
    if not allowed:
        raise DeploymentError("generated publication allowlist is empty")
    staged_before = set(runner(["diff", "--cached", "--name-only"]).splitlines())
    if not staged_before.issubset(allowed):
        raise DeploymentError("unrelated paths are already staged")
    runner(["add", "--", *allowed])
    staged_after = set(runner(["diff", "--cached", "--name-only"]).splitlines())
    if not staged_after.issubset(allowed) or not staged_after:
        raise DeploymentError("generated publication staged an unexpected or empty set")
    runner(["diff", "--cached", "--check"])
    runner(["config", "user.name", "follow-the-money[bot]"])
    runner(["config", "user.email", "follow-the-money[bot]@users.noreply.github.com"])
    runner(["commit", "-m", message])
    runner(["push", "origin", "HEAD:main"])


def _write_output(path: str | None, mode: str) -> None:
    if path:
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(f"mode={mode}\n")


def _write_feed_status(path: Path, result: Any) -> None:
    status: dict[str, Any] = {"status": result.status, "warnings": result.warnings}
    if result.status == "failure":
        status["message"] = result.message
    if result.feed is not None and result.status in {"failure", "degraded"}:
        provider_outcomes = result.feed.get("provider_outcomes")
        if isinstance(provider_outcomes, list):
            status["provider_outcomes"] = provider_outcomes
    if result.feed is not None and result.status in {"healthy", "degraded"}:
        status.update(
            {
                "run_id": result.feed["run_id"],
                "evidence_cutoff_at": result.feed["evidence_cutoff_at"],
                "manifest_relative_path": MANIFEST_FILENAME,
                "superseded_relative_paths": list(getattr(result, "superseded_paths", ())),
            }
        )
    Path(path).write_text(json.dumps(status), encoding="utf-8")


def _write_typed_failure_status(path: Path, message: str) -> None:
    Path(path).write_text(
        json.dumps({"status": "failure", "message": message, "warnings": []}),
        encoding="utf-8",
    )


def _bound_diagnostic_text(value: str, limit: int = _DIAGNOSTIC_FIELD_LIMIT) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="ignore").rstrip("\\")


def _sanitize_diagnostic_text(value: str) -> str:
    pieces: list[str] = []
    for char in value:
        code = ord(char)
        category = unicodedata.category(char)
        if char == "\n":
            pieces.append("\\\\n")
        elif char == "\r":
            pieces.append("\\\\r")
        elif char == "\t":
            pieces.append("\\\\t")
        elif char in {"\u2028", "\u2029"}:
            pieces.append(f"\\\\u{code:04x}")
        elif category.startswith("C"):
            pieces.append(f"\\\\x{code:02x}" if code <= 0xFF else f"\\\\u{code:04x}")
        elif char in _MARKDOWN_SPECIAL:
            pieces.append(f"\\{char}")
        else:
            pieces.append(char)
    return _bound_diagnostic_text("".join(pieces))


def _read_diagnostic_status(path: Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("status") not in {"failure", "degraded"}:
        raise ValueError("diagnostic status is not renderable")

    message = raw.get("message")
    if message is not None and not isinstance(message, str):
        raise ValueError("diagnostic message is invalid")
    warnings = raw.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise ValueError("diagnostic warnings are invalid")

    outcomes = raw.get("provider_outcomes", [])
    if not isinstance(outcomes, list):
        raise TypeError("diagnostic provider outcomes are invalid")
    selected_outcomes: list[dict[str, Any]] = []
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            raise TypeError("diagnostic provider outcome is invalid")
        selected: dict[str, Any] = {}
        for field in _DIAGNOSTIC_PROVIDER_FIELDS:
            if field not in outcome:
                continue
            value = outcome[field]
            if field in {"error", "availability_reason"}:
                if value is not None and not isinstance(value, str):
                    raise ValueError("diagnostic provider text is invalid")
            elif field == "upstream_http_status":
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, int) or not 100 <= value <= 599
                ):
                    raise ValueError("diagnostic provider HTTP status is invalid")
            elif field == "affected_coverage_groups":
                if (
                    not isinstance(value, list)
                    or any(not isinstance(group, str) for group in value)
                    or value != sorted(set(value))
                ):
                    raise ValueError("diagnostic provider coverage groups are invalid")
            elif field in _DIAGNOSTIC_COUNTER_FIELDS:
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError("diagnostic provider counter is invalid")
            elif field == "availability":
                if value not in {"success", "blocked", "failed", "disabled"}:
                    raise ValueError("diagnostic provider availability is invalid")
            elif not isinstance(value, str):
                raise ValueError("diagnostic provider field is invalid")
            selected[field] = value
        selected_outcomes.append(selected)
    if any(
        any(field in outcome for field in _DIAGNOSTIC_PROVIDER_FIELDS[2:6]) for outcome in outcomes
    ):
        selected_outcomes.sort(key=lambda outcome: outcome.get("provider_id", ""))
    return {
        "status": raw["status"],
        "message": message,
        "warnings": warnings,
        "provider_outcomes": selected_outcomes,
    }


def _diagnostic_report(status: dict[str, Any]) -> str:
    lines = ["Feed failure diagnostics", f"status: {status['status']}"]
    if status["message"] is not None:
        lines.append(f"message: {_sanitize_diagnostic_text(status['message'])}")
    for index, warning in enumerate(status["warnings"], start=1):
        lines.append(f"warning[{index}]: {_sanitize_diagnostic_text(warning)}")
    for index, outcome in enumerate(status["provider_outcomes"], start=1):
        lines.append(f"provider[{index}]:")
        for field in _DIAGNOSTIC_PROVIDER_FIELDS:
            value = outcome.get(field)
            if value is None:
                continue
            if isinstance(value, str):
                rendered = _sanitize_diagnostic_text(value)
            elif isinstance(value, list):
                rendered = _sanitize_diagnostic_text(", ".join(value) or "none")
            else:
                rendered = str(value)
            lines.append(f"{field}: {rendered}")
    return _bound_diagnostic_text("\n".join(lines), _DIAGNOSTIC_REPORT_LIMIT)


def _render_feed_diagnostics(status_path: Path, summary_path: Path | None) -> int:
    try:
        report = _diagnostic_report(_read_diagnostic_status(Path(status_path)))
    except (KeyError, OSError, TypeError, UnicodeError, ValueError):
        print(_DIAGNOSTIC_UNAVAILABLE)
        return 0

    print(report)
    if summary_path is not None:
        try:
            with Path(summary_path).open("a", encoding="utf-8") as summary:
                summary.write(report + "\n")
        except OSError:
            print(_DIAGNOSTIC_UNAVAILABLE)
    return 0


def _command_prepare(args: argparse.Namespace) -> int:
    from .cli import _load_app_config

    refresh_repository(Path(args.repo))
    config = _load_app_config(args.config)
    result = prepare_deployment(
        Path(args.product_root),
        Path(args.runtime_state_root),
        config,
        deployment_run_id=args.run_id,
        now=lambda: datetime.now(UTC),
    )
    _write_output(args.output, result.mode)
    return 0


def _bootstrap_allowlisted_paths(runtime_state_root: Path) -> tuple[Path, ...]:
    runtime_state_root = Path(runtime_state_root)
    return allowlisted_paths(runtime_state_root) + (runtime_state_root / CHECKPOINT_FILENAME,)


def _tracked_exact_paths(
    repo_root: Path, paths: Iterable[Path], *, git: GitRunner
) -> tuple[Path, ...]:
    relative = _relative_allowed(repo_root, paths)
    if not relative:
        return ()
    tracked = set(git(["ls-files", "--", *relative]).splitlines())
    if not tracked.issubset(relative):
        raise DeploymentError("repository index returned unexpected migration paths")
    root = Path(repo_root).resolve()
    by_relative = {str(Path(path).resolve().relative_to(root)): Path(path) for path in paths}
    return tuple(by_relative[path] for path in relative if path in tracked)


def _migration_allowlisted_paths(
    product_root: Path,
    runtime_state_root: Path,
    *,
    repo_root: Path | None = None,
    git: GitRunner | None = None,
) -> tuple[Path, ...]:
    runtime_state_root = Path(runtime_state_root)
    product_root = Path(product_root)
    registry = RateRegistry(runtime_state_root)
    product_paths: tuple[Path, ...] = ()
    manifest_path = product_root / MANIFEST_FILENAME
    if manifest_path.exists():
        try:
            manifest = load_canonical_json(manifest_path.read_bytes(), where="Feed manifest")
            if not isinstance(manifest, dict):
                raise DeploymentError("migration Feed manifest is not an object")
            product_paths = (manifest_path,) + tuple(
                product_root / entry["path"] for entry in manifest["artifacts"]
            )
        except (OSError, TypeError, ValueError, KeyError) as exc:
            raise DeploymentError("migration Feed manifest is invalid") from exc
    latest = product_root / LEGACY_FILENAME
    if latest.exists():
        product_paths += (latest,)

    required_paths = (
        allowlisted_paths(runtime_state_root)
        + (runtime_state_root / CHECKPOINT_FILENAME,)
        + product_paths
    )
    missing = sorted(str(path) for path in required_paths if not path.is_file())
    if missing:
        raise DeploymentError(f"migration required paths are missing: {missing}")
    if repo_root is None or git is None:
        return required_paths + _legacy_paths(product_root, registry)
    repo_root = Path(repo_root)
    if latest.exists() and not _tracked_exact_paths(repo_root, (latest,), git=git):
        raise DeploymentError("migration latest Feed is not tracked")
    return required_paths + _tracked_exact_paths(
        repo_root, _legacy_paths(product_root, registry), git=git
    )


def _remove_migrated_latest(product_root: Path) -> None:
    latest = product_root / LEGACY_FILENAME
    if not latest.exists():
        return
    try:
        active = validate_bundle(product_root)
        legacy = load_canonical_json(latest.read_bytes(), where="legacy latest.json")
        if not isinstance(legacy, dict):
            raise DeploymentError("legacy latest Feed must be an object")
        validate_feed(legacy)
        assert_feed_identity(legacy)
        if active != legacy:
            raise DeploymentError("migrated bundle does not match legacy latest Feed")
        latest.unlink()
    except DeploymentError:
        raise
    except (OSError, BundleError, SchemaError, TypeError, ValueError) as exc:
        raise DeploymentError("cannot stage legacy latest Feed deletion") from exc


def _command_publish(args: argparse.Namespace) -> int:
    product_root = Path(args.product_root)
    runtime_state_root = Path(args.runtime_state_root)
    repo_root = Path(args.repo)
    mode = args.mode
    git: GitRunner | None = None
    if mode == "migration":
        lease = read_lease(runtime_state_root / LEASE_FILENAME)
        if lease.state not in LEASE_STATES:
            raise DeploymentError("migration publication requires a preserved lease")
        git = _default_git(repo_root)
        paths = _migration_allowlisted_paths(
            product_root, runtime_state_root, repo_root=repo_root, git=git
        )
        _remove_migrated_latest(product_root)
    elif mode == "bootstrap":
        lease = read_lease(runtime_state_root / LEASE_FILENAME, expected_run_id=args.run_id)
        if lease.state != "bootstrap":
            raise DeploymentError("bootstrap publication requires a bootstrap lease")
        paths = _bootstrap_allowlisted_paths(runtime_state_root)
    elif mode == "armed":
        lease = read_lease(runtime_state_root / LEASE_FILENAME, expected_run_id=args.run_id)
        if lease.state != "in_progress":
            raise DeploymentError("armed publication requires an in_progress lease")
        paths = allowlisted_paths(runtime_state_root)
    else:
        raise DeploymentError(f"unsupported pre-network publication mode: {mode!r}")
    publish_generated_state(
        repo_root,
        paths,
        message=f"feeds: {mode}",
        git=git,
    )
    return 0


def _command_collect(args: argparse.Namespace) -> int:
    from .cli import FeedExecutionError, FeedInputError, run_feed

    status_path = Path(args.status_file)
    exit_path = Path(args.exit_file) if args.exit_file else None
    try:
        assert_feed_admitted(
            Path(args.runtime_state_root),
            deployment_run_id=args.run_id,
            now=lambda: datetime.now(UTC),
        )
        result = run_feed(
            config_path=args.config,
            output_root=str(args.product_root),
            runtime_state_root=str(args.runtime_state_root),
        )
        _write_feed_status(status_path, result)
        code = result.exit_code
    except FeedInputError as exc:
        _write_typed_failure_status(status_path, str(exc))
        code = 2
    except FeedExecutionError as exc:
        _write_typed_failure_status(status_path, str(exc))
        code = 1
    if exit_path:
        exit_path.write_text(str(code), encoding="utf-8")
    return code


def _command_finalize(args: argparse.Namespace) -> int:
    paths = finalize_deployment(
        Path(args.product_root),
        Path(args.runtime_state_root),
        deployment_run_id=args.run_id,
        feed_succeeded=args.feed_succeeded == "true",
        status_path=Path(args.status_file),
        now=lambda: datetime.now(UTC),
    )
    publish_generated_state(
        Path(args.repo),
        paths,
        message=f"feeds: {'success' if args.feed_succeeded == 'true' else 'failure'}",
    )
    return 0


def _command_diagnostics(args: argparse.Namespace) -> int:
    summary_path = Path(args.summary_file) if args.summary_file else None
    return _render_feed_diagnostics(Path(args.status_file), summary_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="follow-the-money-feed-deployment")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--repo", default=".")
    prepare.add_argument("--product-root", default="feeds")
    prepare.add_argument("--runtime-state-root", default=".feed-state")
    prepare.add_argument("--config", default=None)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--output", default=None)
    subparsers.add_parser("publish").add_argument("--phase", choices=("pre",), required=True)
    publish = subparsers.choices["publish"]
    publish.add_argument("--repo", default=".")
    publish.add_argument("--product-root", default="feeds")
    publish.add_argument("--runtime-state-root", default=".feed-state")
    publish.add_argument("--mode", choices=("bootstrap", "migration", "armed"), required=True)
    publish.add_argument("--run-id", required=True)
    collect = subparsers.add_parser("collect")
    collect.add_argument("--product-root", default="feeds")
    collect.add_argument("--runtime-state-root", default=".feed-state")
    collect.add_argument("--config", default=None)
    collect.add_argument("--run-id", required=True)
    collect.add_argument("--status-file", default="feed-status.json")
    collect.add_argument("--exit-file", default=None)
    diagnostics = subparsers.add_parser("diagnostics")
    diagnostics.add_argument("--status-file", default="feed-status.json")
    diagnostics.add_argument("--summary-file", default=None)
    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--repo", default=".")
    finalize.add_argument("--product-root", default="feeds")
    finalize.add_argument("--runtime-state-root", default=".feed-state")
    finalize.add_argument("--run-id", required=True)
    finalize.add_argument("--status-file", default="feed-status.json")
    finalize.add_argument("--feed-succeeded", choices=("true", "false"), required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        if args.command == "prepare":
            return _command_prepare(args)
        if args.command == "publish":
            return _command_publish(args)
        if args.command == "collect":
            return _command_collect(args)
        if args.command == "diagnostics":
            return _command_diagnostics(args)
        return _command_finalize(args)
    except DeploymentError as exc:
        print(f"follow-the-money-feed-deployment: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
