"""Feed orchestration and CLI wiring (task 4.4/4.8, gate 13.1).

The Feed command:

1. loads explicit config and output root (never machine-global state),
2. acquires the exclusive output-root collection lock (production path),
3. captures one fixed ``evidence_cutoff_at`` before any provider request,
4. plans the strictly advancing window from ``feeds/latest.json``,
5. runs enabled providers with the durable rate-state debit/reconcile
   lifecycle, bounded HTTP clients, global/per-host concurrency limits,
   and the 300-second pre-commit deadline + 15-second reserve,
6. normalizes/dedupes, validates the Feed schema/digest/identity,
7. publishes dated (no-replace) then latest (atomic replace) — or dry-runs.

Exit contract: 0 healthy/degraded success; 1 generation/publication failure;
2 usage/config/startup-capability errors.
"""

from __future__ import annotations

import argparse
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
from ..canonical import canonical_digest, canonical_sha256, load_canonical_json
from ..config import load_config
from ..config.load import ConfigError
from ..config.model import AppConfig
from ..feed.validate import assert_feed_identity, recompute_feed_identity, validate_feed
from ..providers.http import FetchError
from ..providers.lock import CollectionLock, CollectionLockError
from ..providers.manifest import ManifestError
from ..providers.rate import RateRegistry, RateStateError, eligibility_delay, refill_tokens
from ..schema import SchemaError
from .dedupe import deduplicate_items, deterministic_item_order
from .plan import FeedPlanError, ProviderOutcome, assess_pipeline, plan_window
from .publish import PublishError, publish_feed

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


def _default_config_path() -> Path:
    return REPO_ROOT / "config" / "config.yaml"


def _default_providers_path() -> Path:
    return REPO_ROOT / "config" / "providers.yaml"


def _load_app_config(config_path: str | None) -> AppConfig:
    cfg = config_path or str(_default_config_path())
    providers = str(_default_providers_path())
    try:
        return load_config(cfg, providers, require_verified_enabled=True)
    except ConfigError as exc:
        raise FeedInputError(str(exc)) from exc


