"""Manifest-led typed Feed bundle regressions."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.canonical import canonical_bytes, canonical_digest
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
    feed = {
        "schema_version": 1,
        "run_id": "",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(minutes=1)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=1)),
        "generated_at": _ts(T0 + timedelta(minutes=2)),
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "c" * 64},
        "provider_contracts": [],
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


def test_prechange_legacy_identity_can_be_migrated_without_changing_identity(tmp_path: Path):
    feed = _feed()
    digest = canonical_digest(
        {key: value for key, value in feed.items() if key not in {"content_digest", "run_id"}}
    )
    feed["content_digest"] = digest
    feed["run_id"] = f"{feed['evidence_cutoff_at']}::{digest[:32]}"

    bundle = build_bundle(feed)
    _write_bundle(tmp_path, bundle)

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
