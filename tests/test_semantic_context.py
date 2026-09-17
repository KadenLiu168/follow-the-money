"""Focused ECO-130 semantic-context construction regressions."""

from __future__ import annotations

from copy import deepcopy
from decimal import ROUND_DOWN, localcontext

import pytest

from follow_the_money.schema import SchemaError
from follow_the_money.semantic.context import SemanticContext
from follow_the_money.semantic.macro import build_macro_context
from follow_the_money.semantic.news import build_news_context
from follow_the_money.semantic.policy import build_policy_context


def _news_context() -> dict:
    return {
        "version": 1,
        "entities": [
            {"role": "subject", "name": "U.S. Bureau of Labor Statistics", "type": "organization"},
            {"role": "reference", "name": "Consumer Price Index", "type": "indicator"},
        ],
        "event": {
            "category": "official_statistical_release",
            "occurred_at": "2026-08-11T00:19:00.000Z",
        },
        "numeric_facts": [
            {
                "metric": "headline",
                "role": "actual",
                "value": "1.2",
                "unit": "percent",
                "unknown_reason": None,
            }
        ],
        "extension": {
            "type": "news",
            "document": {"title": "CPI Release", "type": "news_release"},
        },
    }


def test_common_context_is_closed_immutable_and_serializable():
    context = SemanticContext.from_dict(_news_context())

    serialized = context.to_dict()
    assert SemanticContext.from_dict(serialized).to_dict() == serialized
    assert serialized["version"] == 1
    assert serialized["extension"]["type"] == "news"
    with pytest.raises((AttributeError, TypeError)):
        context.version = 2

    unknown = deepcopy(_news_context())
    unknown["unexpected"] = "not evidence"
    with pytest.raises(SchemaError, match="unknown|unexpected|closed"):
        SemanticContext.from_dict(unknown)

    boolean_version = deepcopy(_news_context())
    boolean_version["version"] = True
    with pytest.raises(SchemaError, match="version"):
        SemanticContext.from_dict(boolean_version)


def test_context_bounds_and_forbidden_analytical_keys_fail_closed():
    too_long = deepcopy(_news_context())
    too_long["entities"][0]["name"] = "x" * 301
    with pytest.raises(SchemaError):
        SemanticContext.from_dict(too_long)

    too_many_entities = deepcopy(_news_context())
    too_many_entities["entities"] = [
        {"role": "reference", "name": f"Indicator {index}", "type": "indicator"}
        for index in range(33)
    ]
    with pytest.raises(SchemaError):
        SemanticContext.from_dict(too_many_entities)

    analytical = deepcopy(_news_context())
    analytical["extension"]["impact"] = "bullish"
    with pytest.raises(SchemaError, match="unknown|impact|closed"):
        SemanticContext.from_dict(analytical)


def test_context_ordering_and_exact_duplicate_elision_are_input_order_independent():
    first = _news_context()
    first["entities"] = [first["entities"][1], first["entities"][0], first["entities"][1]]
    actual = first["numeric_facts"][0]
    previous = {
        "metric": "headline",
        "role": "previous",
        "value": "0.8",
        "unit": "percent",
        "unknown_reason": None,
    }
    first["numeric_facts"] = [previous, actual, previous]

    second = _news_context()
    second["entities"] = list(reversed(second["entities"]))
    second["numeric_facts"] = [actual, previous]

    assert SemanticContext.from_dict(first).to_dict() == SemanticContext.from_dict(second).to_dict()
    assert len(SemanticContext.from_dict(first).to_dict()["entities"]) == 2
    assert len(SemanticContext.from_dict(first).to_dict()["numeric_facts"]) == 2


def test_mapper_numeric_serialization_ignores_ambient_decimal_context():
    payload = {
        "type": "macro_release",
        "series_id": "cn_industrial_production_yoy",
        "released_at": "2026-08-11T00:12:00Z",
        "observation_period": {"period": "2026-07"},
        "actual": {"value": "5.4", "unit": "percent"},
        "consensus": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "previous": {"value": "5.3", "unit": "percent"},
        "raw_metadata": {},
    }
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        first = build_macro_context("nbs", payload, {}).to_dict()
    with localcontext() as context:
        context.prec = 80
        first_again = build_macro_context("nbs", dict(reversed(payload.items())), {}).to_dict()
    assert first == first_again


