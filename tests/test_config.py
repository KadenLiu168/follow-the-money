"""Task 1.3 — failing positive and negative configuration fixtures.

Covers strict-UTF-8/lone-surrogate rejection, numeric-vs-categorical unknown
semantics, duplicate provider IDs, unverified enabled adapters, charset/BOM
rules, closed fetch/redirect/source-link policies, the six-group coverage
matrix with copied shipped manifests, the 13 roles / nine asset groups / three
surprise scales, weight sums, lookback/limit positivity, and provider configuration.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from follow_the_money.config import load_config
from follow_the_money.config.load import ConfigError
from follow_the_money.config.model import V1_ROLE_IDS

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_MANIFEST_ROOT = REPO_ROOT / "providers"


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    return tmp_path


def _copy_contracts(tmp_path: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config" / "config.yaml"
    providers_path = tmp_path / "config" / "providers.yaml"
    manifest_root = tmp_path / "providers"
    config_path.parent.mkdir(parents=True)
    shutil.copy2(DEFAULT_CONFIG, config_path)
    shutil.copy2(DEFAULT_PROVIDERS, providers_path)
    shutil.copytree(DEFAULT_MANIFEST_ROOT, manifest_root)
    return config_path, providers_path, manifest_root


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Positive: shipped defaults load structurally (enablement owned by task 3.18)
# ---------------------------------------------------------------------------


def test_shipped_defaults_load_structure_without_enablement():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    assert cfg.schema_version == 1
    assert cfg.name == "follow-the-money"
    assert len(cfg.providers) == 9
    assert len(cfg.roles) == 13
    assert cfg.role_ids == V1_ROLE_IDS
    assert len(cfg.scoring.asset_groups) == 9
    assert len(cfg.scoring.surprise_scales) == 3
    assert sum(cfg.scoring.significance_weights) == 100
    # Verified core adapters are enabled; optional/unverified stay disabled.
    assert all(
        p.enabled
        for p in cfg.providers
        if p.id
        in ("federal_reserve", "bls", "sec_edgar", "pboc", "nbs", "sse", "szse", "yahoo_market")
    )
    assert not cfg.provider("cftc").enabled  # verified optional; disabled by default
    # v1 defaults
    assert cfg.feed.bootstrap_lookback_hours == 72
    assert cfg.feed.gap_threshold_hours == 72
    assert cfg.feed.calendar_horizon_hours == 26
    assert cfg.feed.pre_commit_deadline_seconds == 300
    assert cfg.feed.commit_reserve_seconds == 15
    assert cfg.feed.global_concurrency == 8
    assert cfg.feed.per_host_concurrency == 2
    assert cfg.feed.http_attempt_timeout_seconds == 20
    assert cfg.feed.max_attempts == 3
    assert cfg.scoring.family_penalty == "15"
    assert cfg.scoring.min_component_coverage == "60"
    assert cfg.scoring.anomaly_z_threshold == "2.0"
    assert cfg.market_state.z_supportive == "0.5"
    assert cfg.market_state.breadth_supportive == "0.20"
    assert cfg.market_state.regime_sum_threshold == "2"
    assert cfg.calendar.max_items == 6
    assert cfg.calendar.allowed_priorities == ("critical", "high")
    assert cfg.rate_registry.crash_cooldown_hours == 24
    assert cfg.freshness_limit_minutes == 30
    assert cfg.normal_lag_hours == 2
    assert len(cfg.scoring.freshness_bins) == 4
    assert cfg.scoring.relevance_weights == (40, 25, 20, 15)


def test_shipped_defaults_pass_strict_enablement_after_verification():
    # Gate 13.1: every mandatory matrix row is verified and enabled; strict
    # validation must now pass rather than block Apply.
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    for row in cfg.coverage.rows:
        enabled = [m for m in row.members if cfg.provider(m).enabled and cfg.provider(m).verified]
        assert len(enabled) >= row.minimum, f"{row.group}: {row.minimum} enabled required"


# ---------------------------------------------------------------------------
# Negative: strict UTF-8 and lone surrogates
# ---------------------------------------------------------------------------


def test_lone_surrogate_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    # Hand-write bytes: PyYAML cannot safely round-trip lone surrogates, so
    # emit the escaped sequence directly as raw YAML text.
    path.write_text('schema_version: 1\nname: "bad\\ud800name"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="surrogate"):
        load_config(path, DEFAULT_PROVIDERS, manifest_root=DEFAULT_MANIFEST_ROOT)


def test_lone_low_surrogate_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text('schema_version: 1\nname: "bad\\udfff"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="surrogate"):
        load_config(path, DEFAULT_PROVIDERS, manifest_root=DEFAULT_MANIFEST_ROOT)


def test_invalid_utf8_bytes_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"schema_version: 1\nname: \xff\xfe broken\n")
    with pytest.raises(ConfigError, match="UTF-8"):
        load_config(path, DEFAULT_PROVIDERS, manifest_root=DEFAULT_MANIFEST_ROOT)


def test_unknown_top_level_key_rejected(tmp_path):
    # Config objects are closed: unknown keys must be rejected.
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["extra_secret_key"] = True
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="unknown"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=False,
        )


# ---------------------------------------------------------------------------
# Negative: duplicate provider IDs
# ---------------------------------------------------------------------------


def test_duplicate_provider_ids_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers = _read_yaml(providers_path)
    providers["providers"].append({"id": "federal_reserve", "enabled": False})
    _write_yaml(providers_path, providers)
    with pytest.raises(ConfigError, match="duplicate provider id"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=False,
        )


# ---------------------------------------------------------------------------
# Negative: unverified enabled adapters
# ---------------------------------------------------------------------------


def test_enabled_unverified_adapter_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest = _read_yaml(manifest_root / "federal_reserve" / "manifest.yaml")
    manifest["verification"]["verified"] = False
    _write_yaml(manifest_root / "federal_reserve" / "manifest.yaml", manifest)
    with pytest.raises(ConfigError, match="enabled but unverified"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_disabled_unverified_adapter_ok(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest = _read_yaml(manifest_root / "cftc" / "manifest.yaml")
    manifest["verification"]["verified"] = False
    _write_yaml(manifest_root / "cftc" / "manifest.yaml", manifest)
    load_config(config_path, providers_path, manifest_root=manifest_root)  # OK


# ---------------------------------------------------------------------------
# Negative: invalid source tiers
# ---------------------------------------------------------------------------


def test_invalid_source_tier_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["source_families"][0]["tier"] = "Tier 5"
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="tier"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=False,
        )


# ---------------------------------------------------------------------------
# Coverage matrix semantics
# ---------------------------------------------------------------------------


def test_coverage_row_missing_member_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers = _read_yaml(providers_path)
    providers["coverage"][0]["members"] = ["ghost"]
    _write_yaml(providers_path, providers)
    with pytest.raises(ConfigError, match="unknown member"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_coverage_row_unverified_member_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers = _read_yaml(providers_path)
    providers["coverage"][0]["members"] = ["federal_reserve"]
    _write_yaml(providers_path, providers)
    manifest = _read_yaml(manifest_root / "federal_reserve" / "manifest.yaml")
    manifest["verification"]["verified"] = False
    _write_yaml(manifest_root / "federal_reserve" / "manifest.yaml", manifest)
    with pytest.raises(ConfigError, match="unverified"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_coverage_row_disabled_member_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers = _read_yaml(providers_path)
    providers["coverage"][0]["members"] = ["cftc"]
    _write_yaml(providers_path, providers)
    with pytest.raises(ConfigError, match="disabled"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_coverage_row_unachievable_minimum_rejected(tmp_path):
    # Row requires 3 enabled members but only two are enabled/verified.
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers = _read_yaml(providers_path)
    providers["coverage"][0].update(
        members=["federal_reserve", "bls"],
        minimum=3,
    )
    _write_yaml(providers_path, providers)
    with pytest.raises(ConfigError, match="not achievable"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_optional_row_can_be_unachievable(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers = _read_yaml(providers_path)
    providers["coverage"][0].update(
        members=["federal_reserve", "bls"],
        minimum=3,
        optional=True,
    )
    _write_yaml(providers_path, providers)
    load_config(
        config_path, providers_path, manifest_root=manifest_root
    )  # optional rows are not enforced


# ---------------------------------------------------------------------------
# Roles: exact canonical 13
# ---------------------------------------------------------------------------


def test_roles_must_be_exact_canonical_set(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"] = [dict(config["roles"][0], id="sp500")]  # only one role
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="canonical v1 set"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_role_order_must_match_canonical(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"] = list(reversed(config["roles"]))
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="canonical v1 set"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_every_role_requires_explicit_session_id(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    del config["roles"][0]["session_id"]
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="session_id"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_role_unknown_session_id_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][0]["session_id"] = "missing"
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="unknown session"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_role_session_class_mismatch_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][0]["session_id"] = "crypto_247"
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="incompatible"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_exchange_traded_session_unknown_calendar_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["sessions"][0]["calendar"] = "XNYX"
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="unknown exchange calendar"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_duplicate_role_ownership_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][1]["id"] = config["roles"][0]["id"]
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="duplicate role"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_role_contract_does_not_require_parallel_source_provenance(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    loaded = load_config(config_path, providers_path, manifest_root=manifest_root)
    assert not hasattr(loaded.roles[0], "source_provenance")


def test_role_contract_requires_non_negative_availability_lag(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][0]["availability_lag_seconds"] = -1
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="availability_lag_seconds"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_role_mapping_verified_must_be_boolean(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][0]["mapping_verified"] = "false"
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="mapping_verified must be boolean"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_shipped_roles_expose_a_complete_verified_contract():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    assert all(role.provider_id == "yahoo_market" for role in cfg.roles)
    assert all(role.economic_identity for role in cfg.roles)
    assert all(role.daily_close_semantics for role in cfg.roles)
    assert {role.id for role in cfg.roles if not role.mapping_verified} == {
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
    }
    assert all(role.availability_lag_seconds >= 0 for role in cfg.roles)


def test_shipped_role_contract_matches_yahoo_manifest_mappings():
    from follow_the_money.providers.manifest import load_all_manifests

    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    mappings = {str(m["role_id"]): m for m in load_all_manifests()["yahoo_market"]["role_mappings"]}
    assert set(mappings) == set(cfg.role_ids)
    for role in cfg.roles:
        mapping = mappings[role.id]
        assert mapping["instrument"] == role.instrument, role.id
        assert mapping["unit"] == role.unit, role.id
        assert mapping["mapping_verified"] == role.mapping_verified, role.id
        if role.mapping_verified:
            assert "unverified" not in role.daily_close_semantics.lower(), role.id
        else:
            assert str(mapping.get("reason", "")).strip(), f"{role.id} lacks an explicit reason"


# ---------------------------------------------------------------------------
# Scoring weights and maps
# ---------------------------------------------------------------------------


def test_significance_weights_must_sum_100(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["scoring"]["significance_weights"] = [30, 20, 20, 20, 9]
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="sum to 100"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_asset_groups_must_be_nine(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["scoring"]["asset_groups"] = [{"group": "only", "name_zh": "only", "proxies": []}]
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="nine asset groups"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


def test_surprise_scale_must_be_positive(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["scoring"]["surprise_scales"] = [{"series_id": "x", "scale": "0", "note": "test"}]
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="positive"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


# ---------------------------------------------------------------------------
# Feed limits positivity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "bootstrap_lookback_hours",
        "gap_threshold_hours",
        "calendar_horizon_hours",
        "pre_commit_deadline_seconds",
        "commit_reserve_seconds",
    ],
)
def test_non_positive_feed_limit_rejected(tmp_path, field):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["feed"][field] = 0
    _write_yaml(config_path, config)
    with pytest.raises(ConfigError, match="positive"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


# ---------------------------------------------------------------------------
# Rate policy checks
# ---------------------------------------------------------------------------


def test_rate_capacity_must_be_positive(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    manifest["rate_policy"]["capacity"] = 0
    _write_yaml(manifest_path, manifest)
    with pytest.raises(ConfigError, match="capacity"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=False,
        )


def test_rate_refill_must_be_positive(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "federal_reserve" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    manifest["rate_policy"]["refill_period_seconds"] = 0
    _write_yaml(manifest_path, manifest)
    with pytest.raises(ConfigError, match="refill"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=False,
        )


def test_inconsistent_same_scope_rate_policies_rejected(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    federal_path = manifest_root / "federal_reserve" / "manifest.yaml"
    bls_path = manifest_root / "bls" / "manifest.yaml"
    federal = _read_yaml(federal_path)
    bls = _read_yaml(bls_path)
    federal["rate_policy"]["scope_id"] = "shared_test_scope"
    bls["rate_policy"].update(scope_id="shared_test_scope", capacity=999)
    _write_yaml(federal_path, federal)
    _write_yaml(bls_path, bls)
    with pytest.raises(ConfigError, match="inconsistently"):
        load_config(config_path, providers_path, manifest_root=manifest_root)


# ---------------------------------------------------------------------------
# Charset/BOM strictness is a manifest rule (3.x); config exposes the fields.
# ---------------------------------------------------------------------------


def test_shipped_charset_is_utf8_strict():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    for p in cfg.providers:
        assert p.allowed_charset.lower() in {"utf-8", "utf8"}
        assert p.allowed_bom is False  # no conflicting BOM policy shipped


def test_config_loads_without_any_llm_section():
    # The deterministic engine is credential-free: no `llm:` section exists
    # in the config contract and loading never reads a model or API key.
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=False,
    )
    assert not hasattr(cfg, "llm")
    assert not hasattr(cfg, "audit_severity")
    assert cfg.safety_lexicon.zh_terms  # deterministic safety contract still loads


# ---------------------------------------------------------------------------
# Python-to-YAML round trip
# ---------------------------------------------------------------------------


def test_config_yaml_round_trip(tmp_path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _write_yaml(config_path, _read_yaml(config_path))
    _write_yaml(providers_path, _read_yaml(providers_path))
    cfg = load_config(config_path, providers_path, manifest_root=manifest_root)
    assert cfg.name == "follow-the-money"
    assert cfg.provider("federal_reserve").name == "Federal Reserve"
    assert cfg.role("sp500").id == "sp500"
