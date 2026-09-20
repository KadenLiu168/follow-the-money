"""Feed-only configuration regressions."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from follow_the_money.canonical import canonical_digest
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
    for provider_id in CONTENT_PROVIDERS + EXCHANGE_CONTENT_PROVIDERS:
        assert SUPPORTED_CONTRACT_VERSIONS[provider_id] == frozenset({1, 2})
    assert all(
        versions == frozenset({1})
        for provider_id, versions in SUPPORTED_CONTRACT_VERSIONS.items()
        if provider_id
        not in {"sec_edgar", "cftc"} | set(CONTENT_PROVIDERS + EXCHANGE_CONTENT_PROVIDERS)
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


def test_config_snapshot_embeds_source_content_deadline_headroom():
    cfg = _load()
    from follow_the_money.feed.cli import _feed_config_snapshot

    snapshot = _feed_config_snapshot(cfg)["snapshot"]
    assert (
        snapshot["feed"]["source_content_request_network_headroom_seconds"]
        == cfg.feed.source_content_request_network_headroom_seconds
    )


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


CONTENT_PROVIDERS = ("federal_reserve", "pboc")
EXCHANGE_CONTENT_PROVIDERS = ("sse", "szse")
PRODUCTION_CONTENT = {
    "acquisition": "detail_document",
    "extraction_method": "official_html_text_v1",
    "allowed_content_types": ["text/html"],
    "max_document_bytes": 2097152,
    "max_text_chars": 12000,
    "max_detail_documents_per_window": 50,
    "required_for_selected_item": True,
}
EXCHANGE_CONTENT = {
    **PRODUCTION_CONTENT,
    "max_discovery_pages_per_window": 10,
    "discovery_order": "published_at_descending",
}


def test_shipped_provider_v2_content_contracts_resolve_exactly():
    cfg = _load()
    for provider_id in CONTENT_PROVIDERS:
        provider = cfg.provider(provider_id)
        assert provider.contract_version == 2
        content = provider.source_content
        assert content is not None
        assert content.acquisition == "detail_document"
        assert content.extraction_method == "official_html_text_v1"
        assert content.allowed_content_types == ("text/html",)
        assert content.max_document_bytes == 2097152
        assert content.max_text_chars == 12000
        assert content.max_detail_documents_per_window == 50
        assert content.required_for_selected_item is True
        assert content.max_discovery_pages_per_window is None
        assert content.discovery_order is None
    for provider_id in EXCHANGE_CONTENT_PROVIDERS:
        content = cfg.provider(provider_id).source_content
        assert content is not None
        assert content.max_discovery_pages_per_window == 10
        assert content.discovery_order == "published_at_descending"
    for provider_id in ("bls", "nbs", "sec_edgar", "cftc"):
        assert cfg.provider(provider_id).source_content is None


def test_provider_content_contract_rejects_every_unsupported_mutation(tmp_path: Path):
    cases = [
        (lambda content: content.pop("max_text_chars"), "missing required keys"),
        (lambda content: content.update({"undeclared": 1}), "unknown keys"),
        (lambda content: content.update({"acquisition": "index_entry"}), "acquisition must be"),
        (
            lambda content: content.update({"extraction_method": "readability_v1"}),
            "extraction method",
        ),
        (
            lambda content: content.update({"allowed_content_types": ["text/html", "text/plain"]}),
            "content types",
        ),
        (
            lambda content: content.update({"allowed_content_types": ["application/pdf"]}),
            "content types",
        ),
        (lambda content: content.update({"max_document_bytes": 2097153}), "max_document_bytes"),
        (lambda content: content.update({"max_text_chars": 12001}), "max_text_chars"),
        (
            lambda content: content.update({"max_detail_documents_per_window": 51}),
            "max_detail_documents",
        ),
        (
            lambda content: content.update({"required_for_selected_item": False}),
            "required for every",
        ),
        (lambda content: content.update({"max_discovery_pages_per_window": 10}), "unknown keys"),
        (
            lambda content: content.update({"discovery_order": "published_at_descending"}),
            "unknown keys",
        ),
    ]
    for index, (mutation, message) in enumerate(cases):
        case_root = tmp_path / f"content-mutation-{index}"
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        path = manifests / "federal_reserve" / "manifest.yaml"
        value = _yaml(path)
        mutation(value["content"])
        _write(path, value)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)


def test_exchange_content_contract_requires_the_bounded_discovery_contract(tmp_path: Path):
    cases = [
        (lambda content: content.pop("max_discovery_pages_per_window"), "missing required keys"),
        (lambda content: content.update({"max_discovery_pages_per_window": 11}), "discovery pages"),
        (lambda content: content.pop("discovery_order"), "missing required keys"),
        (
            lambda content: content.update({"discovery_order": "published_at_ascending"}),
            "discovery order",
        ),
    ]
    for index, (mutation, message) in enumerate(cases):
        case_root = tmp_path / f"exchange-mutation-{index}"
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        path = manifests / "sse" / "manifest.yaml"
        value = _yaml(path)
        mutation(value["content"])
        _write(path, value)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)


def test_content_section_is_forbidden_outside_the_v2_target_contracts(tmp_path: Path):
    for index, provider_id in enumerate(("bls", "nbs")):
        case_root = tmp_path / f"foreign-content-{index}"
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        path = manifests / provider_id / "manifest.yaml"
        value = _yaml(path)
        value["content"] = dict(PRODUCTION_CONTENT)
        _write(path, value)
        with pytest.raises(ConfigError, match="content section is only supported"):
            _load(config, providers, manifests)

    case_root = tmp_path / "version-three"
    case_root.mkdir()
    config, providers, manifests = _copy_contracts(case_root)
    path = manifests / "federal_reserve" / "manifest.yaml"
    value = _yaml(path)
    value["contract_version"] = 3
    _write(path, value)
    with pytest.raises(ConfigError, match="unsupported contract_version"):
        _load(config, providers, manifests)


def test_provider_contract_snapshot_embeds_the_content_contract():
    from follow_the_money.feed.cli import _provider_contract_snapshots

    cfg = _load()
    snapshots = {entry["provider_id"]: entry for entry in _provider_contract_snapshots(cfg)}
    sse = snapshots["sse"]["snapshot"]
    assert sse["contract_version"] == 2
    assert sse["content"] == EXCHANGE_CONTENT
    assert snapshots["sse"]["hash"] == canonical_digest(sse)
    assert "content" not in snapshots["nbs"]["snapshot"]


def test_source_content_network_headroom_is_required_and_closed(tmp_path: Path):
    assert _load().feed.source_content_request_network_headroom_seconds == 120

    for mutation, message in (
        (lambda feed: feed.pop("source_content_request_network_headroom_seconds"), "missing"),
        (
            lambda feed: feed.update({"source_content_request_network_headroom_seconds": 0}),
            "positive",
        ),
        (
            lambda feed: feed.update({"source_content_request_network_headroom_seconds": True}),
            "integer",
        ),
    ):
        case_root = tmp_path / f"headroom-{message}"
        case_root.mkdir()
        config, providers, manifests = _copy_contracts(case_root)
        value = _yaml(config)
        mutation(value["feed"])
        _write(config, value)
        with pytest.raises(ConfigError, match=message):
            _load(config, providers, manifests)


def _with_feed(cfg, **overrides):
    from dataclasses import replace

    return replace(cfg, feed=replace(cfg.feed, **overrides))


def _with_provider(cfg, provider_id: str, **overrides):
    from dataclasses import replace

    providers = tuple(
        replace(provider, **overrides) if provider.id == provider_id else provider
        for provider in cfg.providers
    )
    return replace(cfg, providers=providers)


def test_source_content_send_shape_covers_every_shared_scope():
    from follow_the_money.providers.manifest import validate_source_content_deadline

    cfg = _load()
    shapes = validate_source_content_deadline(cfg)

    assert set(shapes) == {"china_gov", "us_gov"}
    us_gov = shapes["us_gov"]
    assert (us_gov.base_requests, us_gov.exchange_discovery_pages, us_gov.detail_documents) == (
        3,
        0,
        50,
    )
    assert us_gov.total == 53
    china_gov = shapes["china_gov"]
    assert (
        china_gov.base_requests,
        china_gov.exchange_discovery_pages,
        china_gov.detail_documents,
    ) == (4, 18, 150)
    assert china_gov.total == 172

    # Every affected scope still re-enters the managed-send boundary with the
    # exact configured headroom and commit reserve inside the deadline.
    for scope_id, shape in shapes.items():
        assert shape.scope_id == scope_id
        reference = cfg.provider("federal_reserve").rate_policy
        assert (
            shape.policy.capacity,
            shape.policy.refill_period_seconds,
            shape.policy.minimum_interval_seconds,
        ) == (
            reference.capacity,
            reference.refill_period_seconds,
            reference.minimum_interval_seconds,
        )
        assert (
            shape.managed_send_floor
            + (
                cfg.feed.source_content_request_network_headroom_seconds
                + cfg.feed.commit_reserve_seconds
            )
            <= cfg.feed.pre_commit_deadline_seconds
        )


def test_source_content_deadline_rejects_an_inadmissible_configured_deadline():
    from follow_the_money.providers.manifest import validate_source_content_deadline

    cfg = _load()
    china_gov = validate_source_content_deadline(cfg)["china_gov"]
    required = china_gov.managed_send_floor + (
        cfg.feed.source_content_request_network_headroom_seconds + cfg.feed.commit_reserve_seconds
    )
    assert required == 591

    admissible = _with_feed(cfg, pre_commit_deadline_seconds=required)
    assert "china_gov" in validate_source_content_deadline(admissible)

    with pytest.raises(ValueError, match="china_gov"):
        validate_source_content_deadline(_with_feed(cfg, pre_commit_deadline_seconds=required - 1))


def test_source_content_deadline_fails_closed_on_missing_overflowing_and_incompatible_bounds():
    from dataclasses import replace

    from follow_the_money.providers.manifest import validate_source_content_deadline

    cfg = _load()
    content = cfg.provider("federal_reserve").source_content
    assert content is not None

    for bound, message in (
        (None, "integer"),
        (True, "integer"),
        (0, "positive"),
        (2**31, "representable"),
    ):
        broken = _with_provider(
            cfg,
            "federal_reserve",
            source_content=replace(content, max_detail_documents_per_window=bound),
        )
        with pytest.raises((TypeError, ValueError), match=message):
            validate_source_content_deadline(broken)

    from follow_the_money.config.model import RatePolicy

    inconsistent = _with_provider(
        cfg,
        "cftc",
        rate_policy=RatePolicy(
            scope_id="us_gov",
            capacity=5,
            refill_period_seconds=60,
            minimum_interval_seconds=1,
        ),
    )
    with pytest.raises(ValueError, match="inconsistent"):
        validate_source_content_deadline(inconsistent)


def test_inadmissible_source_content_deadline_fails_before_config_resolution_completes(
    tmp_path: Path,
):
    case_root = tmp_path / "source-content-deadline"
    case_root.mkdir()
    config, providers, manifests = _copy_contracts(case_root)
    value = _yaml(config)
    # The unchanged SEC budget still fits the configured deadline; only the
    # shared source-content scope no longer does.
    value["feed"]["source_content_request_network_headroom_seconds"] = 250
    _write(config, value)
    with pytest.raises(ConfigError, match="source content"):
        _load(config, providers, manifests)
