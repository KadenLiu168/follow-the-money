"""ECO-26 source-authority and single-resolved-contract tests.

These tests deliberately mutate copied checked-in contracts. Expected values
are literal so a second parser cannot make the test tautological.
"""

from __future__ import annotations

import inspect
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
        require_verified_enabled=True,
    )


@pytest.mark.parametrize("authority_key", ["providers", "coverage"])
def test_application_file_cannot_declare_provider_authority(tmp_path: Path, authority_key: str):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config[authority_key] = []
    _write_yaml(config_path, config)

    with pytest.raises(ConfigError, match="unknown keys"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=True,
        )


def test_explicit_provider_authorities_must_be_readable(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers_path.unlink()

    with pytest.raises(ConfigError, match="cannot read config"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=True,
        )


def test_explicit_provider_authorities_must_be_valid(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    providers_path.write_text("providers: [", encoding="utf-8")

    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            require_verified_enabled=True,
        )


def test_complete_contract_resolves_at_an_unrelated_path(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path / "unrelated")

    cfg = load_config(
        config_path,
        providers_path,
        manifest_root=manifest_root,
        require_verified_enabled=True,
    )

    assert cfg.name == "follow-the-money"
    assert cfg.provider("federal_reserve").enabled is True
    assert cfg.provider("federal_reserve").coverage_groups == (
        "future_calendar",
        "us_official_macro_policy",
    )


def test_load_config_exposes_only_explicit_strict_authorities():
    parameters = inspect.signature(load_config).parameters

    assert parameters["providers_path"].default is inspect.Parameter.empty
    assert parameters["manifest_root"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["manifest_root"].default is inspect.Parameter.empty
    assert "strict" not in parameters


def test_load_config_rejects_implicit_authorities_and_removed_strict_keyword(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)

    with pytest.raises(TypeError):
        load_config(config_path, providers_path)
    with pytest.raises(TypeError):
        load_config(
            config_path,
            providers_path,
            manifest_root=manifest_root,
            strict=True,
        )


def _mutate_yahoo_mapping(manifest_root: Path, role_id: str, **changes: object) -> None:
    path = manifest_root / "yahoo_market" / "manifest.yaml"
    data = _read_yaml(path)
    mapping = next(item for item in data["role_mappings"] if item["role_id"] == role_id)
    mapping.update(changes)
    _write_yaml(path, data)


def test_yaml_owned_values_reach_resolved_model(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    data = _read_yaml(config_path)
    data["timezone"] = "UTC"
    data["feed"]["lock_timeout_seconds"] = 17
    data["scoring"]["relevance_weights"] = [45, 25, 15, 15]
    data["market_state"]["required_known_dimensions"] = 3
    data["calendar"]["max_items"] = 9
    data["safety_lexicon"]["zh_terms"] = ["仅测试词"]
    data["rate_registry"]["crash_cooldown_hours"] = 11
    _write_yaml(config_path, data)

    cfg = _strict_load(config_path, providers_path, manifest_root)

    assert cfg.timezone == "UTC"
    assert cfg.feed.lock_timeout_seconds == 17
    assert cfg.scoring.relevance_weights == (45, 25, 15, 15)
    assert cfg.market_state.required_known_dimensions == 3
    assert cfg.calendar.max_items == 9
    assert cfg.safety_lexicon.zh_terms == ("仅测试词",)
    assert cfg.rate_registry.crash_cooldown_hours == 11


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("top", "timezone"),
        ("feed", "lock_timeout_seconds"),
        ("scoring", "relevance_weights"),
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


def test_strict_roles_reject_parallel_source_provenance_mirror(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][0]["source_provenance"] = "legacy-parallel-source"
    _write_yaml(config_path, config)

    with pytest.raises(ConfigError, match="unknown keys.*source_provenance"):
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


@pytest.mark.parametrize(
    ("role_id", "changes", "error"),
    [
        (
            "sp500",
            {"mapping_verified": True, "verification_provenance": None},
            "verification_provenance",
        ),
        ("hsi", {"mapping_verified": False, "reason": ""}, "reason"),
        ("sp500", {"mapping_verified": True, "reason": "duplicate branch"}, "exclusive"),
        (
            "hsi",
            {
                "mapping_verified": False,
                "verification_provenance": {
                    "kind": "repository_fixture",
                    "reference": "providers/yahoo_market/fixtures/chart.json",
                },
            },
            "exclusive",
        ),
    ],
)
def test_mapping_verification_state_is_closed(
    tmp_path: Path, role_id: str, changes: dict[str, object], error: str
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _mutate_yahoo_mapping(manifest_root, role_id, **changes)

    with pytest.raises(ConfigError, match=error):
        _strict_load(config_path, providers_path, manifest_root)


def test_valid_repository_fixture_provenance_resolves_without_network(tmp_path: Path, monkeypatch):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={
            "kind": "repository_fixture",
            "reference": "providers/yahoo_market/fixtures/chart.json",
        },
    )

    def no_network(*_args, **_kwargs):
        raise AssertionError("mapping validation must not make a network request")

    monkeypatch.setattr("httpx.Client", no_network)
    cfg = _strict_load(config_path, providers_path, manifest_root)
    mapping = next(
        item for item in cfg.provider("yahoo_market").role_mappings if item["role_id"] == "sp500"
    )
    assert mapping["verification_provenance"] == {
        "kind": "repository_fixture",
        "reference": "providers/yahoo_market/fixtures/chart.json",
    }


def test_repository_fixture_symlink_cannot_escape_provider(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    escaped = manifest_root / "yahoo_market" / "fixtures" / "escaped.json"
    escaped.symlink_to(outside)
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={
            "kind": "repository_fixture",
            "reference": "providers/yahoo_market/fixtures/escaped.json",
        },
    )

    with pytest.raises(ConfigError, match="owning Provider"):
        _strict_load(config_path, providers_path, manifest_root)


def test_valid_authoritative_https_provenance_uses_existing_manifest_authority(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest = _read_yaml(manifest_root / "yahoo_market" / "manifest.yaml")
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={
            "kind": "authoritative_https",
            "reference": manifest["verification"]["contract_url"],
        },
    )

    cfg = _strict_load(config_path, providers_path, manifest_root)
    mapping = next(
        item for item in cfg.provider("yahoo_market").role_mappings if item["role_id"] == "sp500"
    )
    assert mapping["verification_provenance"]["kind"] == "authoritative_https"


@pytest.mark.parametrize(
    "contract_url",
    [
        "https://contracts.example:bad/provider-contract",
        "not a url",
    ],
)
def test_malformed_manifest_contract_url_fails_as_configuration(tmp_path: Path, contract_url: str):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "yahoo_market" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    manifest["verification"]["contract_url"] = contract_url
    _write_yaml(manifest_path, manifest)

    with pytest.raises(ConfigError, match="contract_url"):
        _strict_load(config_path, providers_path, manifest_root)


@pytest.mark.parametrize(
    "reference",
    [
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EHSI",
        "https://query1.finance.yahoo.com/unrelated/document",
    ],
)
def test_yahoo_authoritative_https_provenance_is_bound_to_mapping_instrument(
    tmp_path: Path, reference: str
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={"kind": "authoritative_https", "reference": reference},
    )

    with pytest.raises(ConfigError, match="chart URL|mapping instrument"):
        _strict_load(config_path, providers_path, manifest_root)


@pytest.mark.parametrize(
    "reference",
    [
        "https://query1.finance.yahoo.com/%",
        " https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC",
        "https://query1.finance.yahoo.com.:443/v8/finance/chart/%5EGSPC",
        "https://query1.finance.yahoo.com:443/v8/finance/chart/%5EGSPC",
    ],
)
def test_authoritative_https_provenance_must_already_be_canonical(tmp_path: Path, reference: str):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={"kind": "authoritative_https", "reference": reference},
    )

    with pytest.raises(ConfigError, match="canonical|verification reference"):
        _strict_load(config_path, providers_path, manifest_root)


@pytest.mark.parametrize(
    ("grammar", "query", "accepted"),
    [
        ("numeric", "period=-1", True),
        ("numeric", "period=01", False),
        ("numeric", "period=1.", False),
        ("numeric", "period=.1", False),
        ("plain", "period=abc-_.~", True),
        ("plain", "period=a+b", False),
        ("plain", "period=a%2Bb", False),
    ],
)
def test_authoritative_https_query_uses_provider_canonical_grammar(
    tmp_path: Path, grammar: str, query: str, accepted: bool
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "yahoo_market" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    manifest["source_link_hosts"].append(
        {
            "host": "query1.finance.yahoo.com",
            "allow_subdomains": False,
            "allowed_ports": [443],
            "allowed_query_params": ["period"],
            "query_value_grammar": grammar,
            "drop_query_params": [],
        }
    )
    mapping = next(item for item in manifest["role_mappings"] if item["role_id"] == "sp500")
    mapping["verification_provenance"] = {
        "kind": "authoritative_https",
        "reference": f"https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?{query}",
    }
    _write_yaml(manifest_path, manifest)

    if accepted:
        _strict_load(config_path, providers_path, manifest_root)
    else:
        with pytest.raises(ConfigError, match="verification reference|Provider URL policy"):
            _strict_load(config_path, providers_path, manifest_root)


@pytest.mark.parametrize(
    ("reference", "error"),
    [
        ("providers/yahoo_market/fixtures/missing.json", "does not exist"),
        ("/tmp/market-evidence.json", "repository-relative"),
        ("providers/yahoo_market/../../config/config.yaml", "repository-relative"),
        ("providers/federal_reserve/manifest.yaml", "owning Provider"),
    ],
)
def test_repository_fixture_provenance_is_bounded(tmp_path: Path, reference: str, error: str):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={"kind": "repository_fixture", "reference": reference},
    )

    with pytest.raises(ConfigError, match=error):
        _strict_load(config_path, providers_path, manifest_root)


def test_yahoo_fixture_symbol_must_match_mapping(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    fixture = manifest_root / "yahoo_market" / "fixtures" / "chart.json"
    fixture_data = __import__("json").loads(fixture.read_text(encoding="utf-8"))
    fixture_data["chart"]["result"][0]["meta"]["symbol"] = "^HSI"
    fixture.write_text(__import__("json").dumps(fixture_data), encoding="utf-8")
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={
            "kind": "repository_fixture",
            "reference": "providers/yahoo_market/fixtures/chart.json",
        },
    )

    with pytest.raises(ConfigError, match="meta.symbol"):
        _strict_load(config_path, providers_path, manifest_root)


def test_mapping_tuple_must_match_canonical_role_mirror(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    config = _read_yaml(config_path)
    config["roles"][0]["unit"] = "price"
    _write_yaml(config_path, config)

    with pytest.raises(ConfigError, match="role mapping mirror mismatch"):
        _strict_load(config_path, providers_path, manifest_root)


def test_duplicate_mapping_ids_are_not_collapsed_during_resolution(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "yahoo_market" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    manifest["role_mappings"].append(dict(manifest["role_mappings"][0]))
    _write_yaml(manifest_path, manifest)

    with pytest.raises(ConfigError, match="duplicate role ids"):
        _strict_load(config_path, providers_path, manifest_root)


@pytest.mark.parametrize(
    "reference",
    [
        "http://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC",
        "https://user:pass@query1.finance.yahoo.com/v8/finance/chart/%5EGSPC",
        "https://query1.finance.yahoo.com:8443/v8/finance/chart/%5EGSPC",
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC#fragment",
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?symbol=%5EGSPC",
        "https://evil.example/v8/finance/chart/%5EGSPC",
    ],
)
def test_authoritative_https_provenance_is_policy_checked_without_network(
    tmp_path: Path, reference: str
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    _mutate_yahoo_mapping(
        manifest_root,
        "sp500",
        verification_provenance={"kind": "authoritative_https", "reference": reference},
    )

    with pytest.raises(ConfigError, match="authoritative HTTPS|HTTPS URL|verification reference"):
        _strict_load(config_path, providers_path, manifest_root)


def test_shipped_mapping_inventory_is_exact_and_evidence_backed():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    mappings = {str(item["role_id"]): item for item in cfg.provider("yahoo_market").role_mappings}
    assert tuple(mappings) == (
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
    assert mappings["sp500"]["mapping_verified"] is True
    assert mappings["sp500"]["verification_provenance"] == {
        "kind": "repository_fixture",
        "reference": "providers/yahoo_market/fixtures/chart.json",
    }
    assert mappings["csi300"]["mapping_verified"] is False
    assert "missing" in str(mappings["csi300"]["reason"]).lower()
    assert all(
        item["mapping_verified"] is True or str(item.get("reason", "")).strip()
        for item in mappings.values()
    )
    assert sum(item["mapping_verified"] for item in mappings.values()) == 1


def test_production_yahoo_planning_uses_only_verified_mappings():
    from follow_the_money.feed.cli import _production_adapters
    from follow_the_money.providers.adapters import build_registry

    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    planned = _production_adapters(cfg, build_registry({p.id: p for p in cfg.providers}))

    assert [adapter._role_id for adapter in planned["yahoo_market"]] == ["sp500"]


def test_provider_snapshot_retains_mapping_audit_state():
    from follow_the_money.feed.cli import _provider_contract_snapshots

    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    snapshot = next(
        item for item in _provider_contract_snapshots(cfg) if item["provider_id"] == "yahoo_market"
    )
    mappings = snapshot["snapshot"]["role_mappings"]

    assert [item["role_id"] for item in mappings] == list(cfg.role_ids)
    assert mappings[0]["verification_provenance"]["reference"].endswith(
        "providers/yahoo_market/fixtures/chart.json"
    )
    assert mappings[1]["mapping_verified"] is False
    assert mappings[1]["reason"]


def test_resolved_mapping_and_nested_provenance_are_immutable():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
    mapping = cfg.provider("yahoo_market").role_mappings[0]

    with pytest.raises(TypeError):
        mapping["mapping_verified"] = False  # type: ignore[index]
    with pytest.raises(TypeError):
        mapping["verification_provenance"]["reference"] = "changed"  # type: ignore[index]


def test_enabled_market_provider_with_zero_verified_mappings_fails_static_resolution(
    tmp_path: Path,
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "yahoo_market" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    for mapping in manifest["role_mappings"]:
        mapping["mapping_verified"] = False
        mapping.pop("verification_provenance", None)
        mapping["reason"] = "test mapping is not verified"
    _write_yaml(manifest_path, manifest)

    config = _read_yaml(config_path)
    for role in config["roles"]:
        role["mapping_verified"] = False
    _write_yaml(config_path, config)

    with pytest.raises(ConfigError, match="zero verified|verified runnable"):
        _strict_load(config_path, providers_path, manifest_root)


def test_disabled_market_provider_with_zero_verified_mappings_remains_valid(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    manifest_path = manifest_root / "yahoo_market" / "manifest.yaml"
    manifest = _read_yaml(manifest_path)
    for mapping in manifest["role_mappings"]:
        mapping["mapping_verified"] = False
        mapping.pop("verification_provenance", None)
        mapping["reason"] = "test mapping is not verified"
    _write_yaml(manifest_path, manifest)

    config = _read_yaml(config_path)
    for role in config["roles"]:
        role["mapping_verified"] = False
    _write_yaml(config_path, config)
    registry = _read_yaml(providers_path)
    yahoo_policy = next(item for item in registry["providers"] if item["id"] == "yahoo_market")
    yahoo_policy["enabled"] = False
    yahoo_row = next(row for row in registry["coverage"] if "yahoo_market" in row["members"])
    yahoo_row["members"] = []
    yahoo_row["optional"] = True
    _write_yaml(providers_path, registry)

    cfg = _strict_load(config_path, providers_path, manifest_root)
    assert cfg.provider("yahoo_market").enabled is False


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
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
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
        feed_cli.run_feed(
            config_path=str(config_path),
            output_root=str(output_root),
            runtime_state_root=str(tmp_path / "state"),
        )

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
        feed_cli.run_feed(
            config_path=str(config_path),
            output_root=str(output_root),
            runtime_state_root=str(tmp_path / "state"),
        )

    assert latest.read_bytes() == b"previous-latest"
    assert not (output_root / "rate-registry.json").exists()
    assert (
        not list((output_root / "daily").rglob("*.json"))
        if (output_root / "daily").exists()
        else True
    )


@pytest.mark.parametrize("mutation", ["mapping", "coverage"])
def test_mapping_and_coverage_failures_precede_all_feed_mutation(
    tmp_path: Path, monkeypatch, mutation: str
):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    if mutation == "mapping":
        manifest_path = manifest_root / "yahoo_market" / "manifest.yaml"
        manifest = _read_yaml(manifest_path)
        mapping = next(item for item in manifest["role_mappings"] if item["role_id"] == "sp500")
        mapping.pop("verification_provenance")
        _write_yaml(manifest_path, manifest)
    else:
        registry = _read_yaml(providers_path)
        row = next(row for row in registry["coverage"] if row["group"] == "verified_market_data")
        row["group"] = "china_hk_cross_asset_market"
        row["capability"] = "market_data_all_13_roles"
        _write_yaml(providers_path, registry)

    from follow_the_money.feed import cli as feed_cli

    monkeypatch.setattr(feed_cli, "_default_providers_path", lambda: providers_path)
    monkeypatch.setattr(feed_cli, "_default_manifest_root", lambda: manifest_root)
    output_root = tmp_path / "out"
    with pytest.raises(feed_cli.FeedInputError):
        feed_cli.run_feed(
            config_path=str(config_path),
            output_root=str(output_root),
            runtime_state_root=str(tmp_path / "state"),
        )

    assert not output_root.exists()


def test_market_provider_coverage_rejects_unknown_broad_claim(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    registry = _read_yaml(providers_path)
    row = next(row for row in registry["coverage"] if row["group"] == "verified_market_data")
    row["group"] = "global_cross_asset_all_roles"
    row["capability"] = "global_cross_asset_all_roles"
    _write_yaml(providers_path, registry)

    with pytest.raises(ConfigError, match="market coverage claim"):
        _strict_load(config_path, providers_path, manifest_root)


def test_verified_market_coverage_rejects_non_market_member(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    registry = _read_yaml(providers_path)
    row = next(row for row in registry["coverage"] if row["group"] == "verified_market_data")
    row["members"].append("federal_reserve")
    row["minimum"] = 2
    _write_yaml(providers_path, registry)

    with pytest.raises(ConfigError, match="non-market|verified runnable"):
        _strict_load(config_path, providers_path, manifest_root)


def test_disabled_market_provider_rejects_stale_broad_coverage_label(tmp_path: Path):
    config_path, providers_path, manifest_root = _copy_contracts(tmp_path)
    registry = _read_yaml(providers_path)
    yahoo_policy = next(item for item in registry["providers"] if item["id"] == "yahoo_market")
    yahoo_policy["enabled"] = False
    row = next(row for row in registry["coverage"] if row["group"] == "verified_market_data")
    row.update(
        group="china_hk_cross_asset_market",
        members=[],
        capability="market_data_all_13_roles",
        optional=True,
    )
    _write_yaml(providers_path, registry)

    with pytest.raises(ConfigError, match="unsupported market coverage claim"):
        _strict_load(config_path, providers_path, manifest_root)


def test_existing_v1_role_and_coverage_facts_remain_literal():
    cfg = load_config(
        DEFAULT_CONFIG,
        DEFAULT_PROVIDERS,
        manifest_root=DEFAULT_MANIFEST_ROOT,
        require_verified_enabled=True,
    )
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
        ("csi300", "000300.SS", "index", False),
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
        "verified_market_data",
        "future_calendar",
    )
