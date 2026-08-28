"""Canonical Event construction — script-owned identity and labels.

Design sections 6/7:

- Canonical event IDs hash the versioned tuple of sorted evidence IDs, event
  type, normalized resolved entity IDs, and an atomic discriminator formed
  from the sorted complete canonical keys of the event-defining facts.
- ``fully_known_at`` is the maximum ``knowledge_available_at`` across the
  exact ``key_fact_ids``; ``key_fact_ids = sorted(unique(event_defining_fact_ids))``.
- ``story_family_id`` derives from the sorted member Event IDs; coexistence
  pairs are unordered Event-ID pairs.
- Chinese display labels come only from a versioned template over the closed
  event type, resolved entity display names, and structured values/units of
  existing key facts — never from LLM free text.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from .canonical import canonical_text
from .ledger import Ledger, LedgerEntry, canonical_fact_key

DISPLAY_TEMPLATES: Mapping[str, str] = {
    "macro_release": "{subject_zh}发布{label_zh}：{value}{unit}",
    "policy": "{subject_zh}政策调整：{value}",
    "filing": "{company}提交{form}申报",
    "news": "{subject_zh}：{summary}",
    "default": "{subject_zh} {predicate} {value}{unit}",
}

_EVENT_TYPE_HINTS = {
    "macro_release": "宏观数据",
    "policy": "政策",
    "filing": "公司申报",
    "news": "事件",
    "flow": "资金流",
    "positioning": "持仓",
    "default": "事件",
}


def max_knowledge_time(entries: Iterable[LedgerEntry]) -> str:
    times = [e.knowledge_available_at for e in entries]
    if not times:
        raise ValueError("cannot compute fully_known_at from an empty fact set")
    return max(times, key=lambda t: datetime.fromisoformat(t))


def key_fact_ids_from(event_defining_fact_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(event_defining_fact_ids)))


def canonical_event_id(
    *,
    evidence_ids: Iterable[str],
    event_type: str,
    entity_ids: Iterable[str],
    defining_fact_keys: Iterable[str],
    version: int = 1,
) -> str:
    """Deterministic event ID from sorted canonical components."""
    payload = {
        "version": version,
        "evidence_ids": sorted(set(evidence_ids)),
        "event_type": event_type,
        "entity_ids": sorted(set(entity_ids)),
        "discriminator": sorted(set(defining_fact_keys)),
    }
    digest = hashlib.sha256(canonical_text(payload).encode("utf-8")).hexdigest()
    return f"evt_{digest[:40]}"


def story_family_id(member_event_ids: Iterable[str]) -> str:
    """Canonical family ID from sorted member Event IDs.

    Unknown/singleton families become Event-ID-specific singletons.
    """
    members = tuple(sorted(set(member_event_ids)))
    if not members:
        raise ValueError("story family requires at least one member Event ID")
    if len(members) == 1:
        return f"fam_single_{members[0]}"
    digest = hashlib.sha256("|".join(members).encode("utf-8")).hexdigest()
    return f"fam_{digest[:40]}"


def unordered_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def display_label(
    *,
    event_type: str,
    subject_zh: str,
    key_facts: Iterable[LedgerEntry],
    company: str | None = None,
    form: str | None = None,
) -> str:
    """Script-derived Chinese display label from closed structured fields only."""
    facts = list(key_facts)
    if not facts:
        raise ValueError("display label requires at least one key fact")
    first = facts[0]
    template = DISPLAY_TEMPLATES.get(event_type, DISPLAY_TEMPLATES["default"])
    label_zh = _EVENT_TYPE_HINTS.get(event_type, "事件")
    value = first.value or "—"
    unit = first.unit or ""
    return template.format(
        subject_zh=subject_zh,
        label_zh=label_zh,
        value=value,
        unit=unit,
        company=company or subject_zh,
        form=form or "",
        predicate=first.predicate,
        summary=first.predicate,
    )


def build_event(
    *,
    event_type: str,
    evidence_ids: Iterable[str],
    entity_ids: Iterable[str],
    event_defining_fact_ids: Iterable[str],
    ledger: Ledger,
    subject_zh: str,
    company: str | None = None,
    form: str | None = None,
    member_events: Iterable[str] | None = None,
    coexistence_pairs: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Construct a canonical Event object with script-owned identity.

    The event's key facts are looked up from the frozen ledger; the display
    label is derived deterministically. Returns a closed structured dict with
    script-owned identity; the old ``event.schema.json`` contract was removed
    with the four-pass pipeline.
    """
    evidence = tuple(sorted(set(evidence_ids)))
    entities = tuple(sorted(set(entity_ids)))
    key_ids = key_fact_ids_from(event_defining_fact_ids)
    key_facts = tuple(ledger.get(fid) for fid in key_ids)
    fully_known = max_knowledge_time(key_facts)

    fact_keys = tuple(sorted(canonical_fact_key(f) for f in key_facts))
    event_id = canonical_event_id(
        evidence_ids=evidence,
        event_type=event_type,
        entity_ids=entities,
        defining_fact_keys=fact_keys,
    )

    members = member_events if member_events is not None else (event_id,)
    fam = story_family_id(members)
    pairs = tuple(sorted(unordered_pair(a, b) for a, b in (coexistence_pairs or ())))

    label = display_label(
        event_type=event_type,
        subject_zh=subject_zh,
        key_facts=key_facts,
        company=company,
        form=form,
    )

    # Economic effective/reference times from key facts.
    first_key_fact = key_facts[0]
    times = [f.effective_time for f in key_facts if f.effective_time is not None]
    precisions = {f.effective_precision for f in key_facts}
    common = None
    multiple = len(set(times)) > 1 or len(precisions) > 1
    if first_key_fact.effective_time is not None and all(
        fact.effective_time == first_key_fact.effective_time
        and fact.effective_precision == first_key_fact.effective_precision
        for fact in key_facts
    ):
        common = {
            "value": first_key_fact.effective_time,
            "precision": first_key_fact.effective_precision,
        }
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "evidence_ids": list(evidence),
        "key_fact_ids": list(key_ids),
        "fully_known_at": fully_known,
        "story_family_id": fam,
        "coexistence_pair_ids": [list(p) for p in pairs],
        "display_label": label,
        "economic_effective_time": {
            "value": first_key_fact.effective_time,
            "precision": first_key_fact.effective_precision,
        },
        "common_effective_time": common,
        "multiple_effective_times": multiple if times else False,
        "key_fact_effective_times": [
            {
                "fact_id": f.fact_id,
                "value": f.effective_time,
                "precision": f.effective_precision,
            }
            for f in key_facts
        ],
    }


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
