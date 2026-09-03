from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from follow_the_money.canonical import canonical_bytes, canonical_digest
from follow_the_money.config.model import FreshnessContract
from follow_the_money.feed.bundle import artifact_relative_path, build_bundle
from follow_the_money.feed.freshness import FreshnessError, evaluate_freshness
from follow_the_money.feed.plan import ProviderOutcome
from follow_the_money.feed.snapshot import load_active_feed, select_provider_slices
from follow_the_money.feed.validate import recompute_feed_identity

T0 = datetime(2026, 8, 11, 0, 20, tzinfo=UTC)


def ts(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def policy_item(
    item_id: str = "item", at: datetime = T0 - timedelta(hours=1), title: str | None = None
) -> dict:
    return {
        "id": item_id,
        "provider_id": "provider",
        "source": {
            "id": item_id,
            "name": "Source",
            "tier": "Tier 1",
            "kind": "policy",
            "url": f"https://example.com/{item_id}",
            "published_at": ts(at),
            "knowledge_available_at": ts(at),
        },
        "payload": {
            "type": "policy",
            "title": title or item_id,
            "announced_at": ts(at),
            "raw_metadata": {},
        },
    }


def test_bounded_and_event_driven_freshness_use_different_authorities():
    item = policy_item()
    assert (
        evaluate_freshness(
            [item],
            FreshnessContract("weekly", "source_updated_at", 7 * 86400),
            ts(T0),
        )
        == "fresh"
    )
    assert (
        evaluate_freshness(
            [item],
            FreshnessContract("event_driven", "checked_at"),
            ts(T0),
            carried_forward=True,
            checked_at=ts(T0 + timedelta(minutes=1)),
        )
        == "valid_unchanged"
    )


def test_market_session_expiry_ignores_retrieval_time():
    item = policy_item()
    item["payload"] = {
        "type": "market_data",
        "instrument_id": "sp500",
        "observations": [{"as_of": ts(T0 - timedelta(days=2)), "value": "1", "unit": "index"}],
        "raw_metadata": {},
    }
    assert (
        evaluate_freshness(
            [item],
            FreshnessContract("market_session", "data_as_of", 86400),
            ts(T0),
            checked_at=ts(T0 + timedelta(minutes=1)),
        )
        == "stale"
    )
    assert (
        evaluate_freshness(
            [item],
            FreshnessContract("market_session", "data_as_of", 3 * 86400),
            ts(T0),
            checked_at=ts(T0 + timedelta(minutes=1)),
        )
        == "fresh"
    )


@pytest.mark.parametrize(
    "item",
    [
        {**policy_item(), "source": {**policy_item()["source"], "published_at": None}},
        {
            **policy_item(),
            "source": {**policy_item()["source"], "published_at": ts(T0 + timedelta(days=1))},
        },
    ],
)
def test_missing_or_future_reference_fails_closed(item):
    with pytest.raises(FreshnessError):
        evaluate_freshness(
            [item],
            FreshnessContract("scheduled", "source_updated_at", 86400),
            ts(T0),
        )


def _selection(
    outcome: ProviderOutcome,
    current: list[dict],
    prior: list[dict] | None,
):
    return select_provider_slices(
        outcomes={"provider": outcome},
        current_items=current,
        active_feed=(
            {
                "run_id": "prior-run",
                "items": prior or [],
                "provider_contracts": [
                    {
                        "provider_id": "provider",
                        "snapshot": {},
                        "hash": "a" * 64,
                    }
                ],
            }
            if prior is not None
            else None
        ),
        contracts={"provider": FreshnessContract("scheduled", "source_updated_at", 86400)},
        current_contract_hashes={"provider": "b" * 64},
        empty_valid_for_window={"provider": True},
        evidence_cutoff_at=ts(T0),
    )


def test_unchanged_complete_empty_carries_exact_prior_slice():
    prior = [policy_item()]
    outcome = ProviderOutcome("provider", state="empty", retrieved_at=ts(T0 + timedelta(minutes=1)))
    result = _selection(outcome, [], prior)
    assert list(result.items) == prior
    assert outcome.freshness == {
        "cadence": "scheduled",
        "status": "valid_unchanged",
        "origin_contract_hash": "a" * 64,
        "carried_forward_from_run_id": "prior-run",
    }


def test_repeated_carry_preserves_original_contract_hash():
    prior = [policy_item()]
    outcome = ProviderOutcome("provider", state="empty", retrieved_at=ts(T0 + timedelta(minutes=1)))
    result = select_provider_slices(
        outcomes={"provider": outcome},
        current_items=[],
        active_feed={
            "schema_version": 2,
            "run_id": "prior-run",
            "items": prior,
            "provider_contracts": [{"provider_id": "provider", "snapshot": {}, "hash": "b" * 64}],
            "provider_outcomes": [
                {
                    "provider_id": "provider",
                    "freshness": {"origin_contract_hash": "a" * 64},
                }
            ],
        },
        contracts={"provider": FreshnessContract("scheduled", "source_updated_at", 86400)},
        current_contract_hashes={"provider": "c" * 64},
        empty_valid_for_window={"provider": True},
        evidence_cutoff_at=ts(T0),
    )

    assert list(result.items) == prior
    assert outcome.freshness["origin_contract_hash"] == "a" * 64


def test_new_or_revised_identity_replaces_prior_slice_without_merge():
    prior = [policy_item("old")]
    current = [policy_item("new"), policy_item("old", title="not-used")]
    outcome = ProviderOutcome(
        "provider", state="healthy", retrieved_at=ts(T0 + timedelta(minutes=1))
    )
    result = _selection(outcome, list(reversed(current)), prior)
    assert [item["id"] for item in result.items] == ["new", "old"]
    assert outcome.freshness["status"] == "fresh"
    assert outcome.freshness["origin_contract_hash"] == "b" * 64
    assert outcome.freshness["carried_forward_from_run_id"] is None


def test_complete_empty_without_prior_is_no_snapshot():
    outcome = ProviderOutcome("provider", state="empty", retrieved_at=ts(T0 + timedelta(minutes=1)))
    result = _selection(outcome, [], None)
    assert result.items == ()
    assert outcome.freshness["status"] == "no_snapshot"
    assert outcome.freshness["origin_contract_hash"] is None


def test_incomplete_outcome_never_carries_prior_slice():
    prior = [policy_item()]
    outcome = ProviderOutcome("provider", state="failed")
    result = _selection(outcome, [], prior)
    assert result.items == ()
    assert outcome.freshness["status"] == "not_evaluated"
    assert outcome.freshness["origin_contract_hash"] is None


def test_blocked_outcome_never_carries_prior_slice():
    prior = [policy_item()]
    outcome = ProviderOutcome(
        "provider",
        state="failed",
        availability="blocked",
        availability_reason="HTTP 403",
        upstream_http_status=403,
    )
    result = _selection(outcome, [], prior)
    assert result.items == ()
    assert outcome.freshness["status"] == "not_evaluated"
    assert outcome.freshness["origin_contract_hash"] is None


def _active_bundle():
    contract_snapshot = {
        "provider_id": "provider",
        "empty_valid_for_window": True,
        "freshness": {
            "cadence": "scheduled",
            "reference_time": "source_updated_at",
            "valid_for_seconds": 86400,
        },
    }
    contract_hash = canonical_digest(contract_snapshot)
    outcome = {
        "provider_id": "provider",
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
        "retrieved_at": ts(T0 + timedelta(minutes=1)),
        "availability": "success",
        "availability_reason": None,
        "upstream_http_status": None,
        "affected_coverage_groups": [],
        "freshness": {
            "cadence": "scheduled",
            "status": "fresh",
            "origin_contract_hash": contract_hash,
            "carried_forward_from_run_id": None,
        },
    }
    feed = {
        "schema_version": 3,
        "run_id": "",
        "window": {"start": ts(T0 - timedelta(days=1)), "end": ts(T0)},
        "collection_started_at": ts(T0 - timedelta(minutes=1)),
        "evidence_cutoff_at": ts(T0),
        "collection_completed_at": ts(T0 + timedelta(minutes=2)),
        "generated_at": ts(T0 + timedelta(minutes=3)),
        "provider_outcomes": [outcome],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "b" * 64},
        "feed_config": {"snapshot": {}, "hash": "c" * 64},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": "d" * 64},
        "provider_contracts": [
            {
                "provider_id": "provider",
                "snapshot": contract_snapshot,
                "hash": contract_hash,
            }
        ],
        "git": None,
        "content_digest": "",
        "items": [policy_item()],
        "pipeline": {"status": "healthy", "warnings": []},
    }
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    return build_bundle(feed)


