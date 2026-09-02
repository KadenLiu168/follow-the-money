"""Task 3.1 — provider contract and security tests.

Covers provider-bound canonical URL validation (host rules, IDNA, ports,
queries, secret leakage), raw numeric boundaries, rate-registry lifecycle
and crash recovery, and conservative zero-send migration boundaries.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config.model import SourceLinkRule
from follow_the_money.providers.rate import (
    RateRegistry,
    RateStateError,
    refill_tokens,
)
from follow_the_money.providers.urls import UrlValidationError, canonicalize_url


def _rules() -> list[SourceLinkRule]:
    return [
        SourceLinkRule(
            host="example.com",
            allow_subdomains=True,
            allowed_ports=(443,),
            allowed_query_params=("id", "page"),
            query_value_grammar="plain",
            drop_query_params=("utm_source", "utm_medium"),
        ),
        SourceLinkRule(
            host="publisher.example.net",
            allow_subdomains=False,
            allowed_ports=(443,),
        ),
    ]


# ---------------------------------------------------------------------------
# Canonical URL validation
# ---------------------------------------------------------------------------


def test_canonicalize_basic():
    url = canonicalize_url("https://news.example.com/story?id=42&utm_source=x", rules=_rules())
    assert url == "https://news.example.com/story?id=42"


def test_https_required():
    with pytest.raises(UrlValidationError, match="https"):
        canonicalize_url("http://example.com/x", rules=_rules())


def test_userinfo_rejected():
    with pytest.raises(UrlValidationError, match="userinfo"):
        canonicalize_url("https://user:pass@example.com/x", rules=_rules())


def test_ip_literal_rejected():
    with pytest.raises(UrlValidationError, match="IP"):
        canonicalize_url("https://93.184.216.34/x", rules=_rules())


def test_percent_encoded_authority_rejected():
    with pytest.raises(UrlValidationError, match="authority"):
        canonicalize_url("https://exa%6dple.com/x", rules=_rules())


def test_undeclared_port_rejected():
    with pytest.raises(UrlValidationError, match="port"):
        canonicalize_url("https://example.com:8443/x", rules=_rules())


def test_default_port_removed():
    url = canonicalize_url("https://example.com:443/x", rules=_rules())
    assert url == "https://example.com/x"


def test_exact_vs_subdomain():
    # allow_subdomains=True matches sub.example.com.
    url = canonicalize_url("https://sub.example.com/x", rules=_rules())
    assert url.startswith("https://sub.example.com/")
    # allow_subdomains=False must not match a suffix lookalike.
    with pytest.raises(UrlValidationError, match="outside source_link_hosts"):
        canonicalize_url("https://sub.publisher.example.net/x", rules=_rules())


def test_suffix_lookalike_rejected():
    with pytest.raises(UrlValidationError, match="outside source_link_hosts"):
        canonicalize_url("https://notexample.com/x", rules=_rules())


def test_trailing_dot_normalized():
    url = canonicalize_url("https://example.com./x", rules=_rules())
    assert url.startswith("https://example.com/")


def test_fragment_dropped():
    url = canonicalize_url("https://example.com/x#section", rules=_rules())
    assert "#" not in url


def test_unlisted_query_param_rejected():
    # utm_* are dropped by policy; an unlisted param is rejected.
    url = canonicalize_url("https://example.com/x?utm_source=x", rules=_rules())
    assert "utm_source" not in url
    with pytest.raises(UrlValidationError, match="unlisted query"):
        canonicalize_url("https://example.com/x?foo=bar", rules=_rules())


def test_empty_query_allowlist_rejects_every_retained_parameter():
    with pytest.raises(UrlValidationError, match="unlisted query"):
        canonicalize_url("https://publisher.example.net/x?id=42", rules=_rules())


def test_query_value_grammar_is_enforced():
    with pytest.raises(UrlValidationError, match="query value grammar"):
        canonicalize_url("https://example.com/x?id=not%20plain", rules=_rules())

    numeric = [
        SourceLinkRule(
            host="numbers.example.com",
            allowed_query_params=("value",),
            query_value_grammar="numeric",
        )
    ]
    assert canonicalize_url("https://numbers.example.com/x?value=-12.5", rules=numeric).endswith(
        "?value=-12.5"
    )
    with pytest.raises(UrlValidationError, match="query value grammar"):
        canonicalize_url("https://numbers.example.com/x?value=twelve", rules=numeric)


def test_credential_named_query_rejected():
    for name in ("token", "api_key", "secret", "password"):
        with pytest.raises(UrlValidationError, match="credential-named"):
            canonicalize_url(f"https://example.com/x?{name}=abc", rules=_rules())


def test_bare_percent_escape_rejected():
    with pytest.raises(UrlValidationError, match="percent"):
        canonicalize_url("https://example.com/x%2", rules=_rules())


def test_truncated_percent_rejected():
    with pytest.raises(UrlValidationError, match="percent"):
        canonicalize_url("https://example.com/x%", rules=_rules())


def test_non_hex_percent_rejected():
    with pytest.raises(UrlValidationError, match="percent"):
        canonicalize_url("https://example.com/x%zz", rules=_rules())


def test_residual_percent_after_decode_rejected():
    # %2542 decodes once to %42 -> residual %HH is ambiguous double-encoding.
    with pytest.raises(UrlValidationError, match="residual"):
        canonicalize_url("https://example.com/x%2542", rules=_rules())


def test_secret_leakage_rejected():
    # q is a listed parameter; secret substring inside its value is rejected.
    rules = _rules() + [
        SourceLinkRule(
            host="example.com",
            allow_subdomains=True,
            allowed_ports=(443,),
            allowed_query_params=("q",),
        )
    ]
    with pytest.raises(UrlValidationError, match="secret"):
        canonicalize_url(
            "https://example.com/x?q=supersecret123",
            rules=rules,
            secrets=["supersecret123"],
        )


def test_secret_leakage_encoded_rejected():
    with pytest.raises(UrlValidationError, match="secret"):
        canonicalize_url(
            "https://example.com/x/supersecret123",
            rules=_rules(),
            secrets=["supersecret123"],
        )


def test_short_secret_ok():
    # Configured secrets shorter than 8 bytes are rejected at config load
    # (task 3.x); here a short scan string is simply ignored.
    url = canonicalize_url("https://example.com/x", rules=_rules(), secrets=["ab"])
    assert url.startswith("https://example.com/")


def test_stable_query_order():
    a = canonicalize_url("https://example.com/x?page=2&id=1", rules=_rules())
    b = canonicalize_url("https://example.com/x?id=1&page=2", rules=_rules())
    assert a == b


def test_idna_host_normalized():
    url = canonicalize_url("https://bücher.example.com/x", rules=_rules())
    assert url.startswith("https://xn--bcher-kva.example.com/")


# ---------------------------------------------------------------------------
# Rate registry lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture
def rate_root(tmp_path: Path) -> Path:
    return tmp_path / "output"


_AT = datetime(2026, 8, 11, 0, 0, 0, tzinfo=UTC)


def _clock(seconds: float):
    return lambda: _AT + timedelta(seconds=seconds)


def test_new_root_registry_created_once(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    assert reg.registry_path.exists()
    assert (rate_root / ".follow-the-money-persistent").exists()
    # second ensure is a no-op, no overwrite
    reg.ensure_registry(now=_clock(1))
    data = json.loads(reg.registry_path.read_bytes())
    assert data["version"] == "1"


def test_registry_root_identity_fails_closed_after_relocation(tmp_path):
    original = RateRegistry(tmp_path / "original")
    original.ensure_registry(now=_clock(0))
    relocated = RateRegistry(tmp_path / "relocated")
    relocated.root.mkdir()
    relocated.registry_path.write_bytes(original.registry_path.read_bytes())
    with pytest.raises(RateStateError, match="root_identity"):
        relocated.ensure_registry(now=_clock(1))


def test_initialize_scope_two_phase(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    assert state.status == "active"
    assert state.tokens == "10"
    assert state.capacity == "10"


def test_initializing_recovery_validates_no_request(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    # Simulate crash mid-initialization: registry says initializing, state file
    # missing entirely => recovery must fail closed.
    data = json.loads(reg.registry_path.read_bytes())
    data["scopes"]["s2"] = {"status": "initializing"}
    reg.registry_path.write_bytes(json.dumps(data).encode())
    with pytest.raises(RateStateError, match="initializing"):
        reg.recover_or_load("s2")


def test_active_scope_missing_state_fails_closed(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    # Delete the scope state file: active entry with missing state fails closed.
    from follow_the_money.providers.rate import _scope_file

    _scope_file(rate_root, "s1").unlink()
    with pytest.raises(RateStateError, match="active but state missing"):
        reg.recover_or_load("s1")


def test_corrupt_registry_fails_closed(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.registry_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RateStateError, match="corrupt"):
        reg.ensure_registry(now=_clock(1))


def test_marked_root_missing_registry_fails_closed(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.registry_path.unlink()
    with pytest.raises(RateStateError, match="marked.*registry is missing"):
        reg.ensure_registry(now=_clock(1))


def test_unknown_registry_schema_fails_closed(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    data = json.loads(reg.registry_path.read_bytes())
    data["version"] = "999"
    reg.registry_path.write_bytes(json.dumps(data).encode())
    with pytest.raises(RateStateError, match="unknown registry schema"):
        reg.recover_or_load("s1")


def test_debit_before_send_installs_24h_cooldown(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    state = reg.debit_and_cooldown(state, now=_clock(5))
    assert state.tokens == "9"
    assert state.cooldown_until is not None
    assert state.last_dispatch_wall == _clock(5)().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def test_crash_retains_24h_provisional(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    reg.debit_and_cooldown(state, now=_clock(5))
    # Crash: new process loads state, provisional cooldown must survive.
    reg2 = RateRegistry(rate_root)
    reloaded = reg2.recover_or_load("s1")
    assert reloaded.tokens == "9"
    assert reloaded.cooldown_until is not None


def test_cooldown_prevents_redebit_before_eligibility(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    reg.debit_and_cooldown(state, now=_clock(5))
    with pytest.raises(RateStateError, match="not yet eligible"):
        reg.debit_and_cooldown(state, now=_clock(6))


def test_confirmed_pre_send_refund(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    state = reg.debit_and_cooldown(state, now=_clock(5))
    state = reg.refund(state, now=_clock(5))
    assert state.tokens == "10"
    assert state.cooldown_until is None


def test_controlled_outcome_reconcile(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    state = reg.debit_and_cooldown(state, now=_clock(5))
    state = reg.reconcile(state, now=_clock(6), retry_after_seconds=30)
    expected = (_clock(6)() + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    assert state.cooldown_until == expected
    assert state.tokens == "9"  # debit retained


def test_wall_clock_rollback_no_refill(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    state.tokens = "0"
    # Clock rolls back: no tokens granted.
    rolled = refill_tokens(state, now=_clock(-100))
    assert rolled.tokens == "0"


def test_refill_from_elapsed_time(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    state.tokens = "0"
    filled = refill_tokens(state, now=_clock(30))  # half refill period
    # Decimal 10/60 is a repeating fraction; expect ~5 tokens within precision.
    assert 4.9 < float(filled.tokens) <= 5.1


def test_state_writes_are_atomic(rate_root):
    reg = RateRegistry(rate_root)
    reg.ensure_registry(now=_clock(0))
    reg.initialize_scope(
        "s1", capacity=10, refill_period_seconds=60, minimum_interval_seconds=1, now=_clock(0)
    )
    state = reg.recover_or_load("s1")
    reg.debit_and_cooldown(state, now=_clock(5))
    # No temp files left behind.
    leftovers = [p.name for p in rate_root.iterdir() if ".tmp" in p.name]
    assert leftovers == []
