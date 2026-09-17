"""Managed per-send Provider HTTP boundary.

The adapter protocol remains deliberately small; this client owns the actual
wire-send lifecycle so redirects and pagination cannot bypass rate, deadline,
concurrency, host, or identity policy.
"""

from __future__ import annotations

import ipaddress
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from threading import Event, Lock
from typing import Any
from urllib.parse import urljoin, urlsplit

from ..config.model import FetchRule, ProviderEntry
from .http import FetchError, _parse_retry_after, _validate_fetch_url
from .rate import RateRegistry, RateStateError, ScopeState, eligibility_delay, refill_tokens

MAX_REDIRECT_HOPS = 5


def _host_key(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").rstrip(".").lower()
    port = parts.port or 443
    return f"{host}:{port}"


def _settle_rate_state(
    rate: RateRegistry | None,
    state: ScopeState | None,
    *,
    dispatched: bool,
    reconciled: bool,
    now: Callable[[], datetime],
) -> bool:
    if rate is None or state is None or reconciled:
        return reconciled
    if dispatched:
        rate.reconcile(state, now=now)
    else:
        rate.refund(state, now=now)
    return True


class ManagedProviderClient:
    """A narrow GET-only client with exactly one rate transition per send.

    ``transport`` is an injected httpx-compatible client in tests and is
    created by the Feed production path with redirects disabled.  The
    constructor accepts the shared process gates and deterministic clocks;
    durable scope state is still owned by ``RateRegistry``.
    """

    def __init__(
        self,
        provider: ProviderEntry,
        *,
        rate: RateRegistry | None = None,
        scope_lock: Lock | None = None,
        global_semaphore: Any | None = None,
        host_semaphores: dict[str, Any] | None = None,
        cancel_event: Event | None = None,
        deadline_at: float | None = None,
        monotonic_now: Callable[[], float] = time.monotonic,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep_fn: Callable[[float], None] = time.sleep,
        transport: Any | None = None,
        client: Any | None = None,
        max_redirect_hops: int = MAX_REDIRECT_HOPS,
    ) -> None:
        if transport is not None and client is not None:
            raise TypeError("pass only one of transport or client")
        self.provider = provider
        self.rate = rate
        self.scope_lock = scope_lock
        self.global_semaphore = global_semaphore
        self.host_semaphores = host_semaphores if host_semaphores is not None else {}
        self.cancel_event = cancel_event or Event()
        self.deadline_at = deadline_at
        self.monotonic_now = monotonic_now
        self.now_fn = now_fn
        self.sleep_fn = sleep_fn
        self.transport = transport if transport is not None else client
        self.max_redirect_hops = max_redirect_hops
        self.last_response_at: datetime | None = None
        self.successful_resource_observed = False
        self.last_response_url: str | None = None
        self._closed = False

    @property
    def response_observed_at(self) -> datetime | None:
        return self.last_response_at

    @property
    def acquisition_progress(self) -> bool:
        return self.successful_resource_observed

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        follow_redirects: bool = True,
    ) -> Any:
        """GET one resource, manually following a bounded redirect chain."""
        current_url = url
        visited = {current_url}
        for hop in range(self.max_redirect_hops + 1):
            response = self._send(
                current_url,
                headers=headers,
                timeout=timeout,
                rules=self.provider.fetch_hosts if hop == 0 else self.provider.redirect_hosts,
            )
            try:
                status = int(getattr(response, "status_code", 0))
            except (OverflowError, TypeError, ValueError) as exc:
                raise FetchError("response status is invalid", response_observed=True) from exc
            if not follow_redirects or status not in {301, 302, 303, 307, 308}:
                self._set_response_url(response, current_url)
                return response
            location = self._header(response, "location")
            if not isinstance(location, str) or not location.strip():
                self._set_response_url(response, current_url)
                return response
            target = urljoin(current_url, location.strip())
            self._validate_redirect_target(target)
            if target in visited:
                raise FetchError("redirect cycle detected", response_observed=True)
            if hop >= self.max_redirect_hops:
                raise FetchError("redirect limit exceeded", response_observed=True)
            visited.add(target)
            current_url = target
        raise FetchError("redirect limit exceeded", response_observed=True)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close = getattr(self.transport, "close", None)
        if close is not None:
            close()

    def _send(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        rules: tuple[FetchRule, ...],
    ) -> Any:
        _validate_fetch_url(url, rules, where="fetch_url")
        self._admit_deadline(timeout)
        request_headers = {
            key: value for key, value in (headers or {}).items() if key.lower() != "user-agent"
        }
        request_headers["User-Agent"] = self.provider.user_agent

        lock_acquired = False
        state = None
        dispatched = False
        reconciled = False
        global_acquired = False
        host_sem = self._host_sem(url)
        host_acquired = False
        try:
            if self.scope_lock is not None:
                self._acquire_lock(self.scope_lock)
                lock_acquired = True
            if self.rate is not None and self.provider.rate_policy is not None:
                state = self._load_rate_state()
                state = refill_tokens(state, now=self.now_fn)
                delay = eligibility_delay(state, now=self.now_fn)
                if delay > 0:
                    self._wait(delay)
                    state = self._load_rate_state()
                    state = refill_tokens(state, now=self.now_fn)
                state = self.rate.debit_and_cooldown(state, now=self.now_fn)
            if self.global_semaphore is not None:
                self._acquire_gate(self.global_semaphore)
                global_acquired = True
            if host_sem is not None:
                self._acquire_gate(host_sem)
                host_acquired = True
            self._admit_deadline(timeout)
            if self.transport is None:
                raise FetchError("managed Provider client has no transport")
            dispatched = True
            try:
                response = self.transport.get(
                    url,
                    headers=request_headers,
                    timeout=timeout,
                    follow_redirects=False,
                )
            except RateStateError:
                raise
            except Exception as exc:  # transport errors are typed once
                reconciled = _settle_rate_state(
                    self.rate,
                    state,
                    dispatched=True,
                    reconciled=reconciled,
                    now=self.now_fn,
                )
                if isinstance(exc, FetchError):
                    exc.response_observed = True
                    exc.acquisition_progress = self.successful_resource_observed
                    raise
                import httpx

                retryable = isinstance(
                    exc,
                    (
                        httpx.TimeoutException,
                        httpx.TransportError,
                        TimeoutError,
                        ConnectionError,
                        OSError,
                    ),
                )
                error = FetchError(
                    f"fetch failed for {urlsplit(url).hostname}: {exc.__class__.__name__}",
                    retryable=retryable,
                    response_observed=False,
                )
                error.acquisition_progress = self.successful_resource_observed
                raise error from exc
            observed = self.now_fn()
            self.last_response_at = observed
            self.last_response_url = str(getattr(response, "url", url) or url)
            if int(getattr(response, "status_code", 0)) in range(200, 300):
                self.successful_resource_observed = True
            retry_after = _parse_retry_after(
                self._header(response, "retry-after"), now_fn=self.now_fn
            )
            if state is not None and self.rate is not None:
                self.rate.reconcile(
                    state,
                    now=self.now_fn,
                    retry_after_seconds=retry_after,
                )
                reconciled = True
            return response
        except RateStateError:
            raise
        except FetchError as exc:
            # Errors raised before dispatch (URL/deadline/gate) refund the
            # provisional debit; post-dispatch errors reconcile exactly once.
            # Response errors are reconciled at the return boundary.
            _settle_rate_state(
                self.rate,
                state,
                dispatched=dispatched,
                reconciled=reconciled,
                now=self.now_fn,
            )
            exc.acquisition_progress = self.successful_resource_observed
            raise
        except Exception:
            _settle_rate_state(
                self.rate,
                state,
                dispatched=dispatched,
                reconciled=reconciled,
                now=self.now_fn,
            )
            raise
        finally:
            if host_acquired:
                self._release_gate(host_sem)
            if global_acquired:
                self._release_gate(self.global_semaphore)
            if lock_acquired and self.scope_lock is not None:
                self.scope_lock.release()

    def _load_rate_state(self) -> Any:
        assert self.rate is not None
        scope = self.provider.rate_policy
        assert scope is not None
        return self.rate.recover_or_load(scope.scope_id)

    def _admit_deadline(self, timeout: float | None) -> None:
        if self.cancel_event.is_set():
            raise FetchError("pre_commit_deadline_exceeded: provider request cancelled")
        if self.deadline_at is not None:
            remaining = self.deadline_at - self.monotonic_now()
            if remaining <= 0:
                raise FetchError("pre_commit_deadline_exceeded: provider request cancelled")
            if timeout is not None and timeout <= 0:
                raise FetchError("provider request timeout must be positive")
            if timeout is not None and timeout > remaining:
                raise FetchError("pre_commit_deadline_exceeded: request timeout exceeds deadline")

    def _wait(self, delay: float) -> None:
        if self.deadline_at is not None and delay >= self.deadline_at - self.monotonic_now():
            raise FetchError("rate_not_eligible_before_deadline")
        if delay > 0:
            self.sleep_fn(delay)
        self._admit_deadline(None)

    def _acquire_lock(self, lock: Lock) -> None:
        while True:
            if self.cancel_event.is_set():
                raise FetchError("pre_commit_deadline_exceeded: scope lock wait cancelled")
            timeout = 0.1
            if self.deadline_at is not None:
                remaining = self.deadline_at - self.monotonic_now()
                if remaining <= 0:
                    raise FetchError("pre_commit_deadline_exceeded: scope lock wait expired")
                timeout = min(timeout, remaining)
            if lock.acquire(timeout=timeout):
                return

    def _acquire_gate(self, gate: Any) -> None:
        acquire = gate.acquire
        try:
            acquire(
                cancel_event=self.cancel_event,
                deadline_at=self.deadline_at,
                monotonic_now=self.monotonic_now,
            )
        except TypeError:
            acquire()

    @staticmethod
    def _release_gate(gate: Any | None) -> None:
        if gate is not None:
            gate.release()

    def _host_sem(self, url: str) -> Any | None:
        key = _host_key(url)
        if key in self.host_semaphores:
            return self.host_semaphores[key]
        # Permit callers that key maps by hostname rather than host:port.
        host = urlsplit(url).hostname
        if host and host.rstrip(".").lower() in self.host_semaphores:
            return self.host_semaphores[host.rstrip(".").lower()]
        return None

    def _validate_redirect_target(self, target: str) -> None:
        try:
            parts = urlsplit(target)
            if parts.fragment or parts.username is not None or parts.password is not None:
                raise FetchError("redirect target contains forbidden authority")
            if parts.hostname:
                try:
                    ipaddress.ip_address(parts.hostname)
                except ValueError:
                    pass
                else:
                    raise FetchError("redirect target must not use an IP address")
        except ValueError as exc:
            raise FetchError("redirect target is malformed") from exc
        _validate_fetch_url(target, self.provider.redirect_hosts, where="redirect_url")

    @staticmethod
    def _header(response: Any, name: str) -> Any:
        headers = getattr(response, "headers", {})
        try:
            direct = headers.get(name) or headers.get(name.lower())
            if direct is not None:
                return direct
            return next(
                (value for key, value in headers.items() if str(key).lower() == name.lower()),
                None,
            )
        except AttributeError:
            return None

    @staticmethod
    def _set_response_url(response: Any, url: str) -> None:
        try:
            response.url = url
        except (AttributeError, TypeError):
            pass
