"""Closed, deterministic semantic context for affected Feed domains."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from ..schema import SchemaError
from .numeric import canonicalize_canonical

MAX_ENTITIES = 32
MAX_NUMERIC_FACTS = 32
MAX_AFFECTED_SCOPE = 16
MAX_TEXT = 300
MAX_SHORT_TEXT = 128

ENTITY_ROLES = frozenset({"issuer", "reference", "subject"})
ENTITY_TYPES = frozenset({"asset", "indicator", "instrument", "market", "organization", "policy"})
EVENT_CATEGORIES = frozenset(
    {
        "official_exchange_notice",
        "official_policy_announcement",
        "official_statistical_release",
        "monetary_policy",
        "open_market_operations_announcement",
        "reserve_requirement_announcement",
        "consumer_price_index_release",
        "employment_situation_release",
    }
)
NUMERIC_ROLES = frozenset(
    {"actual", "consensus", "previous", "revision_previous", "revision_revised"}
)
UNKNOWN_REASONS = frozenset({"missing", "unsupported", "incompatible_unit", "non_numeric"})
NEWS_DOCUMENT_TYPES = frozenset({"exchange_notice", "news_release", "statistical_release"})
POLICY_TYPES = frozenset({"monetary_policy", "official_policy"})
POLICY_ACTIONS = frozenset(
    {
        "official_policy_announcement",
        "open_market_operations_announcement",
        "reserve_requirement_announcement",
        "monetary_policy_statement",
    }
)


def _text(value: Any, *, where: str, max_length: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{where}: non-empty text is required")
    normalized = unicodedata.normalize("NFC", value)
    if normalized != value:
        value = normalized
    if len(value) > max_length:
        raise SchemaError(f"{where}: text exceeds {max_length} characters")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise SchemaError(f"{where}: control characters are not allowed")
    return value


def _optional_text(value: Any, *, where: str, max_length: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    return _text(value, where=where, max_length=max_length)


def _closed_keys(value: Mapping[str, Any], allowed: set[str], *, where: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise SchemaError(f"{where}: unknown members {sorted(unknown)!r}")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _timestamp(value: Any, *, where: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise SchemaError(f"{where}: timestamp is required")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SchemaError(f"{where}: invalid RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise SchemaError(f"{where}: timestamp must carry a timezone")
    return value


@dataclass(frozen=True, slots=True)
class SemanticEntity:
    role: str
    name: str
    type: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, where: str) -> SemanticEntity:
        _closed_keys(value, {"role", "name", "type"}, where=where)
        role = value.get("role")
        entity_type = value.get("type")
        if role not in ENTITY_ROLES:
            raise SchemaError(f"{where}.role: unsupported entity role")
        if entity_type not in ENTITY_TYPES:
            raise SchemaError(f"{where}.type: unsupported entity type")
        return cls(
            role=role,
            name=_text(value.get("name"), where=f"{where}.name"),
            type=entity_type,
        )

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "name": self.name, "type": self.type}


@dataclass(frozen=True, slots=True)
class SemanticEvent:
    category: str
    occurred_at: str | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, where: str) -> SemanticEvent:
        _closed_keys(value, {"category", "occurred_at"}, where=where)
        category = value.get("category")
        if category not in EVENT_CATEGORIES:
            raise SchemaError(f"{where}.category: unsupported event category")
        occurred_at = _timestamp(
            value.get("occurred_at"), where=f"{where}.occurred_at", nullable=True
        )
        return cls(category=category, occurred_at=occurred_at)

    def to_dict(self) -> dict[str, str | None]:
        return {"category": self.category, "occurred_at": self.occurred_at}


@dataclass(frozen=True, slots=True)
class SemanticNumericFact:
    metric: str
    role: str
    value: str | None
    unit: str
    unknown_reason: str | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, where: str) -> SemanticNumericFact:
        _closed_keys(value, {"metric", "role", "value", "unit", "unknown_reason"}, where=where)
        role = value.get("role")
        if role not in NUMERIC_ROLES:
            raise SchemaError(f"{where}.role: unsupported numeric-fact role")
        raw_value = value.get("value")
        unknown_reason = value.get("unknown_reason")
        if unknown_reason is not None and unknown_reason not in UNKNOWN_REASONS:
            raise SchemaError(f"{where}.unknown_reason: unsupported unavailable reason")
        if raw_value is None:
            if unknown_reason is None:
                raise SchemaError(f"{where}: null value requires unknown_reason")
            normalized_value = None
        else:
            if not isinstance(raw_value, str):
                raise SchemaError(f"{where}.value: canonical decimal is required")
            normalized_value = canonicalize_canonical(raw_value, where=f"{where}.value")
            if unknown_reason is not None:
                raise SchemaError(f"{where}: available value cannot have unknown_reason")
        return cls(
            metric=_text(value.get("metric"), where=f"{where}.metric", max_length=MAX_SHORT_TEXT),
            role=role,
            value=normalized_value,
            unit=_text(value.get("unit"), where=f"{where}.unit", max_length=64),
            unknown_reason=unknown_reason,
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "metric": self.metric,
            "role": self.role,
            "value": self.value,
            "unit": self.unit,
            "unknown_reason": self.unknown_reason,
        }


def _document(value: Mapping[str, Any], *, where: str) -> dict[str, str]:
    _closed_keys(value, {"title", "type"}, where=where)
    document_type = value.get("type")
    if document_type not in NEWS_DOCUMENT_TYPES:
        raise SchemaError(f"{where}.type: unsupported news document type")
    return {
        "title": _text(value.get("title"), where=f"{where}.title"),
        "type": document_type,
    }


def _period(value: Any, *, where: str) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: period must be an object or null")
    _closed_keys(value, {"period"}, where=where)
    return {"period": _text(value.get("period"), where=f"{where}.period", max_length=64)}


def _numeric_value(value: Mapping[str, Any], *, where: str) -> dict[str, str]:
    _closed_keys(value, {"value", "unit"}, where=where)
    raw = value.get("value")
    if not isinstance(raw, str):
        raise SchemaError(f"{where}.value: canonical decimal is required")
    return {
        "value": canonicalize_canonical(raw, where=f"{where}.value"),
        "unit": _text(value.get("unit"), where=f"{where}.unit", max_length=64),
    }


def _extension(value: Mapping[str, Any], *, where: str) -> dict[str, Any]:
    extension_type = value.get("type")
    if extension_type == "news":
        _closed_keys(value, {"type", "document"}, where=where)
        document = value.get("document")
        if not isinstance(document, Mapping):
            raise SchemaError(f"{where}.document: object is required")
        return {"type": "news", "document": _document(document, where=f"{where}.document")}
    if extension_type == "macro_release":
        _closed_keys(value, {"type", "indicator", "period", "revision"}, where=where)
        indicator = value.get("indicator")
        if not isinstance(indicator, Mapping):
            raise SchemaError(f"{where}.indicator: object is required")
        _closed_keys(indicator, {"id", "name"}, where=f"{where}.indicator")
        revision = value.get("revision")
        if revision is not None:
            if not isinstance(revision, Mapping):
                raise SchemaError(f"{where}.revision: object or null is required")
            _closed_keys(revision, {"previous", "revised"}, where=f"{where}.revision")
            if not all(isinstance(revision.get(key), Mapping) for key in ("previous", "revised")):
                raise SchemaError(f"{where}.revision: previous and revised values are required")
            revision = {
                "previous": _numeric_value(
                    revision["previous"], where=f"{where}.revision.previous"
                ),
                "revised": _numeric_value(revision["revised"], where=f"{where}.revision.revised"),
            }
        return {
            "type": "macro_release",
            "indicator": {
                "id": _text(
                    indicator.get("id"), where=f"{where}.indicator.id", max_length=MAX_SHORT_TEXT
                ),
                "name": _text(indicator.get("name"), where=f"{where}.indicator.name"),
            },
            "period": _period(value.get("period"), where=f"{where}.period"),
            "revision": revision,
        }
    if extension_type == "policy":
        _closed_keys(
            value, {"type", "policy_type", "action", "effective_at", "affected_scope"}, where=where
        )
        policy_type = value.get("policy_type")
        action = value.get("action")
        if policy_type not in POLICY_TYPES:
            raise SchemaError(f"{where}.policy_type: unsupported policy type")
        if action not in POLICY_ACTIONS:
            raise SchemaError(f"{where}.action: unsupported policy action")
        effective_at = _timestamp(
            value.get("effective_at"), where=f"{where}.effective_at", nullable=True
        )
        affected_scope = value.get("affected_scope")
        if not isinstance(affected_scope, list) or len(affected_scope) > MAX_AFFECTED_SCOPE:
            raise SchemaError(f"{where}.affected_scope: bounded array is required")
        scopes = sorted(
            {
                _text(scope, where=f"{where}.affected_scope[]", max_length=MAX_SHORT_TEXT)
                for scope in affected_scope
            }
        )
        return {
            "type": "policy",
            "policy_type": policy_type,
            "action": action,
            "effective_at": effective_at,
            "affected_scope": scopes,
        }
    raise SchemaError(f"{where}.type: unsupported semantic-context extension")


@dataclass(frozen=True, slots=True)
class SemanticContext:
    """Immutable common context with canonical array ordering."""

    version: int
    entities: tuple[SemanticEntity, ...]
    event: SemanticEvent
    numeric_facts: tuple[SemanticNumericFact, ...]
    extension: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "extension", _freeze(self.extension))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SemanticContext:
        if not isinstance(value, Mapping):
            raise SchemaError("semantic_context: object is required")
        _closed_keys(
            value,
            {"version", "entities", "event", "numeric_facts", "extension"},
            where="semantic_context",
        )
        if isinstance(value.get("version"), bool) or value.get("version") != 1:
            raise SchemaError("semantic_context.version: unsupported context version")
        entities_value = value.get("entities")
        if not isinstance(entities_value, list) or len(entities_value) > MAX_ENTITIES:
            raise SchemaError("semantic_context.entities: bounded array is required")
        entities = tuple(
            sorted(
                {
                    SemanticEntity.from_dict(entity, where=f"semantic_context.entities[{index}]")
                    for index, entity in enumerate(entities_value)
                    if isinstance(entity, Mapping)
                },
                key=lambda entity: (entity.role, entity.name, entity.type),
            )
        )
        if len(entities) != len(entities_value):
            invalid_count = sum(not isinstance(entity, Mapping) for entity in entities_value)
            if invalid_count:
                raise SchemaError("semantic_context.entities: every member must be an object")
        event_value = value.get("event")
        if not isinstance(event_value, Mapping):
            raise SchemaError("semantic_context.event: object is required")
        numeric_value = value.get("numeric_facts")
        if not isinstance(numeric_value, list) or len(numeric_value) > MAX_NUMERIC_FACTS:
            raise SchemaError("semantic_context.numeric_facts: bounded array is required")
        numeric_facts = tuple(
            sorted(
                {
                    SemanticNumericFact.from_dict(
                        fact, where=f"semantic_context.numeric_facts[{index}]"
                    )
                    for index, fact in enumerate(numeric_value)
                    if isinstance(fact, Mapping)
                },
                key=lambda fact: (
                    fact.metric,
                    fact.role,
                    fact.unit,
                    fact.value or "",
                    fact.unknown_reason or "",
                ),
            )
        )
        if len(numeric_facts) != len(numeric_value):
            invalid_count = sum(not isinstance(fact, Mapping) for fact in numeric_value)
            if invalid_count:
                raise SchemaError("semantic_context.numeric_facts: every member must be an object")
        extension_value = value.get("extension")
        if not isinstance(extension_value, Mapping):
            raise SchemaError("semantic_context.extension: object is required")
        return cls(
            version=1,
            entities=entities,
            event=SemanticEvent.from_dict(event_value, where="semantic_context.event"),
            numeric_facts=numeric_facts,
            extension=_extension(extension_value, where="semantic_context.extension"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "entities": [entity.to_dict() for entity in self.entities],
            "event": self.event.to_dict(),
            "numeric_facts": [fact.to_dict() for fact in self.numeric_facts],
            "extension": _thaw(self.extension),
        }


__all__ = [
    "ENTITY_ROLES",
    "ENTITY_TYPES",
    "EVENT_CATEGORIES",
    "MAX_AFFECTED_SCOPE",
    "MAX_ENTITIES",
    "MAX_NUMERIC_FACTS",
    "NEWS_DOCUMENT_TYPES",
    "NUMERIC_ROLES",
    "POLICY_ACTIONS",
    "POLICY_TYPES",
    "SemanticContext",
    "SemanticEntity",
    "SemanticEvent",
    "SemanticNumericFact",
]
