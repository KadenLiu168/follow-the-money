"""Closed conditional editor slot allocator, projection, and merge (design 16).

Slot kinds and counts are closed, not implementation-selected:

- exactly one ``market_state_explanation``;
- per full-formatted Event (count ``F``, ``0 <= F <= 3``) exactly one each of
  ``event_fact_summary``, ``why_it_matters``, ``reaction_attribution``,
  ``price_in``, ``money_flow``, ``asset_mapping``, ``alternative``, and
  ``uncertainty``;
- per compact-formatted Event (count ``C``, ``0 <= C <= 12 - F``) exactly one
  each of ``event_fact_summary``, ``why_it_matters``, and ``uncertainty``;
- one ``watchlist_explanation`` per selected calendar item;
- ``min(3, F + C)`` optional ``bottom_line_point`` slots owned, in final
  selection order, by those first selected Events.

Scripts build a closed bounded source view per slot, expose only the owning
event's evidence aliases, and map filled wording back into the authoritative
Brief projection. A required unfilled slot fails assembly; an unknown slot,
a non-subset reference, or any attempt to supply a script-owned field is
rejected (no fallback). ``bottom_line_point`` slots are optional; optional
unfilled slots appear only in the allocation trace, never in the claim
inventory.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .brief import BriefError

FULL_SLOT_KINDS = (
    "event_fact_summary",
    "why_it_matters",
    "reaction_attribution",
    "price_in",
    "money_flow",
    "asset_mapping",
    "alternative",
    "uncertainty",
)
COMPACT_SLOT_KINDS = ("event_fact_summary", "why_it_matters", "uncertainty")

FACTUAL_KINDS = frozenset(
    {
        "market_state_explanation",
        "event_fact_summary",
        "reaction_attribution",
        "price_in",
        "money_flow",
        "asset_mapping",
    }
)
CAUSAL_KINDS = frozenset({"why_it_matters", "alternative", "bottom_line_point"})


@dataclass(frozen=True)
class EditorSlot:
    alias: str
    kind: str
    owner: str  # event_id | "market_state" | "watchlist:<calendar_id>" | "bottom_line"
    required: bool
    is_factual: bool
    is_causal: bool
    exposed_aliases: tuple[str, ...] = ()


def allocate_slots(
    *,
    market_state: Mapping[str, Any],
    full_events: Sequence[Mapping[str, Any]],
    compact_events: Sequence[Mapping[str, Any]],
    watchlist: Sequence[Mapping[str, Any]],
    bottom_line_owners: Sequence[str],
    evidence_aliases: Mapping[str, str],
) -> list[EditorSlot]:
    """Allocate the closed conditional slot set in render order."""
    slots: list[EditorSlot] = []
    n = 0

    def add(kind: str, owner: str, required: bool, exposed: Sequence[str]) -> None:
        nonlocal n
        slots.append(
            EditorSlot(
                alias=f"s{n:02d}",
                kind=kind,
                owner=owner,
                required=required,
                is_factual=kind in FACTUAL_KINDS,
                is_causal=kind in CAUSAL_KINDS,
                exposed_aliases=tuple(dict.fromkeys(exposed))[:8],
            )
        )
        n += 1

    # market_state_explanation
    exposed = _aliases_for(evidence_aliases, market_state.get("evidence_ids", ()))
    add("market_state_explanation", "market_state", True, exposed)

    # full events (8 kinds each)
    for event in full_events:
        exposed = _aliases_for(evidence_aliases, event.get("evidence_ids", ()))
        for kind in FULL_SLOT_KINDS:
            add(kind, event.get("event_id", ""), True, exposed)

    # compact events (3 kinds each)
    for event in compact_events:
        exposed = _aliases_for(evidence_aliases, event.get("evidence_ids", ()))
        for kind in COMPACT_SLOT_KINDS:
            add(kind, event.get("event_id", ""), True, exposed)

    # watchlist explanations
    for item in watchlist:
        exposed = _aliases_for(evidence_aliases, item.get("evidence_ids", ()))
        add("watchlist_explanation", f"watchlist:{item.get('calendar_id', '')}", True, exposed)

    # bottom_line points (optional, first selected owners)
    for owner in bottom_line_owners:
        exposed = _aliases_for(
            evidence_aliases,
            next(
                (
                    e.get("evidence_ids", ())
                    for e in [*full_events, *compact_events]
                    if e.get("event_id") == owner
                ),
                (),
            ),
        )
        add("bottom_line_point", owner, False, exposed)

    return slots


def build_projection(
    slots: Sequence[EditorSlot],
    *,
    source_views: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the closed bounded projection sent to the editor.

    ``source_views`` maps slot alias -> the script-owned bounded canonical
    source view (projection_version, slot_kind, owner_alias, kind-specific
    structured fields, and exposed reference aliases).
    """
    return {
        "projection_version": 1,
        "slots": [
            {
                "slot_alias": s.alias,
                "slot_kind": s.kind,
                "owner_alias": s.owner,
                "required": s.required,
                "reference_aliases": list(s.exposed_aliases),
                **source_views.get(s.alias, {}),
            }
            for s in slots
        ],
    }


