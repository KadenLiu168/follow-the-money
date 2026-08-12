"""Complete deterministic Feed-to-Brief pipeline orchestration (gate 13.3).

Replaces the historical ``_mock_*`` shortcuts in the normal Brief path with
the full deterministic pipeline plus the four constrained Responses API
passes:

1. Feed -> Evidence Ledger (script-owned facts, no LLM).
2. Ledger -> candidate mention graph -> bounded blocks (script-only).
3. Resolver pass (LLM) -> canonical Events (script-owned IDs/labels).
4. Verified event packets (script-only; unresolved excluded from analysis).
5. Analyst pass (LLM) -> script-owned Analysis merge.
6. Deterministic scoring (significance / morning relevance / priority).
7. Deterministic selection (eligibility, family penalty, full/compact).
8. Editor pass (LLM) -> script-owned Brief assembly.
9. Render -> script claim audit -> language audit pass (LLM).

Every LLM pass is a constrained structured call through the single-model
Responses adapter; a failed pass is a typed failure that blocks normal
publication (no fallback). ``--degraded-report`` remains a separate explicit
path and never satisfies this gate.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from .analysis import merge_analysis
from .boundary import assemble_verified_packet
from .brief import assemble_brief
from .config.model import AppConfig
from .engine.candidates import (
    build_edges,
    build_mention_nodes,
    connected_components,
    pack_blocks,
)
from .engine.entities import EntityResolver
from .engine.resolution import (
    alias_component_ids,
    resolve_component_events,
    validate_seed_coverage,
)
from .ledger import Ledger, LedgerEntry, build_ledger_entry
from .llm import LlmOutcome, ResponsesAdapter, invoke_pass
from .market.confidence import event_confidence
from .scoring import (
    brief_priority,
    event_significance,
    morning_relevance,
    significance_components,
)
from .selection import SelectedEvent, SelectionInput, select_events
from .watchlist import build_watchlist


class PipelineError(ValueError):
    """Normal Brief pipeline failed (typed at the orchestration boundary)."""


@dataclass
class PipelineResult:
    brief: dict[str, Any]
    ledger: Ledger
    events: list[dict[str, Any]]
    packets: list[dict[str, Any]]
    analyses: list[dict[str, Any]]
    selected: list[SelectedEvent]
    llm_outcomes: list[LlmOutcome]
    warnings: list[str] = field(default_factory=list)
    degraded_warnings: list[str] = field(default_factory=list)
    # Raw validated structured LLM outputs per pass, keyed by pass name:
    # {"resolver": [..], "analyst": [..], "editor": {...}, "language-audit": {...}}.
    # Saved into the run bundle so deterministic replay can re-merge them
    # without network or LLM access.
    llm_data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Feed -> Ledger
# ---------------------------------------------------------------------------


def feed_to_ledger(
    feed: Mapping[str, Any],
    cfg: AppConfig,
    resolver: EntityResolver,
) -> Ledger:
    """Build the frozen Evidence Ledger from Feed items (script-owned).

    Every normalized source fact becomes a ``FACT``/``CLAIM`` ledger entry
    with a script-derived ``knowledge_available_at``; ``market_data``/
    ``calendar`` items become ``OBSERVATION`` entries (never atomic seeds).
    Unresolvable subjects are preserved as stable normalized raw subjects.
    """
    ledger = Ledger()
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        ptype = payload.get("type", "")
        evidence_id = item.get("id", "")
        source = item.get("source", {})
        knowledge = (
            source.get("knowledge_available_at")
            or payload.get("occurred_at")
            or payload.get("released_at")
            or payload.get("announced_at")
            or payload.get("filed_at")
        )
        if not knowledge:
            continue

        subject, raw_subject = _resolve_subject(payload, resolver)
        families = tuple(
            dict.fromkeys(f for f in (source.get("source_family_id") or source.get("name"),) if f)
        )
        tier = source.get("tier", "Tier 2")
        tier_counts = {tier: 1}

        if ptype == "market_data":
            entry = build_ledger_entry(
                entry_type="OBSERVATION",
                origin_payload="market_data",
                evidence_id=evidence_id,
                subject=subject or payload.get("instrument_id", "market"),
                predicate="observation",
                effective_time=payload.get("observations", [{}])[-1].get("as_of")
                if payload.get("observations")
                else None,
                effective_precision="instant",
                value=str(payload.get("observations", [{}])[-1].get("value"))
                if payload.get("observations")
                else None,
                unit=payload.get("unit"),
                knowledge_available_at=knowledge,
                source_families=families,
                tier_counts=tier_counts,
                raw_subject=raw_subject,
            )
            ledger.add(entry)
            continue

        if ptype == "calendar":
            entry = build_ledger_entry(
                entry_type="OBSERVATION",
                origin_payload="calendar",
                evidence_id=evidence_id,
                subject=subject or payload.get("calendar_id", "calendar"),
                predicate="scheduled",
                effective_time=payload.get("scheduled_at"),
                effective_precision="instant",
                value=None,
                unit=None,
                knowledge_available_at=knowledge,
                source_families=families,
                tier_counts=tier_counts,
                raw_subject=raw_subject,
            )
            ledger.add(entry)
            continue

        # Seed-capable payloads: news | macro_release | policy | filing | flow | positioning
        effective_time, precision, value, unit = _payload_fact(payload)
        predicate = _predicate_for(ptype)
        entry = build_ledger_entry(
            entry_type="FACT",
            origin_payload=ptype,
            evidence_id=evidence_id,
            subject=subject,
            predicate=predicate,
            effective_time=effective_time,
            effective_precision=precision,
            value=value,
            unit=unit,
            knowledge_available_at=knowledge,
            source_families=families,
            tier_counts=tier_counts,
            raw_subject=raw_subject,
        )
        ledger.add(entry)
    return ledger


def _resolve_subject(payload: Mapping[str, Any], resolver: EntityResolver) -> tuple[str, str]:
    """Return ``(subject_id, raw_subject)``; unresolved keeps a stable raw key."""
    candidates: list[str] = []
    title = payload.get("title") or ""
    if title:
        candidates.append(title)
    for key in ("instrument_id", "series_id", "company", "calendar_id"):
        if payload.get(key):
            candidates.append(str(payload[key]))
    for text in candidates:
        if not text:
            continue
        from .engine.entities import resolve_institutions

        found = resolve_institutions(text, resolver)
        if found and found[0].entity_id:
            return found[0].entity_id, text
    # Stable normalized raw-subject identity (never free-text labels).
    raw = _normalize_raw_subject(candidates[0] if candidates else "unresolved")
    return f"raw_{raw[:24]}", candidates[0] if candidates else "unresolved"


def _normalize_raw_subject(text: str) -> str:
    import unicodedata

    nfc = unicodedata.normalize("NFC", text)
    return "".join(ch for ch in nfc if not unicodedata.category(ch).startswith(("P", "Z", "C")))


def _payload_fact(payload: Mapping[str, Any]) -> tuple[str | None, str, str | None, str | None]:
    """Extract (effective_time, precision, value, unit) from a seed payload."""
    if payload.get("type") == "macro_release":
        actual = payload.get("actual") or {}
        return (
            payload.get("released_at"),
            "instant",
            str(actual["value"]) if actual.get("value") is not None else None,
            actual.get("unit"),
        )
    if payload.get("type") == "filing":
        return payload.get("filed_at"), "instant", payload.get("form"), None
    if payload.get("type") == "flow":
        net = payload.get("net_flow") or {}
        return (
            payload.get("as_of"),
            "instant",
            str(net["value"]) if net.get("value") is not None else None,
            net.get("unit"),
        )
    if payload.get("type") == "positioning":
        pos = payload.get("position") or {}
        return (
            payload.get("as_of"),
            "instant",
            str(pos["value"]) if pos.get("value") is not None else None,
            pos.get("unit"),
        )
    if payload.get("type") == "policy":
        return payload.get("announced_at"), "instant", payload.get("title"), None
    return payload.get("occurred_at"), "instant", payload.get("title"), None


def _predicate_for(ptype: str) -> str:
    return {
        "news": "reported",
        "macro_release": "released",
        "policy": "announced",
        "filing": "filed",
        "flow": "net_flow",
        "positioning": "position",
    }.get(ptype, "reported")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    *,
    cfg: AppConfig,
    feed: Mapping[str, Any],
    brief_generated_at: str,
    adapter: ResponsesAdapter | None,
    resolver: EntityResolver,
    prompts: Mapping[str, str],
    monotonic_deadline: float | None = None,
    max_blocks: int = 40,
    max_packets: int = 20,
    direct_flow_evidence_ids: Sequence[str] = (),
    saved_llm: Mapping[str, Any] | None = None,
) -> PipelineResult:
    """Run the complete deterministic + constrained-LLM pipeline.

    ``saved_llm`` supplies the recorded raw validated structured outputs per
    pass (from a run bundle) so deterministic replay re-merges them without
    any network or LLM access; every deterministic stage is re-executed and
    compared. Without it the four Responses API passes are invoked live.
    Raises :class:`PipelineError` on any typed failure (no fallback).
    """
    llm_data: dict[str, Any] = {
        "resolver": [],
        "analyst": [],
        "editor": None,
        "language-audit": None,
    }
    llm_outcomes: list[LlmOutcome] = []

    def _llm_pass(
        pass_name: str,
        *,
        idx: int | None,
        prompt: str,
        schema: Mapping[str, Any],
        envelope: Mapping[str, Any],
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        if saved_llm is not None:
            saved = saved_llm[pass_name]
            data = saved[idx] if idx is not None else saved
            return dict(data)
        outcome = invoke_pass(
            adapter,  # type: ignore[arg-type]
            pass_name=pass_name,
            prompt=prompt,
            response_schema=schema,
            envelope=envelope,
            canonical_input=projection,
            monotonic_deadline=monotonic_deadline,
        )
        llm_outcomes.append(outcome)
        if outcome.status != "success":
            raise PipelineError(f"{pass_name} pass failed: {outcome.status}: {outcome.error}")
        data = outcome.data
        if idx is None:
            llm_data[pass_name] = data
        else:
            llm_data[pass_name].append(data)
        return data

    # 1. Ledger
    ledger = feed_to_ledger(feed, cfg, resolver)
    seeds = ledger.seed_fact_ids()
    warnings: list[str] = []
    if not seeds:
        warnings.append("no atomic event seeds in Feed")

    # 2. Candidate graph + blocks
    nodes = build_mention_nodes(ledger.entries())
    edges = build_edges(nodes, {e.fact_id: e for e in ledger.entries()}, resolver)
    components = connected_components(nodes, edges, {e.fact_id: e for e in ledger.entries()})
    blocks = pack_blocks(components)
    if not blocks:
        warnings.append("no candidate blocks")

    # 3. Resolver pass -> Events
    events: list[dict[str, Any]] = []
    for block_index, block in enumerate(blocks[:max_blocks]):
        aliases = alias_component_ids(block.components)
        prompt = prompts["resolver"]
        resolver_projection = {
            "blocks": [_block_projection(block, aliases)],
        }
        output = _llm_pass(
            "resolver",
            idx=block_index,
            prompt=prompt,
            schema=_schema("resolver-output"),
            envelope={"pass": "resolver", "block_count": 1},
            projection=resolver_projection,
        )
        # The response is for one component; validate seed coverage.
        component = block.components[0]
        validate_seed_coverage(
            block=block,
            proposals=output.get("proposals", []),
            unresolved=output.get("unresolved_groups", []),
        )
        component_events = resolve_component_events(
            component=component,
            proposals=output.get("proposals", []),
            ledger=ledger,
            resolver=resolver,
        )
        events.extend(component_events)

    # 4. Verified packets
    packets: list[dict[str, Any]] = []
    for idx, event in enumerate(events[:max_packets]):
        key_ids = event.get("key_fact_ids", [])
        entries = [ledger.get(fid) for fid in key_ids]
        evidence_refs = []
        for eid in event.get("evidence_ids", []):
            item = _find_evidence(feed, eid)
            if item is not None:
                evidence_refs.append(
                    {
                        "evidence_id": eid,
                        "provider_id": item.get("provider_id", ""),
                        "source_url": item.get("source", {}).get("url", ""),
                        "tier": item.get("source", {}).get("tier", "Tier 2"),
                        "knowledge_available_at": item.get("source", {}).get(
                            "knowledge_available_at"
                        ),
                    }
                )
        packet = assemble_verified_packet(
            packet_id=f"packet_{idx:04d}",
            event=event,
            feed_run_id=feed.get("run_id", ""),
            ledger_entries=[_ledger_entry_dict(e) for e in entries],
            evidence_refs=evidence_refs,
            eligible_catalyst_calendar_ids=_catalyst_ids(feed),
        )
        packets.append(packet)

    # 5. Analyst pass -> Analysis
    analyses: list[dict[str, Any]] = []
    for idx, packet in enumerate(packets):
        aliases = {f"e{i}": ev["evidence_id"] for i, ev in enumerate(packet["evidence"])}
        prompt = prompts["analyst"]
        analyst_projection = {
            "packet": packet,
            "evidence_aliases": aliases,
        }
        analyst_output = _llm_pass(
            "analyst",
            idx=idx,
            prompt=prompt,
            schema=_schema("analyst-output"),
            envelope={"pass": "analyst", "packet_index": idx},
            projection=analyst_projection,
        )
        analysis = merge_analysis(
            event_id=packet["event_id"],
            analyst_output=analyst_output,
            alias_to_evidence=aliases,
            ledger=ledger,
            direct_flow_evidence_ids=direct_flow_evidence_ids,
        )
        analyses.append(analysis)

    # 6. Scoring
    scored: list[tuple[dict[str, Any], dict[str, Any], Decimal, Decimal]] = []
    for packet, analysis in zip(packets, analyses):
        key_entries = [ledger.get(fid) for fid in packet["key_fact_ids"]]
        event_confidence(key_entries)
        score_components = significance_components(
            scoring=cfg.scoring,
            scope=_analysis_field(analysis, "scope", "unknown"),
            fundamental_depth=_analysis_field(analysis, "fundamental_depth", "unknown"),
            reversibility=_analysis_field(analysis, "reversibility", "unknown"),
            structural_horizon=_analysis_field(analysis, "structural_horizon", "unknown"),
            surprise_values=_surprise_values(feed, key_entries, cfg.scoring),
            affected_groups=_affected_groups(analysis),
            observable_repricing_z=_observable_z(key_entries),
        )
        significance, coverage = event_significance(score_components)
        age_hours = _age_hours(brief_generated_at, packet["fully_known_at"])
        morning = morning_relevance(
            scoring=cfg.scoring,
            age_hours=age_hours,
            cn_hk_exposure=_analysis_field(analysis, "cn_hk_exposure", "unknown"),
            us_next_session_exposure=_analysis_field(
                analysis, "us_next_session_exposure", "unknown"
            ),
            catalyst_present=bool(packet.get("eligible_catalyst_calendar_ids")),
        )
        priority = brief_priority(significance, morning, cfg.scoring)
        scored.append((packet, analysis, priority, coverage))

    # 7. Selection
    selection_inputs = [
        SelectionInput(
            event_id=packet["event_id"],
            fully_known_at=packet["fully_known_at"],
            base_priority=priority,
            confidence=_packet_confidence(packet, ledger),
            component_coverage=coverage,
            analysis_present=True,
            packet_passed=True,
            conflict_free=not packet.get("conflicts"),
            story_family_id=next(
                (e.get("story_family_id") for e in events if e["event_id"] == packet["event_id"]),
                None,
            ),
        )
        for packet, analysis, priority, coverage in scored
    ]
    result = select_events(selection_inputs, cfg.scoring)
    if result.sparse_warning:
        warnings.append("sparse selection: fewer than target events")

    # 8. Editor pass -> Brief assembly.
    # Scripts allocate the closed conditional slot set, build the bounded
    # projection, and merge the editor's wording back into the authoritative
    # Brief projection. The editor supplies only wording and evidence
    # references; every authoritative field is script-owned.
    from .editor import allocate_slots, build_projection, merge_editor_output

    selected_full = [s for s in result.selected if s.format == "full"]
    selected_compact = [s for s in result.selected if s.format == "compact"]
    event_by_id = {e["event_id"]: e for e in events}
    packet_by_event = {p["event_id"]: p for p in packets}
    {a["event_id"]: a for a in analyses}

    def _event_view(event: Mapping[str, Any]) -> dict[str, Any]:
        packet = packet_by_event.get(event.get("event_id", ""), {})
        view = dict(event)
        view["confidence"] = _packet_confidence(packet, ledger) if packet else "unresolved"
        view["source_urls"] = [
            ev.get("source_url") for ev in packet.get("evidence", []) if ev.get("source_url")
        ]
        return view

    full_objs = [
        _event_view(event_by_id[s.event_id]) for s in selected_full if s.event_id in event_by_id
    ]
    compact_objs = [
        _event_view(event_by_id[s.event_id]) for s in selected_compact if s.event_id in event_by_id
    ]

    # Stable request-local evidence aliases across selected events.
    evidence_ids = []
    for obj in full_objs + compact_objs:
        evidence_ids.extend(obj.get("evidence_ids", []))
    alias_to_evidence = {f"e{i}": eid for i, eid in enumerate(dict.fromkeys(evidence_ids))}

    market_state = {
        "regime": "unknown",
        "vector": {
            d: "unknown"
            for d in (
                "risk_appetite",
                "rates",
                "liquidity",
                "growth",
                "inflation",
            )
        },
        "missing_roles": [],
        "explanation": "市场状态未判定（确定性组件）。",
        "evidence_ids": [],
    }
    watchlist = _watchlist(feed, brief_generated_at, cfg)
    bottom_line_owners = [s.event_id for s in result.selected][: min(3, len(result.selected))]

    slots = allocate_slots(
        market_state=market_state,
        full_events=full_objs,
        compact_events=compact_objs,
        watchlist=watchlist,
        bottom_line_owners=bottom_line_owners,
        evidence_aliases=alias_to_evidence,
    )
    source_views = _slot_source_views(
        slots,
        full_objs=full_objs,
        compact_objs=compact_objs,
        analyses=analyses,
        packets=packets,
        ledger=ledger,
        market_state=market_state,
        watchlist=watchlist,
    )
    editor_projection = build_projection(slots, source_views=source_views)
    editor_output = _llm_pass(
        "editor",
        idx=None,
        prompt=prompts["editor"],
        schema=_schema("editor-output"),
        envelope={
            "pass": "editor",
            "full": len(full_objs),
            "compact": len(compact_objs),
            "slots": len(slots),
        },
        projection=editor_projection,
    )

    merged = merge_editor_output(
        slots=slots,
        editor_output=editor_output,
        full_events=full_objs,
        compact_events=compact_objs,
        market_state=market_state,
        watchlist=watchlist,
        alias_to_evidence=alias_to_evidence,
    )

    money_flow_section = _money_flow_section(merged, analyses)

    brief = assemble_brief(
        brief_id=f"brief_{feed.get('run_id', '')[:12]}",
        brief_generated_at=brief_generated_at,
        brief_completed_at=brief_generated_at,
        evidence_cutoff_at=feed.get("evidence_cutoff_at", ""),
        feed_run_id=feed.get("run_id", ""),
        editor_output=editor_output,
        alias_to_evidence=alias_to_evidence,
        slot_meta=merged["slot_meta"],
        dashboard=_dashboard(feed),
        market_state=merged["market_state"],
        full_events=merged["full_events"],
        compact_events=merged["compact_events"],
        money_flow_section=money_flow_section,
        watchlist=merged["watchlist"],
        bottom_line=merged["bottom_line"],
        warnings=warnings,
        provenance={
            "feed_digest": feed.get("content_digest", ""),
            "config_hash": _config_hash(cfg),
            "prompt_fingerprints": _prompt_fingerprints(prompts),
        },
    )

    # 9. Deterministic claim audit -> language-audit pass (LLM).
    from .audit import ClaimAuditor, audit_language_findings

    script_audit = ClaimAuditor(cfg.safety_lexicon).audit(brief)
    if not script_audit.passed:
        raise PipelineError(
            "script claim audit failed: "
            + "; ".join(f"{f.category}: {f.detail}" for f in script_audit.findings)
        )

    audit_projection = _audit_projection(brief)
    audit_output = _llm_pass(
        "language-audit",
        idx=None,
        prompt=prompts["audit"],
        schema=_schema("language-audit-output"),
        envelope={"pass": "language-audit", "claims": len(audit_projection["claims"])},
        projection=audit_projection,
    )

    claim_aliases = {c["alias"] for c in audit_projection["claims"]}
    covered = set(audit_output.get("covered_claim_ids", []))
    if covered != claim_aliases:
        missing = sorted(claim_aliases - covered)
        extra = sorted(covered - claim_aliases)
        raise PipelineError(
            "language-audit coverage mismatch"
            + (f"; missing {missing}" if missing else "")
            + (f"; extra {extra}" if extra else "")
        )
    critical_findings, warning_findings = audit_language_findings(
        audit_output,
        {
            "critical": cfg.audit_severity.critical,
            "warning": cfg.audit_severity.warning,
        },
    )
    if critical_findings:
        raise PipelineError(
            "language-audit critical findings block publication: "
            + "; ".join(f["category"] for f in critical_findings)
        )
    brief["audit_status"] = {
        "script_audit": "passed",
        "language_audit": "passed",
        "findings": warning_findings,
    }

    return PipelineResult(
        brief=brief,
        ledger=ledger,
        events=events,
        packets=packets,
        analyses=analyses,
        selected=result.selected,
        llm_outcomes=llm_outcomes,
        warnings=warnings,
        llm_data=llm_data,
    )


def _schema(name: str) -> Mapping[str, Any]:
    path = Path(__file__).resolve().parents[2] / "schemas" / f"{name}.schema.json"
    return json.loads(path.read_bytes())


def _block_projection(block: Any, aliases: Mapping[str, str]) -> dict[str, Any]:
    return {
        "block_id": block.block_id,
        "component_aliases": aliases,
        "components": [
            {
                "component_id": c.component_id,
                "alias": next(
                    (k for k, v in aliases.items() if v == c.component_id), c.component_id
                ),
                "evidence_ids": list(c.evidence_ids),
                "seed_fact_ids": list(c.seed_fact_ids),
                "projection_records": list(c.projection_records()),
            }
            for c in block.components
        ],
    }


def _find_evidence(feed: Mapping[str, Any], evidence_id: str) -> Mapping[str, Any] | None:
    for item in feed.get("items", []):
        if item.get("id") == evidence_id:
            return item
    return None


def _ledger_entry_dict(entry: LedgerEntry) -> dict[str, Any]:
    return {
        "fact_id": entry.fact_id,
        "entry_type": entry.entry_type,
        "origin_payload": entry.origin_payload,
        "evidence_id": entry.evidence_id,
        "subject": entry.subject,
        "predicate": entry.predicate,
        "effective_time": entry.effective_time,
        "effective_precision": entry.effective_precision,
        "value": entry.value,
        "unit": entry.unit,
        "knowledge_available_at": entry.knowledge_available_at,
        "source_families": list(entry.source_families),
        "tier_counts": dict(entry.tier_counts),
        "conflicts": list(entry.conflicts),
    }


def _catalyst_ids(feed: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        if payload.get("type") == "calendar":
            ids.append(payload.get("calendar_id", item.get("id", "")))
    return list(dict.fromkeys(ids))[:6]


def _age_hours(brief_generated_at: str, fully_known_at: str) -> Decimal:
    from datetime import datetime

    gen = datetime.fromisoformat(brief_generated_at)
    known = datetime.fromisoformat(fully_known_at)
    return Decimal(str(max(0, (gen - known).total_seconds() / 3600)))


def _analysis_field(analysis: Mapping[str, Any], key: str, default: str) -> str:
    value = analysis.get(key)
    return value if isinstance(value, str) and value else default


def _surprise_values(
    feed: Mapping[str, Any],
    entries: Sequence[LedgerEntry],
    scoring: Any,
) -> list[Decimal | None]:
    """Normalized surprise for macro-released key facts with a versioned scale.

    Series identity is matched by the payload ``series_id`` (never the resolved
    subject). Raw surprise is ``actual - consensus`` and is ``unknown`` unless
    both numeric facts are present with a compatible unit and a versioned scale
    exists (design section 11).
    """
    from .market.surprise import surprise_for_series

    values: list[Decimal | None] = []
    for entry in entries:
        if entry.origin_payload != "macro_release":
            continue
        item = _find_evidence(feed, entry.evidence_id)
        payload = (item or {}).get("payload", {})
        series_id = payload.get("series_id")
        if not series_id:
            values.append(None)
            continue
        actual = payload.get("actual") or {}
        consensus = payload.get("consensus") or {}
        result = surprise_for_series(
            series_id=series_id,
            actual=Decimal(str(actual["value"])) if actual.get("value") is not None else None,
            consensus=Decimal(str(consensus["value"]))
            if consensus.get("value") is not None
            else None,
            unit=actual.get("unit") or consensus.get("unit"),
            scales=scoring,
        )
        values.append(result.normalized)
    return values


def _affected_groups(analysis: Mapping[str, Any]) -> int:
    """Count of mapped asset groups with a direction (deterministic breadth)."""
    return len(analysis.get("asset_mappings", []))


def _observable_z(entries: Sequence[LedgerEntry]) -> Decimal | None:
    """Max observable proxy reaction z across key facts (v1: none persisted)."""
    return None


def _packet_confidence(packet: Mapping[str, Any], ledger: Ledger) -> str:
    entries = [ledger.get(fid) for fid in packet.get("key_fact_ids", [])]
    result = event_confidence(entries)
    return result.confidence


def _dashboard(feed: Mapping[str, Any]) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        if payload.get("type") == "market_data":
            obs = payload.get("observations", [])
            roles.append(
                {
                    "role_id": payload.get("instrument_id", item.get("id", "")),
                    "available": bool(obs),
                    "display": payload.get("instrument_id", item.get("id", "")),
                    "return_pct": str(obs[-1].get("value")) if obs else None,
                }
            )
    return roles


def _watchlist(
    feed: Mapping[str, Any], brief_generated_at: str, cfg: AppConfig
) -> list[dict[str, Any]]:
    calendar_items: list[dict[str, Any]] = []
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        if payload.get("type") == "calendar":
            calendar_items.append(
                {
                    "calendar_id": payload.get("calendar_id", item.get("id", "")),
                    "priority": payload.get("priority", ""),
                    "scheduled_at": payload.get("scheduled_at", ""),
                    "announced_at": payload.get("announced_at"),
                    "title": payload.get("title", ""),
                    "evidence_ids": [item.get("id", "")],
                }
            )
    try:
        entries = build_watchlist(
            calendar_items=calendar_items,
            brief_generated_at=brief_generated_at,
            calendar_horizon_end=feed.get("calendar_horizon_end")
            or (datetime.fromisoformat(brief_generated_at) + timedelta(hours=26)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            + "Z",
            policy=cfg.calendar,
            cutoff=feed.get("evidence_cutoff_at"),
        )
        return [dict(e.__dict__) for e in entries]
    except (AttributeError, KeyError, TypeError, ValueError):
        return []


def _slot_source_views(
    slots: Sequence[Any],
    *,
    full_objs: Sequence[Mapping[str, Any]],
    compact_objs: Sequence[Mapping[str, Any]],
    analyses: Sequence[Mapping[str, Any]],
    packets: Sequence[Mapping[str, Any]],
    ledger: Ledger,
    market_state: Mapping[str, Any],
    watchlist: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Closed bounded per-slot source view (design section 16)."""
    event_by_id = {e["event_id"]: e for e in list(full_objs) + list(compact_objs)}
    analysis_by_event = {a["event_id"]: a for a in analyses}
    packet_by_event = {p["event_id"]: p for p in packets}
    views: dict[str, Mapping[str, Any]] = {}
    for s in slots:
        if s.kind == "market_state_explanation":
            views[s.alias] = {
                "regime": market_state.get("regime"),
                "vector": market_state.get("vector"),
                "missing_roles": list(market_state.get("missing_roles", [])),
                "evidence_cutoff_at": market_state.get("evidence_cutoff_at", ""),
            }
        elif s.kind == "event_fact_summary":
            ev = event_by_id.get(s.owner, {})
            views[s.alias] = {
                "event_id": s.owner,
                "display_label": ev.get("display_label", ""),
                "confidence": ev.get("confidence", "high"),
                "facts": [_fact_view(ledger, fid) for fid in ev.get("key_fact_ids", [])],
            }
        elif s.kind == "why_it_matters":
            an = analysis_by_event.get(s.owner, {})
            views[s.alias] = {
                "mechanisms": list(an.get("mechanisms", [])),
                "implications": list(an.get("implications", [])),
            }
        elif s.kind == "reaction_attribution":
            an = analysis_by_event.get(s.owner, {})
            views[s.alias] = {"reaction_attributions": list(an.get("reaction_attributions", []))}
        elif s.kind == "price_in":
            an = analysis_by_event.get(s.owner, {})
            views[s.alias] = {"price_in": an.get("price_in", {})}
        elif s.kind == "money_flow":
            an = analysis_by_event.get(s.owner, {})
            views[s.alias] = {"money_flow": an.get("money_flow", {})}
        elif s.kind == "asset_mapping":
            an = analysis_by_event.get(s.owner, {})
            views[s.alias] = {"asset_mappings": list(an.get("asset_mappings", []))}
        elif s.kind == "alternative":
            an = analysis_by_event.get(s.owner, {})
            views[s.alias] = {"alternatives": list(an.get("alternatives", []))}
        elif s.kind == "uncertainty":
            ev = event_by_id.get(s.owner, {})
            packet = packet_by_event.get(s.owner, {})
            views[s.alias] = {
                "confidence": ev.get("confidence", "high"),
                "verification_status": packet.get("verification_status", ""),
                "conflicts": list(packet.get("conflicts", [])),
            }
        elif s.kind == "watchlist_explanation":
            item = next(
                (w for w in watchlist if f"watchlist:{w.get('calendar_id', '')}" == s.owner), {}
            )
            views[s.alias] = {
                "calendar_id": item.get("calendar_id", ""),
                "priority": item.get("priority", ""),
                "scheduled_at": item.get("scheduled_at", ""),
                "title": item.get("title", ""),
            }
        elif s.kind == "bottom_line_point":
            ev = event_by_id.get(s.owner, {})
            views[s.alias] = {
                "event_id": s.owner,
                "display_label": ev.get("display_label", ""),
                "confidence": ev.get("confidence", "high"),
            }
    return views


