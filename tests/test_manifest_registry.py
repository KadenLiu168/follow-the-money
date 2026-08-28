"""Task 3.17/3.18 — manifest/registry coverage-matrix gates.

Proves that no mandatory v1 matrix row is silently weakened: every adapter
without a verified contract and implementation stays disabled and cannot
count as working coverage; CFTC stays verified-optional; AKShare/BEA/HKEX/
Tier-2 media/paid enhancements stay disabled.
"""

from __future__ import annotations

from follow_the_money.config import load_config
from follow_the_money.providers.manifest import (
    load_all_manifests,
    manifest_to_provider_entry,
)

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"

# The six mandatory v1 groups and their exact members (design matrix).
MANDATORY_ROWS = {
    "us_official_macro_policy": ("federal_reserve", "bls"),
    "us_company_filings": ("sec_edgar",),
    "china_official_macro_policy": ("pboc", "nbs"),
    "china_exchange_evidence": ("sse", "szse"),
    "verified_market_data": ("yahoo_market",),
    "future_calendar": ("federal_reserve", "bls", "nbs"),
}


def test_shipped_config_declares_exact_six_groups():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    rows = {r.group: r.members for r in cfg.coverage.rows}
    assert rows == MANDATORY_ROWS


def test_shipped_matrix_minima_match_design():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    for r in cfg.coverage.rows:
        expected_min = {
            "us_official_macro_policy": 2,
            "us_company_filings": 1,
            "china_official_macro_policy": 2,
            "china_exchange_evidence": 2,
            "verified_market_data": 1,
            "future_calendar": 3,
        }[r.group]
        assert r.minimum == expected_min
        assert r.capability  # every row names its capability


def test_unverified_adapters_never_enabled_by_manifest():
    manifests = load_all_manifests()
    for pid, m in manifests.items():
        entry = manifest_to_provider_entry(m)
        if pid == "akshare":
            assert not entry.enabled, f"{pid} must stay disabled (optional extra)"
        # Verified manifests with default_enabled enable; unverified never do.
        if not m["verification"]["verified"]:
            assert not entry.enabled, f"{pid} must stay disabled until verified"
            assert not entry.verified, f"{pid} must not claim verified status"


def test_cftc_verified_optional_not_mandatory():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    mandatory = {m for r in cfg.coverage.rows for m in r.members}
    assert "cftc" not in mandatory  # CFTC is verified-optional coverage


def test_akshare_never_counts_as_coverage():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    mandatory = {m for r in cfg.coverage.rows for m in r.members}
    assert "akshare" not in mandatory
    assert not cfg.provider("akshare").enabled


def test_no_hidden_default_enablement():
    # Every mandatory matrix row must be backed by verified enabled members;
    # an optional/unverified extra (AKShare) never counts as coverage.
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    assert not cfg.provider("akshare").enabled
    assert not cfg.provider("cftc").enabled
    for row in cfg.coverage.rows:
        enabled = [m for m in row.members if cfg.provider(m).enabled and cfg.provider(m).verified]
        assert len(enabled) >= row.minimum, f"{row.group}: insufficient verified coverage"


def test_every_shipped_provider_has_manifest():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    manifests = load_all_manifests()
    for p in cfg.providers:
        # provider ids in config use underscores; manifest dirs match.
        assert p.id in manifests, f"provider {p.id} missing contract manifest"


def test_manifest_charset_and_source_link_rules_present():
    manifests = load_all_manifests()
    for pid, m in manifests.items():
        assert m["charset"]["allowed"], f"{pid} missing allowed charset"
        assert "source_link_hosts" in m, f"{pid} missing source_link_hosts"


def test_all_verified_core_adapters_are_implemented():
    # Every mandatory provider has a concrete adapter; optional extras remain
    # disabled and are not part of the production registry.
    from follow_the_money.providers.adapters import (
        BlsAdapter,
        FedAdapter,
        NbsAdapter,
        PbocAdapter,
        SecEdgarAdapter,
        SseAdapter,
        SzseAdapter,
        YahooMarketAdapter,
    )

    for adapter_cls in (
        FedAdapter,
        BlsAdapter,
        SecEdgarAdapter,
        PbocAdapter,
        NbsAdapter,
        SseAdapter,
        SzseAdapter,
        YahooMarketAdapter,
    ):
        a = adapter_cls()
        assert a.provider_id
        assert a._rules  # every adapter binds source-link rules
