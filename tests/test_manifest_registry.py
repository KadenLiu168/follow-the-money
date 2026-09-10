"""Feed-only manifest and coverage-matrix gates."""

from __future__ import annotations

from pathlib import Path

from follow_the_money.config import load_config
from follow_the_money.providers.manifest import load_all_manifests

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"
REQUIRED = {
    "federal_reserve",
    "bls",
    "pboc",
    "nbs",
    "sse",
    "szse",
    "sec_edgar",
    "cftc",
}
MANDATORY_ROWS = {
    "us_official_macro_policy": ("federal_reserve", "bls"),
    "us_company_filings": ("sec_edgar",),
    "china_official_macro_policy": ("pboc", "nbs"),
    "china_exchange_evidence": ("sse", "szse"),
    "cftc_positioning": ("cftc",),
}
RETAINED_DOMAINS = {"news", "macro_release", "policy", "positioning", "filing"}


def _config():
    return load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )


def test_shipped_config_declares_exact_required_providers_and_groups():
    cfg = _config()
    assert {provider.id for provider in cfg.providers} == REQUIRED
    assert {row.group: row.members for row in cfg.coverage.rows} == MANDATORY_ROWS
    assert cfg.coverage.row("cftc_positioning").minimum == 1


def test_shipped_matrix_minima_are_achievable():
    cfg = _config()
    for row in cfg.coverage.rows:
        enabled = [member for member in row.members if cfg.provider(member).enabled]
        assert len(enabled) >= row.minimum


def test_every_shipped_provider_has_a_verified_credential_free_manifest():
    cfg = _config()
    manifests = load_all_manifests()
    assert set(manifests) == REQUIRED
    for provider in cfg.providers:
        manifest = manifests[provider.id]
        assert manifest["provider_id"] == provider.id
        assert manifest["verification"]["verified"]
        assert manifest["authentication"] == "none"
        assert set(manifest["time"]["payload_types"]) <= RETAINED_DOMAINS


def test_all_shipped_adapters_are_implemented():
    from follow_the_money.providers.adapters import (
        BlsAdapter,
        CftcAdapter,
        FedAdapter,
        NbsAdapter,
        PbocAdapter,
        SecEdgarAdapter,
        SseAdapter,
        SzseAdapter,
    )

    for adapter_cls in (
        FedAdapter,
        BlsAdapter,
        CftcAdapter,
        NbsAdapter,
        PbocAdapter,
        SecEdgarAdapter,
        SseAdapter,
        SzseAdapter,
    ):
        adapter = adapter_cls()
        assert adapter.provider_id in REQUIRED
        assert adapter._rules