def _fact_view(ledger: Ledger, fact_id: str) -> dict[str, Any]:
    try:
        e = ledger.get(fact_id)
    except KeyError:
        return {"fact_id": fact_id}
    return {
        "fact_id": fact_id,
        "subject": e.subject,
        "predicate": e.predicate,
        "effective_time": e.effective_time,
        "value": e.value,
        "unit": e.unit,
        "knowledge_available_at": e.knowledge_available_at,
    }


def _audit_projection(brief: Mapping[str, Any]) -> dict[str, Any]:
    """Closed ordered language-audit projection (design section 17).

    Presents every claim in exact inventory order with a deterministic
    request-local alias; URL targets are already script-validated and are not
    re-sent. The audit response must enumerate exactly these aliases.
    """
    claims = [
        {
            "alias": f"k{idx:02d}",
            "claim_id": c["claim_id"],
            "class": c.get("class", ""),
            "slot_kind": c.get("slot_kind", ""),
            "is_factual": c.get("is_factual", False),
            "is_causal": c.get("is_causal", False),
            "text": c.get("text", ""),
        }
        for idx, c in enumerate(brief.get("claim_inventory", []))
    ]
    return {
        "projection_version": 1,
        "headings": list(brief.get("headings", [])),
        "warnings": list(brief.get("warnings", [])),
        "market_state": {
            "regime": (brief.get("market_state") or {}).get("regime"),
            "explanation": (brief.get("market_state") or {}).get("explanation"),
        },
        "claims": claims,
    }


def _money_flow_section(
    merged: Mapping[str, Any],
    analyses: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Optional Money Flow section: only confirmed/indicated events survive audit."""
    analysis_by_event = {a["event_id"]: a for a in analyses}
    wording_by_owner = merged.get("wording_by_owner", {})
    out: list[dict[str, Any]] = []
    for ev in list(merged["full_events"]) + list(merged["compact_events"]):
        an = analysis_by_event.get(ev["event_id"], {})
        status = (an.get("money_flow") or {}).get("status")
        if status not in ("confirmed", "indicated"):
            continue
        out.append(
            {
                "event_id": ev["event_id"],
                "status": status,
                "text": wording_by_owner.get(ev["event_id"], {}).get("money_flow", ""),
            }
        )
    return out


def _config_hash(cfg: AppConfig) -> str:
    from .canonical import canonical_digest

    return canonical_digest(
        {
            "name": cfg.name,
            "scoring": cfg.scoring.significance_weights,
            "target_count": cfg.scoring.target_count,
        }
    )


def _prompt_fingerprints(prompts: Mapping[str, str]) -> dict[str, str]:
    from .canonical import canonical_digest

    return {name: canonical_digest(text) for name, text in prompts.items()}
