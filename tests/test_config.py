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


def test_manifest_units_and_pagination_are_closed(tmp_path: Path):
    config, providers, manifests = _copy_contracts(tmp_path)
    sec_path = manifests / "sec_edgar" / "manifest.yaml"
    sec = _yaml(sec_path)
    sec["units"]["unexpected"] = "usd"
    _write(sec_path, sec)
    with pytest.raises(ConfigError, match=r"SEC v[34] units"):
        _load(config, providers, manifests)

    cftc_root = tmp_path / "cftc"
    cftc_root.mkdir()
    config, providers, manifests = _copy_contracts(cftc_root)
    cftc_path = manifests / "cftc" / "manifest.yaml"
    cftc = _yaml(cftc_path)
    cftc["pagination"] = "none"
    _write(cftc_path, cftc)
    with pytest.raises(ConfigError, match="page-number"):
        _load(config, providers, manifests)


def test_watched_form4_issuer_selection_is_closed_and_ordered(tmp_path: Path):
    for mutation, message in (
        (lambda value: value.pop("watched_form4_issuers"), "missing"),
        (lambda value: value["watched_form4_issuers"][0].update({"unexpected": True}), "unknown"),
        (
            lambda value: value["watched_form4_issuers"].append(
                {"cik": "0001067983", "name": "Duplicate"}
            ),
            "duplicate",
        ),
        (lambda value: value["watched_form4_issuers"][0].update({"cik": "bad"}), "normalized"),
    ):
        case_root = tmp_path / message
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        value = _yaml(config)
        mutation(value)
        _write(config, value)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)

    case_root = tmp_path / "reordered"
    case_root.mkdir()
    config, providers, manifests = _copy_contracts(case_root)
    value = _yaml(config)
    value["watched_form4_issuers"] = [
        {"cik": "0000000002", "name": "B"},
        {"cik": "0000000001", "name": "A"},
    ]
    _write(config, value)
    with pytest.raises(ConfigError, match="ordered"):
        _load(config, providers, manifests)


def test_watched_beneficial_ownership_filer_selection_is_closed_and_exact(tmp_path: Path):
    for mutation, message in (
        (lambda value: value.pop("watched_beneficial_ownership_filers"), "missing"),
        (
            lambda value: value["watched_beneficial_ownership_filers"][0].update(
                {"unexpected": True}
            ),
            "unknown",
        ),
        (
            lambda value: value["watched_beneficial_ownership_filers"][0].update({"cik": "bad"}),
            "normalized",
        ),
        (
            lambda value: value["watched_beneficial_ownership_filers"][0].update(
                {"cik": "0000000001"}
            ),
            "only Berkshire",
        ),
    ):
        root = tmp_path / message.replace(" ", "-")
        root.mkdir()
        config, providers, manifests = _copy_contracts(root)
        value = _yaml(config)
        mutation(value)
        _write(config, value)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)

    root = tmp_path / "duplicate"
    root.mkdir()
    config, providers, manifests = _copy_contracts(root)
    value = _yaml(config)
    value["watched_beneficial_ownership_filers"].append({"cik": "0001067983", "name": "Duplicate"})
    _write(config, value)
    with pytest.raises(ConfigError, match="duplicate"):
        _load(config, providers, manifests)


def test_sec_v4_beneficial_ownership_manifest_bounds_are_closed(tmp_path: Path):
    case_root = tmp_path / "v4"
    case_root.mkdir()
    config, providers, manifests = _copy_contracts(case_root)
    config_value = _yaml(config)
    config_value["feed"]["pre_commit_deadline_seconds"] = 720
    _write(config, config_value)
    manifest_path = manifests / "sec_edgar" / "manifest.yaml"
    manifest = _yaml(manifest_path)
    manifest["contract_version"] = 4
    manifest["beneficial_ownership"] = {
        "max_filings_per_window": 7,
        "max_history_files": 1,
        "max_historical_candidate_documents": 64,
        "max_reporting_positions_per_filing": 32,
        "structured_formats": ["edgarSubmission"],
        "schema_versions": ["X0202"],
        "locator_prefixes": ["xslSCHEDULE_13G_X01", "xslSCHEDULE_13G_X02"],
    }
    _write(manifest_path, manifest)
    loaded = _load(config, providers, manifests)
    sec = loaded.provider("sec_edgar")
    assert sec.contract_version == 4
    assert sec.beneficial_ownership_max_filings_per_window == 7
    assert sec.beneficial_ownership_max_history_files == 1
    assert sec.beneficial_ownership_max_historical_candidate_documents == 64
    assert sec.beneficial_ownership_max_reporting_positions == 32
    assert sec.beneficial_ownership_schema_versions == ("X0202",)
    from follow_the_money.providers.manifest import sec_send_shape, validate_sec_deadline

    shape = sec_send_shape(loaded, sec)
    assert shape.total == 118
    assert shape.spacing_floor_seconds == 117
    assert validate_sec_deadline(loaded, sec).total == 118

    mutations = (
        (lambda value: value.pop("beneficial_ownership"), "required"),
        (
            lambda value: value["beneficial_ownership"].update({"unexpected": True}),
            "unknown keys",
        ),
        (
            lambda value: value["beneficial_ownership"].update({"max_history_files": 2}),
            "max history files",
        ),
        (
            lambda value: value["beneficial_ownership"].update({"schema_versions": ["X0201"]}),
            "schema_versions",
        ),
    )
    for index, (mutation, message) in enumerate(mutations):
        root = tmp_path / f"v4-mutation-{index}"
        root.mkdir()
        mutated_config, mutated_providers, mutated_manifests = _copy_contracts(root)
        config_value = _yaml(mutated_config)
        config_value["feed"]["pre_commit_deadline_seconds"] = 720
        _write(mutated_config, config_value)
        value = _yaml(mutated_manifests / "sec_edgar" / "manifest.yaml")
        value["contract_version"] = 4
        value["beneficial_ownership"] = dict(manifest["beneficial_ownership"])
        mutation(value)
        _write(mutated_manifests / "sec_edgar" / "manifest.yaml", value)
        with pytest.raises(ConfigError, match=message):
            _load(mutated_config, mutated_providers, mutated_manifests)


