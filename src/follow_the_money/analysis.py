"""Analyst-output → authoritative Analysis merge (task 2.8).

Script-owned rules (design sections 7/8/15):

- The analyst may only reference packet/evidence aliases that resolve to the
  verified packet's existing evidence IDs.
- The analyst cannot assign ``confirmed`` money flow; scripts own the final
  money-flow merge from typed ``flow``/``positioning`` evidence.
- Exactly one Event-level price-in assessment; a second is rejected.
- At most one mapping per asset group; duplicate groups reject the result.
- Asset-mapping ``audit_reason`` must be non-null when direction is
  ``unclear`` or confidence/horizon is ``unknown``, and null otherwise.
- Attempted Event/ledger replacement, script-owned score/status injection,
  and trading instructions are rejected.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .ledger import Ledger
from .schema import validate_against

ASSET_GROUPS = {
    "cn_hk_equities",
    "us_equities",
    "us_rates",
    "china_rates",
    "usd_fx",
    "industrial_commodities",
    "energy",
    "precious_metals",
    "crypto",
}
UNCERTAIN_DIRECTIONS = {"unclear"}
UNCERTAIN_ENUMS = {"unknown"}


class AnalysisError(ValueError):
    """Analyst output failed ownership or reference validation."""


def _resolve_aliases(
    aliases: Sequence[str],
    alias_to_evidence: Mapping[str, str],
    where: str,
) -> tuple[str, ...]:
    resolved = []
    for alias in aliases:
        if alias not in alias_to_evidence:
            raise AnalysisError(f"{where}: unknown reference alias {alias!r}")
        resolved.append(alias_to_evidence[alias])
    return tuple(dict.fromkeys(resolved))  # dedupe preserving order


def _validate_audit_reason_nullability(mapping: Mapping[str, Any]) -> None:
    direction = mapping["direction"]
    confidence = mapping["confidence"]
    horizon = mapping["horizon"]
    audit_reason = mapping.get("audit_reason")
    needs_reason = (
        direction in UNCERTAIN_DIRECTIONS
        or confidence in UNCERTAIN_ENUMS
        or horizon in UNCERTAIN_ENUMS
    )
    if needs_reason and audit_reason is None:
        raise AnalysisError(
            f"asset mapping {mapping['asset_group']}: audit_reason required "
            "when direction is unclear or confidence/horizon is unknown"
        )
    if not needs_reason and audit_reason is not None:
        raise AnalysisError(
            f"asset mapping {mapping['asset_group']}: audit_reason must be null "
            "when all values are certain"
        )


def merge_analysis(
    *,
    event_id: str,
    analyst_output: Mapping[str, Any],
    alias_to_evidence: Mapping[str, str],
    ledger: Ledger,
    direct_flow_evidence_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Validate analyst output and merge LLM-owned fields into an Analysis.

    ``alias_to_evidence`` maps request-local aliases to canonical evidence IDs
    from the verified packet. ``direct_flow_evidence_ids`` are typed
    ``flow``/``positioning`` evidence IDs that confer ``confirmed`` status.
    """
    # Ownership: analyst output must not attempt to inject script-owned fields.
    # Checked before schema validation so the error is precise.
    for forbidden in (
        "score",
        "status",
        "final_priority",
        "event_facts",
        "ledger",
        "event_id",
        "money_flow",
    ):
        if forbidden in analyst_output:
            raise AnalysisError(f"analyst output must not supply {forbidden!r}")

    validate_against("analyst-output.schema.json", analyst_output)

    # Exactly one price-in assessment is structurally enforced by the schema;
    # enforce that a second cannot hide under an extra property.
    if not analyst_output.get("price_in"):
        raise AnalysisError("analyst output requires exactly one price_in assessment")

    # Duplicate asset groups reject the result.
    seen_groups: set[str] = set()
    mappings_out = []
    for m in analyst_output.get("asset_mappings", []):
        group = m["asset_group"]
        if group in seen_groups:
            raise AnalysisError(f"duplicate asset group mapping {group!r}")
        seen_groups.add(group)
        _validate_audit_reason_nullability(m)
        mappings_out.append(
            {
                "asset_group": group,
                "direction": m["direction"],
                "confidence": m["confidence"],
                "horizon": m["horizon"],
                "mechanism": m["mechanism"],
                "evidence_ids": list(
                    _resolve_aliases(m["reference_aliases"], alias_to_evidence, "asset_mapping")
                ),
                "audit_reason": m.get("audit_reason"),
            }
        )

    # Reaction attributions.
    attributions_out = []
    for ra in analyst_output.get("reaction_attributions", []):
        attributions_out.append(
            {
                "asset_group": ra["asset_group"],
                "attribution": ra["attribution"],
                "evidence_ids": list(
                    _resolve_aliases(
                        ra["reference_aliases"], alias_to_evidence, "reaction_attribution"
                    )
                ),
            }
        )

    # Price-in.
    price_in = analyst_output["price_in"]
    price_in_out = {
        "status": price_in["status"],
        "explanation": price_in["explanation"],
        "evidence_ids": list(
            _resolve_aliases(price_in["reference_aliases"], alias_to_evidence, "price_in")
        ),
    }

    # Money-flow merge: scripts own the final status.
    direct = tuple(dict.fromkeys(direct_flow_evidence_ids))
    indirect_alias = analyst_output.get("indirect_indication", {})
    indirect_refs = tuple(indirect_alias.get("reference_aliases", []))
    indirect_evidence = _resolve_aliases(indirect_refs, alias_to_evidence, "indirect_indication")
    if direct:
        status = "confirmed"
    elif indirect_alias.get("indicated") and indirect_evidence:
        status = "indicated"
    else:
        status = "no_evidence"

    analysis = {
        "schema_version": 1,
        "analysis_id": f"analysis_{event_id}",
        "event_id": event_id,
        "mechanisms": list(analyst_output.get("mechanisms", [])),
        "implications": list(analyst_output.get("implications", [])),
        "reaction_attributions": attributions_out,
        "price_in": price_in_out,
        "money_flow": {
            "status": status,
            "direct_evidence_ids": list(direct),
            "indirect_reference_aliases": list(indirect_evidence),
        },
        "asset_mappings": mappings_out,
        "alternatives": list(analyst_output.get("alternatives", [])),
        "watch_points": list(analyst_output.get("watch_points", [])),
        "scope": analyst_output["scope"],
        "fundamental_depth": analyst_output["fundamental_depth"],
        "reversibility": analyst_output["reversibility"],
        "structural_horizon": analyst_output["structural_horizon"],
        "cn_hk_exposure": analyst_output["cn_hk_exposure"],
        "us_next_session_exposure": analyst_output["us_next_session_exposure"],
        "catalyst_calendar_ids": list(analyst_output.get("catalyst_calendar_ids", [])),
    }
    validate_against("analysis.schema.json", analysis)
    return analysis
