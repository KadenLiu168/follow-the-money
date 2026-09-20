"""Feed-only manifest and coverage-matrix gates."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from follow_the_money.config import load_config
from follow_the_money.config.load import ConfigError
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


RECORDED_CONTENT_FIXTURES = {
    "federal_reserve": (
        "fixtures/press_all.xml",
        "fixtures/detail-monetary20260916a.htm",
    ),
    "pboc": (
        "fixtures/index.html",
        "fixtures/detail-2026091815494839605.html",
    ),
    "sse": (
        "fixtures/s_list.shtml",
        "fixtures/s_list_2.shtml",
        "fixtures/detail-c_20260918_10832703.shtml",
    ),
    "szse": (
        "fixtures/index.html",
        "fixtures/index_1.html",
        "fixtures/detail-t20260917_622911.html",
    ),
}


def test_recorded_source_content_fixtures_are_declared_and_present():
    cfg = _config()
    for provider_id, expected in RECORDED_CONTENT_FIXTURES.items():
        provider = cfg.provider(provider_id)
        assert provider.contract_version == 2
        for relative in expected:
            assert relative in provider.fixture_files
            declared = DEFAULT_MANIFEST_ROOT / provider_id / relative
            assert declared.is_file()
            payload = declared.read_bytes()
            assert payload
            payload.decode("utf-8")


def test_declared_fixture_provenance_files_exist_and_are_addressed_safely(tmp_path: Path):
    for index, mutation in enumerate(
        (
            lambda files: files.append("fixtures/absent.html"),
            lambda files: files.append("../../schemas/feed.schema.json"),
            lambda files: files.clear(),
        )
    ):
        root = tmp_path / f"provenance-{index}"
        root.mkdir()
        shutil.copytree(DEFAULT_MANIFEST_ROOT, root / "providers")
        shutil.copy2(DEFAULT_CONFIG, root / "config.yaml")
        shutil.copy2(DEFAULT_PROVIDERS, root / "providers.yaml")
        manifest_path = root / "providers" / "sse" / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        mutation(manifest["fixture_provenance"]["files"])
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        with pytest.raises(ConfigError, match="fixture_provenance"):
            load_config(
                root / "config.yaml",
                root / "providers.yaml",
                manifest_root=root / "providers",
                require_verified_enabled=True,
            )