def test_sec_v3_form4_manifest_section_is_exact_and_required(tmp_path: Path):
    cases = (
        (lambda form4: form4.pop("max_filings_per_window"), "required"),
        (lambda form4: form4.update({"max_filings_per_window": 19}), "must be 20"),
        (
            lambda form4: form4.update({"ownership_xml_schema_versions": ["X0608"]}),
            "ownership_xml_schema_versions",
        ),
        (lambda form4: form4.update({"unexpected": True}), "unknown keys"),
    )
    for index, (mutation, message) in enumerate(cases):
        case_root = tmp_path / f"v3-{index}"
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        manifest_path = manifests / "sec_edgar" / "manifest.yaml"
        manifest = _yaml(manifest_path)
        mutation(manifest["form4"])
        _write(manifest_path, manifest)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)

    case_root = tmp_path / "v2-form4"
    case_root.mkdir()
    config, providers, manifests = _copy_contracts(case_root)
    manifest_path = manifests / "sec_edgar" / "manifest.yaml"
    manifest = _yaml(manifest_path)
    manifest["contract_version"] = 2
    _write(manifest_path, manifest)
    with pytest.raises(ConfigError, match="only supported by SEC v3"):
        _load(config, providers, manifests)


def test_supported_contract_versions_are_explicit_and_bounded():
    from follow_the_money.providers.manifest import SUPPORTED_CONTRACT_VERSIONS

    assert SUPPORTED_CONTRACT_VERSIONS["sec_edgar"] == frozenset({1, 2, 3, 4})
    assert SUPPORTED_CONTRACT_VERSIONS["cftc"] == frozenset({1, 2})
    assert all(
        versions == frozenset({1})
        for provider_id, versions in SUPPORTED_CONTRACT_VERSIONS.items()
        if provider_id not in {"sec_edgar", "cftc"}
    )


def test_config_snapshot_has_no_runtime_root_or_removed_surface():
    cfg = _load()
    from follow_the_money.feed.cli import _feed_config_snapshot

    snapshot = _feed_config_snapshot(cfg)["snapshot"]
    assert "runtime_state_root" not in snapshot
    assert set(snapshot) == {
        "name",
        "feed",
        "coverage",
        "watched_companies",
        "watched_form4_issuers",
        "watched_beneficial_ownership_filers",
    }
    assert snapshot["watched_form4_issuers"] == [
        {"cik": "0001067983", "name": "Berkshire Hathaway"}
    ]
    assert snapshot["watched_beneficial_ownership_filers"] == [
        {"cik": "0001067983", "name": "Berkshire Hathaway"}
    ]

    changed = dict(snapshot)
    changed["watched_beneficial_ownership_filers"] = [
        {"cik": "0001067983", "name": "Changed audit label"}
    ]
    from follow_the_money.canonical import canonical_digest

    assert canonical_digest(changed) != canonical_digest(snapshot)


VERIFIED_WATCHED_CIKS = (
    "0000949509",
    "0001061768",
    "0001067983",
    "0001135730",
    "0001167483",
    "0001336528",
    "0001649339",
    "0001697748",
)


def test_shipped_watched_company_ciks_are_exact_and_runtime_ordered():
    """Pin the shipped watched-CIK set and its runtime-derived CIK ordering.

    The exact set is the verified SEC identity set documented in
    `references/provider-source-verification.md`. `config/config.yaml` is
    deliberately not in CIK order, so a snapshot that matches the checked-in
    order instead of normalized-CIK order fails this regression.
    """
    cfg = _load()
    from follow_the_money.feed.cli import _feed_config_snapshot

    checked_in = [company.cik for company in cfg.watched_companies]
    assert set(checked_in) == set(VERIFIED_WATCHED_CIKS)
    assert checked_in != sorted(checked_in)

    snapshot = _feed_config_snapshot(cfg)["snapshot"]
    assert [company["cik"] for company in snapshot["watched_companies"]] == sorted(
        VERIFIED_WATCHED_CIKS
    )


def test_watched_company_cik_selection_is_fail_closed(tmp_path: Path):
    for mutation, message in (
        (lambda value: value["watched_companies"][0].update({"cik": "1067983"}), "normalized"),
        (
            lambda value: value["watched_companies"].append(
                {"cik": "0001067983", "name": "Duplicate", "tickers": []}
            ),
            "duplicate",
        ),
    ):
        case_root = tmp_path / message
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        value = _yaml(config)
        mutation(value)
        _write(config, value)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)