def _write_active_bundle(root, bundle) -> None:
    (root / "feed-manifest.json").write_bytes(bundle.manifest_bytes)
    for domain, data in bundle.artifact_bytes.items():
        (root / artifact_relative_path(domain, bundle.run_id)).write_bytes(data)


def test_freshness_is_semantic_but_audit_times_are_not():
    bundle = _active_bundle()
    feed = {
        key: value
        for key, value in bundle.manifest.items()
        if key not in {"bundle_schemas", "artifacts"}
    }
    feed["items"] = bundle.artifacts["policy"]["items"]
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"], feed["run_id"] = digest, run_id

    audit = dict(feed)
    audit["generated_at"] = ts(T0 + timedelta(hours=1))
    audit["provider_outcomes"] = [dict(feed["provider_outcomes"][0])]
    audit["provider_outcomes"][0]["retrieved_at"] = ts(T0 + timedelta(minutes=2))
    assert recompute_feed_identity(audit) == (digest, run_id)

    semantic = dict(feed)
    semantic["provider_outcomes"] = [dict(feed["provider_outcomes"][0])]
    semantic["provider_outcomes"][0]["freshness"] = {
        **feed["provider_outcomes"][0]["freshness"],
        "status": "stale",
    }
    assert recompute_feed_identity(semantic)[0] != digest