def merge_editor_output(
    *,
    slots: Sequence[EditorSlot],
    editor_output: Mapping[str, Any],
    full_events: Sequence[Mapping[str, Any]],
    compact_events: Sequence[Mapping[str, Any]],
    market_state: Mapping[str, Any],
    watchlist: Sequence[Mapping[str, Any]],
    alias_to_evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Validate the editor response and merge wording into the Brief projection.

    Returns ``{full_events, compact_events, market_state, watchlist,
    bottom_line, slot_meta}`` ready for :func:`assemble_brief`. Script-owned
    fields (event_id, display_label, confidence, source_links, market_state,
    watchlist priority/order, bottom-line ownership) come only from the script
    side; the editor supplies only wording fragments and evidence references.
    """
    for forbidden in ("headings", "dashboard", "market_state", "score", "status", "urls"):
        if forbidden in editor_output:
            raise BriefError(f"editor output must not supply {forbidden!r}")
    from .schema import validate_against

    validate_against("editor-output.schema.json", editor_output)

    slot_by_alias = {s.alias: s for s in slots}
    filled = editor_output.get("filled_slots", [])
    if len(filled) > len(slots):
        raise BriefError(f"editor filled {len(filled)} slots; only {len(slots)} allocated")

    wording: dict[str, str] = {}
    reference_aliases_by_slot: dict[str, tuple[str, ...]] = {}
    for entry in filled:
        alias = entry["slot_alias"]
        if alias not in slot_by_alias:
            raise BriefError(f"editor filled unallocated slot {alias!r}")
        if alias in wording:
            raise BriefError(f"editor filled slot {alias!r} more than once")
        refs = entry.get("reference_aliases", [])
        allowed = set(slot_by_alias[alias].exposed_aliases)
        if not set(refs) <= allowed:
            raise BriefError(
                f"slot {alias}: editor referenced non-exposed evidence aliases {sorted(set(refs) - allowed)}"
            )
        wording[alias] = entry["wording_fragment"]
        reference_aliases_by_slot[alias] = tuple(refs)

    # Required unfilled slots fail assembly (no fallback).
    for s in slots:
        if s.required and s.alias not in wording:
            raise BriefError(f"required editor slot {s.alias!r} ({s.kind}) was not filled")
        if (
            s.kind == "market_state_explanation"
            and market_state.get("regime") != "unknown"
            and not reference_aliases_by_slot.get(s.alias)
        ):
            raise BriefError(
                "classified Market State explanation requires at least one evidence reference"
            )

    slot_meta = {
        s.alias: {
            "class": "editor" if s.kind != "bottom_line_point" else "bottom_line",
            "slot_kind": s.kind,
            "is_factual": s.is_factual
            and (
                s.kind != "market_state_explanation" or bool(reference_aliases_by_slot.get(s.alias))
            ),
            "is_causal": s.is_causal,
        }
        for s in slots
        if s.alias in wording
    }

    full_projs = [
        _project_event(e, wording, slots, kind=kind, alias_to_evidence=alias_to_evidence)
        for e, kind in ((e, "full") for e in full_events)
    ]
    compact_projs = [
        _project_event(e, wording, slots, kind="compact", alias_to_evidence=alias_to_evidence)
        for e in compact_events
    ]

    # market_state: script-owned (editor may not change it).
    market_out = dict(market_state)
    market_out.pop("evidence_ids", None)
    market_out.pop("evidence_cutoff_at", None)
    state_explanation = next(
        (
            wording[s.alias]
            for s in slots
            if s.kind == "market_state_explanation" and s.alias in wording
        ),
        "",
    )
    market_out["explanation"] = state_explanation
    # watchlist: label is script-derived from the calendar title; explanation
    # is the editor's ``watchlist_explanation`` wording for that item.
    watchlist_out = []
    for item in watchlist:
        w = dict(item)
        w.pop("evidence_ids", None)
        w.pop("announced_at", None)
        w["label"] = (item.get("title") or item.get("calendar_id") or "")[:300]
        explanation = next(
            (
                wording[s.alias]
                for s in slots
                if s.kind == "watchlist_explanation"
                and s.owner == f"watchlist:{item.get('calendar_id', '')}"
                and s.alias in wording
            ),
            "",
        )
        w["explanation"] = explanation
        watchlist_out.append(w)

    bottom_line = [
        {
            "event_id": s.owner,
            "text": wording[s.alias],
        }
        for s in slots
        if s.kind == "bottom_line_point" and s.alias in wording
    ]

    wording_by_owner: dict[str, dict[str, str]] = {}
    for s in slots:
        if (
            s.alias in wording
            and s.owner
            and s.owner != "market_state"
            and not s.owner.startswith("watchlist:")
        ):
            wording_by_owner.setdefault(s.owner, {})[s.kind] = wording[s.alias]

    return {
        "full_events": full_projs,
        "compact_events": compact_projs,
        "market_state": market_out,
        "watchlist": watchlist_out,
        "bottom_line": bottom_line,
        "slot_meta": slot_meta,
        "wording_by_owner": wording_by_owner,
    }


def _project_event(
    event: Mapping[str, Any],
    wording: Mapping[str, str],
    slots: Sequence[EditorSlot],
    *,
    kind: str,
    alias_to_evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Project one event into the full/compact Brief schema shape.

    Editor wording is merged per slot kind; every authoritative field
    (event_id, display_label, confidence, source_links) is script-owned.
    """
    eid = event.get("event_id", "")
    kinds = FULL_SLOT_KINDS if kind == "full" else COMPACT_SLOT_KINDS
    by_kind: dict[str, str] = {}
    for s in slots:
        if s.owner == eid and s.kind in kinds and s.alias in wording:
            by_kind[s.kind] = wording[s.alias]

    # Slot kinds are the allocator vocabulary; the Brief schema field names
    # differ for two of them (event_fact_summary -> fact_summary,
    # asset_mapping -> asset_mappings).
    FIELD_BY_KIND = {
        "event_fact_summary": "fact_summary",
        "why_it_matters": "why_it_matters",
        "reaction_attribution": "reaction_attribution",
        "price_in": "price_in",
        "money_flow": "money_flow",
        "asset_mapping": "asset_mappings",
        "alternative": "alternative",
        "uncertainty": "uncertainty",
    }
    projection: dict[str, Any] = {
        "event_id": eid,
        "display_label": event.get("display_label", ""),
        "confidence": event.get("confidence", "high"),
        "source_links": [u for u in event.get("source_urls", ()) if isinstance(u, str) and u],
    }
    for k in kinds:
        projection[FIELD_BY_KIND[k]] = by_kind.get(k, "")
    return projection


def _aliases_for(evidence_aliases: Mapping[str, str], evidence_ids: Sequence[str]) -> list[str]:
    reverse = {eid: alias for alias, eid in evidence_aliases.items()}
    return [reverse[eid] for eid in dict.fromkeys(evidence_ids) if eid in reverse]
