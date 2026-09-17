"""Pure Federal Reserve and PBOC policy semantic-context mappings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..schema import SchemaError
from .context import SemanticContext

_ISSUERS = {
    "federal_reserve": "Federal Reserve",
    "pboc": "中国人民银行",
}


def _require_text(value: Any, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{where}: required source text is missing")
    return value


def build_policy_context(
    provider_id: str,
    payload: Mapping[str, Any],
    source: Mapping[str, Any],
) -> SemanticContext:
    """Build one closed context from one normalized policy item."""
    issuer = _ISSUERS.get(provider_id)
    if issuer is None:
        raise SchemaError(f"policy semantic mapping does not support Provider {provider_id!r}")
    if payload.get("type") != "policy":
        raise SchemaError("policy semantic mapping requires a policy payload")
    title = _require_text(payload.get("title"), where="payload.title")
    url = _require_text(source.get("url"), where="source.url").casefold()
    lowered = title.casefold()
    if provider_id == "federal_reserve" and ("monetary" in url or "fomc" in lowered):
        event_category = "monetary_policy"
        policy_type = "monetary_policy"
        action = "monetary_policy_statement"
    elif provider_id == "pboc" and ("降准" in title or "存款准备金" in title):
        event_category = "reserve_requirement_announcement"
        policy_type = "monetary_policy"
        action = "reserve_requirement_announcement"
    elif provider_id == "pboc" and "公开市场" in title:
        event_category = "open_market_operations_announcement"
        policy_type = "monetary_policy"
        action = "open_market_operations_announcement"
    else:
        event_category = "official_policy_announcement"
        policy_type = "official_policy"
        action = "official_policy_announcement"
    context = {
        "version": 1,
        "entities": [{"role": "issuer", "name": issuer, "type": "organization"}],
        "event": {"category": event_category, "occurred_at": payload.get("announced_at")},
        "numeric_facts": [],
        "extension": {
            "type": "policy",
            "policy_type": policy_type,
            "action": action,
            "effective_at": payload.get("effective_at"),
            "affected_scope": [],
        },
    }
    return SemanticContext.from_dict(context)


map_policy_context = build_policy_context

__all__ = ["build_policy_context", "map_policy_context"]
