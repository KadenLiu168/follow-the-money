"""Manifest-led five-domain Feed bundle regressions."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.canonical import canonical_bytes, canonical_digest, canonical_sha256
from follow_the_money.feed import bundle as bundle_module
from follow_the_money.feed.bundle import (
    DOMAINS,
    BundleError,
    artifact_relative_path,
    build_bundle,
    generation_key,
    load_feed,
    migrate_feed,
    validate_bundle,
)
from follow_the_money.feed.publish import publish_bundle
from follow_the_money.feed.validate import recompute_feed_identity, validate_feed
from follow_the_money.schema import SchemaError, validate_against

T0 = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)
PROVIDERS = (
    "bls",
    "cftc",
    "federal_reserve",
    "nbs",
    "pboc",
    "sec_edgar",
    "sse",
    "szse",
)
PROVIDER_PAYLOADS = {
    "bls": "news",
    "cftc": "positioning",
    "federal_reserve": "policy",
    "nbs": "macro_release",
    "pboc": "policy",
    "sec_edgar": "filing",
    "sse": "news",
    "szse": "news",
}
COVERAGE = (
    {
        "group": "us_official_macro_policy",
        "members": ["federal_reserve", "bls"],
        "minimum": 2,
        "capability": "policy_and_news",
        "optional": False,
    },
    {
        "group": "us_company_filings",
        "members": ["sec_edgar"],
        "minimum": 1,
        "capability": "watched_company_filings",
        "optional": False,
    },
    {
        "group": "china_official_macro_policy",
        "members": ["pboc", "nbs"],
        "minimum": 2,
        "capability": "policy_and_macro_release",
        "optional": False,
    },
    {
        "group": "china_exchange_evidence",
        "members": ["sse", "szse"],
        "minimum": 2,
        "capability": "news",
        "optional": False,
    },
    {
        "group": "cftc_positioning",
        "members": ["cftc"],
        "minimum": 1,
        "capability": "positioning",
        "optional": False,
    },
)


def _ts(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _news(item_id: str = "item-1", at: datetime = T0 - timedelta(hours=1)) -> dict:
    return {
        "id": item_id,
        "provider_id": "bls",
        "source": {
            "id": item_id,
            "name": "BLS",
            "tier": "Tier 1",
            "kind": "news",
            "url": f"https://www.bls.gov/{item_id}",
            "published_at": _ts(at),
            "knowledge_available_at": _ts(at),
        },
        "payload": {
            "type": "news",
            "title": "title",
            "snippet": "snippet",
            "occurred_at": _ts(at),
            "raw_metadata": {},
        },
    }


def _coverage_groups(provider_id: str) -> list[str]:
    return sorted(row["group"] for row in COVERAGE if provider_id in row["members"])


def _feed(items: list[dict] | None = None) -> dict:
    selected = items or []
    contracts = []
    outcomes = []
    for provider_id in PROVIDERS:
        cadence = "weekly" if provider_id == "cftc" else "event_driven"
        freshness = {
            "cadence": cadence,
            "reference_time": "data_as_of" if cadence == "weekly" else "checked_at",
        }
        if cadence == "weekly":
            freshness["valid_for_seconds"] = 604800
        snapshot = {
            "provider_id": provider_id,
            "empty_valid_for_window": True,
            "payload_types": [PROVIDER_PAYLOADS[provider_id]],
            "freshness": freshness,
        }
        contract_hash = canonical_digest(snapshot)
        contracts.append({"provider_id": provider_id, "snapshot": snapshot, "hash": contract_hash})
        provider_items = [item for item in selected if item["provider_id"] == provider_id]
        state = "healthy"
        checked = _ts(T0 + timedelta(minutes=1))
        outcome = {
            "provider_id": provider_id,
            "state": state,
            "attempted": 1,
            "fetched": 1,
            "succeeded": True,
            "empty": False,
            "partial": False,
            "failed": False,
            "skipped": False,
            "accepted": len(provider_items),
            "rejected": 0,
            "error": None,
            "retrieved_at": checked,
            "freshness": {
                "cadence": cadence,
                "status": "fresh" if provider_items else "no_snapshot",
                "origin_contract_hash": contract_hash if provider_items else None,
                "carried_forward_from_run_id": None,
            },
            "availability": "success",
            "availability_reason": None,
            "upstream_http_status": None,
            "affected_coverage_groups": _coverage_groups(provider_id),
        }
        outcomes.append(outcome)

    feed = {
        "schema_version": 4,
        "run_id": "",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(minutes=1)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=1)),
        "generated_at": _ts(T0 + timedelta(minutes=2)),
        "provider_outcomes": outcomes,
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {
            "snapshot": {
                "schema_version": 1,
                "name": "fixture",
                "timezone": "Asia/Shanghai",
                "output_root": "feeds",
                "runs_root": "runs",
                "feed": {},
                "rate_registry": {},
                "source_families": [],
                "watched_companies": [],
                "coverage": list(COVERAGE),
            },
            "hash": "b" * 64,
        },
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": contracts,
        "content_digest": "",
        "items": selected,
        "pipeline": {"status": "healthy", "warnings": []},
    }
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    return feed


def _write_bundle(root: Path, bundle) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "feed-manifest.json").write_bytes(bundle.manifest_bytes)
    for domain, data in bundle.artifact_bytes.items():
        (root / artifact_relative_path(domain, bundle.run_id)).write_bytes(data)


def test_artifact_schema_is_closed_to_five_domains():
    artifact = {"schema_version": 2, "run_id": "run", "domain": "news", "items": [_news()]}
    validate_against("feed-artifact.schema.json", artifact)
    with pytest.raises(SchemaError):
        validate_against("feed-artifact.schema.json", {**artifact, "domain": "market_data"})


def test_split_emits_exactly_five_domains_and_reconstructs_identity(tmp_path: Path):
    feed = _feed([_news()])
    bundle = build_bundle(feed)
    assert (
        tuple(bundle.artifacts)
        == DOMAINS
        == (
            "news",
            "macro_release",
            "policy",
            "positioning",
            "filing",
        )
    )
    assert [len(bundle.artifacts[domain]["items"]) for domain in DOMAINS] == [1, 0, 0, 0, 0]
    assert generation_key(feed["run_id"]) in bundle.manifest["artifacts"][0]["path"]
    _write_bundle(tmp_path, bundle)
    reconstructed = validate_bundle(tmp_path)
    assert reconstructed["items"] == feed["items"]
    assert reconstructed["content_digest"] == feed["content_digest"]
    assert reconstructed["run_id"] == feed["run_id"]


def test_manifest_prevalidation_returns_ordered_inventory(tmp_path: Path):
    bundle = build_bundle(_feed([_news()]))
    manifest, paths = bundle_module.validate_manifest_and_inventory(bundle.manifest_bytes)
    assert manifest == bundle.manifest
    assert paths == tuple(entry["path"] for entry in bundle.manifest["artifacts"])
    _write_bundle(tmp_path, bundle)
    assert load_feed(tmp_path) == _feed([_news()])


def test_manifest_prevalidation_rejects_unsafe_inventory_path():
    bundle = build_bundle(_feed())
    manifest = deepcopy(bundle.manifest)
    manifest["artifacts"][0]["path"] = "../feed-news.json"
    with pytest.raises(BundleError, match="artifact path"):
        bundle_module.validate_manifest_and_inventory(canonical_bytes(manifest))


def test_bundle_integrity_rejects_corruption_without_legacy_fallback(tmp_path: Path):
    bundle = build_bundle(_feed())
    _write_bundle(tmp_path, bundle)
    artifact = tmp_path / artifact_relative_path("news", bundle.run_id)
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    (tmp_path / "latest.json").write_bytes(canonical_bytes(_feed()))
    with pytest.raises(BundleError):
        load_feed(tmp_path)


def test_load_feed_rejects_previous_major_even_when_manifest_is_valid(tmp_path: Path):
    feed = _feed()
    feed["schema_version"] = 3
    feed["calendar_horizon_end"] = _ts(T0 + timedelta(hours=26))
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    previous_domains = (
        "news",
        "macro_release",
        "policy",
        "market_data",
        "flow",
        "positioning",
        "filing",
        "calendar",
    )
    artifacts = {
        domain: {
            "schema_version": 1,
            "run_id": feed["run_id"],
            "domain": domain,
            "items": [],
        }
        for domain in previous_domains
    }
    data = {domain: canonical_bytes(artifact) for domain, artifact in artifacts.items()}
    current = build_bundle(_feed())
    manifest = {key: value for key, value in feed.items() if key != "items"}
    manifest["bundle_schemas"] = current.manifest["bundle_schemas"]
    manifest["artifacts"] = [
        {
            "domain": domain,
            "path": f"feed-{domain}-{generation_key(feed['run_id'])}.json",
            "item_count": 0,
            "size_bytes": len(data[domain]),
            "sha256": canonical_sha256(data[domain]),
        }
        for domain in previous_domains
    ]
    (tmp_path / "feed-manifest.json").write_bytes(canonical_bytes(manifest))
    for domain, value in data.items():
        (tmp_path / f"feed-{domain}-{generation_key(feed['run_id'])}.json").write_bytes(value)
    with pytest.raises(BundleError, match="previous eight-domain"):
        load_feed(tmp_path)


def test_validate_feed_requires_explicit_previous_migration_permission():
    feed = _feed()
    feed["schema_version"] = 3
    feed["calendar_horizon_end"] = _ts(T0 + timedelta(hours=26))
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    with pytest.raises(SchemaError, match="bounded migration"):
        validate_feed(feed)
    validate_feed(feed, allow_previous=True)


def test_bundle_publication_is_idempotent_and_generation_qualified(tmp_path: Path):
    feed = _feed()
    bundle = build_bundle(feed)
    first = publish_bundle(output_root=tmp_path, bundle=bundle, cutoff=T0, run_id=feed["run_id"])
    second = publish_bundle(output_root=tmp_path, bundle=bundle, cutoff=T0, run_id=feed["run_id"])
    assert first.manifest_replaced and second.idempotent
    assert (tmp_path / "feed-manifest.json").is_file()
    assert len(tuple(tmp_path.glob("feed-*-????????????????????????????????.json"))) == 5
    assert not (tmp_path / "latest.json").exists()


def test_migration_projects_removed_payload_and_recomputes_identity(tmp_path: Path):
    current = _feed([_news()])
    old = deepcopy(current)
    old["schema_version"] = 3
    old["calendar_horizon_end"] = _ts(T0 + timedelta(hours=26))
    market_item = deepcopy(_news("market-item"))
    market_item["provider_id"] = "yahoo_market"
    market_item["source"]["id"] = "market-item"
    market_item["source"]["url"] = "https://example.com/market-item"
    market_item["payload"] = {
        "type": "market_data",
        "instrument_id": "sp500",
        "observations": [{"as_of": _ts(T0 - timedelta(hours=2)), "value": "100", "unit": "index"}],
        "raw_metadata": {},
    }
    old["items"].append(market_item)
    old_contract = {
        "provider_id": "yahoo_market",
        "snapshot": {
            "provider_id": "yahoo_market",
            "empty_valid_for_window": True,
            "payload_types": ["market_data"],
            "freshness": {
                "cadence": "market_session",
                "reference_time": "data_as_of",
                "valid_for_seconds": 86400,
            },
        },
    }
    old_contract["hash"] = canonical_digest(old_contract["snapshot"])
    old["provider_contracts"].append(old_contract)
    old["provider_contracts"].sort(key=lambda entry: entry["provider_id"])
    old_outcome = {
        "provider_id": "yahoo_market",
        "state": "healthy",
        "attempted": 1,
        "fetched": 1,
        "succeeded": True,
        "empty": False,
        "partial": False,
        "failed": False,
        "skipped": False,
        "accepted": 1,
        "rejected": 0,
        "error": None,
        "retrieved_at": _ts(T0 + timedelta(minutes=1)),
        "freshness": {
            "cadence": "market_session",
            "status": "fresh",
            "origin_contract_hash": old_contract["hash"],
            "carried_forward_from_run_id": None,
        },
        "availability": "success",
        "availability_reason": None,
        "upstream_http_status": None,
        "affected_coverage_groups": [],
    }
    old["provider_outcomes"].append(old_outcome)
    old["provider_outcomes"].sort(key=lambda outcome: outcome["provider_id"])
    old["content_digest"], old["run_id"] = recompute_feed_identity(old)

    migrated = migrate_feed(
        old,
        target_feed_config=current["feed_config"],
        target_provider_contracts=current["provider_contracts"],
        target_feed_schema=current["feed_schema"],
    )
    validate_feed(migrated)
    assert migrated["schema_version"] == 4
    assert all(item["payload"]["type"] in DOMAINS for item in migrated["items"])
    assert "market-item" not in {item["id"] for item in migrated["items"]}
    assert migrated["run_id"] != old["run_id"]
    assert migrated["content_digest"] != old["content_digest"]
