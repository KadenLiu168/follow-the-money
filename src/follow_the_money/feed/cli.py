"""Deterministic five-domain Evidence Feed orchestration.

The Feed command:

1. loads explicit config and product/runtime-state roots (never machine-global state),
2. acquires the exclusive runtime-state-root collection lock (production path),
3. captures the real collection-start instant and one fixed
   ``evidence_cutoff_at`` after collection starts and before any provider
   request,
4. plans the strictly advancing window from the runtime checkpoint,
5. runs enabled providers with the durable rate-state debit/reconcile
   lifecycle, bounded HTTP clients, global/per-host concurrency limits,
   and the 300-second pre-commit deadline + 15-second reserve,
6. captures ``retrieved_at`` when each provider response actually returns,
   ``collection_completed_at`` after all provider work is terminal/fenced,
   and ``generated_at`` when the envelope is finalized — no offset or copied
   audit timestamps,
7. normalizes/dedupes (stable ``(knowledge_available_at, id)`` total order),
   validates the Feed schema/semantic-digest identity, and serializes
   published bytes with the shared ``canonical_bytes()``,
8. builds five typed artifacts and a manifest, then atomically activates
   ``feed-manifest.json`` — or dry-runs; an existing equal bundle is an
   idempotent no-op that retains the stored bytes.

Exit contract: 0 healthy/degraded success; 1 generation/publication failure;
2 usage/config/startup-capability errors.
"""

from __future__ import annotations

import argparse
import inspect
import json
import time
from collections.abc import Callable, Mapping
from concurrent.futures import CancelledError, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock
from typing import Any

from ..boundary import application_build_fingerprint, build_fingerprint_to_dict
from ..canonical import canonical_digest, canonical_sha256
from ..config import load_config
from ..config.load import ConfigError
from ..config.model import AppConfig
from ..feed.validate import assert_feed_identity, recompute_feed_identity, validate_feed
from ..providers.http import FetchError, validate_provider_url
from ..providers.lock import LOCK_FILENAME, CollectionLock, CollectionLockError
from ..providers.manifest import ManifestError
from ..providers.rate import RateRegistry, RateStateError
from ..providers.session import ManagedProviderClient
from ..schema import SchemaError
from .bundle import SUPPORTED_BUNDLE_MAJOR, BundleError, FeedBundle, build_bundle
from .checkpoint import (
    CHECKPOINT_FILENAME,
    CheckpointError,
    FeedCheckpoint,
    PreviousSuccess,
    read_checkpoint,
    write_checkpoint,
)
from .dedupe import deduplicate_items, deterministic_item_order
from .plan import (
    FeedPlanError,
    ProviderOutcome,
    assess_pipeline,
    bounded_availability_reason,
    fmt_utc,
    ordered_outcomes,
    plan_window,
)
from .publish import PublishError, publish_bundle
from .snapshot import SnapshotError, load_active_feed, select_provider_slices

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / "schemas"


class FeedCliError(ValueError):
    """Typed Feed CLI failure."""


class FeedInputError(FeedCliError):
    """Invalid invocation, configuration, or startup-capability failure."""


class FeedExecutionError(FeedCliError):
    """Failure after a valid Feed invocation entered execution."""


@dataclass
class FeedRunResult:
    status: str  # healthy | degraded | failure
    exit_code: int
    feed: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    message: str = ""
    bundle: FeedBundle | None = None
    superseded_paths: tuple[str, ...] = ()


def _default_config_path() -> Path:
    return REPO_ROOT / "config" / "config.yaml"


def _default_providers_path() -> Path:
    return REPO_ROOT / "config" / "providers.yaml"


def _default_manifest_root() -> Path:
    return REPO_ROOT / "providers"


def _load_app_config(config_path: str | None) -> AppConfig:
    cfg = config_path or str(_default_config_path())
    providers = str(_default_providers_path())
    try:
        return load_config(
            cfg,
            providers,
            require_verified_enabled=True,
            manifest_root=_default_manifest_root(),
        )
    except ConfigError as exc:
        raise FeedInputError(str(exc)) from exc


