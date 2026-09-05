"""Manifest-led typed Feed bundle regressions."""

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
    validate_bundle,
)
from follow_the_money.feed.publish import publish_bundle
from follow_the_money.feed.validate import recompute_feed_identity
from follow_the_money.schema import SchemaError, validate_against

T0 = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)


def _ts(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _news(item_id: str = "item-1", at: datetime = T0 - timedelta(hours=1)) -> dict:
    return {
        "id": item_id,
        "provider_id": "provider",
        "source": {
            "id": item_id,
            "name": "Source",
            "tier": "Tier 1",
            "kind": "news",
            "url": f"https://example.com/{item_id}",
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


def _feed(items: list[dict] | None = None) -> dict:
    snapshot = {
        "provider_id": "provider",
        "empty_valid_for_window": True,
        "freshness": {
            "cadence": "event_driven",
            "reference_time": "checked_at",
        },
    }
    contract_hash = canonical_digest(snapshot)
    feed = {
        "schema_version": 3,
        "run_id": "",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(minutes=1)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=1)),
        "generated_at": _ts(T0 + timedelta(minutes=2)),
        "provider_outcomes": [
            {
                "provider_id": "provider",
                "state": "healthy",
                "attempted": 1,
                "fetched": 1,
                "succeeded": True,
                "empty": False,
                "partial": False,
                "failed": False,
                "skipped": False,
                "accepted": len(items or []),
                "rejected": 0,
                "error": None,
                "retrieved_at": _ts(T0 + timedelta(minutes=1)),
                "freshness": {
                    "cadence": "event_driven",
                    "status": "fresh" if items else "no_snapshot",
                    "origin_contract_hash": contract_hash if items else None,
                    "carried_forward_from_run_id": None,
                },
                "availability": "success",
                "availability_reason": None,
                "upstream_http_status": None,
                "affected_coverage_groups": [],
            }
        ],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": [
            {"provider_id": "provider", "snapshot": snapshot, "hash": contract_hash}
        ],
        "git": None,
        "content_digest": "",
        "items": items or [],
        "pipeline": {"status": "healthy", "warnings": []},
    }
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    return feed


def _write_bundle(root: Path, bundle) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "feed-manifest.json").write_bytes(bundle.manifest_bytes)
    for domain, data in bundle.artifact_bytes.items():
        (root / artifact_relative_path(domain, bundle.run_id)).write_bytes(data)


def test_artifact_schema_reuses_item_shape_and_rejects_unknown_or_mismatched_domain():
    artifact = {"schema_version": 1, "run_id": "run", "domain": "news", "items": [_news()]}
    validate_against("feed-artifact.schema.json", artifact)
    with pytest.raises(SchemaError):
        validate_against("feed-artifact.schema.json", {**artifact, "domain": "unknown"})
    bad = deepcopy(artifact)
    bad["domain"] = "macro_release"
    with pytest.raises(SchemaError):
        validate_against("feed-artifact.schema.json", bad)


def test_split_emits_all_domains_and_reconstructs_identity(tmp_path: Path):
    feed = _feed([_news()])
    bundle = build_bundle(feed)
    assert tuple(bundle.artifacts) == DOMAINS
    assert [len(bundle.artifacts[domain]["items"]) for domain in DOMAINS] == [
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    assert generation_key(feed["run_id"]) in bundle.manifest["artifacts"][0]["path"]
    _write_bundle(tmp_path, bundle)
    reconstructed = validate_bundle(tmp_path)
    assert reconstructed["items"] == feed["items"]
    assert reconstructed["content_digest"] == feed["content_digest"]
    assert reconstructed["run_id"] == feed["run_id"]


def test_manifest_prevalidation_returns_ordered_safe_inventory_and_preserves_local_loading(
    tmp_path: Path,
):
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


def test_bundle_integrity_and_manifest_first_fallback(tmp_path: Path):
    bundle = build_bundle(_feed())
    _write_bundle(tmp_path, bundle)
    artifact = tmp_path / artifact_relative_path("news", bundle.run_id)
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(BundleError):
        load_feed(tmp_path)

    # A present invalid manifest must not hide behind a valid legacy file.
    (tmp_path / "latest.json").write_bytes(canonical_bytes(_feed()))
    with pytest.raises(BundleError):
        load_feed(tmp_path)


def test_legacy_read_is_allowed_only_without_manifest(tmp_path: Path):
    feed = _feed()
    (tmp_path / "latest.json").write_bytes(canonical_bytes(feed))
    assert load_feed(tmp_path)["run_id"] == feed["run_id"]


def test_preceding_major_legacy_read_preserves_identity(tmp_path: Path):
    feed = _feed()
    feed["schema_version"] = 2
    for key in (
        "availability",
        "availability_reason",
        "upstream_http_status",
        "affected_coverage_groups",
    ):
        feed["provider_outcomes"][0].pop(key)
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    (tmp_path / "latest.json").write_bytes(canonical_bytes(feed))

    assert load_feed(tmp_path) == feed


def test_preceding_major_manifest_bundle_is_a_valid_active_input(tmp_path: Path):
    feed = _feed([_news()])
    feed["schema_version"] = 2
    for outcome in feed["provider_outcomes"]:
        for key in (
            "availability",
            "availability_reason",
            "upstream_http_status",
            "affected_coverage_groups",
        ):
            outcome.pop(key)
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)

    current = build_bundle(_feed([_news()]))
    artifacts = {
        domain: {**artifact, "run_id": feed["run_id"]}
        for domain, artifact in current.artifacts.items()
    }
    artifact_bytes = {domain: canonical_bytes(artifact) for domain, artifact in artifacts.items()}
    manifest = {key: value for key, value in feed.items() if key != "items"}
    manifest["bundle_schemas"] = current.manifest["bundle_schemas"]
    manifest["artifacts"] = [
        {
            "domain": domain,
            "path": artifact_relative_path(domain, feed["run_id"]),
            "item_count": len(artifacts[domain]["items"]),
            "size_bytes": len(artifact_bytes[domain]),
            "sha256": canonical_sha256(artifact_bytes[domain]),
        }
        for domain in DOMAINS
    ]
    (tmp_path / "feed-manifest.json").write_bytes(canonical_bytes(manifest))
    for domain, data in artifact_bytes.items():
        (tmp_path / artifact_relative_path(domain, feed["run_id"])).write_bytes(data)

    assert validate_bundle(tmp_path) == feed


def test_bundle_publication_is_idempotent_and_generation_qualified(tmp_path: Path):
    feed = _feed()
    bundle = build_bundle(feed)
    first = publish_bundle(output_root=tmp_path, bundle=bundle, cutoff=T0, run_id=feed["run_id"])
    second = publish_bundle(output_root=tmp_path, bundle=bundle, cutoff=T0, run_id=feed["run_id"])
    assert first.manifest_replaced and second.idempotent
    assert (tmp_path / "feed-manifest.json").is_file()
    assert len(tuple(tmp_path.glob("feed-*-????????????????????????????????.json"))) == 8
    assert not (tmp_path / "latest.json").exists()