def run_feed(
    *,
    config_path: str | None = None,
    output_root: str | None = None,
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
    the exclusive output-root collection lock, the durable rate-state
    debit/reconcile lifecycle, global 8 / per-host 2 concurrency, and the
    300-second pre-commit deadline. ``enabled_provider_ids`` overrides
    config enablement for fixtures.
    """
    from ..providers.adapters import build_registry

    now_fn = now_fn or (lambda: datetime.now(UTC))
    monotonic = monotonic_now or time.monotonic
    sleep = sleep_fn or time.sleep
    cfg = _load_app_config(config_path)
    # The 300-second pre-commit deadline anchors at command startup (before
    # lock acquisition) so lock-waiting time counts against the deadline.
    deadline_started = monotonic()
    deadline_seconds = cfg.feed.pre_commit_deadline_seconds - cfg.feed.commit_reserve_seconds
    deadline_at = deadline_started + deadline_seconds
    root = Path(output_root or cfg.output_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FeedExecutionError(f"cannot prepare output root {root}: {exc}") from exc
    latest_path = root / "latest.json"

    # Coordinate every run that can use production adapters. Fixture-injected
    # dry runs cannot send a real request and remain write-light and
    # deterministic.
    coordinates_run = not dry_run or providers_fn is None
    lock: CollectionLock | None = None
    rate: RateRegistry | None = None
    if coordinates_run:
        try:
            lock = CollectionLock(
                root,
                timeout_seconds=min(
                    cfg.feed.lock_timeout_seconds,
                    max(0.0, deadline_at - monotonic()),
                ),
                monotonic_now=monotonic,
            )
            lock.acquire()
        except CollectionLockError as exc:
            raise FeedExecutionError(str(exc)) from exc

    # Capture the fixed cutoff only after the cooperating run owns the lock.
    # This prevents lock wait time from freezing a stale planning window.
    cutoff = cutoff or now_fn()
    if cutoff.tzinfo is None:
        if lock is not None:
            lock.release()
        raise FeedInputError("cutoff must be timezone-aware")

    try:
        plan = plan_window(
            cutoff=cutoff,
            latest_path=latest_path,
            bootstrap_lookback_hours=cfg.feed.bootstrap_lookback_hours,
            gap_threshold_hours=cfg.feed.gap_threshold_hours,
            validate_latest=_validate_latest if latest_path.exists() else None,
        )
    except FeedPlanError as exc:
        if lock is not None:
            lock.release()
        raise FeedExecutionError(str(exc)) from exc

    # Durable rate-state registry is created only after planning succeeds:
    # an invalid latest makes zero writes beyond the lock file itself.
    if coordinates_run:
        try:
            rate = RateRegistry(root)
            rate.ensure_registry(now=now_fn)
        except (OSError, RateStateError) as exc:
            if lock is not None:
                lock.release()
            raise FeedExecutionError(str(exc)) from exc

    try:
        # Registry: production uses the verified-enabled manifest registry.
        if providers_fn is not None:
            registry = providers_fn()
            adapters_by_id = {
                pid: list(adapter) if isinstance(adapter, (list, tuple)) else [adapter]
                for pid, adapter in registry.items()
            }
        else:
            try:
                adapters_by_id = _production_adapters(cfg, build_registry())
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

        outcomes: dict[str, ProviderOutcome] = {}
        items: list[dict[str, Any]] = []

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
                    for rule in p.fetch_hosts:
                        host_sems.setdefault(rule.host, _Semaphore(cfg.feed.per_host_concurrency))

        def execute_adapter(pid: str, adapter: Any, outcome: ProviderOutcome) -> None:
            host = _adapter_fetch_host(pid, cfg)
            request_window = {"start": plan.window_start, "end": plan.evidence_cutoff_at}

            def request() -> Any:
                if cancel_event.is_set() or monotonic() >= deadline_at:
                    raise FetchError("pre_commit_deadline_exceeded: provider request cancelled")
                global_sem.acquire(
                    cancel_event=cancel_event,
                    deadline_at=deadline_at,
                    monotonic_now=monotonic,
                )
                host_sem = host_sems.get(host) if host is not None else None
                host_acquired = False
                try:
                    if host_sem is not None:
                        host_sem.acquire(
                            cancel_event=cancel_event,
                            deadline_at=deadline_at,
                            monotonic_now=monotonic,
                        )
                        host_acquired = True
                    try:
                        if cancel_event.is_set() or monotonic() >= deadline_at:
                            raise FetchError(
                                "pre_commit_deadline_exceeded: provider request cancelled"
                            )
                        client = _client_for(adapter)
                        with active_clients_lock:
                            if cancel_event.is_set() or monotonic() >= deadline_at:
                                close = getattr(client, "close", None)
                                if close is not None:
                                    close()
                                raise FetchError(
                                    "pre_commit_deadline_exceeded: provider request cancelled"
                                )
                            active_clients[id(client)] = client
                        try:
                            return adapter.fetch(request_window, client)
                        finally:
                            with active_clients_lock:
                                active_clients.pop(id(client), None)
                            close = getattr(client, "close", None)
                            if close is not None:
                                close()
                    finally:
                        if host_acquired and host_sem is not None:
                            host_sem.release()
                finally:
                    global_sem.release()

            scope_lock = scope_locks.get(_provider_scope(pid, cfg))
            if scope_lock is None:
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
            else:
                acquired = False
                while not acquired:
                    if cancel_event.is_set() or monotonic() >= deadline_at:
                        outcome.state = "partial" if outcome.accepted else "failed"
                        outcome.error = "pre_commit_deadline_exceeded: scope lock wait cancelled"
                        outcome.execution_failure = True
                        return
                    remaining = max(0.0, deadline_at - monotonic())
                    acquired = scope_lock.acquire(timeout=min(0.1, remaining))
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
                    scope_lock.release()

        def execute_one(pid: str) -> None:
            if monotonic() - deadline_started > deadline_seconds:
                outcome = ProviderOutcome(provider_id=pid, state="skipped")
                outcome.error = "pre_commit_deadline_exceeded"
                outcome.execution_failure = True
                outcomes[pid] = outcome
                return
            outcome = ProviderOutcome(provider_id=pid)
            outcomes[pid] = outcome
            for adapter in adapters_by_id[pid]:
                execute_adapter(pid, adapter, outcome)
                if outcome.state == "failed":
                    break  # provider-level failure: no further attempts

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

        # Dedup + deterministic order.
        deduped, _dropped = deduplicate_items(items)
        ordered = deterministic_item_order(deduped)

        status, warnings = assess_pipeline(
            config=cfg, outcomes=outcomes, total_accepted=len(ordered)
        )
        if plan.gap_warning:
            warnings.append(f"coverage gap: {plan.gap_warning[0]} to {plan.gap_warning[1]}")

        collected = now_fn()
        feed = _build_feed(
            cfg=cfg,
            plan=plan,
            cutoff=cutoff,
            collected_at=collected,
            outcomes=outcomes,
            items=ordered,
            status=status,
            warnings=warnings,
        )

        # Validate before publication.
        try:
            validate_feed(feed)
            assert_feed_identity(feed)
        except SchemaError as exc:
            raise FeedExecutionError(str(exc)) from exc

        if status == "failure":
            return FeedRunResult(
                status=status,
                exit_code=1,
                feed=feed,
                warnings=warnings,
                message="no accepted evidence; Feed was not admitted for publication",
            )

        if dry_run:
            return FeedRunResult(status=status, exit_code=0, feed=feed, warnings=warnings)

        feed_bytes = json.dumps(feed, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        try:
            publication = publish_feed(
                output_root=root,
                cutoff=cutoff,
                run_id=feed["run_id"],
                feed_bytes=feed_bytes,
                latest_bytes=feed_bytes,
                monotonic_now=monotonic,
                deadline_at=deadline_at,
            )
        except (OSError, PublishError) as exc:
            raise FeedExecutionError(str(exc)) from exc
        if publication.commit_durability_unknown:
            raise FeedExecutionError(
                "commit_durability_unknown: Feed publication durability is unknown"
            )
        if not publication.latest_replaced:
            raise FeedExecutionError(
                "Feed dated artifact committed but latest.json was not updated"
            )

        code = 0 if status in ("healthy", "degraded") else 1
        return FeedRunResult(status=status, exit_code=code, feed=feed, warnings=warnings)
    finally:
        if lock is not None:
            lock.release()


def _production_adapters(cfg: AppConfig, registry: Any) -> dict[str, list[Any]]:
    """Build per-provider adapter lists for the production registry.

    The Yahoo-compatible contract fans out over the 13 configured dashboard
    roles; every other enabled provider contributes one adapter instance.
    """
    from ..providers.adapters import SecEdgarAdapter, YahooMarketAdapter

    adapters: dict[str, list[Any]] = {}
    for p in cfg.providers:
        if not p.enabled:
            continue
        if p.id == "yahoo_market":
            adapters[p.id] = [
                YahooMarketAdapter(instrument=r.instrument, role_id=r.id, unit=r.unit)
                for r in cfg.roles
            ]
        elif p.id == "sec_edgar":
            adapters[p.id] = [
                SecEdgarAdapter(
                    watched_ciks=tuple(company.cik for company in cfg.watched_companies)
                )
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
    """One bounded fetch + normalize with durable rate debit/reconcile."""

    window = {"start": plan.window_start, "end": plan.evidence_cutoff_at}
    scope = _provider_scope(outcome.provider_id, cfg)
    max_attempts = max(1, int(cfg.feed.max_attempts))
    empty_valid_for_window = _provider_empty_valid_for_window(outcome.provider_id, cfg)

    def mark_incomplete(message: str) -> None:
        outcome.state = "partial" if outcome.accepted else "failed"
        outcome.error = message

    def reject_late_result(state) -> None:
        mark_incomplete("pre_commit_deadline_exceeded: late provider result ignored")
        outcome.execution_failure = True
        if rate is not None and scope is not None and state is not None:
            rate.reconcile(state, now=now_fn)

    def deadline_expired() -> bool:
        return (
            cancel_event is not None and cancel_event.is_set()
        ) or monotonic_now() >= deadline_at

    for attempt in range(max_attempts):
        if deadline_expired():
            mark_incomplete("pre_commit_deadline_exceeded: provider work cancelled")
            outcome.execution_failure = True
            return
        state = None
        if rate is not None and scope is not None:
            state = _ensure_scope_state(rate, scope, cfg, now_fn)
            state = refill_tokens(state, now=now_fn)
            delay = eligibility_delay(state, now=now_fn)
            if delay > 0:
                if delay >= deadline_at - monotonic_now():
                    mark_incomplete("rate_not_eligible_before_deadline")
                    outcome.execution_failure = True
                    return
                sleep_fn(delay)
                state = _ensure_scope_state(rate, scope, cfg, now_fn)
                state = refill_tokens(state, now=now_fn)
            state = rate.debit_and_cooldown(state, now=now_fn)

        outcome.attempted += 1
        request_started = False
        try:
            request_started = True
            raw = request_fn()
            outcome.fetched += 1
            outcome.retrieved_at = now_fn().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            if deadline_expired():
                reject_late_result(state)
                return
            normalized = list(adapter.normalize(raw, window))
            accepted_items = []
            rejected = 0
            for item in normalized:
                if item.get("source", {}).get("url"):
                    accepted_items.append(item)
                else:
                    rejected += 1
            if deadline_expired():
                reject_late_result(state)
                return
            items.extend(accepted_items)
            accepted = len(accepted_items)
            outcome.accepted += accepted
            outcome.rejected += rejected
            if not accepted and not rejected and not empty_valid_for_window:
                outcome.non_permitted_empty_observed = True
            if rejected:
                outcome.state = "partial" if outcome.accepted else "failed"
            elif accepted:
                if outcome.state == "partial" or outcome.non_permitted_empty_observed:
                    outcome.state = "partial"
                else:
                    outcome.state = "healthy"
            elif outcome.accepted:
                if empty_valid_for_window and outcome.state != "partial":
                    outcome.state = "healthy"
                else:
                    outcome.state = "partial"
                    outcome.error = "non-permitted empty result after accepted evidence"
            else:
                outcome.state = "empty"
            if rate is not None and scope is not None and state is not None:
                rate.reconcile(state, now=now_fn)
            return
        except FetchError as exc:
            mark_incomplete(str(exc))
            if deadline_expired():
                outcome.execution_failure = True
            if rate is not None and scope is not None and state is not None:
                rate.reconcile(state, now=now_fn, retry_after_seconds=exc.retry_after_seconds)
            if deadline_expired():
                outcome.error = f"pre_commit_deadline_exceeded: {exc}"
                return
            if exc.retryable and attempt + 1 < max_attempts:
                delay = max(
                    float(exc.retry_after_seconds or 0),
                    float(state.minimum_interval_seconds) if state is not None else 0.0,
                )
                remaining = deadline_at - monotonic_now()
                if delay > remaining:
                    outcome.error = f"{exc}; retry_not_admitted_before_deadline"
                    outcome.execution_failure = True
                    return
                if delay > 0:
                    sleep_fn(delay)
                if monotonic_now() >= deadline_at:
                    outcome.error = f"{exc}; retry_not_admitted_before_deadline"
                    outcome.execution_failure = True
                    return
                continue
            return
        except RateStateError:
            raise
        except Exception as exc:  # noqa: BLE001 - orchestration boundary
            mark_incomplete(str(exc))
            if rate is not None and scope is not None and state is not None:
                if request_started:
                    rate.reconcile(state, now=now_fn)
                else:
                    rate.refund(state, now=now_fn)
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


_client_cache: dict[str, Any] = {}


def _client_for(adapter: Any) -> Any:
    import httpx

    return httpx.Client(timeout=20.0, follow_redirects=True)


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

    def __exit__(self, *exc: object) -> None:
        self.release()

    def release(self) -> None:
        self._sem.release()


def _validate_latest(path: Path) -> dict[str, Any]:
    """Validate a present latest Feed; raises on any integrity failure."""
    try:
        raw = path.read_bytes()
        feed = load_canonical_json(raw, where="latest.json")
        validate_feed(feed)
        assert_feed_identity(feed)
        return feed
    except Exception as exc:
        raise FeedPlanError(f"invalid_latest_integrity: {exc}") from exc


def _schema_descriptor(rel: str) -> dict[str, str]:
    path = SCHEMA_ROOT / rel
    try:
        sha = canonical_sha256(path.read_bytes())
    except OSError as exc:
        raise FeedExecutionError(f"cannot read schema {rel}: {exc}") from exc
    return {"path": f"schemas/{rel}", "sha256": sha}


def _provider_contract_snapshots(cfg: AppConfig) -> list[dict[str, Any]]:
    """Sorted canonical redacted non-secret runtime-contract snapshots for
    every enabled provider (design section 4)."""
    snapshots: list[dict[str, Any]] = []
    for p in sorted(cfg.providers, key=lambda x: x.id):
        if not p.enabled:
            continue
        payload = {
            "provider_id": p.id,
            "group": p.group,
            "source_family_id": p.source_family_id,
            "tier": p.tier,
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
            "credentials_required": p.credentials_required,
            "verification_date": p.verification_date,
            "contract_url": p.contract_url,
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
            "calendar_horizon_hours": cfg.feed.calendar_horizon_hours,
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
            "max_observations_per_instrument": cfg.feed.max_observations_per_instrument,
            "max_serialized_feed_bytes": cfg.feed.max_serialized_feed_bytes,
        },
        "coverage": [
            {
                "group": r.group,
                "members": list(r.members),
                "minimum": r.minimum,
                "capability": r.capability,
            }
            for r in cfg.coverage.rows
        ],
    }
    return {"snapshot": payload, "hash": canonical_digest(payload)}


def _build_feed(
    *, cfg, plan, cutoff, collected_at, outcomes, items, status, warnings
) -> dict[str, Any]:
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    started_at = cutoff - timedelta(seconds=30)  # collection began before cutoff capture
    completed = max(collected_at, cutoff)
    feed_config = _feed_config_snapshot(cfg)
    feed_schema = _schema_descriptor("feed.schema.json")
    provider_contracts = _provider_contract_snapshots(cfg)
    feed = {
        "schema_version": 1,
        "run_id": "",  # recomputed below
        "window": {"start": plan.window_start, "end": plan.evidence_cutoff_at},
        "collection_started_at": started_at.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "evidence_cutoff_at": plan.evidence_cutoff_at,
        "collection_completed_at": completed.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "generated_at": completed.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "provider_outcomes": [o.to_dict() for o in outcomes.values()],
        "producer": build_fingerprint_to_dict(build),
        "feed_config": feed_config,
        "feed_schema": feed_schema,
        "provider_contracts": provider_contracts,
        "git": None,
        "content_digest": "0" * 64,
        "items": items,
        "pipeline": {"status": status, "warnings": warnings, "coverage_gap": None},
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
    parser.add_argument(
        "--output-root", default=None, help="Explicit output root for feeds/ and rate state."
    )
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
        if result.feed is not None and result.status in ("healthy", "degraded"):
            from datetime import datetime
            from zoneinfo import ZoneInfo

            cutoff = datetime.fromisoformat(result.feed["evidence_cutoff_at"])
            asia_date = cutoff.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
            status.update(
                {
                    "run_id": result.feed["run_id"],
                    "evidence_cutoff_at": result.feed["evidence_cutoff_at"],
                    "dated_relative_path": f"daily/{asia_date}/{result.feed['run_id']}.json",
                    "latest_relative_path": "latest.json",
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
        print(json.dumps(result.feed, ensure_ascii=False, indent=2)[:2000])
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
