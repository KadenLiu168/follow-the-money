"""Feed-only configuration regressions."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from follow_the_money.config import load_config
from follow_the_money.config.load import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"
REQUIRED_PROVIDERS = (
    "federal_reserve",
    "bls",
    "pboc",
    "nbs",
    "sse",
    "szse",
    "sec_edgar",
    "cftc",
)
RETAINED_DOMAINS = {"news", "macro_release", "policy", "positioning", "filing"}


def _copy_contracts(tmp_path: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config.yaml"
    providers_path = tmp_path / "providers.yaml"
    manifest_root = tmp_path / "providers"
    shutil.copy2(DEFAULT_CONFIG, config_path)
    shutil.copy2(DEFAULT_PROVIDERS, providers_path)
    shutil.copytree(DEFAULT_MANIFEST_ROOT, manifest_root)
    return config_path, providers_path, manifest_root


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _load(
    config: Path = DEFAULT_CONFIG,
    providers: Path = DEFAULT_PROVIDERS,
    manifests: Path = DEFAULT_MANIFEST_ROOT,
):
    return load_config(config, providers, manifest_root=manifests, require_verified_enabled=True)


def test_shipped_defaults_are_exactly_feed_only_and_credential_free():
    cfg = _load()

    assert cfg.schema_version == 1
    assert tuple(provider.id for provider in cfg.providers) == REQUIRED_PROVIDERS
    assert all(provider.enabled and provider.verified for provider in cfg.providers)
    assert all(provider.authentication == "none" for provider in cfg.providers)
    assert all(set(provider.payload_types) <= RETAINED_DOMAINS for provider in cfg.providers)
    assert {row.group for row in cfg.coverage.rows} == {
        "us_official_macro_policy",
        "us_company_filings",
        "china_official_macro_policy",
        "china_exchange_evidence",
        "cftc_positioning",
    }
    assert cfg.coverage.row("cftc_positioning").members == ("cftc",)
    assert cfg.coverage.row("cftc_positioning").minimum == 1
    assert cfg.feed.bootstrap_lookback_hours == 72
    assert cfg.feed.lock_timeout_seconds == 60


def test_unknown_top_level_key_fails_closed(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(config)
    value["analysis"] = {}
    _write(config, value)

    with pytest.raises(ConfigError, match="unknown"):
        _load(config, providers, manifests)


def test_removed_nested_key_fails_closed(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(config)
    value["feed"]["calendar_horizon_hours"] = 26
    _write(config, value)

    with pytest.raises(ConfigError, match="unknown"):
        _load(config, providers, manifests)


def test_missing_runtime_state_root_fails_closed(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(config)
    del value["runtime_state_root"]
    _write(config, value)

    with pytest.raises(ConfigError, match="runtime_state_root"):
        _load(config, providers, manifests)


def test_duplicate_provider_activation_fails_closed(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(providers)
    value["providers"].append({"id": "cftc", "enabled": True})
    _write(providers, value)

    with pytest.raises(ConfigError, match="duplicate provider id"):
        _load(config, providers, manifests)


@pytest.mark.parametrize("provider_id", ["cftc", "federal_reserve"])
def test_required_provider_cannot_be_disabled(tmp_path: Path, provider_id: str):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(providers)
    for entry in value["providers"]:
        if entry["id"] == provider_id:
            entry["enabled"] = False
    _write(providers, value)

    with pytest.raises(ConfigError, match="disabled"):
        _load(config, providers, manifests)


def test_unknown_provider_is_rejected(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(providers)
    value["providers"].append({"id": "yahoo_market", "enabled": True})
    _write(providers, value)

    with pytest.raises(ConfigError, match="removed or unsupported Provider"):
        _load(config, providers, manifests)


def test_manifest_overdeclared_payload_fails_before_resolution(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    manifest_path = manifests / "cftc" / "manifest.yaml"
    value = _yaml(manifest_path)
    value["time"]["payload_types"].append("market_data")
    _write(manifest_path, value)

    with pytest.raises(ConfigError, match="payload"):
        _load(config, providers, manifests)


def test_provider_coverage_must_name_known_members(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    value = _yaml(providers)
    value["coverage"][0]["members"] = ["removed_provider", "bls"]
    _write(providers, value)

    with pytest.raises(ConfigError, match="unknown Provider"):
        _load(config, providers, manifests)


def test_config_snapshot_has_no_runtime_root_or_removed_surface():
    cfg = _load()
    from follow_the_money.feed.cli import _feed_config_snapshot

    snapshot = _feed_config_snapshot(cfg)["snapshot"]
    assert "runtime_state_root" not in snapshot
    assert set(snapshot) == {"name", "feed", "coverage"}