@pytest.mark.parametrize(
    ("provider_id", "title", "url", "document_type", "category"),
    [
        (
            "bls",
            "Consumer Price Index - August 2026",
            "https://www.bls.gov/news.release/cpi.nr0.htm",
            "news_release",
            "consumer_price_index_release",
        ),
        (
            "nbs",
            "国家统计局关于2026年7月国民经济运行情况的发布",
            "https://www.stats.gov.cn/sj/zxfb/202608/t20260811_1890120.html",
            "statistical_release",
            "official_statistical_release",
        ),
        (
            "sse",
            "关于科创50指数成份股调整的公告",
            "https://www.sse.com.cn/disclosure/announcement/general/c/c_20260811_5789123.shtml",
            "exchange_notice",
            "official_exchange_notice",
        ),
        (
            "szse",
            "关于深证成份指数样本股定期调整的公告",
            "https://www.szse.cn/disclosure/notice/general/t20260811_612345.html",
            "exchange_notice",
            "official_exchange_notice",
        ),
    ],
)
def test_news_mappings_are_bounded_and_provider_specific(
    provider_id, title, url, document_type, category
):
    payload = {
        "type": "news",
        "title": title,
        "snippet": "",
        "occurred_at": "2026-08-11T00:10:00Z",
        "raw_metadata": {},
    }
    context = build_news_context(
        provider_id,
        payload,
        {"name": provider_id, "url": url},
    ).to_dict()

    assert context["event"]["category"] == category
    assert context["event"]["occurred_at"] == payload["occurred_at"]
    assert context["extension"] == {
        "type": "news",
        "document": {"title": title, "type": document_type},
    }
    assert (
        all(entity["role"] != "reference" for entity in context["entities"]) or provider_id == "bls"
    )


def test_news_mapper_rejects_unsupported_provider_and_does_not_infer_entities():
    payload = {
        "type": "news",
        "title": "Official notice about an unnamed company",
        "snippet": "Company X will be affected.",
        "occurred_at": None,
        "raw_metadata": {},
    }
    with pytest.raises(SchemaError):
        build_news_context("sec_edgar", payload, {"name": "SEC", "url": "https://www.sec.gov/a"})
    context = build_news_context(
        "nbs", payload, {"name": "国家统计局", "url": "https://www.stats.gov.cn/a"}
    ).to_dict()
    assert not any(entity["name"] == "Company X" for entity in context["entities"])
    assert context["entities"] == [
        {"role": "subject", "name": "国家统计局", "type": "organization"}
    ]


def test_macro_mapping_preserves_period_and_previous_without_claiming_revision():
    payload = {
        "type": "macro_release",
        "series_id": "cn_industrial_production_yoy",
        "released_at": "2026-08-11T00:12:00Z",
        "observation_period": {"period": "2026-07"},
        "actual": {"value": "5.4", "unit": "percent"},
        "consensus": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "previous": {"value": "5.3", "unit": "percent"},
        "raw_metadata": {},
    }
    context = build_macro_context("nbs", payload, {}).to_dict()

    assert context["extension"]["indicator"] == {
        "id": "cn_industrial_production_yoy",
        "name": "Industrial Production Year-over-Year",
    }
    assert context["extension"]["period"] == {"period": "2026-07"}
    assert context["extension"]["revision"] is None
    assert [(fact["role"], fact["value"]) for fact in context["numeric_facts"]] == [
        ("actual", "5.4"),
        ("consensus", None),
        ("previous", "5.3"),
    ]


def test_macro_mapping_rejects_incompatible_observation_units():
    payload = {
        "type": "macro_release",
        "series_id": "cn_industrial_production_yoy",
        "released_at": "2026-08-11T00:12:00Z",
        "observation_period": {"period": "2026-07"},
        "actual": {"value": "5.4", "unit": "percent"},
        "consensus": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "previous": {"value": "5.3", "unit": "index"},
        "raw_metadata": {},
    }
    with pytest.raises(SchemaError, match="unit"):
        build_macro_context("nbs", payload, {})


