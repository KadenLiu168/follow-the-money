"""Gate 13.4 — Bundle and replay gate.

The complete create-only atomic run bundle contains the exact canonical Feed,
effective config, real schema/config/prompt/model/build fingerprints, events,
ledger, verified packets, structured LLM outcomes, analytics, selection,
Brief object, rendered Markdown, claim inventory, audits, and generation
status. ``replay`` re-executes the full deterministic recorded-clock pipeline
from the saved Feed with the recorded LLM outputs (no network, no LLM) and
fails on any member, identity, build, schema, config, reference, or output
drift.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.brief_cli import _config_fingerprint, run_brief
from follow_the_money.bundle import BundleError, replay_bundle, verify_bundle_integrity
from follow_the_money.canonical import canonical_digest
from follow_the_money.config import load_config
from follow_the_money.feed.validate import recompute_feed_identity

REPO_ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class FakeClient:
    def __init__(self, outputs: dict[str, object]) -> None:
        self.outputs = outputs

    def create(self, **kwargs):
        prompt = kwargs.get("input", "")
        for key, phrase in (
            ("resolver", "Resolve atomic financial events"),
            ("analyst", "Analyze one verified"),
            ("editor", "Render the Chinese Morning"),
            ("audit", "Audit the Chinese Morning"),
        ):
            if key in self.outputs and phrase in prompt:
                return SimpleNamespace(
                    status="completed",
                    output_text=json.dumps(self.outputs[key]),
                    model="gpt-test",
                    output_tokens_details=SimpleNamespace(reasoning_tokens=0),
                )
        return SimpleNamespace(
            status="refused",
            output_text="",
            model="gpt-test",
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        )


def _valid_feed() -> dict:
    feed = {
        "schema_version": 1,
        "run_id": "feed_run_13_4",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(seconds=30)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=4)),
        "generated_at": _ts(T0 + timedelta(minutes=5)),
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "x", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "d" * 64,
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
        "calendar_horizon_end": _ts(T0 + timedelta(hours=26)),
    }
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return feed


def _macro_item() -> dict:
    published = T0 - timedelta(hours=2)
    return {
        "id": "ev_1",
        "provider_id": "bls",
        "source": {
            "id": "src-ev_1",
            "name": "BLS",
            "tier": "Tier 1",
            "kind": "news",
            "url": "https://www.bls.gov/news.release/cpi.nr0.htm",
            "published_at": _ts(published),
            "knowledge_available_at": _ts(published),
        },
        "payload": {
            "type": "macro_release",
            "series_id": "us_cpi_all_items_sa_mom",
            "released_at": _ts(published),
            "observation_period": None,
            "actual": {"value": "0.4", "unit": "percent"},
            "consensus": {"value": "0.1", "unit": "percent"},
            "raw_metadata": {},
        },
    }


_GROUPS = [
    "cn_hk_equities",
    "us_equities",
    "us_rates",
    "china_rates",
    "usd_fx",
    "industrial_commodities",
    "energy",
    "precious_metals",
    "crypto",
]


def _resolver_output(seed_fact_ids: list[str]) -> dict:
    return {
        "proposals": [
            {
                "component_alias": "c0",
                "position_alias": "p00",
                "event_type": "macro_release",
                "evidence_ids": ["ev_1"],
                "entity_ids": [],
                "event_defining_fact_ids": seed_fact_ids,
                "supporting_fact_ids": [],
                "story_family_label": "unknown",
                "coexistence_relations": [],
            }
        ],
        "unresolved_groups": [],
    }


def _analyst_output() -> dict:
    return {
        "packet_alias": "p0",
        "mechanisms": ["通胀超预期强化紧缩预期，压制风险资产估值。"],
        "implications": ["美债收益率与美元短期承压上行。"],
        "reaction_attributions": [
            {"asset_group": g, "attribution": "likely", "reference_aliases": ["e0"]}
            for g in _GROUPS
        ],
        "price_in": {
            "status": "partial",
            "explanation": "市场已部分计入该数据。",
            "reference_aliases": ["e0"],
        },
        "indirect_indication": {"indicated": False, "reference_aliases": ["e0"]},
        "asset_mappings": [
            {
                "asset_group": g,
                "direction": "positive" if g != "usd_fx" else "negative",
                "confidence": "medium",
                "horizon": "weeks",
                "mechanism": "通胀超预期推升利率与避险资产波动。",
                "reference_aliases": ["e0"],
                "audit_reason": None,
            }
            for g in _GROUPS
        ],
        "alternatives": ["若后续数据回落，市场或修正紧缩定价。"],
        "watch_points": ["关注后续通胀与就业数据。"],
        "scope": "cross_market",
        "fundamental_depth": "systemic",
        "reversibility": "low",
        "structural_horizon": "months",
        "cn_hk_exposure": "direct",
        "us_next_session_exposure": "direct",
        "catalyst_calendar_ids": [],
        "audit_reasons": [],
    }


def _editor_output() -> dict:
    return {
        "filled_slots": [
            {
                "slot_alias": "s00",
                "wording_fragment": "市场状态未判定，风险偏好数据不足。",
                "reference_aliases": [],
            },
            {
                "slot_alias": "s01",
                "wording_fragment": "美国 8 月 CPI 环比超预期上涨。",
                "reference_aliases": ["e0"],
            },
            {
                "slot_alias": "s02",
                "wording_fragment": "通胀超预期强化紧缩预期，压制风险资产估值。",
                "reference_aliases": [],
            },
            {
                "slot_alias": "s03",
                "wording_fragment": "美债收益率与美元指数相应上行。",
                "reference_aliases": ["e0"],
            },
            {
                "slot_alias": "s04",
                "wording_fragment": "市场已部分计入该数据。",
                "reference_aliases": ["e0"],
            },
            {
                "slot_alias": "s05",
                "wording_fragment": "资金流证据不足，未判定方向。",
                "reference_aliases": ["e0"],
            },
            {
                "slot_alias": "s06",
                "wording_fragment": "美股与新兴市场风险资产短期承压。",
                "reference_aliases": ["e0"],
            },
            {
                "slot_alias": "s07",
                "wording_fragment": "若后续数据回落，市场或修正紧缩定价。",
                "reference_aliases": [],
            },
            {
                "slot_alias": "s08",
                "wording_fragment": "数据置信度高，后续关注就业数据。",
                "reference_aliases": [],
            },
        ]
    }


def _llm_client_for(feed: dict):
    from follow_the_money.config import load_config
    from follow_the_money.engine.entities import EntityResolver
    from follow_the_money.pipeline import feed_to_ledger

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    seed_ids = [
        e.fact_id
        for e in feed_to_ledger(feed, cfg, EntityResolver(cfg.entities)).entries()
        if e.is_atomic_seed
    ]
    editor_slots = _editor_output()["filled_slots"]
    claim_aliases = [f"k{i:02d}" for i in range(len(editor_slots) + 13)]
    outputs = {
        "resolver": _resolver_output(seed_ids),
        "analyst": _analyst_output(),
        "editor": _editor_output(),
        "audit": {"covered_claim_ids": claim_aliases, "findings": []},
    }
    client = FakeClient(outputs)
    return SimpleNamespace(responses=client, create=client.create)


def _write_feed(tmp_path: Path) -> Path:
    feed = _valid_feed()
    feed["items"] = [_macro_item()]
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    path = tmp_path / "latest.json"
    path.write_bytes(json.dumps(feed, ensure_ascii=False).encode("utf-8"))
    return path


def _run_normal_brief(tmp_path: Path):
    feed_path = _write_feed(tmp_path)
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(feed_path),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        runs_root=str(tmp_path / "runs"),
        llm_client=_llm_client_for(json.loads(feed_path.read_bytes())),
        model="gpt-test",
    )
    assert result.exit_code == 0, result.message
    return Path(result.brief_path)


def test_full_bundle_contains_all_members_and_replays(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    assert manifest["mode"] == "normal"
    assert manifest["generation_status"] == "ready_for_commit"
    for member in (
        "input/feed.json",
        "config-effective.json",
        "pipeline/events.json",
        "pipeline/unresolved.json",
        "pipeline/ledger.json",
        "pipeline/packets.json",
        "pipeline/analyses.json",
        "pipeline/selection.json",
        "pipeline/llm.json",
        "output/brief.json",
        "output/brief.md",
        "output/claim_inventory.json",
        "audit/results.json",
    ):
        assert (bundle / member).is_file(), f"missing bundle member {member}"

    # No indexed member carries brief_run_id/bundle_digest (no ID/digest cycle).
    for m in manifest["members"]:
        assert "brief_run_id" not in m
        assert "bundle_digest" not in m

    # Full deterministic replay: ok.
    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert replay.ok, replay.errors

    # Saved LLM outcomes present and complete for replay injection.
    llm = json.loads((bundle / "pipeline" / "llm.json").read_bytes())
    assert llm["resolver"] and llm["analyst"] and llm["editor"] and llm["language-audit"]


def test_replay_detects_output_drift(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    assert replay_bundle(bundle, repo_root=REPO_ROOT).ok
    # Mutate a deterministic pipeline member: replay must detect drift.
    events = json.loads((bundle / "pipeline" / "events.json").read_bytes())
    events[0]["display_label"] = "被篡改的标签"
    (bundle / "pipeline" / "events.json").write_bytes(
        json.dumps(events, ensure_ascii=False).encode("utf-8")
    )
    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert not replay.ok
    assert any("drift" in e for e in replay.errors)


def test_replay_detects_unresolved_audit_drift(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    assert replay_bundle(bundle, repo_root=REPO_ROOT).ok
    unresolved = json.loads((bundle / "pipeline" / "unresolved.json").read_bytes())
    unresolved.append(
        {"component_id": "tampered", "seed_fact_ids": [], "evidence_ids": [], "reason": "ambiguous"}
    )
    (bundle / "pipeline" / "unresolved.json").write_bytes(
        json.dumps(unresolved, ensure_ascii=False).encode("utf-8")
    )
    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert not replay.ok
    assert any("drift" in e for e in replay.errors)


def test_replay_requires_unresolved_audit_member(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    (bundle / "pipeline" / "unresolved.json").unlink()
    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert not replay.ok
    assert any("unresolved" in e for e in replay.errors)


def test_unindexed_unresolved_audit_member_is_rejected(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    (bundle / "pipeline" / "unresolved-extra.json").write_bytes(b"[]")
    with pytest.raises(BundleError, match="unlisted"):
        verify_bundle_integrity(bundle)


def test_replay_detects_rendered_drift(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    assert replay_bundle(bundle, repo_root=REPO_ROOT).ok
    (bundle / "output" / "brief.md").write_bytes("被篡改的渲染内容\n".encode())
    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert not replay.ok
    assert any("drift" in e for e in replay.errors)


def test_replay_detects_bundle_tamper(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    (bundle / "input" / "feed.json").write_bytes(b"tampered-feed")
    with pytest.raises(BundleError, match="tamper"):
        verify_bundle_integrity(bundle)
    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert not replay.ok


def test_bundle_directory_id_binds_member_index(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["members"][0]["sha256"] = "0" * 64
    manifest["bundle_digest"] = canonical_digest(
        {key: value for key, value in manifest.items() if key != "bundle_digest"}
    )
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True).encode("utf-8"))
    with pytest.raises(BundleError, match="directory_id mismatch"):
        verify_bundle_integrity(bundle)


def test_replay_requires_build_fingerprint_match(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    # Replaying against an empty root => build fingerprint mismatch.
    replay = replay_bundle(bundle, repo_root=tmp_path)
    assert not replay.ok
    assert any("build" in e for e in replay.errors)


def test_replay_does_not_require_current_prompt_fingerprint(tmp_path):
    bundle = _run_normal_brief(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["prompt_fingerprints"]["resolver"] = "0" * 64
    manifest["bundle_digest"] = canonical_digest(
        {key: value for key, value in manifest.items() if key != "bundle_digest"}
    )
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True).encode("utf-8"))

    replay = replay_bundle(bundle, repo_root=REPO_ROOT)
    assert replay.ok, replay.errors


def test_config_fingerprint_binds_provider_contract_fields():
    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    first = cfg.providers[0]
    changed = replace(first, name=f"{first.name} changed")
    drifted = replace(cfg, providers=(changed, *cfg.providers[1:]))
    assert _config_fingerprint(cfg) != _config_fingerprint(drifted)
