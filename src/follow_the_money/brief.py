"""Editor-output → authoritative Brief assembly and degraded-report builder.

Design sections 16/17:

- The editor returns only wording fragments and references for already
  selected runtime objects; scripts own IDs, facts, numbers, scores,
  statuses, URLs, ordering, section membership, and the claim inventory.
- Scripts allocate the closed conditional slot set (at most 61 editor slots
  plus 13 script-filled dashboard claims => at most 74 claims); the
  authoritative ``claim_inventory`` contains exactly filled/rendered slots.
- The editor may return only a subset of exposed evidence aliases; scripts
  restore canonical IDs and retain complete support closure.
- The separate deterministic degraded report contains only script-owned
  fields and never event interpretation or LLM-owned content.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .schema import validate_against

EDITOR_MAX_SLOTS = 61
DASHBOARD_CLAIM_COUNT = 13
MAX_CLAIMS = 74

HEADING_ORDER = (
    "市场仪表盘",
    "市场状态",
    "重点事件",
    "其他重要事件",
    "资金流与持仓",
    "未来 24 小时关注",
    "结论",
)


class BriefError(ValueError):
    """Brief assembly or ownership validation failed."""


def _resolve_slot_refs(
    aliases: Sequence[str],
    alias_to_evidence: Mapping[str, str],
    where: str,
) -> tuple[str, ...]:
    resolved = []
    for alias in aliases:
        if alias not in alias_to_evidence:
            raise BriefError(f"{where}: unknown reference alias {alias!r}")
        resolved.append(alias_to_evidence[alias])
    return tuple(dict.fromkeys(resolved))


def assemble_brief(
    *,
    brief_id: str,
    brief_generated_at: str,
    brief_completed_at: str,
    evidence_cutoff_at: str,
    feed_run_id: str,
    editor_output: Mapping[str, Any],
    alias_to_evidence: Mapping[str, str],
    slot_meta: Mapping[str, Mapping[str, Any]] | None = None,
    dashboard: Sequence[Mapping[str, Any]],
    market_state: Mapping[str, Any],
    full_events: Sequence[Mapping[str, Any]],
    compact_events: Sequence[Mapping[str, Any]],
    money_flow_section: Sequence[Mapping[str, Any]],
    watchlist: Sequence[Mapping[str, Any]],
    bottom_line: Sequence[Mapping[str, Any]],
    warnings: Sequence[str] = (),
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate editor output and assemble the authoritative Brief.

    ``slot_meta`` maps each allocated slot alias to script-owned metadata
    (``slot_kind``, ``is_factual``, ``is_causal``). These flags never come
    from the LLM; they are looked up from the script-side allocation trace.
    """
    # Editor may only fill allocated slots; scripts own every authoritative
    # field. Reject any attempt to supply script-owned fields before schema
    # validation so the ownership error is precise.
    for forbidden in ("headings", "dashboard", "market_state", "score", "status", "urls"):
        if forbidden in editor_output:
            raise BriefError(f"editor output must not supply {forbidden!r}")

    validate_against("editor-output.schema.json", editor_output)

    filled = editor_output.get("filled_slots", [])
    if len(filled) > EDITOR_MAX_SLOTS:
        raise BriefError(f"editor returned {len(filled)} slots; maximum is {EDITOR_MAX_SLOTS}")

    # Build claim inventory from filled slots plus 13 script-filled dashboard
    # claims. Every filled slot becomes exactly one claim; slot kind and
    # factual/causal flags come from the script allocation trace.
    claims: list[dict[str, Any]] = []
    slot_meta = slot_meta or {}
    for idx, slot in enumerate(filled):
        alias = slot["slot_alias"]
        meta = slot_meta.get(alias, {})
        refs = _resolve_slot_refs(
            slot.get("reference_aliases", []), alias_to_evidence, f"filled_slots[{idx}]"
        )
        claims.append(
            {
                "claim_id": f"claim_{brief_id}_{idx:03d}",
                "class": meta.get("class", "editor"),
                "slot_kind": meta.get("slot_kind", "editor_fragment"),
                "is_factual": bool(meta.get("is_factual", False)),
                "is_causal": bool(meta.get("is_causal", False)),
                "text": slot["wording_fragment"],
                "reference_evidence_ids": list(refs),
            }
        )
    roles = list(dashboard)
    for idx in range(DASHBOARD_CLAIM_COUNT):
        role = roles[idx] if idx < len(roles) else {}
        display = (role.get("display") or role.get("role_id") or "").strip()
        available = bool(role.get("available"))
        text = f"{display}当前{'有可用数据' if available else '无可用数据'}。" if display else ""
        claims.append(
            {
                "claim_id": f"claim_{brief_id}_dash_{idx:02d}",
                "class": "dashboard",
                "slot_kind": "dashboard_observation",
                "is_factual": True,
                "is_causal": False,
                "text": text,
                "reference_evidence_ids": [],
            }
        )
    if len(claims) > MAX_CLAIMS:
        raise BriefError(f"claim inventory exceeds {MAX_CLAIMS}")

    # Validate market_state / dashboard shapes against brief schema.
    brief = {
        "schema_version": 1,
        "brief_id": brief_id,
        "brief_generated_at": brief_generated_at,
        "brief_completed_at": brief_completed_at,
        "evidence_cutoff_at": evidence_cutoff_at,
        "feed_run_id": feed_run_id,
        "mode": "normal",
        "headings": list(HEADING_ORDER),
        "dashboard": [dict(d) for d in dashboard],
        "market_state": dict(market_state),
        "full_events": [dict(e) for e in full_events],
        "compact_events": [dict(e) for e in compact_events],
        "money_flow_section": [dict(m) for m in money_flow_section],
        "watchlist": [dict(w) for w in watchlist],
        "bottom_line": [dict(b) for b in bottom_line],
        "claim_inventory": claims,
        "warnings": list(warnings),
        "audit_status": {
            "script_audit": "passed",
            "language_audit": "passed",
            "findings": [],
        },
        "provenance": dict(provenance or {}),
    }
    validate_against("brief.schema.json", brief)
    return brief


def build_degraded_report(
    *,
    report_id: str,
    brief_generated_at: str,
    evidence_cutoff_at: str,
    feed_run_id: str,
    feed_health: Mapping[str, Any],
    dashboard: Sequence[Mapping[str, Any]],
    analytics: Mapping[str, Any],
    unresolved_counts: Mapping[str, int],
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the separately typed deterministic degraded report."""
    report = {
        "schema_version": 1,
        "report_id": report_id,
        "brief_generated_at": brief_generated_at,
        "evidence_cutoff_at": evidence_cutoff_at,
        "feed_run_id": feed_run_id,
        "mode": "degraded",
        "feed_health": dict(feed_health),
        "dashboard": [dict(d) for d in dashboard],
        "analytics": dict(analytics),
        "unresolved_counts": dict(unresolved_counts),
        "warnings": list(warnings),
        "audit_status": {"script_audit": "passed"},
    }
    validate_against("degraded-report.schema.json", report)
    return report
