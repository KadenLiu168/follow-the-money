"""Per-send Provider transport boundary tests (ECO-124 Task 1.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.config.model import FetchRule
from follow_the_money.providers.http import FetchError, bounded_fetch
from follow_the_money.providers.manifest import load_manifest, manifest_to_provider_entry
from follow_the_money.providers.rate import RateRegistry, RateStateError
from follow_the_money.providers.session import ManagedProviderClient

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)
RULE = FetchRule("example.gov", False, (443,))


class Response:
    def __init__(self, status=200, *, url="https://example.gov/resource", headers=None, body=b"ok"):
        self.status_code = status
        self.url = url
        self.headers = headers or {}
        self.content = body
        self.body_bytes = body


class Transport:
    def __init__(self, responses=(), error=None):
        self.responses = list(responses)
        self.error = error
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error is not None:
            error, self.error = self.error, None
            raise error
        if not self.responses:
            return Response(url=url)
        response = self.responses.pop(0)
        response.url = response.url or url
        return response

    def close(self):
        self.closed = True


class Gate:
    def __init__(self, *, fail=None):
        self.calls = 0
        self.fail = fail

    def acquire(self, **_kwargs):
        self.calls += 1
        if self.fail is not None:
            raise self.fail

    def release(self):
        pass


def provider():
    return manifest_to_provider_entry(load_manifest("sec_edgar"))


def rate_for(tmp_path, p, *, now=NOW):
    registry = RateRegistry(tmp_path)
    registry.ensure_registry(now=lambda: now)
    policy = p.rate_policy
    assert policy is not None
    registry.initialize_scope(
        policy.scope_id,
        policy.capacity,
        policy.refill_period_seconds,
        0,
        now=lambda: now,
    )
    return registry


def client_for(tmp_path, transport, *, now_fn=lambda: NOW, deadline_at=1000, **kwargs):
    p = provider()
    rate = rate_for(tmp_path, p, now=now_fn())
    return ManagedProviderClient(
        p,
        rate=rate,
        transport=transport,
        now_fn=now_fn,
        monotonic_now=lambda: 0.0,
        deadline_at=deadline_at,
        **kwargs,
    )


def test_two_sends_have_two_debits_and_reconciliations(tmp_path, monkeypatch):
    transport = Transport(
        [Response(url="https://example.gov/a"), Response(url="https://example.gov/b")]
    )
    p = provider()
    registry = rate_for(tmp_path, p)
    counts = {"debit": 0, "reconcile": 0}
    debit = registry.debit_and_cooldown
    reconcile = registry.reconcile

    def counted_debit(*args, **kwargs):
        counts["debit"] += 1
        return debit(*args, **kwargs)

    def counted_reconcile(*args, **kwargs):
        counts["reconcile"] += 1
        return reconcile(*args, **kwargs)

    monkeypatch.setattr(registry, "debit_and_cooldown", counted_debit)
    monkeypatch.setattr(registry, "reconcile", counted_reconcile)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    client.get("https://data.sec.gov/a", follow_redirects=False)
    client.get("https://data.sec.gov/b", follow_redirects=False)
    state = registry.recover_or_load(p.rate_policy.scope_id)
    assert counts == {"debit": 2, "reconcile": 2}
    assert state.tokens == "8"


def test_deadline_between_sends_does_not_dispatch_or_debit_second_send(tmp_path):
    clock = {"value": 0.0}
    transport = Transport(
        [Response(url="https://data.sec.gov/a"), Response(url="https://data.sec.gov/b")]
    )
    p = provider()
    registry = rate_for(tmp_path, p)

    def monotonic():
        return clock["value"]

    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=monotonic,
        deadline_at=1.0,
    )
    client.get("https://data.sec.gov/a", follow_redirects=False)
    clock["value"] = 1.0
    with pytest.raises(FetchError, match="deadline"):
        client.get("https://data.sec.gov/b", follow_redirects=False)
    assert [call[0] for call in transport.calls] == ["https://data.sec.gov/a"]
    assert registry.recover_or_load(p.rate_policy.scope_id).tokens == "9"


def test_global_and_target_host_gates_are_admitted_for_each_send(tmp_path):
    transport = Transport(
        [Response(url="https://data.sec.gov/a"), Response(url="https://data.sec.gov/b")]
    )
    global_gate = Gate()
    host_gate = Gate()
    p = provider()
    registry = rate_for(tmp_path, p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        global_semaphore=global_gate,
        host_semaphores={"data.sec.gov:443": host_gate},
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    client.get("https://data.sec.gov/a", follow_redirects=False)
    client.get("https://data.sec.gov/b", follow_redirects=False)
    assert global_gate.calls == 2
    assert host_gate.calls == 2


@pytest.mark.parametrize("retry_after", ["17", "Tue, 11 Aug 2026 00:20:17 GMT"])
def test_retry_after_is_reconciled_once_with_injected_clock(tmp_path, retry_after):
    transport = Transport(
        [Response(429, url="https://data.sec.gov/a", headers={"retry-after": retry_after})]
    )
    p = provider()
    registry = rate_for(tmp_path, p)
    counts = {"reconcile": 0}
    original = registry.reconcile

    def counted(*args, **kwargs):
        counts["reconcile"] += 1
        return original(*args, **kwargs)

    registry.reconcile = counted
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    with pytest.raises(FetchError) as info:
        bounded_fetch(
            client,
            "https://data.sec.gov/a",
            fetch_rules=p.fetch_hosts,
            redirect_rules=p.redirect_hosts,
            now_fn=lambda: NOW,
        )
    error = info.value
    assert error.status_code == 429
    assert error.retry_after_seconds == 17
    assert counts["reconcile"] == 1
    assert client.last_response_at == NOW


def test_transport_failure_reconciles_after_dispatch(tmp_path):
    transport = Transport(error=ConnectionError("reset"))
    p = provider()
    registry = rate_for(tmp_path, p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    with pytest.raises(FetchError) as info:
        client.get("https://data.sec.gov/a", follow_redirects=False)
    assert info.value.retryable
    assert registry.recover_or_load(p.rate_policy.scope_id).tokens == "9"


def test_confirmed_pre_send_gate_failure_refunds_debit(tmp_path):
    p = provider()
    registry = rate_for(tmp_path, p)
    gate = Gate(fail=FetchError("gate closed"))
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=Transport(),
        global_semaphore=gate,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    with pytest.raises(FetchError, match="gate closed"):
        client.get("https://data.sec.gov/a", follow_redirects=False)
    assert registry.recover_or_load(p.rate_policy.scope_id).tokens == "10"


def test_redirects_are_manual_bounded_and_each_hop_is_a_send(tmp_path):
    transport = Transport(
        [
            Response(302, url="https://data.sec.gov/a", headers={"Location": "/b"}),
            Response(200, url="https://data.sec.gov/b"),
        ]
    )
    p = provider()
    registry = rate_for(tmp_path, p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    result = client.get("https://data.sec.gov/a")
    assert result.status_code == 200
    assert [url for url, _ in transport.calls] == [
        "https://data.sec.gov/a",
        "https://data.sec.gov/b",
    ]
    assert registry.recover_or_load(p.rate_policy.scope_id).tokens == "8"
    assert all(kwargs["follow_redirects"] is False for _, kwargs in transport.calls)


@pytest.mark.parametrize("location", ["https://evil.example/b", "https://data.sec.gov/a#fragment"])
def test_unsafe_redirect_target_is_not_sent(tmp_path, location):
    transport = Transport(
        [Response(302, url="https://data.sec.gov/a", headers={"Location": location})]
    )
    p = provider()
    registry = rate_for(tmp_path, p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    with pytest.raises(FetchError):
        client.get("https://data.sec.gov/a")
    assert len(transport.calls) == 1


def test_cyclic_and_unbounded_redirects_fail_closed(tmp_path):
    cycle = Transport([Response(302, url="https://data.sec.gov/a", headers={"Location": "/a"})])
    p = provider()
    registry = rate_for(tmp_path / "cycle", p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=cycle,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    with pytest.raises(FetchError, match="cycle"):
        client.get("https://data.sec.gov/a")
    assert len(cycle.calls) == 1

    responses = [
        Response(302, url=f"https://data.sec.gov/{i}", headers={"Location": f"/{i + 1}"})
        for i in range(7)
    ]
    unbounded = Transport(responses)
    registry = rate_for(tmp_path / "limit", p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=unbounded,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    with pytest.raises(FetchError, match="limit"):
        client.get("https://data.sec.gov/0")
    assert len(unbounded.calls) == 6


def test_bounded_fetch_preserves_typed_errors_and_rate_state_errors():
    typed = FetchError(
        "typed", status_code=403, retry_after_seconds=3, retryable=False, acquisition_progress=True
    )

    class Typed:
        def get(self, *_args, **_kwargs):
            raise typed

    with pytest.raises(FetchError) as info:
        bounded_fetch(Typed(), "https://example.gov/a", fetch_rules=(RULE,), redirect_rules=(RULE,))
    assert info.value is typed
    assert info.value.status_code == 403
    assert info.value.acquisition_progress

    class Broken:
        def get(self, *_args, **_kwargs):
            raise RateStateError("durable rate state failed")

    with pytest.raises(RateStateError, match="durable"):
        bounded_fetch(
            Broken(), "https://example.gov/a", fetch_rules=(RULE,), redirect_rules=(RULE,)
        )


def test_reconcile_failure_inside_managed_send_is_a_hard_rate_state_error(tmp_path):
    # A durable reconciliation failure must surface as RateStateError, perform
    # exactly one reconciliation attempt, and never refund the debit as if the
    # send had not been dispatched.
    p = provider()
    registry = rate_for(tmp_path, p)
    calls = {"reconcile": 0, "refund": 0}
    original_refund = registry.refund

    def failing_reconcile(state, **kwargs):
        calls["reconcile"] += 1
        raise RateStateError("provider unavailable during reconcile")

    def counting_refund(state, **kwargs):
        calls["refund"] += 1
        return original_refund(state, **kwargs)

    registry.reconcile = failing_reconcile
    registry.refund = counting_refund
    transport = Transport([Response(200, url="https://data.sec.gov/a")])
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=transport,
        now_fn=lambda: NOW,
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )

    with pytest.raises(RateStateError, match="during reconcile"):
        client.get("https://data.sec.gov/a", follow_redirects=False)

    assert calls == {"reconcile": 1, "refund": 0}
    assert len(transport.calls) == 1


def test_last_concrete_response_and_successful_resource_progress_survive_later_failure(tmp_path):
    clock = {"now": NOW}
    responses = Transport([Response(200, url="https://data.sec.gov/a")])
    p = provider()
    registry = rate_for(tmp_path, p)
    client = ManagedProviderClient(
        p,
        rate=registry,
        transport=responses,
        now_fn=lambda: clock["now"],
        monotonic_now=lambda: 0.0,
        deadline_at=1000,
    )
    client.get("https://data.sec.gov/a", follow_redirects=False)
    responses.error = TimeoutError("late")
    with pytest.raises(FetchError) as info:
        bounded_fetch(
            client,
            "https://data.sec.gov/b",
            fetch_rules=p.fetch_hosts,
            redirect_rules=p.redirect_hosts,
        )
    assert client.last_response_at == NOW
    assert info.value.observed_at == NOW
    assert info.value.acquisition_progress


def test_sec_v2_send_shape_respects_the_rate_floor_and_fits_the_pre_commit_budget(tmp_path):
    """The one deterministic acquisition cost driver is SEC: one adapter per
    watched company with at most three resource GETs each. Simulate that exact
    send shape against the resolved production rate policy and budget so a
    lowered deadline, raised minimum interval, or grown watched set cannot
    silently make the Provider unacquirable, while the per-send spacing itself
    cannot be lost.
    """
    cfg = load_config(
        ROOT / "config" / "config.yaml",
        ROOT / "config" / "providers.yaml",
        manifest_root=ROOT / "providers",
        require_verified_enabled=False,
    )
    provider_entry = manifest_to_provider_entry(load_manifest("sec_edgar"))
    policy = provider_entry.rate_policy
    assert policy is not None
    sends = len(cfg.watched_companies) * 3
    assert sends > 1
    budget = cfg.feed.pre_commit_deadline_seconds - cfg.feed.commit_reserve_seconds

    class Clock:
        def __init__(self) -> None:
            self.monotonic = 0.0
            self.wall = NOW

        def sleep(self, delay: float) -> None:
            self.monotonic += delay
            self.wall += timedelta(seconds=delay)

    clock = Clock()
    registry = RateRegistry(tmp_path / "rate")
    registry.ensure_registry(now=lambda: clock.wall)
    registry.initialize_scope(
        policy.scope_id,
        policy.capacity,
        policy.refill_period_seconds,
        policy.minimum_interval_seconds,
        now=lambda: clock.wall,
    )
    transport = Transport([])
    client = ManagedProviderClient(
        provider_entry,
        rate=registry,
        transport=transport,
        now_fn=lambda: clock.wall,
        monotonic_now=lambda: clock.monotonic,
        deadline_at=budget,
        sleep_fn=clock.sleep,
    )
    for index in range(sends):
        transport.responses.append(Response(200, url=f"https://data.sec.gov/{index}"))
        client.get(f"https://data.sec.gov/{index}", follow_redirects=False)

    # Measured 2026-09-15 with the resolved policy: 24 sends -> 115.0s.
    assert clock.monotonic == (sends - 1) * policy.minimum_interval_seconds
    assert clock.monotonic < budget


def test_existing_single_request_bounded_fetch_behavior_is_unchanged():
    transport = Transport([Response(200, url="https://example.gov/a", body=b"body")])
    result = bounded_fetch(
        transport, "https://example.gov/a", fetch_rules=(RULE,), redirect_rules=(RULE,)
    )
    assert result.url == "https://example.gov/a"
    assert result.status == 200
    assert result.body_bytes == b"body"