def test_macro_mapping_preserves_null_period_and_rejects_unknown_series():
    payload = {
        "type": "macro_release",
        "series_id": "cn_industrial_production_yoy",
        "released_at": "2026-08-11T00:12:00Z",
        "observation_period": None,
        "actual": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "consensus": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "previous": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "raw_metadata": {},
    }
    assert build_macro_context("nbs", payload, {}).to_dict()["extension"]["period"] is None
    with pytest.raises(SchemaError):
        build_macro_context("nbs", {**payload, "series_id": "not-a-closed-series"}, {})


def test_macro_mapping_only_emits_source_explicit_same_period_revision():
    payload = {
        "type": "macro_release",
        "series_id": "cn_industrial_production_yoy",
        "released_at": "2026-08-11T00:12:00Z",
        "observation_period": {"period": "2026-07"},
        "actual": {"value": "5.4", "unit": "percent"},
        "consensus": {"value": None, "unit": "percent", "unknown_reason": "missing"},
        "previous": {"value": "5.3", "unit": "percent"},
        "raw_metadata": {},
    }
    source_record = {
        "revision": {
            "period": "2026-07",
            "previous": "5.2",
            "revised": "5.4",
            "unit": "percent",
        }
    }
    context = build_macro_context("nbs", payload, source_record).to_dict()
    assert context["extension"]["revision"] == {
        "previous": {"value": "5.2", "unit": "percent"},
        "revised": {"value": "5.4", "unit": "percent"},
    }
    assert {fact["role"] for fact in context["numeric_facts"]} == {
        "actual",
        "consensus",
        "previous",
        "revision_previous",
        "revision_revised",
    }

    prior_period = deepcopy(source_record)
    prior_period["revision"]["period"] = "2026-06"
    assert (
        build_macro_context("nbs", payload, prior_period).to_dict()["extension"]["revision"] is None
    )


@pytest.mark.parametrize(
    ("provider_id", "title", "url", "policy_type", "action", "category"),
    [
        (
            "federal_reserve",
            "Federal Reserve issues FOMC statement",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260811a.htm",
            "monetary_policy",
            "monetary_policy_statement",
            "monetary_policy",
        ),
        (
            "pboc",
            "中国人民银行决定于2026年8月实施降准",
            "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/5456789/index.html",
            "monetary_policy",
            "reserve_requirement_announcement",
            "reserve_requirement_announcement",
        ),
    ],
)
def test_policy_mappings_keep_issuer_action_and_null_optional_facts(
    provider_id, title, url, policy_type, action, category
):
    payload = {
        "type": "policy",
        "title": title,
        "announced_at": "2026-08-11T00:15:00Z",
        "effective_at": None,
        "raw_metadata": {},
    }
    context = build_policy_context(provider_id, payload, {"url": url}).to_dict()
    assert context["event"] == {
        "category": category,
        "occurred_at": payload["announced_at"],
    }
    assert context["extension"] == {
        "type": "policy",
        "policy_type": policy_type,
        "action": action,
        "effective_at": None,
        "affected_scope": [],
    }
    assert context["entities"] == [
        {
            "role": "issuer",
            "name": "Federal Reserve" if provider_id == "federal_reserve" else "中国人民银行",
            "type": "organization",
        }
    ]


def test_generic_policy_fallback_is_factual_and_does_not_infer_scope():
    payload = {
        "type": "policy",
        "title": "Official policy notice",
        "announced_at": "2026-08-11T00:15:00Z",
        "effective_at": None,
        "raw_metadata": {},
    }
    context = build_policy_context(
        "pboc", payload, {"url": "https://www.pbc.gov.cn/goutongjiaoliu/notice.html"}
    ).to_dict()
    assert context["extension"]["action"] == "official_policy_announcement"
    assert context["extension"]["affected_scope"] == []
