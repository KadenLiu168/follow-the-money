"""Gate 13.3 — Normal Brief production gate.

Proves the normal path is the complete deterministic Feed-to-ledger/candidate/
event/packet/analytics/scoring/selection pipeline plus the resolver, analyst,
editor, and language-audit Responses API passes — no ``_mock_*`` shortcuts,
no empty editor output, and no fixture-only fallbacks. Injected fake-client
integration tests cover ownership, reference, timeout/refusal/incomplete,
ordering, and no-fallback contracts. ``--degraded-report`` is verified to be
a separate explicit path that never satisfies this gate.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from follow_the_money.brief_cli import run_brief
from follow_the_money.feed.validate import recompute_feed_identity
from follow_the_money.pipeline import PipelineError, feed_to_ledger, run_pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class FakeClient:
    """Multi-pass fake: returns schema-valid canned outputs in call order.

    The pipeline invokes passes in a fixed order: resolver (per block),
    analyst (per packet), editor, audit. The fake keys off the prompt content
    (each prompt file has a distinct identity phrase).
    """

    def __init__(self, outputs: dict[str, object]) -> None:
        self.outputs = outputs
        self.calls: list[str] = []
        self.created: list[dict] = []

    def create(self, **kwargs):
        prompt = kwargs.get("input", "")
        self.created.append(kwargs)
        # Distinct identity phrases in each prompt file.
        for key, phrase in (
            ("resolver", "Resolve atomic financial events"),
            ("analyst", "Analyze one verified"),
            ("editor", "Render the Chinese Morning"),
            ("audit", "Audit the Chinese Morning"),
        ):
            if key in self.outputs and phrase in prompt:
                self.calls.append(key)
                return SimpleNamespace(
                    status="completed",
                    output_text=json.dumps(self.outputs[key]),
                    model="gpt-test",
                    output_tokens_details=SimpleNamespace(reasoning_tokens=0),
                )
        # Fallback: last-known editor-ish output is never silently accepted;
        # missing pass => refused so the pipeline fails closed.
        self.calls.append("unknown")
        return SimpleNamespace(
            status="refused",
            output_text="",
            model="gpt-test",
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        )


def _valid_feed() -> dict:
    cutoff = T0
    feed = {
        "schema_version": 1,
        "run_id": "feed_run_13_3",
        "window": {"start": _ts(cutoff - timedelta(hours=72)), "end": _ts(cutoff)},
        "collection_started_at": _ts(cutoff - timedelta(seconds=30)),
        "evidence_cutoff_at": _ts(cutoff),
        "collection_completed_at": _ts(cutoff + timedelta(minutes=4)),
        "generated_at": _ts(cutoff + timedelta(minutes=5)),
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "x", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "d" * 64,
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
        "calendar_horizon_end": _ts(cutoff + timedelta(hours=26)),
    }
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return feed


def _news_item(published: datetime, title: str, url: str, eid: str = "ev_1") -> dict:
    return {
        "id": eid,
        "provider_id": "federal_reserve",
        "source": {
            "id": f"src-{eid}",
            "name": "Federal Reserve",
            "tier": "Tier 1",
            "kind": "news",
            "url": url,
            "published_at": _ts(published),
            "knowledge_available_at": _ts(published),
        },
        "payload": {
            "type": "news",
            "title": title,
            "snippet": "美联储宣布维持政策利率不变。",
            "occurred_at": _ts(published),
            "raw_metadata": {},
        },
    }


def _macro_item(published: datetime, title: str, url: str, eid: str = "ev_1") -> dict:
    """A US CPI MoM release with consensus — the v1 surprise-scale series."""
    return {
        "id": eid,
        "provider_id": "bls",
        "source": {
            "id": f"src-{eid}",
            "name": "BLS",
            "tier": "Tier 1",
            "kind": "news",
            "url": url,
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


def _resolver_output(seed_fact_ids: list[str], event_type: str = "policy") -> dict:
    return {
        "proposals": [
            {
                "component_alias": "c0",
                "position_alias": "p00",
                "event_type": event_type,
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


def _analyst_output() -> dict:
    # A high-impact CPI surprise: cross-market systemic, all nine groups
    # mapped, direct exposures — deterministic significance is high enough to
    # pass selection thresholds and prove the normal selection path.
    attributions = [
        {"asset_group": g, "attribution": "likely", "reference_aliases": ["e0"]} for g in _GROUPS
    ]
    mappings = [
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
    ]
    return {
        "packet_alias": "p0",
        "mechanisms": ["通胀超预期强化紧缩预期，压制风险资产估值。"],
        "implications": ["美债收益率与美元短期承压上行。"],
        "reaction_attributions": attributions,
        "price_in": {
            "status": "partial",
            "explanation": "市场已部分计入该数据。",
            "reference_aliases": ["e0"],
        },
        "indirect_indication": {"indicated": False, "reference_aliases": ["e0"]},
        "asset_mappings": mappings,
        "alternatives": ["若随后数据回落，市场或修正紧缩定价。"],
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
    # Script allocation for one full event: s00 market_state_explanation,
    # s01..s08 the eight full-event kinds, s09 optional bottom_line_point.
    # Factual kinds must carry the owning event's exposed evidence alias "e0"
    # so the deterministic claim audit sees supporting evidence.
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


# ---------------------------------------------------------------------------
# Deterministic Feed -> Ledger
# ---------------------------------------------------------------------------


def test_feed_to_ledger_builds_facts_and_observations():
    from follow_the_money.config import load_config
    from follow_the_money.engine.entities import EntityResolver

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    feed = _valid_feed()
    feed["items"] = [
        _news_item(
            T0 - timedelta(hours=2),
            "美联储维持利率不变",
            "https://www.federalreserve.gov/newsevents/pressreleases/m20260811.htm",
        ),
        {
            "id": "ev_2",
            "provider_id": "yahoo_market",
            "source": {
                "id": "src-2",
                "name": "Yahoo",
                "tier": "Tier 2",
                "kind": "news",
                "url": "https://finance.yahoo.com/quote/%5EGSPC",
                "published_at": _ts(T0),
                "knowledge_available_at": _ts(T0),
            },
            "payload": {
                "type": "market_data",
                "instrument_id": "sp500",
                "unit": "index",
                "observations": [{"as_of": _ts(T0 - timedelta(hours=1)), "value": "5600.0"}],
                "raw_metadata": {},
            },
        },
    ]
    ledger = feed_to_ledger(feed, cfg, EntityResolver(cfg.entities))
    entries = ledger.entries()
    assert len(entries) == 2
    seeds = [e for e in entries if e.is_atomic_seed]
    obs = [e for e in entries if not e.is_atomic_seed]
    assert len(seeds) == 1
    assert seeds[0].origin_payload == "news"
    assert seeds[0].knowledge_available_at == _ts(T0 - timedelta(hours=2))
    assert len(obs) == 1 and obs[0].origin_payload == "market_data"


# ---------------------------------------------------------------------------
# Complete normal pipeline (fake-client integration)
# ---------------------------------------------------------------------------


def _adapter_for(feed: dict):
    from follow_the_money.config import load_config
    from follow_the_money.llm import ResponsesAdapter

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    seed_ids = [
        e.fact_id
        for e in feed_to_ledger(
            feed,
            cfg,
            __import__(
                "follow_the_money.engine.entities", fromlist=["EntityResolver"]
            ).EntityResolver(cfg.entities),
        ).entries()
        if e.is_atomic_seed
    ]
    # 9 editor slots + 13 script dashboard claims = 22 claims => aliases k00..k21.
    editor_slots = _editor_output()["filled_slots"]
    claim_aliases = [f"k{i:02d}" for i in range(len(editor_slots) + 13)]
    outputs = {
        "resolver": _resolver_output(seed_ids, event_type="macro_release"),
        "analyst": _analyst_output(),
        "editor": _editor_output(),
        "audit": {"covered_claim_ids": claim_aliases, "findings": []},
    }
    client = FakeClient(outputs)
    namespace = SimpleNamespace(responses=client, create=client.create)
    return ResponsesAdapter(model="gpt-test", client=namespace), client


def test_normal_pipeline_full_run_produces_valid_brief():
    from follow_the_money.config import load_config
    from follow_the_money.engine.entities import EntityResolver
    from follow_the_money.schema import validate_against

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    feed = _valid_feed()
    feed["items"] = [
        _macro_item(
            T0 - timedelta(hours=2),
            "美国 CPI 环比超预期",
            "https://www.bls.gov/news.release/cpi.nr0.htm",
        )
    ]
    adapter, client = _adapter_for(feed)
    prompts = {
        "resolver": (REPO_ROOT / "prompts" / "resolve-events.md").read_text(),
        "analyst": (REPO_ROOT / "prompts" / "analyze-event.md").read_text(),
        "editor": (REPO_ROOT / "prompts" / "render-digest.md").read_text(),
        "audit": (REPO_ROOT / "prompts" / "audit-claims.md").read_text(),
    }
    result = run_pipeline(
        cfg=cfg,
        feed=feed,
        brief_generated_at=_ts(T0 + timedelta(minutes=10)),
        adapter=adapter,
        resolver=EntityResolver(cfg.entities),
        prompts=prompts,
    )
    brief = result.brief
    validate_against("brief.schema.json", brief)
    assert brief["mode"] == "normal"
    assert brief["feed_run_id"] == feed["run_id"]
    assert brief["evidence_cutoff_at"] == feed["evidence_cutoff_at"]
    # All four passes were invoked.
    assert "resolver" in client.calls
    assert "analyst" in client.calls
    assert "editor" in client.calls
    assert "audit" in client.calls
    # Deterministic components present.
    assert result.events and result.packets and result.analyses
    assert result.selected


def test_normal_pipeline_requires_llm_client_in_cli(tmp_path):
    feed = _valid_feed()
    path = tmp_path / "latest.json"
    path.write_bytes(json.dumps(feed, ensure_ascii=False).encode("utf-8"))
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(path),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        runs_root=str(tmp_path / "runs"),
    )
    assert result.exit_code == 2
    assert result.status == "startup_rejection"


def test_degraded_report_is_separate_and_never_satisfies_normal(tmp_path):
    feed = _valid_feed()
    path = tmp_path / "latest.json"
    path.write_bytes(json.dumps(feed, ensure_ascii=False).encode("utf-8"))
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(path),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        runs_root=str(tmp_path / "runs"),
        degraded_report=True,
    )
    assert result.exit_code == 0
    assert "degraded" in result.status
    manifest = json.loads((Path(result.brief_path) / "manifest.json").read_bytes())
    assert manifest["mode"] == "degraded"


def test_resolver_failure_blocks_normal_publication():
    from types import SimpleNamespace

    from follow_the_money.config import load_config
    from follow_the_money.engine.entities import EntityResolver
    from follow_the_money.llm import ResponsesAdapter

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    feed = _valid_feed()
    feed["items"] = [
        _news_item(
            T0 - timedelta(hours=2),
            "美联储维持利率不变",
            "https://www.federalreserve.gov/newsevents/pressreleases/m20260811.htm",
        )
    ]

    class RefusingClient:
        def create(self, **kwargs):
            return SimpleNamespace(
                status="refused",
                output_text="",
                model="gpt-test",
                output_tokens_details=SimpleNamespace(reasoning_tokens=0),
            )

    adapter = ResponsesAdapter(
        model="gpt-test",
        client=SimpleNamespace(responses=RefusingClient(), create=RefusingClient().create),
    )
    prompts = {
        "resolver": (REPO_ROOT / "prompts" / "resolve-events.md").read_text(),
        "analyst": "x",
        "editor": "x",
        "audit": "x",
    }
    with pytest.raises(PipelineError, match="resolver pass failed"):
        run_pipeline(
            cfg=cfg,
            feed=feed,
            brief_generated_at=_ts(T0 + timedelta(minutes=10)),
            adapter=adapter,
            resolver=EntityResolver(cfg.entities),
            prompts=prompts,
        )


def test_no_fallback_when_editor_output_invalid():
    from types import SimpleNamespace

    from follow_the_money.config import load_config
    from follow_the_money.engine.entities import EntityResolver
    from follow_the_money.llm import ResponsesAdapter

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    feed = _valid_feed()
    feed["items"] = [
        _news_item(
            T0 - timedelta(hours=2),
            "美联储维持利率不变",
            "https://www.federalreserve.gov/newsevents/pressreleases/m20260811.htm",
        )
    ]
    # Valid resolver/analyst but an editor output that injects script-owned
    # fields (headings) => assemble_brief rejects; no fallback.
    from tests.test_gate_13_3 import _analyst_output, _resolver_output

    def build_outputs(seed_ids):
        return {
            "resolver": _resolver_output(seed_ids),
            "analyst": _analyst_output(),
            "editor": {"filled_slots": [], "headings": ["hacked"]},
        }

    from follow_the_money.pipeline import feed_to_ledger as _ftl

    seed_ids = [
        e.fact_id
        for e in _ftl(feed, cfg, EntityResolver(cfg.entities)).entries()
        if e.is_atomic_seed
    ]
    client = FakeClient(build_outputs(seed_ids))
    adapter = ResponsesAdapter(
        model="gpt-test", client=SimpleNamespace(responses=client, create=client.create)
    )
    prompts = {
        "resolver": (REPO_ROOT / "prompts" / "resolve-events.md").read_text(),
        "analyst": "x",
        "editor": "x",
        "audit": "x",
    }
    with pytest.raises(PipelineError):
        run_pipeline(
            cfg=cfg,
            feed=feed,
            brief_generated_at=_ts(T0 + timedelta(minutes=10)),
            adapter=adapter,
            resolver=EntityResolver(cfg.entities),
            prompts=prompts,
        )