def run_feed(
    *,
    config_path: str | None = None,
    output_root: str | None = None,
    runtime_state_root: str | None = None,
    dry_run: bool = False,
    cutoff: datetime | None = None,
    window_start: str | None = None,
    providers_fn: Callable[[], Mapping[str, Any]] | None = None,
    now_fn: Callable[[], datetime] | None = None,
    enabled_provider_ids: list[str] | None = None,
    monotonic_now: Callable[[], float] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> FeedRunResult:
    """Execute one Feed run with injected clocks/clients (fixture-friendly).

    Production path (``providers_fn is None``) uses the verified-enabled
    registry built from checked-in manifests, a bounded ``httpx`` client,
    the exclusive runtime-state-root collection lock, the durable rate-state
    debit/reconcile lifecycle, global 8 / per-host 2 concurrency, and the
    300-second pre-commit deadline. ``enabled_provider_ids`` overrides
    config enablement for fixtures.
    """
    from ..providers.adapters import build_registry

    if now_fn is None and cutoff is not None:
        # Fixture mode: an explicit cutoff anchors the run's collection clock
        # at that instant. The first lifecycle observation (collection start)
        # reads the anchored instant and every later observation advances
        # with real elapsed time, so rate eligibility and lifecycle ordering
        # behave like production. Production never fixes the cutoff and
        # observes the real clock directly at each lifecycle event.
        fixed_cutoff = cutoff
        anchor: dict[str, float | None] = {"elapsed": None}

        def fixture_now() -> datetime:
            if anchor["elapsed"] is None:
                anchor["elapsed"] = time.monotonic()
                return fixed_cutoff
            return fixed_cutoff + timedelta(seconds=time.monotonic() - anchor["elapsed"])

        now_fn = fixture_now
    now_fn = now_fn or (lambda: datetime.now(UTC))
    monotonic = monotonic_now or time.monotonic
    sleep = sleep_fn or time.sleep
    cfg = _load_app_config(config_path)
    # The 300-second pre-commit deadline anchors at command startup (before
    # lock acquisition) so lock-waiting time counts against the deadline.
    deadline_started = monotonic()
    deadline_seconds = cfg.feed.pre_commit_deadline_seconds - cfg.feed.commit_reserve_seconds
    deadline_at = deadline_started + deadline_seconds
    product_root = Path(output_root or cfg.output_root)
    state_root = Path(runtime_state_root or cfg.runtime_state_root)
    if product_root.resolve() == state_root.resolve():
        raise FeedInputError("Feed product and runtime-state roots must be distinct")
    try:
        product_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FeedExecutionError(f"cannot prepare product root {product_root}: {exc}") from exc

    # Coordinate every run that can use production adapters. Fixture-injected
    # dry runs cannot send a real request and remain write-light and
    # deterministic.
    coordinates_run = not dry_run or providers_fn is None
    lock: CollectionLock | None = None
    rate: RateRegistry | None = None
    if coordinates_run:
        try:
            state_root.mkdir(parents=True, exist_ok=True)
            lock = CollectionLock(
                state_root,
                timeout_seconds=min(
                    cfg.feed.lock_timeout_seconds,
                    max(0.0, deadline_at - monotonic()),
                ),
                monotonic_now=monotonic,
            )
            lock.acquire()
        except CollectionLockError as exc:
            raise FeedExecutionError(str(exc)) from exc

    # Capture the real collection start and the fixed cutoff only after the
    # cooperating run owns the lock. This prevents lock wait time from
    # freezing a stale planning window; the cutoff is observed after
    # collection starts and before any provider request.
    started_at = now_fn()
    cutoff = cutoff or now_fn()
    if cutoff.tzinfo is None:
        if lock is not None:
            lock.release()
        raise FeedInputError("cutoff must be timezone-aware")
    cutoff = datetime.fromisoformat(fmt_utc(cutoff))

    checkpoint_path = state_root / CHECKPOINT_FILENAME
    if coordinates_run:
        try:
            if checkpoint_path.exists():
                checkpoint = read_checkpoint(checkpoint_path)
            else:
                established = any(path.name != LOCK_FILENAME for path in state_root.iterdir())
                if established:
                    raise CheckpointError(f"missing checkpoint: {checkpoint_path}")
                checkpoint = FeedCheckpoint(previous_success=None)
                write_checkpoint(checkpoint_path, checkpoint)
        except (OSError, CheckpointError) as exc:
            if lock is not None:
                lock.release()
            raise FeedExecutionError(str(exc)) from exc
    else:
        checkpoint = FeedCheckpoint(previous_success=None)

    try:
        plan = plan_window(
            cutoff=cutoff,
            previous_success=checkpoint.previous_success,
            bootstrap_lookback_hours=cfg.feed.bootstrap_lookback_hours,
            gap_threshold_hours=cfg.feed.gap_threshold_hours,
        )
    except FeedPlanError as exc:
        if lock is not None:
            lock.release()
        raise FeedExecutionError(str(exc)) from exc

    # Durable rate-state registry is created only after planning succeeds:
    # an invalid current Feed makes zero writes beyond the lock file itself.
    if coordinates_run:
        try:
            rate = RateRegistry(state_root)
            rate.ensure_registry(now=now_fn)
        except (OSError, RateStateError) as exc:
            if lock is not None:
                lock.release()
            raise FeedExecutionError(str(exc)) from exc

    try:
        # Registry: production uses the verified-enabled manifest registry.
        registry: Any
        if providers_fn is not None:
            registry = providers_fn()
            adapters_by_id = {
                pid: list(adapter) if isinstance(adapter, (list, tuple)) else [adapter]
                for pid, adapter in registry.items()
            }
        else:
            try:
                resolved_providers = {p.id: p for p in cfg.providers}
                # Preserve the existing zero-argument test-factory seam while
                # the production registry receives the resolved contracts.
                registry_factory = build_registry
                if inspect.signature(registry_factory).parameters:
                    registry = registry_factory(resolved_providers)
                else:
                    registry = registry_factory()
                adapters_by_id = _production_adapters(cfg, registry)
            except (KeyError, ManifestError, OSError, ValueError) as exc:
                raise FeedInputError(str(exc)) from exc

        if enabled_provider_ids is not None:
            enabled_ids = [pid for pid in enabled_provider_ids if pid in adapters_by_id]
        else:
            enabled_ids = [p.id for p in cfg.providers if p.enabled and p.id in adapters_by_id]
        if not enabled_ids:
            raise FeedInputError("no provider enabled")

        # Pre-initialize every shared rate scope under the exclusive lock so
        # concurrent providers sharing one scope cannot race on first use.
        if rate is not None:
            try:
                _preinitialize_scopes(cfg, rate, enabled_ids, now_fn)
            except (OSError, RateStateError) as exc:
                raise FeedExecutionError(str(exc)) from exc

        # One outcome per planned provider, keyed by stable provider identity
        # before any worker starts; completion order is never serialized.
        coverage_groups = _coverage_groups_by_provider(cfg)
        outcomes: dict[str, ProviderOutcome] = {
            pid: ProviderOutcome(
                provider_id=pid,
                affected_coverage_groups=coverage_groups.get(pid, ()),
            )
            for pid in enabled_ids
        }
        items: list[dict[str, Any]] = []
        sec_provider = next(
            (provider for provider in cfg.providers if provider.id == "sec_edgar"), None
        )
        sec_outcome = outcomes.get("sec_edgar")
        if (
            sec_provider is not None
            and sec_provider.contract_version == 2
            and not adapters_by_id.get("sec_edgar")
            and not cfg.watched_companies
            and sec_outcome is not None
        ):
            sec_outcome.state = "empty"
            sec_outcome.availability = "success"

        global_sem = _Semaphore(cfg.feed.global_concurrency)
        host_sems: dict[str, _Semaphore] = {}
        # Providers sharing one durable scope must serialize the complete
        # debit -> possible send -> reconcile transition in this process.
        # The collection lock handles other processes; this closes the
        # intra-process window where a peer could observe the provisional
        # crash cooldown before the first request reconciles it.
        scope_ids: set[str] = set()
        for pid in enabled_ids:
            scope = _provider_scope(pid, cfg)
            if scope is not None:
                scope_ids.add(scope)
        scope_locks = {scope_id: Lock() for scope_id in scope_ids}
        cancel_event = Event()
        active_clients: dict[int, Any] = {}
        active_clients_lock = Lock()
        for pid in enabled_ids:
            for p in cfg.providers:
                if p.id == pid:
                    for rule in (*p.fetch_hosts, *p.redirect_hosts):
                        host_sems.setdefault(rule.host, _Semaphore(cfg.feed.per_host_concurrency))

        def execute_adapter(pid: str, adapter: Any, outcome: ProviderOutcome) -> None:
            request_window = {"start": plan.window_start, "end": plan.evidence_cutoff_at}
            scope_id = _provider_scope(pid, cfg)
            managed_client: Any
            if providers_fn is None:
                contract = cfg.provider(pid)
                import httpx

                transport = httpx.Client(
                    timeout=float(contract.attempt_timeout_seconds), follow_redirects=False
                )
                managed_client = ManagedProviderClient(
                    contract,
                    rate=rate,
                    scope_lock=scope_locks.get(scope_id) if scope_id is not None else None,
                    global_semaphore=global_sem,
                    host_semaphores=host_sems,
                    cancel_event=cancel_event,
                    deadline_at=deadline_at,
                    monotonic_now=monotonic,
                    now_fn=now_fn,
                    sleep_fn=sleep,
                    transport=transport,
                )
            else:
                managed_client = _client_for(adapter)

            def request() -> Any:
                if cancel_event.is_set() or monotonic() >= deadline_at:
                    raise FetchError("pre_commit_deadline_exceeded: provider request cancelled")
                with active_clients_lock:
                    active_clients[id(managed_client)] = managed_client
                try:
                    return adapter.fetch(request_window, managed_client)
                finally:
                    with active_clients_lock:
                        active_clients.pop(id(managed_client), None)

            request.client = managed_client  # type: ignore[attr-defined]
            try:
                _run_adapter(
                    outcome,
                    adapter,
                    plan,
                    cutoff,
                    cfg,
                    rate,
                    now_fn,
                    items,
                    monotonic,
                    deadline_at,
                    sleep,
                    request,
                    cancel_event,
                )
            finally:
                close = getattr(managed_client, "close", None)
                if close is not None:
                    close()

        def execute_one(pid: str) -> None:
            outcome = outcomes[pid]
            if monotonic() - deadline_started > deadline_seconds:
                outcome.state = "skipped"
                outcome.error = "pre_commit_deadline_exceeded"
                outcome.availability = "failed"
                outcome.availability_reason = "pre_commit_deadline_exceeded"
                outcome.execution_failure = True
                return
            for adapter in adapters_by_id[pid]:
                execute_adapter(pid, adapter, outcome)
                if outcome.state in {"failed", "partial"} and outcome.terminal_incomplete:
                    break  # terminal acquisition unit failure: stop later units

        pool = ThreadPoolExecutor(max_workers=cfg.feed.global_concurrency)
        futures = [pool.submit(execute_one, pid) for pid in enabled_ids]

        def cancel_provider_work() -> None:
            cancel_event.set()
            with active_clients_lock:
                clients = list(active_clients.values())
            for client in clients:
                close = getattr(client, "close", None)
                if close is not None:
                    close()
            for future in futures:
                future.cancel()

        try:
            remaining = max(0.0, deadline_at - monotonic())
            _done, pending = wait(futures, timeout=remaining)
            if pending:
                cancel_provider_work()
            for future in futures:
                try:
                    future.result()
                except CancelledError:
                    continue
                except (OSError, RateStateError) as exc:
                    raise FeedExecutionError(str(exc)) from exc
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

        deadline_failure = next(
            (outcome for outcome in outcomes.values() if outcome.execution_failure), None
        )
        if deadline_failure is not None:
            raise FeedExecutionError(deadline_failure.error or "pre_commit_deadline_exceeded")

        # Collection completed: every provider outcome reached a terminal or
        # fenced state and aggregation is complete.
        completed_at = now_fn()

        # Snapshot retention is an optional post-acquisition operation. The
        # checkpoint remains the sole window-planning authority.
        active_feed = load_active_feed(product_root)
        providers_by_id = {provider.id: provider for provider in cfg.providers}
        contract_snapshots = _provider_contract_snapshots(cfg, include_disabled=True)
        current_contract_hashes = {
            entry["provider_id"]: entry["hash"] for entry in contract_snapshots
        }
        freshness_contracts = {
            pid: provider.freshness
            for pid, provider in providers_by_id.items()
            if provider.freshness is not None
        }
        empty_validity = {
            pid: provider.empty_valid_for_window for pid, provider in providers_by_id.items()
        }
        complete_state_provider_ids = tuple(
            entry["provider_id"]
            for entry in contract_snapshots
            if entry["provider_id"] in {"sec_edgar", "cftc"}
            and entry["snapshot"].get("contract_version") == 2
        )
        if (
            "sec_edgar" in complete_state_provider_ids
            and "sec_edgar" in outcomes
            and (
                outcomes["sec_edgar"].state == "healthy"
                or (
                    outcomes["sec_edgar"].state == "empty"
                    and empty_validity.get("sec_edgar", False)
                )
            )
        ):
            expected_sec_ciks = {company.cik for company in cfg.watched_companies}
            sec_items = [item for item in items if item.get("provider_id") == "sec_edgar"]
            actual_sec_cik_values = [
                item.get("payload", {}).get("company_identity", {}).get("cik") for item in sec_items
            ]
            actual_sec_ciks = {value for value in actual_sec_cik_values if isinstance(value, str)}
            if (
                any(not isinstance(value, str) for value in actual_sec_cik_values)
                or actual_sec_ciks != expected_sec_ciks
                or len(actual_sec_cik_values) != len(actual_sec_ciks)
            ):
                outcomes["sec_edgar"].state = "partial"
                outcomes["sec_edgar"].error = "SEC v2 complete slice does not equal watched CIK set"
                outcomes["sec_edgar"].availability = "failed"
                outcomes["sec_edgar"].availability_reason = outcomes["sec_edgar"].error
                outcomes["sec_edgar"].terminal_incomplete = True
        try:
            selection = select_provider_slices(
                outcomes=outcomes,
                current_items=items,
                active_feed=active_feed,
                contracts=freshness_contracts,
                current_contract_hashes=current_contract_hashes,
                empty_valid_for_window=empty_validity,
                evidence_cutoff_at=plan.evidence_cutoff_at,
                strict_identity_provider_ids=tuple(providers_by_id),
                complete_state_provider_ids=complete_state_provider_ids,
            )
        except SnapshotError as exc:
            raise FeedExecutionError(str(exc)) from exc

        # Dedup + deterministic order after slice selection. A valid active
        # bundle was already deduped; this preserves its semantic item bytes
        # on an unchanged carry while retaining current Feed deduplication.
        deduped, _dropped = deduplicate_items(list(selection.items))
        ordered = deterministic_item_order(deduped)

        status, warnings = assess_pipeline(
            config=cfg, planned_provider_ids=enabled_ids, outcomes=outcomes
        )
        if plan.gap_warning:
            warnings.append(f"coverage gap: {plan.gap_warning[0]} to {plan.gap_warning[1]}")

        feed = _build_feed(
            cfg=cfg,
            plan=plan,
            started_at=started_at,
            completed_at=completed_at,
            outcomes=outcomes,
            items=ordered,
            status=status,
            warnings=warnings,
            now_fn=now_fn,
        )

        # Validate before publication.
        try:
            validate_feed(feed)
            assert_feed_identity(feed)
        except SchemaError as exc:
            raise FeedExecutionError(str(exc)) from exc

        try:
            bundle = build_bundle(feed)
        except BundleError as exc:
            raise FeedExecutionError(str(exc)) from exc

        if status == "failure":
            return FeedRunResult(
                status=status,
                exit_code=1,
                feed=feed,
                warnings=warnings,
                message="source completeness failed: " + "; ".join(warnings),
                bundle=bundle,
            )

        serialized_size = len(bundle.manifest_bytes) + sum(
            len(data) for data in bundle.artifact_bytes.values()
        )
        if serialized_size > cfg.feed.max_serialized_feed_bytes:
            raise FeedExecutionError(
                "serialized Feed size "
                f"{serialized_size} exceeds max_serialized_feed_bytes "
                f"{cfg.feed.max_serialized_feed_bytes}"
            )

        if dry_run:
            return FeedRunResult(
                status=status, exit_code=0, feed=feed, warnings=warnings, bundle=bundle
            )

        try:
            publication = publish_bundle(
                output_root=product_root,
                bundle=bundle,
                cutoff=cutoff,
                run_id=feed["run_id"],
                monotonic_now=monotonic,
                deadline_at=deadline_at,
            )
        except (OSError, PublishError) as exc:
            raise FeedExecutionError(str(exc)) from exc
        if publication.commit_durability_unknown:
            raise FeedExecutionError(
                "commit_durability_unknown: Feed publication durability is unknown"
            )
        if not (getattr(publication, "manifest_replaced", False) or publication.idempotent):
            raise FeedExecutionError("Feed manifest ownership was not accepted")
        if publication.cleanup_failed:
            warnings.append("Feed bundle cleanup deferred")

        try:
            write_checkpoint(
                checkpoint_path,
                FeedCheckpoint(
                    previous_success=PreviousSuccess(
                        evidence_cutoff_at=feed["evidence_cutoff_at"],
                        run_id=feed["run_id"],
                    )
                ),
            )
        except CheckpointError as exc:
            raise FeedExecutionError(f"checkpoint persistence failed: {exc}") from exc

        code = 0 if status in ("healthy", "degraded") else 1
        return FeedRunResult(
            status=status,
            exit_code=code,
            feed=feed,
            warnings=warnings,
            bundle=bundle,
            superseded_paths=getattr(publication, "superseded_paths", ()),
        )
    finally:
        if lock is not None:
            lock.release()


def _production_adapters(cfg: AppConfig, registry: Any) -> dict[str, list[Any]]:
    """Build per-provider adapter lists for the production registry.

    Every enabled Provider contributes one adapter instance; SEC EDGAR also
    receives the configured watched-company CIK filter.
    """
    from ..providers.adapters import SecEdgarAdapter

    adapters: dict[str, list[Any]] = {}
    for p in cfg.providers:
        if not p.enabled:
            continue
        if p.id == "sec_edgar":
            adapters[p.id] = [
                SecEdgarAdapter(p, watched_company=company)
                for company in sorted(cfg.watched_companies, key=lambda company: company.cik)
            ]
        else:
            try:
                adapters[p.id] = [registry.get(p.id)]
            except KeyError:
                adapters[p.id] = []
    return adapters


def _adapter_fetch_host(pid: str, cfg: AppConfig) -> str | None:
    for p in cfg.providers:
        if p.id == pid and p.fetch_hosts:
            return p.fetch_hosts[0].host
    return None


def _provider_empty_valid_for_window(pid: str, cfg: AppConfig) -> bool:
    for provider in cfg.providers:
        if provider.id == pid:
            return provider.empty_valid_for_window
    return False


def _coverage_groups_by_provider(cfg: AppConfig) -> dict[str, tuple[str, ...]]:
    groups: dict[str, set[str]] = {}
    for row in cfg.coverage.rows:
        for provider_id in row.members:
            groups.setdefault(provider_id, set()).add(row.group)
    return {provider_id: tuple(sorted(group_ids)) for provider_id, group_ids in groups.items()}


def _run_adapter(
    outcome: ProviderOutcome,
    adapter: Any,
    plan,
    cutoff,
    cfg,
    rate,
    now_fn,
    items: list[dict[str, Any]],
    monotonic_now: Callable[[], float],
    deadline_at: float,
    sleep_fn: Callable[[float], None],
    request_fn: Callable[[], Any],
    cancel_event: Event | None = None,
) -> None:
    """Run Provider-level attempts; actual sends are managed by the client."""

    window = {"start": plan.window_start, "end": plan.evidence_cutoff_at}
    max_attempts = max(1, int(cfg.feed.max_attempts))
    empty_valid_for_window = _provider_empty_valid_for_window(outcome.provider_id, cfg)
    provider_contract = next(
        (provider for provider in cfg.providers if provider.id == outcome.provider_id), None
    )
    managed_client = getattr(request_fn, "client", None)
    prior_terminal = outcome.terminal_incomplete

    def observe_client() -> None:
        observed = getattr(managed_client, "last_response_at", None)
        if observed is not None:
            observed_iso = fmt_utc(observed)
            if outcome.retrieved_at is None or observed_iso > outcome.retrieved_at:
                outcome.retrieved_at = observed_iso
        if bool(getattr(managed_client, "successful_resource_observed", False)):
            outcome.partial_resource_observed = True

    def mark_incomplete(message: str, *, terminal: bool = True) -> None:
        outcome.state = (
            "partial"
            if (
                outcome.accepted
                or outcome.non_permitted_empty_observed
                or outcome.partial_resource_observed
            )
            else "failed"
        )
        outcome.error = message
        outcome.availability = "failed"
        outcome.availability_reason = bounded_availability_reason(message)
        if terminal:
            outcome.terminal_incomplete = True

    def deadline_expired() -> bool:
        return (
            cancel_event is not None and cancel_event.is_set()
        ) or monotonic_now() >= deadline_at

    for attempt in range(max_attempts):
        if deadline_expired():
            mark_incomplete("pre_commit_deadline_exceeded: provider work cancelled")
            outcome.execution_failure = True
            return
        outcome.attempted += 1
        try:
            raw = request_fn()
            outcome.fetched += 1
            observe_client()
            if outcome.retrieved_at is None:
                outcome.retrieved_at = fmt_utc(now_fn())
            if deadline_expired():
                mark_incomplete("pre_commit_deadline_exceeded: late provider result ignored")
                outcome.execution_failure = True
                return
            normalized = list(adapter.normalize(raw, window))
            allowed_payload_types = (
                set(provider_contract.payload_types) if provider_contract is not None else set()
            )
            validated_items: list[dict[str, Any]] = []
            identity_ids: set[str] = set()
            invalid_reason: str | None = None
            for item in normalized:
                if not isinstance(item, Mapping):
                    invalid_reason = "normalized item is not an object"
                    break
                payload = item.get("payload")
                if (
                    not isinstance(payload, Mapping)
                    or payload.get("type") not in allowed_payload_types
                ):
                    invalid_reason = "normalized item payload is outside Provider contract"
                    break
                item_id = item.get("id")
                if (
                    not isinstance(item_id, str)
                    or not item_id
                    or item_id in identity_ids
                    or item.get("provider_id") != outcome.provider_id
                ):
                    invalid_reason = "current item identity is missing, duplicated, or mismatched"
                    break
                identity_ids.add(item_id)
                source = item.get("source")
                if not isinstance(source, Mapping):
                    invalid_reason = "normalized item source URL is outside Provider contract"
                    break
                url = source.get("url")
                if provider_contract is None or not isinstance(url, str) or not url:
                    invalid_reason = "normalized item source URL is outside Provider contract"
                    break
                try:
                    canonical_url = validate_provider_url(
                        url, rules=provider_contract.source_link_hosts
                    )
                except (TypeError, ValueError):
                    invalid_reason = "normalized item source URL is outside Provider contract"
                    break
                if len(canonical_url) > cfg.feed.max_url_characters:
                    invalid_reason = "normalized item source URL exceeds configured limit"
                    break
                normalized_item = dict(item)
                normalized_item["source"] = {**source, "url": canonical_url}
                validated_items.append(normalized_item)
            if invalid_reason is not None:
                outcome.rejected += 1
                mark_incomplete(invalid_reason)
                return
            if deadline_expired():
                mark_incomplete("pre_commit_deadline_exceeded: late provider result ignored")
                outcome.execution_failure = True
                return

            accepted_items = validated_items
            outcome.error = None
            items.extend(accepted_items)
            accepted = len(accepted_items)
            outcome.accepted += accepted
            if not accepted and not empty_valid_for_window:
                outcome.non_permitted_empty_observed = True
            if accepted:
                # A successful retry resolves transient attempt failures. A
                # terminal failure from another acquisition unit is retained.
                if prior_terminal or outcome.terminal_incomplete:
                    outcome.state = "partial"
                    outcome.availability = "failed"
                else:
                    outcome.state = "healthy"
                    outcome.availability = "success"
                    outcome.availability_reason = None
                    outcome.upstream_http_status = None
            elif outcome.accepted:
                outcome.state = "partial"
                outcome.error = "non-permitted empty result after accepted evidence"
                outcome.availability = "failed"
                outcome.availability_reason = outcome.error
                outcome.terminal_incomplete = True
            else:
                outcome.state = "empty"
                if empty_valid_for_window:
                    outcome.availability = "success"
                    outcome.availability_reason = None
                    outcome.upstream_http_status = None
                else:
                    outcome.availability = "failed"
                    outcome.availability_reason = "empty result is not permitted for window"
                    outcome.terminal_incomplete = True
            return
        except FetchError as exc:
            observe_client()
            if exc.observed_at is not None:
                observed_iso = fmt_utc(exc.observed_at)
                if outcome.retrieved_at is None or observed_iso > outcome.retrieved_at:
                    outcome.retrieved_at = observed_iso
            elif exc.response_observed and outcome.retrieved_at is None:
                outcome.retrieved_at = fmt_utc(now_fn())
            outcome.partial_resource_observed |= bool(exc.acquisition_progress)
            outcome.upstream_http_status = exc.status_code
            can_retry = exc.retryable and attempt + 1 < max_attempts
            mark_incomplete(str(exc), terminal=not can_retry)
            outcome.availability = "blocked" if exc.status_code in {401, 403} else "failed"
            outcome.availability_reason = bounded_availability_reason(str(exc))
            if deadline_expired():
                outcome.execution_failure = True
                outcome.error = f"pre_commit_deadline_exceeded: {exc}"
                return
            if can_retry:
                delay = float(exc.retry_after_seconds or 0)
                remaining = deadline_at - monotonic_now()
                if delay > remaining:
                    outcome.error = f"{exc}; retry_not_admitted_before_deadline"
                    outcome.execution_failure = True
                    outcome.terminal_incomplete = True
                    return
                if delay > 0:
                    sleep_fn(delay)
                if monotonic_now() >= deadline_at:
                    outcome.error = f"{exc}; retry_not_admitted_before_deadline"
                    outcome.execution_failure = True
                    outcome.terminal_incomplete = True
                    return
                continue
            return
        except RateStateError:
            raise
        except Exception as exc:  # noqa: BLE001 - Provider orchestration boundary
            observe_client()
            mark_incomplete(str(exc))
            outcome.upstream_http_status = None
            return


def _preinitialize_scopes(
    cfg: AppConfig, rate: RateRegistry, enabled_ids: list[str], now_fn: Callable[[], datetime]
) -> None:
    """Recoverable ``initializing -> active`` first-use for every enabled
    scope, serialized under the collection lock (no concurrent races)."""
    initialized: set[str] = set()
    for pid in enabled_ids:
        scope = _provider_scope(pid, cfg)
        if scope is None or scope in initialized:
            continue
        initialized.add(scope)
        try:
            rate.recover_or_load(scope)
        except RateStateError:
            policy = _scope_policy(scope, cfg)
            if policy is None:
                raise
            rate.initialize_scope(
                scope,
                policy.capacity,
                policy.refill_period_seconds,
                policy.minimum_interval_seconds,
                now=now_fn,
            )


def _ensure_scope_state(rate: RateRegistry, scope_id: str, cfg: AppConfig, now_fn):
    try:
        return rate.recover_or_load(scope_id)
    except RateStateError:
        policy = _scope_policy(scope_id, cfg)
        if policy is None:
            raise
        rate.initialize_scope(
            scope_id,
            policy.capacity,
            policy.refill_period_seconds,
            policy.minimum_interval_seconds,
            now=now_fn,
        )
        return rate.recover_or_load(scope_id)


def _scope_policy(scope_id: str, cfg: AppConfig):
    for p in cfg.providers:
        if p.rate_policy and p.rate_policy.scope_id == scope_id:
            return p.rate_policy
    return None


def _provider_scope(pid: str, cfg: AppConfig):
    for p in cfg.providers:
        if p.id == pid and p.rate_policy:
            return p.rate_policy.scope_id
    return None


def _client_for(adapter: Any) -> Any:
    import httpx

    timeout = getattr(getattr(adapter, "_contract", None), "attempt_timeout_seconds", 20)
    return httpx.Client(timeout=float(timeout), follow_redirects=False)


class _Semaphore:
    """Bounded concurrency gate (global / per-host)."""

    def __init__(self, permits: int) -> None:
        import threading

        self._sem = threading.Semaphore(permits)

    def acquire(
        self,
        *,
        cancel_event: Event | None = None,
        deadline_at: float | None = None,
        monotonic_now: Callable[[], float] = time.monotonic,
    ) -> None:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise FetchError("pre_commit_deadline_exceeded: concurrency wait cancelled")
            timeout = 0.1
            if deadline_at is not None:
                remaining = deadline_at - monotonic_now()
                if remaining <= 0:
                    raise FetchError("pre_commit_deadline_exceeded: concurrency wait expired")
                timeout = min(timeout, remaining)
            if self._sem.acquire(timeout=timeout):
                return

    def __enter__(self) -> None:
        self.acquire()

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.release()

    def release(self) -> None:
        self._sem.release()


def _schema_descriptor(rel: str) -> dict[str, str]:
    path = SCHEMA_ROOT / rel
    try:
        sha = canonical_sha256(path.read_bytes())
    except OSError as exc:
        raise FeedExecutionError(f"cannot read schema {rel}: {exc}") from exc
    return {"path": f"schemas/{rel}", "sha256": sha}


def _provider_contract_snapshots(
    cfg: AppConfig, *, include_disabled: bool = False
) -> list[dict[str, Any]]:
    """Sorted canonical redacted non-secret runtime-contract snapshots."""
    snapshots: list[dict[str, Any]] = []
    for p in sorted(cfg.providers, key=lambda x: x.id):
        if not p.enabled and not include_disabled:
            continue
        payload = {
            "provider_id": p.id,
            "coverage_groups": list(p.coverage_groups),
            "source_family_id": p.source_family_id,
            "tier": p.tier,
            "contract_version": p.contract_version,
            "authentication": p.authentication,
            "protocol": p.protocol,
            "fetch_hosts": [
                {
                    "host": r.host,
                    "allow_subdomains": r.allow_subdomains,
                    "allowed_ports": list(r.allowed_ports),
                }
                for r in p.fetch_hosts
            ],
            "redirect_hosts": [
                {
                    "host": r.host,
                    "allow_subdomains": r.allow_subdomains,
                    "allowed_ports": list(r.allowed_ports),
                }
                for r in p.redirect_hosts
            ],
            "source_link_hosts": [
                {
                    "host": r.host,
                    "allow_subdomains": r.allow_subdomains,
                    "allowed_ports": list(r.allowed_ports),
                    "allowed_query_params": list(r.allowed_query_params),
                    "query_value_grammar": r.query_value_grammar,
                    "drop_query_params": list(r.drop_query_params),
                }
                for r in p.source_link_hosts
            ],
            "rate_policy": {
                "scope_id": p.rate_policy.scope_id,
                "capacity": p.rate_policy.capacity,
                "refill_period_seconds": p.rate_policy.refill_period_seconds,
                "minimum_interval_seconds": p.rate_policy.minimum_interval_seconds,
            }
            if p.rate_policy and not p.rate_policy.unlimited
            else None,
            "allowed_charset": p.allowed_charset,
            "allowed_bom": p.allowed_bom,
            "allowed_content_type_header": p.allowed_content_type_header,
            "pagination": p.pagination,
            "empty_valid_for_window": p.empty_valid_for_window,
            "response_limit_bytes": p.response_limit_bytes,
            "attempt_timeout_seconds": p.attempt_timeout_seconds,
            "request_limit_bytes": p.request_limit_bytes,
            "credentials_required": p.credentials_required,
            "verification_date": p.verification_date,
            "contract_url": p.contract_url,
            "time_knowledge_time": p.time_knowledge_time,
            "payload_types": list(p.payload_types),
            "identity_stable_record_id": p.identity_stable_record_id,
            "units": dict(sorted(p.units.items())),
            "freshness": {
                "cadence": p.freshness.cadence,
                "reference_time": p.freshness.reference_time,
                **(
                    {"valid_for_seconds": p.freshness.valid_for_seconds}
                    if p.freshness.valid_for_seconds is not None
                    else {}
                ),
            }
            if p.freshness is not None
            else None,
            "fixture_provenance_source": p.fixture_provenance_source,
            "fixture_files": list(p.fixture_files),
        }
        snapshot = {"provider_id": p.id, "snapshot": payload, "hash": canonical_digest(payload)}
        snapshots.append(snapshot)
    return snapshots


def _feed_config_snapshot(cfg: AppConfig) -> dict[str, Any]:
    """Canonical redacted resolved Feed-configuration snapshot + hash."""
    payload = {
        "name": cfg.name,
        "feed": {
            "bootstrap_lookback_hours": cfg.feed.bootstrap_lookback_hours,
            "gap_threshold_hours": cfg.feed.gap_threshold_hours,
            "pre_commit_deadline_seconds": cfg.feed.pre_commit_deadline_seconds,
            "commit_reserve_seconds": cfg.feed.commit_reserve_seconds,
            "global_concurrency": cfg.feed.global_concurrency,
            "per_host_concurrency": cfg.feed.per_host_concurrency,
            "http_attempt_timeout_seconds": cfg.feed.http_attempt_timeout_seconds,
            "max_attempts": cfg.feed.max_attempts,
            "max_decompressed_response_bytes": cfg.feed.max_decompressed_response_bytes,
            "max_items_per_provider": cfg.feed.max_items_per_provider,
            "max_title_code_points": cfg.feed.max_title_code_points,
            "max_snippet_code_points": cfg.feed.max_snippet_code_points,
            "max_url_characters": cfg.feed.max_url_characters,
            "max_serialized_feed_bytes": cfg.feed.max_serialized_feed_bytes,
            "lock_timeout_seconds": cfg.feed.lock_timeout_seconds,
        },
        "coverage": [
            {
                "group": r.group,
                "members": list(r.members),
                "minimum": r.minimum,
                "capability": r.capability,
                "optional": r.optional,
            }
            for r in cfg.coverage.rows
        ],
        "watched_companies": [
            {
                "cik": company.cik,
                "name": company.name,
                "tickers": sorted(company.tickers),
            }
            for company in sorted(cfg.watched_companies, key=lambda company: company.cik)
        ],
    }
    return {"snapshot": payload, "hash": canonical_digest(payload)}


def _build_feed(
    *,
    cfg,
    plan,
    started_at,
    completed_at,
    outcomes,
    items,
    status,
    warnings,
    now_fn: Callable[[], datetime],
) -> dict[str, Any]:
    """Assemble the Feed envelope from observed lifecycle instants.

    ``started_at`` is the real collection-start observation, ``completed_at``
    is captured after all provider work reached a terminal/fenced state, and
    ``generated_at`` is captured here at the final envelope-generation
    boundary before identity fields are attached. No offset or copied
    timestamps are synthesized.
    """
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    feed_config = _feed_config_snapshot(cfg)
    feed_schema = _schema_descriptor("feed.schema.json")
    planned_provider_ids = set(outcomes)
    provider_contracts = [
        entry
        for entry in _provider_contract_snapshots(cfg, include_disabled=True)
        if entry["provider_id"] in planned_provider_ids
    ]
    generated_at = now_fn()
    coverage_gap = None
    if plan.gap_warning:
        coverage_gap = {
            "uncovered_start": plan.gap_warning[0],
            "uncovered_end": plan.gap_warning[1],
        }
    serialized_outcomes: list[dict[str, Any]] = []
    coverage_groups = _coverage_groups_by_provider(cfg)
    for outcome in ordered_outcomes(outcomes):
        outcome.affected_coverage_groups = coverage_groups.get(outcome.provider_id, ())
        value = outcome.to_dict()
        if "freshness" not in value:
            raise FeedExecutionError(
                f"missing freshness result for provider {outcome.provider_id!r}"
            )
        serialized_outcomes.append(value)

    feed = {
        "schema_version": SUPPORTED_BUNDLE_MAJOR,
        "run_id": "",  # recomputed below
        "window": {"start": plan.window_start, "end": plan.evidence_cutoff_at},
        "collection_started_at": fmt_utc(started_at),
        "evidence_cutoff_at": plan.evidence_cutoff_at,
        "collection_completed_at": fmt_utc(completed_at),
        "generated_at": fmt_utc(generated_at),
        "provider_outcomes": serialized_outcomes,
        "producer": build_fingerprint_to_dict(build),
        "feed_config": feed_config,
        "feed_schema": feed_schema,
        "provider_contracts": provider_contracts,
        "git": None,
        "content_digest": "0" * 64,
        "items": items,
        "pipeline": {
            "status": status,
            "warnings": warnings,
            "coverage_gap": coverage_gap,
        },
    }
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return feed


def _build_parser() -> argparse.ArgumentParser:
    """Minimal internal Feed entry used by the Agent/Skill (no public CLI)."""
    parser = argparse.ArgumentParser(
        prog="follow-the-money-feed",
        description="Collect and publish the evidence-only Feed (deterministic, credential-free).",
    )
    parser.add_argument(
        "--config", default=None, help="Explicit config file path (default: repo default)."
    )
    parser.add_argument("--output-root", default=None, help="Explicit Feed product root.")
    parser.add_argument("--runtime-state-root", default=None, help="Explicit runtime-state root.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate and report without publishing."
    )
    parser.add_argument(
        "--cutoff", default=None, help="Fixture: explicit ISO-8601 evidence cutoff."
    )
    parser.add_argument(
        "--window-start", default=None, help="Fixture: explicit ISO-8601 window start."
    )
    parser.add_argument(
        "--status-file", default=None, help="Write machine-readable status JSON here."
    )
    return parser


def _parse_cli_datetime(value: str, option: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FeedInputError(f"{option} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise FeedInputError(f"{option} must include a timezone")
    return parsed


def main(argv: list[str] | None = None) -> int:
    """Run one Feed collection. Exit contract: 0 healthy/degraded success;
    1 generation/publication failure; 2 usage/config/startup-capability error."""
    import sys

    try:
        args = _build_parser().parse_args(argv)
        cutoff = _parse_cli_datetime(args.cutoff, "--cutoff") if args.cutoff else None
        if args.window_start:
            window_start = _parse_cli_datetime(args.window_start, "--window-start")
            if cutoff is not None and window_start >= cutoff:
                raise FeedInputError("--window-start must precede --cutoff")
        result = run_feed(
            config_path=args.config,
            output_root=args.output_root,
            runtime_state_root=args.runtime_state_root,
            dry_run=args.dry_run,
            cutoff=cutoff,
            window_start=args.window_start,
        )
    except FeedInputError as exc:
        print(f"follow-the-money-feed: {exc}", file=sys.stderr)
        return 2
    except FeedExecutionError as exc:
        print(f"follow-the-money-feed: {exc}", file=sys.stderr)
        return 1
    if args.status_file:
        status = {"status": result.status, "warnings": result.warnings}
        if result.feed is not None and result.status in ("failure", "degraded"):
            provider_outcomes = result.feed.get("provider_outcomes")
            if isinstance(provider_outcomes, list):
                status["provider_outcomes"] = provider_outcomes
        if result.feed is not None and result.status in ("healthy", "degraded"):
            status.update(
                {
                    "run_id": result.feed["run_id"],
                    "evidence_cutoff_at": result.feed["evidence_cutoff_at"],
                    "manifest_relative_path": "feed-manifest.json",
                    "superseded_relative_paths": list(result.superseded_paths),
                }
            )
        try:
            Path(args.status_file).write_text(json.dumps(status), encoding="utf-8")
        except OSError as exc:
            print(f"follow-the-money-feed: {exc}", file=sys.stderr)
            return 1
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if result.feed is not None and args.dry_run and result.status != "failure":
        print(
            json.dumps(
                result.bundle.manifest if result.bundle else result.feed,
                ensure_ascii=False,
                indent=2,
            )[:2000]
        )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