def test_active_bundle_is_optional_and_manifest_first(tmp_path):
    bundle = _active_bundle()
    _write_active_bundle(tmp_path, bundle)
    assert load_active_feed(tmp_path)["run_id"] == bundle.run_id

    # Major 1 is no longer an active-bundle compatibility boundary.
    unsupported = deepcopy(bundle.manifest)
    unsupported["schema_version"] = 1
    (tmp_path / "feed-manifest.json").write_bytes(canonical_bytes(unsupported))
    assert load_active_feed(tmp_path) is None

    (tmp_path / "feed-manifest.json").write_bytes(b"{}")
    assert load_active_feed(tmp_path) is None
    (tmp_path / "latest.json").write_bytes(canonical_bytes(bundle.manifest))
    assert load_active_feed(tmp_path) is None


def test_failed_active_bundle_is_not_active(tmp_path):
    bundle = _active_bundle()
    _write_active_bundle(tmp_path, bundle)
    manifest = deepcopy(bundle.manifest)
    manifest["pipeline"]["status"] = "failure"
    (tmp_path / "feed-manifest.json").write_bytes(canonical_bytes(manifest))

    assert load_active_feed(tmp_path) is None


def test_untrusted_contract_hash_is_not_active(tmp_path):
    bundle = _active_bundle()
    _write_active_bundle(tmp_path, bundle)
    manifest = deepcopy(bundle.manifest)
    manifest["provider_contracts"][0]["hash"] = "0" * 64
    (tmp_path / "feed-manifest.json").write_bytes(canonical_bytes(manifest))

    assert load_active_feed(tmp_path) is None
