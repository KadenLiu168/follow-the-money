"""Pure Provider-local News semantic-context mappings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..schema import SchemaError
from .context import SemanticContext

_SUBJECTS = {
    "bls": "U.S. Bureau of Labor Statistics",
    "nbs": "国家统计局",
    "sse": "上海证券交易所",
    "szse": "深圳证券交易所",
}
_DOCUMENT_TYPES = {
    "bls": "news_release",
    "nbs": "statistical_release",
    "sse": "exchange_notice",
    "szse": "exchange_notice",
}


def _require_text(value: Any, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{where}: required source text is missing")
    return value


def _exact_reference(provider_id: str, title: str) -> tuple[str, str] | None:
    if provider_id == "bls":
        lowered = title.casefold()
        if "consumer price index" in lowered or "cpi" in lowered:
            return "Consumer Price Index", "consumer_price_index_release"
        if "employment situation" in lowered:
            return "Employment Situation", "employment_situation_release"
    if provider_id == "nbs" and "工业增加值" in title:
        return "工业增加值", "official_statistical_release"
    return None


def build_news_context(
    provider_id: str,
    payload: Mapping[str, Any],
    source: Mapping[str, Any],
) -> SemanticContext:
    """Build one closed context from an already normalized news item."""
    if provider_id not in _SUBJECTS:
        raise SchemaError(f"news semantic mapping does not support Provider {provider_id!r}")
    if payload.get("type") != "news":
        raise SchemaError("news semantic mapping requires a news payload")
    title = _require_text(payload.get("title"), where="payload.title")
    _require_text(source.get("url"), where="source.url")
    reference = _exact_reference(provider_id, title)
    if provider_id == "bls" and reference is not None:
        category = reference[1]
    elif provider_id in {"sse", "szse"}:
        category = "official_exchange_notice"
    else:
        category = "official_statistical_release"
    entities = [{"role": "subject", "name": _SUBJECTS[provider_id], "type": "organization"}]
    if reference is not None:
        entities.append({"role": "reference", "name": reference[0], "type": "indicator"})
    context = {
        "version": 1,
        "entities": entities,
        "event": {"category": category, "occurred_at": payload.get("occurred_at")},
        "numeric_facts": [],
        "extension": {
            "type": "news",
            "document": {"title": title, "type": _DOCUMENT_TYPES[provider_id]},
        },
    }
    return SemanticContext.from_dict(context)


map_news_context = build_news_context

__all__ = ["build_news_context", "map_news_context"]
