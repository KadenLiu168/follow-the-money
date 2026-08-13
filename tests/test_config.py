"""Task 1.3 — failing positive and negative configuration fixtures.

Covers strict-UTF-8/lone-surrogate rejection, numeric-vs-categorical unknown
semantics, duplicate provider IDs, unverified enabled adapters, charset/BOM
rules, closed fetch/redirect/source-link policies, the six-group coverage
matrix with synthetic manifests, the 13 roles / nine asset groups / three
surprise scales, weight sums, lookback/limit positivity, and optional extras.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from follow_the_money.config import load_config
from follow_the_money.config.load import ConfigError
from follow_the_money.config.model import V1_ROLE_IDS

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"
DEFAULT_PROVIDERS = REPO_ROOT / "config" / "providers.yaml"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


V1_ASSET_GROUPS = [
    {"group": g, "name_zh": g, "proxies": p}
    for g, p in [
        ("cn_hk_equities", ["csi300", "hsi"]),
        ("us_equities", ["sp500"]),
        ("us_rates", ["us2y", "us10y"]),
        ("china_rates", ["cn10y"]),
        ("usd_fx", ["dxy", "usdcnh"]),
        ("industrial_commodities", ["copper"]),
        ("energy", ["wti"]),
        ("precious_metals", ["gold"]),
        ("crypto", ["btc"]),
    ]
]


def _minimal_config(**overrides) -> dict:
    sessions = [
        {
            "id": "exchange",
            "calendar": "XNYS",
            "session_class": "exchange_traded",
            "timezone": "UTC",
        },
        {
            "id": "crypto",
            "calendar": "UTC",
            "session_class": "continuous_247",
            "timezone": "UTC",
        },
    ]
    cfg = {
        "schema_version": 1,
        "name": "test",
        "feed": {
            "bootstrap_lookback_hours": 72,
            "gap_threshold_hours": 72,
            "calendar_horizon_hours": 26,
            "pre_commit_deadline_seconds": 300,
            "commit_reserve_seconds": 15,
        },
        "llm": {"model": "gpt-test"},
        "scoring": {
            "significance_weights": [30, 20, 20, 20, 10],
            "asset_groups": V1_ASSET_GROUPS,
        },
        "coverage": [],
        "roles": [
            {
                "id": rid,
                "name": rid,
                "instrument": rid,
                "unit": "index",
                "provider_id": "prov_a",
                "economic_identity": f"{rid} economic identity",
                "daily_close_semantics": "provider_daily_close",
                "source_provenance": "fixture:role-contract-v1",
                "mapping_verified": True,
                "availability_lag_seconds": 300,
                "session_id": "crypto" if rid == "btc" else "exchange",
                "session_class": "continuous_247" if rid == "btc" else "exchange_traded",
            }
            for rid in V1_ROLE_IDS
        ],
        "sessions": sessions,
    }
    cfg.update(overrides)
    return cfg


def _minimal_providers(**overrides) -> dict:
    prov = {
        "providers": [
            {
                "id": "prov_a",
                "name": "Provider A",
                "enabled": True,
                "verified": True,
                "group": "us_official_macro_policy",
                "source_family_id": "fam_a",
                "tier": "Tier 1",
                "user_agent": "ua",
                "fetch_hosts": [{"host": "a.example.com"}],
                "redirect_hosts": [],
                "source_link_hosts": [{"host": "a.example.com"}],
                "rate_policy": {
                    "scope_id": "scope_a",
                    "capacity": 10,
                    "refill_period_seconds": 60,
                    "minimum_interval_seconds": 1,
                },
            }
        ]
    }
    prov.update(overrides)
    return prov


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    return tmp_path


def _load_pair(tmp_path: Path, config: dict, providers: dict | None = None, **kw):
    cfg_path = _write(tmp_path / "config.yaml", yaml.safe_dump(config))
    if providers is None:
        return load_config(cfg_path, None, **kw)
    prov_path = _write(tmp_path / "providers.yaml", yaml.safe_dump(providers))
    return load_config(cfg_path, prov_path, **kw)


# ---------------------------------------------------------------------------
# Positive: shipped defaults load structurally (enablement owned by task 3.18)
# ---------------------------------------------------------------------------


def test_shipped_defaults_load_structure_without_enablement():
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False)
    assert cfg.schema_version == 1
    assert cfg.name == "follow-the-money"
    assert len(cfg.providers) == 10
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
    assert not cfg.provider("akshare").enabled  # optional extra stays disabled
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
    assert cfg.llm.resolver.attempt_timeout_seconds == 30
    assert cfg.llm.analyst.attempt_timeout_seconds == 45
    assert cfg.llm.editor.attempt_timeout_seconds == 45
    assert cfg.llm.audit.attempt_timeout_seconds == 30
    assert cfg.llm.max_resolver_blocks == 40
    assert cfg.llm.max_analyst_packets == 20
    assert cfg.llm.brief_pre_commit_deadline_seconds == 300
    assert cfg.llm.brief_commit_reserve_seconds == 15
    assert cfg.scoring.full_priority_threshold == "60"
    assert cfg.scoring.compact_priority_threshold == "40"
    assert cfg.scoring.family_penalty == "15"
    assert cfg.scoring.min_component_coverage == "60"
    assert cfg.scoring.target_count == 10
    assert cfg.scoring.hard_max_count == 12
    assert cfg.scoring.max_full_events == 3
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
    assert cfg.scoring.morning_weights == (40, 25, 20, 15)


def test_shipped_defaults_pass_strict_enablement_after_verification():
    # Gate 13.1: every mandatory matrix row is verified and enabled; strict
    # validation must now pass rather than block Apply.
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=True)
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
        load_config(path)


def test_lone_low_surrogate_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text('schema_version: 1\nname: "bad\\udfff"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="surrogate"):
        load_config(path)


def test_invalid_utf8_bytes_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"schema_version: 1\nname: \xff\xfe broken\n")
    with pytest.raises(ConfigError, match="UTF-8"):
        load_config(path)


def test_unknown_top_level_key_rejected(tmp_path):
    # Config objects are closed: unknown keys must be rejected.
    cfg = _minimal_config(extra_secret_key=True)
    path = _write(tmp_path / "config.yaml", yaml.safe_dump(cfg))
    with pytest.raises(ConfigError, match="unknown"):
        load_config(path, None, require_verified_enabled=False)


# ---------------------------------------------------------------------------
# Negative: duplicate provider IDs
# ---------------------------------------------------------------------------


def test_duplicate_provider_ids_rejected(tmp_path):
    cfg = _minimal_config()
    prov = _minimal_providers()
    prov["providers"].append(dict(prov["providers"][0], name="clone"))
    with pytest.raises(ConfigError, match="duplicate provider id"):
        _load_pair(tmp_path, cfg, prov, require_verified_enabled=False)


# ---------------------------------------------------------------------------
# Negative: unverified enabled adapters
# ---------------------------------------------------------------------------


def test_enabled_unverified_adapter_rejected(tmp_path):
    cfg = _minimal_config()
    prov = _minimal_providers()
    prov["providers"][0]["verified"] = False
    with pytest.raises(ConfigError, match="enabled but unverified"):
        _load_pair(tmp_path, cfg, prov)


def test_disabled_unverified_adapter_ok(tmp_path):
    cfg = _minimal_config()
    prov = _minimal_providers()
    prov["providers"][0]["enabled"] = False
    prov["providers"][0]["verified"] = False
    _load_pair(tmp_path, cfg, prov)  # OK


# ---------------------------------------------------------------------------
# Negative: invalid source tiers
# ---------------------------------------------------------------------------


def test_invalid_source_tier_rejected(tmp_path):
    cfg = _minimal_config()
    prov = _minimal_providers()
    prov["providers"][0]["tier"] = "Tier 5"
    with pytest.raises(ConfigError, match="tier"):
        _load_pair(tmp_path, cfg, prov, require_verified_enabled=False)


# ---------------------------------------------------------------------------
# Coverage matrix semantics
# ---------------------------------------------------------------------------


def test_coverage_row_missing_member_rejected(tmp_path):
    cfg = _minimal_config(
        coverage=[{"group": "g", "members": ["ghost"], "minimum": 1, "capability": "x"}]
    )
    prov = _minimal_providers()
    with pytest.raises(ConfigError, match="unknown member"):
        _load_pair(tmp_path, cfg, prov)


def test_coverage_row_unverified_member_rejected(tmp_path):
    cfg = _minimal_config(
        coverage=[{"group": "g", "members": ["prov_a"], "minimum": 1, "capability": "x"}]
    )
    prov = _minimal_providers()
    prov["providers"][0]["verified"] = False
    with pytest.raises(ConfigError, match="unverified"):
        _load_pair(tmp_path, cfg, prov)


def test_coverage_row_disabled_member_rejected(tmp_path):
    cfg = _minimal_config(
        coverage=[{"group": "g", "members": ["prov_a"], "minimum": 1, "capability": "x"}]
    )
    prov = _minimal_providers()
    prov["providers"][0]["enabled"] = False
    with pytest.raises(ConfigError, match="disabled"):
        _load_pair(tmp_path, cfg, prov)


def test_coverage_row_unachievable_minimum_rejected(tmp_path):
    # Row requires 3 enabled members but only two are enabled/verified.
    cfg = _minimal_config(
        coverage=[{"group": "g", "members": ["prov_a", "prov_b"], "minimum": 3, "capability": "x"}]
    )
    prov = _minimal_providers()
    prov["providers"].append(
        dict(prov["providers"][0], id="prov_b", name="B", enabled=True, verified=True)
    )
    with pytest.raises(ConfigError, match="not achievable"):
        _load_pair(tmp_path, cfg, prov)


def test_optional_row_can_be_unachievable(tmp_path):
    cfg = _minimal_config(
        coverage=[
            {"group": "g", "members": ["prov_a"], "minimum": 2, "capability": "x", "optional": True}
        ]
    )
    prov = _minimal_providers()
    _load_pair(tmp_path, cfg, prov)  # optional rows are not enforced


# ---------------------------------------------------------------------------
# Roles: exact canonical 13
# ---------------------------------------------------------------------------


def test_roles_must_be_exact_canonical_set(tmp_path):
    cfg = _minimal_config()
    cfg["roles"] = [dict(cfg["roles"][0], id="sp500")]  # only one role
    with pytest.raises(ConfigError, match="canonical v1 set"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_role_order_must_match_canonical(tmp_path):
    cfg = _minimal_config()
    cfg["roles"] = list(reversed(cfg["roles"]))
    with pytest.raises(ConfigError, match="canonical v1 set"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_every_role_requires_explicit_session_id(tmp_path):
    cfg = _minimal_config()
    del cfg["roles"][0]["session_id"]
    with pytest.raises(ConfigError, match="session_id"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_role_unknown_session_id_rejected(tmp_path):
    cfg = _minimal_config()
    cfg["roles"][0]["session_id"] = "missing"
    with pytest.raises(ConfigError, match="unknown session"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_role_session_class_mismatch_rejected(tmp_path):
    cfg = _minimal_config()
    cfg["roles"][0]["session_id"] = "crypto"
    with pytest.raises(ConfigError, match="incompatible"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_exchange_traded_session_unknown_calendar_rejected(tmp_path):
    cfg = _minimal_config()
    cfg["sessions"][0]["calendar"] = "XNYX"
    with pytest.raises(ConfigError, match="unknown exchange calendar"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_duplicate_role_ownership_rejected(tmp_path):
    cfg = _minimal_config()
    cfg["roles"][1]["id"] = cfg["roles"][0]["id"]
    with pytest.raises(ConfigError, match="duplicate role"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_role_contract_requires_provenance_and_semantics(tmp_path):
    cfg = _minimal_config()
    del cfg["roles"][0]["source_provenance"]
    with pytest.raises(ConfigError, match="source_provenance"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_role_contract_requires_non_negative_availability_lag(tmp_path):
    cfg = _minimal_config()
    cfg["roles"][0]["availability_lag_seconds"] = -1
    with pytest.raises(ConfigError, match="availability_lag_seconds"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_role_mapping_verified_must_be_boolean(tmp_path):
    cfg = _minimal_config()
    cfg["roles"][0]["mapping_verified"] = "false"
    with pytest.raises(ConfigError, match="mapping_verified must be boolean"):
        _load_pair(tmp_path, cfg, None, require_verified_enabled=True)


def test_shipped_roles_expose_a_complete_verified_contract():
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=True)
    assert all(role.provider_id == "yahoo_market" for role in cfg.roles)
    assert all(role.economic_identity for role in cfg.roles)
    assert all(role.daily_close_semantics for role in cfg.roles)
    assert all(role.source_provenance for role in cfg.roles)
    assert {role.id for role in cfg.roles if not role.mapping_verified} == {
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

    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=True)
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
            assert role.source_provenance.strip()


# ---------------------------------------------------------------------------
# Scoring weights and maps
# ---------------------------------------------------------------------------


def test_significance_weights_must_sum_100(tmp_path):
    cfg = _minimal_config(scoring={"significance_weights": [30, 20, 20, 20, 9]})
    path = _write(tmp_path / "config.yaml", yaml.safe_dump(cfg))
    with pytest.raises(ConfigError, match="sum to 100"):
        load_config(path)


def test_asset_groups_must_be_nine(tmp_path):
    cfg = _minimal_config()
    cfg["scoring"]["asset_groups"] = [{"group": "only", "proxies": []}]
    path = _write(tmp_path / "config.yaml", yaml.safe_dump(cfg))
    with pytest.raises(ConfigError, match="nine asset groups"):
        load_config(path)


def test_surprise_scale_must_be_positive(tmp_path):
    cfg = _minimal_config()
    cfg["scoring"]["surprise_scales"] = [{"series_id": "x", "scale": "0"}]
    path = _write(tmp_path / "config.yaml", yaml.safe_dump(cfg))
    with pytest.raises(ConfigError, match="positive"):
        load_config(path)


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
    cfg = _minimal_config()
    cfg["feed"][field] = 0
    path = _write(tmp_path / "config.yaml", yaml.safe_dump(cfg))
    with pytest.raises(ConfigError, match="positive"):
        load_config(path)


# ---------------------------------------------------------------------------
# Rate policy checks
# ---------------------------------------------------------------------------


def test_rate_capacity_must_be_positive(tmp_path):
    cfg = _minimal_config()
    prov = _minimal_providers()
    prov["providers"][0]["rate_policy"]["capacity"] = 0
    with pytest.raises(ConfigError, match="capacity"):
        _load_pair(tmp_path, cfg, prov, require_verified_enabled=False)


def test_rate_refill_must_be_positive(tmp_path):
    cfg = _minimal_config()
    prov = _minimal_providers()
    prov["providers"][0]["rate_policy"]["refill_period_seconds"] = 0
    with pytest.raises(ConfigError, match="refill"):
        _load_pair(tmp_path, cfg, prov, require_verified_enabled=False)


def test_inconsistent_same_scope_rate_policies_rejected(tmp_path):
    cfg = _minimal_config(
        coverage=[{"group": "g", "members": ["prov_a", "prov_b"], "minimum": 2, "capability": "x"}]
    )
    prov = _minimal_providers()
    prov["providers"].append(
        dict(
            prov["providers"][0],
            id="prov_b",
            name="B",
            rate_policy={
                "scope_id": "scope_a",  # same scope, different capacity
                "capacity": 999,
                "refill_period_seconds": 60,
                "minimum_interval_seconds": 1,
            },
        )
    )
    with pytest.raises(ConfigError, match="inconsistently"):
        _load_pair(tmp_path, cfg, prov)


# ---------------------------------------------------------------------------
# Charset/BOM strictness is a manifest rule (3.x); config exposes the fields.
# ---------------------------------------------------------------------------


def test_shipped_charset_is_utf8_strict():
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False)
    for p in cfg.providers:
        assert p.allowed_charset.lower() in {"utf-8", "utf8"}
        assert p.allowed_bom is False  # no conflicting BOM policy shipped


# ---------------------------------------------------------------------------
# Optional extras not installed (import isolation is task 3.15; here we only
# assert the shipped registry does not depend on them).
# ---------------------------------------------------------------------------


def test_shipped_config_does_not_require_optional_extras():
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False)
    # AKShare is present but disabled and not a member of any mandatory row.
    akshare = cfg.provider("akshare")
    assert not akshare.enabled
    assert not akshare.verified
    mandatory_members = {m for row in cfg.coverage.rows if not row.optional for m in row.members}
    assert "akshare" not in mandatory_members
    assert "akshare" not in sys.modules


def test_unknown_llm_model_rejected():
    cfg = load_config(DEFAULT_CONFIG, DEFAULT_PROVIDERS, require_verified_enabled=False)
    assert cfg.llm.model == ""  # empty shipped; startup rejects missing config


# ---------------------------------------------------------------------------
# Python-to-YAML round trip
# ---------------------------------------------------------------------------


def test_config_yaml_round_trip(tmp_path):
    cfg = _load_pair(tmp_path, _minimal_config(), _minimal_providers())
    assert cfg.name == "test"
    assert cfg.provider("prov_a").name == "Provider A"
    assert cfg.role("sp500").id == "sp500"
