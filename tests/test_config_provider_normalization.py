"""ECO-26 source-authority and single-resolved-contract tests.

These tests deliberately mutate copied checked-in contracts. Expected values
are literal so a second parser cannot make the test tautological.
"""

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


def _copy_contracts(tmp_path: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config" / "config.yaml"
    providers_path = tmp_path / "config" / "providers.yaml"
    manifest_root = tmp_path / "providers"
    config_path.parent.mkdir(parents=True)
    shutil.copy2(DEFAULT_CONFIG, config_path)
    shutil.copy2(DEFAULT_PROVIDERS, providers_path)
    shutil.copytree(REPO_ROOT / "providers", manifest_root)
    return config_path, providers_path, manifest_root


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _remove_registry_mirrors(path: Path) -> None:
    registry = _read_yaml(path)
    registry["providers"] = [
        {key: item[key] for key in ("id", "enabled", "optional") if key in item}
        for item in registry["providers"]
    ]
    _write_yaml(path, registry)


def _strict_load(config_path: Path, providers_path: Path, manifest_root: Path):
    return load_config(
        config_path,
        providers_path,
        manifest_root=manifest_root,
        strict=True,
        require_verified_enabled=True,
    )


def test_yaml_owned_values_reach_resolved_model(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    data = _read_yaml(config_path)
    data["timezone"] = "UTC"
    data["feed"]["lock_timeout_seconds"] = 17
    data["scoring"]["full_priority_threshold"] = "73"
    data["market_state"]["required_known_dimensions"] = 3
    data["calendar"]["max_items"] = 9
    data["safety_lexicon"]["zh_terms"] = ["仅测试词"]
    data["rate_registry"]["crash_cooldown_hours"] = 11
    _write_yaml(config_path, data)

    cfg = _strict_load(config_path, providers_path, manifest_root)

    assert cfg.timezone == "UTC"
    assert cfg.feed.lock_timeout_seconds == 17
    assert cfg.scoring.full_priority_threshold == "73"
    assert cfg.market_state.required_known_dimensions == 3
    assert cfg.calendar.max_items == 9
    assert cfg.safety_lexicon.zh_terms == ("仅测试词",)
    assert cfg.rate_registry.crash_cooldown_hours == 11


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("top", "timezone"),
        ("feed", "lock_timeout_seconds"),
        ("scoring", "full_priority_threshold"),
        ("market_state", "z_supportive"),
        ("calendar", "max_items"),
        ("safety_lexicon", "zh_terms"),
        ("rate_registry", "version"),
    ],
)
def test_required_normative_field_never_uses_python_fallback(
    tmp_path: Path, section: str, field: str
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    data = _read_yaml(config_path)
    target = data if section == "top" else data[section]
    if section == "feed" and field not in target:
        target[field] = 60
    del target[field]
    _write_yaml(config_path, data)

    with pytest.raises(ConfigError, match="missing required keys"):
        _strict_load(config_path, providers_path, manifest_root)


@pytest.mark.parametrize(
    "mutation", ["missing", "invalid_yaml", "version", "identity", "incomplete", "verification"]
)
def test_enabled_manifest_contract_failures_are_static(tmp_path: Path, mutation: str):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    if mutation == "missing":
        manifest_path.unlink()
    elif mutation == "invalid_yaml":
        manifest_path.write_text("provider_id: [", encoding="utf-8")
    else:
        data = _read_yaml(manifest_path)
        if mutation == "version":
            data["contract_version"] = 99
        elif mutation == "identity":
            data["provider_id"] = "other"
        elif mutation == "incomplete":
            del data["rate_policy"]
        elif mutation == "verification":
            data["verification"]["verified"] = False
        _write_yaml(manifest_path, data)

    with pytest.raises(ConfigError):
        _strict_load(config_path, providers_path, manifest_root)


def test_manifest_owned_runtime_mutation_does_not_need_registry_edit(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _remove_registry_mirrors(providers_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    data = _read_yaml(manifest_path)
    data["fetch_hosts"][0]["host"] = "changed.federalreserve.gov"
    data["rate_policy"]["scope_id"] = "us_gov_changed"
    data["rate_policy"]["capacity"] = 19
    data["charset"]["allowed"] = ["utf-8"]
    data["response_limit_bytes"] = 12345
    data["empty_valid_for_window"] = False
    _write_yaml(manifest_path, data)

    cfg = _strict_load(config_path, providers_path, manifest_root)
    provider = cfg.provider("federal_reserve")
    assert provider.fetch_hosts[0].host == "changed.federalreserve.gov"
    assert provider.rate_policy is not None
    assert provider.rate_policy.capacity == 19
    assert provider.allowed_charset == "utf-8"
    assert provider.response_limit_bytes == 12345
    assert provider.empty_valid_for_window is False


def test_retained_registry_mirror_must_match_manifest(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    registry = _read_yaml(providers_path)
    registry["providers"][0]["allowed_charset"] = "latin-1"
    _write_yaml(providers_path, registry)

    with pytest.raises(ConfigError, match="mirror|mismatch"):
        _strict_load(config_path, providers_path, manifest_root)


def test_registry_enablement_requires_a_yaml_boolean(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    registry = _read_yaml(providers_path)
    registry["providers"][3]["enabled"] = "false"
    _write_yaml(providers_path, registry)

    with pytest.raises(ConfigError, match="enabled.*boolean"):
        _strict_load(config_path, providers_path, manifest_root)


def test_source_link_rule_omission_has_no_hidden_default(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    del manifest["source_link_hosts"][0]["allowed_ports"]
    _write_yaml(manifest_path, manifest)

    with pytest.raises(ConfigError, match="allowed_ports"):
        _strict_load(config_path, providers_path, manifest_root)


def test_coverage_membership_is_matrix_owned_and_supports_multiple_rows(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    cfg = _strict_load(config_path, providers_path, manifest_root)
    provider = cfg.provider("federal_reserve")

    assert provider.coverage_groups == (
        "future_calendar",
        "us_official_macro_policy",
    )
    assert all(
        row.group in provider.coverage_groups
        for row in cfg.coverage.rows
        if "federal_reserve" in row.members
    )


def test_coverage_optionality_is_explicit_and_snapshotted(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    registry = _read_yaml(providers_path)
    registry["coverage"][0]["optional"] = True
    _write_yaml(providers_path, registry)

    cfg = _strict_load(config_path, providers_path, manifest_root)
    from follow_the_money.feed.cli import _feed_config_snapshot

    assert cfg.coverage.rows[0].optional is True
    assert _feed_config_snapshot(cfg)["snapshot"]["coverage"][0]["optional"] is True


def test_adapter_and_snapshot_share_resolved_provider_contract(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _remove_registry_mirrors(providers_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    data = _read_yaml(manifest_path)
    data["fetch_hosts"][0]["host"] = "changed.federalreserve.gov"
    data["rate_policy"]["scope_id"] = "us_gov_changed"
    data["rate_policy"]["capacity"] = 19
    data["charset"]["allowed"] = ["utf-8"]
    data["response_limit_bytes"] = 12345
    data["empty_valid_for_window"] = False
    _write_yaml(manifest_path, data)

    cfg = _strict_load(config_path, providers_path, manifest_root)
    from follow_the_money.feed.cli import _provider_contract_snapshots
    from follow_the_money.providers.adapters import FedAdapter

    adapter = FedAdapter(cfg.provider("federal_reserve"))
    snapshot = next(
        item
        for item in _provider_contract_snapshots(cfg)
        if item["provider_id"] == "federal_reserve"
    )

    assert adapter._fetch_rules[0].host == "changed.federalreserve.gov"
    assert adapter._contract.rate_policy is not None
    assert adapter._contract.rate_policy.capacity == 19
    assert adapter._contract.response_limit_bytes == 12345
    assert adapter._contract.empty_valid_for_window is False
    assert snapshot["snapshot"]["fetch_hosts"][0]["host"] == "changed.federalreserve.gov"
    assert snapshot["snapshot"]["rate_policy"]["capacity"] == 19
    assert snapshot["snapshot"]["response_limit_bytes"] == 12345
    assert snapshot["snapshot"]["empty_valid_for_window"] is False


def test_disabled_provider_is_not_initialized(monkeypatch):
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=True)
    from follow_the_money.providers import adapters

    class DisabledAdapterMustNotInitialize:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("disabled Provider adapter was initialized")

    assert not cfg.provider("cftc").enabled
    monkeypatch.setattr(adapters, "CftcAdapter", DisabledAdapterMustNotInitialize)

    registry = adapters.build_registry({provider.id: provider for provider in cfg.providers})

    assert "cftc" not in registry.ids()


def test_static_manifest_failure_happens_before_feed_runtime_mutation(tmp_path: Path, monkeypatch):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    data = _read_yaml(manifest_path)
    data["contract_version"] = 99
    _write_yaml(manifest_path, data)

    from follow_the_money.feed import cli as feed_cli

    monkeypatch.setattr(feed_cli, "_default_providers_path", lambda: providers_path)
    monkeypatch.setattr(feed_cli, "_default_manifest_root", lambda: manifest_root)
    output_root = tmp_path / "out"
    with pytest.raises(feed_cli.FeedInputError):
        feed_cli.run_feed(config_path=str(config_path), output_root=str(output_root))

    assert not output_root.exists()


def test_static_manifest_failure_preserves_existing_latest_and_rate_state(
    tmp_path: Path, monkeypatch
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    data = _read_yaml(manifest_path)
    data["verification"]["verified"] = False
    _write_yaml(manifest_path, data)

    from follow_the_money.feed import cli as feed_cli

    monkeypatch.setattr(feed_cli, "_default_providers_path", lambda: providers_path)
    monkeypatch.setattr(feed_cli, "_default_manifest_root", lambda: manifest_root)
    output_root = tmp_path / "out"
    output_root.mkdir()
    latest = output_root / "latest.json"
    latest.write_bytes(b"previous-latest")

    with pytest.raises(feed_cli.FeedInputError):
        feed_cli.run_feed(config_path=str(config_path), output_root=str(output_root))

    assert latest.read_bytes() == b"previous-latest"
    assert not (output_root / "rate-registry.json").exists()
    assert (
        not list((output_root / "daily").rglob("*.json"))
        if (output_root / "daily").exists()
        else True
    )


def test_existing_v1_role_and_coverage_facts_remain_literal():
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=True)
    assert cfg.role_ids == (
        "sp500",
        "csi300",
        "hsi",
        "vix",
        "us2y",
        "us10y",
        "cn10y",
        "dxy",
        "usdcnh",
        "copper",
        "wti",
        "gold",
        "btc",
    )
    assert tuple(
        (role.id, role.instrument, role.unit, role.mapping_verified) for role in cfg.roles
    ) == (
        ("sp500", "^GSPC", "index", True),
        ("csi300", "000300.SS", "index", True),
        ("hsi", "^HSI", "index", False),
        ("vix", "^VIX", "index", False),
        ("us2y", "^IRX", "percent", False),
        ("us10y", "^TNX", "percent", False),
        ("cn10y", "CN10Y", "percent", False),
        ("dxy", "DX-Y.NYB", "index", False),
        ("usdcnh", "CNH=X", "fx", False),
        ("copper", "HG=F", "price", False),
        ("wti", "CL=F", "price", False),
        ("gold", "GC=F", "price", False),
        ("btc", "BTC-USD", "price", False),
    )
    assert tuple(row.group for row in cfg.coverage.rows) == (
        "us_official_macro_policy",
        "us_company_filings",
        "china_official_macro_policy",
        "china_exchange_evidence",
        "china_hk_cross_asset_market",
        "future_calendar",
    )
