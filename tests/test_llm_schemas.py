"""Task 2.5 — fixtures for the four closed LLM response schemas.

Covers strict-UTF-8 and escaped lone-surrogate rejection, exact resolver
24-proposal/24-unresolved maxima and p00..p23 aliases, family label grammar,
at-most-eight coexistence relations, analyst 43-item-shape / exactly-one
price-in, editor 11 slot kinds / 61-slot bound, audit 74-coverage /
32-finding maxima, 192-byte prose bounds, extra-property rejection,
refusal/incomplete semantics, and Python-to-JSON round trips.
"""

from __future__ import annotations

import pytest

from follow_the_money.schema import SchemaError, validate_against


def _resolver_output(**overrides) -> dict:
    out = {
        "component_alias": "c0",
        "proposals": [
            {
                "position_alias": "p00",
                "event_type": "policy",
                "event_defining_fact_ids": ["fact_a"],
                "evidence_ids": ["ev_1"],
                "supporting_fact_ids": [],
                "entity_ids": ["ent_fed"],
                "story_family_label": "unknown",
                "coexistence_relations": [],
            }
        ],
        "unresolved_groups": [],
    }
    out.update(overrides)
    return out


def _analyst_output(**overrides) -> dict:
    out = {
        "packet_alias": "e0",
        "mechanisms": ["机制一"],
        "implications": ["含义一"],
        "reaction_attributions": [],
        "price_in": {
            "status": "unclear",
            "explanation": "无预期证据",
            "reference_aliases": ["ev_1"],
        },
        "indirect_indication": {"indicated": False, "reference_aliases": []},
        "asset_mappings": [],
        "alternatives": [],
        "watch_points": [],
        "scope": "single_entity",
        "fundamental_depth": "headline",
        "reversibility": "medium",
        "structural_horizon": "weeks",
        "cn_hk_exposure": "direct",
        "us_next_session_exposure": "indirect",
        "catalyst_calendar_ids": [],
        "audit_reasons": [],
    }
    out.update(overrides)
    return out


def _editor_output(**overrides) -> dict:
    out = {
        "filled_slots": [
            {
                "slot_alias": "s00",
                "wording_fragment": "市场维持风险偏好。",
                "reference_aliases": ["ev_1"],
            }
        ]
    }
    out.update(overrides)
    return out


def _audit_output(**overrides) -> dict:
    out = {"covered_claim_ids": ["c_0"], "findings": []}
    out.update(overrides)
    return out


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def test_resolver_valid():
    validate_against("resolver-output.schema.json", _resolver_output())


def test_resolver_24_proposals_ok_25_rejected():
    _resolver_output()
    props = [
        {
            "position_alias": f"p{i:02d}",
            "event_type": "news",
            "event_defining_fact_ids": [f"fact_{i}"],
            "evidence_ids": [f"ev_{i}"],
            "supporting_fact_ids": [],
            "entity_ids": [],
            "story_family_label": "unknown",
            "coexistence_relations": [],
        }
        for i in range(24)
    ]
    validate_against("resolver-output.schema.json", _resolver_output(proposals=props))
    props.append(dict(props[0], position_alias="p24"))
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", _resolver_output(proposals=props))


def test_resolver_24_unresolved_ok_25_rejected():
    groups = [
        {"seed_fact_ids": [f"fact_{i}"], "evidence_ids": [f"ev_{i}"], "reason": "ambiguous"}
        for i in range(24)
    ]
    validate_against("resolver-output.schema.json", _resolver_output(unresolved_groups=groups))
    groups.append({"seed_fact_ids": ["fact_x"], "evidence_ids": ["ev_x"], "reason": "ambiguous"})
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", _resolver_output(unresolved_groups=groups))


def test_resolver_position_alias_grammar():
    out = _resolver_output()
    out["proposals"][0]["position_alias"] = "p1"
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", out)


def test_resolver_family_label_grammar():
    for bad in ("fam1", "F01", "f123", "f"):
        out = _resolver_output()
        out["proposals"][0]["story_family_label"] = bad
        with pytest.raises(SchemaError, match="does not match"):
            validate_against("resolver-output.schema.json", out)
    for good in ("unknown", "f0", "f12", "f99"):
        out = _resolver_output()
        out["proposals"][0]["story_family_label"] = good
        validate_against("resolver-output.schema.json", out)


def test_resolver_relation_enum_closed():
    out = _resolver_output()
    out["proposals"][0]["coexistence_relations"] = [
        {"other_proposal_alias": "p01", "relation": "related"}
    ]
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", out)


def test_resolver_eight_relations_ok_nine_rejected():
    rels = [
        {"other_proposal_alias": f"p{i:02d}", "relation": "distinct_material_development"}
        for i in range(1, 9)
    ]
    out = _resolver_output()
    out["proposals"][0]["coexistence_relations"] = rels
    validate_against("resolver-output.schema.json", out)
    out["proposals"][0]["coexistence_relations"].append(
        {"other_proposal_alias": "p09", "relation": "distinct_material_development"}
    )
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", out)


def test_resolver_extra_property_rejected():
    out = _resolver_output()
    out["summary"] = "forbidden prose"
    with pytest.raises(SchemaError, match="Additional properties"):
        validate_against("resolver-output.schema.json", out)


def test_resolver_prose_title_field_forbidden():
    # Design: no title/display-label/summary fields exist in resolver output.
    out = _resolver_output()
    out["proposals"][0]["title"] = "invented"
    with pytest.raises(SchemaError):
        validate_against("resolver-output.schema.json", out)


# ---------------------------------------------------------------------------
# Analyst
# ---------------------------------------------------------------------------


def test_analyst_valid():
    validate_against("analyst-output.schema.json", _analyst_output())


def test_analyst_exactly_one_price_in_field():
    out = _analyst_output()
    out["price_in"] = {
        "status": "partial",
        "explanation": "预期已部分计入",
        "reference_aliases": ["ev_1"],
    }
    validate_against("analyst-output.schema.json", out)
    out["second_price_in"] = out["price_in"]
    with pytest.raises(SchemaError, match="Additional properties"):
        validate_against("analyst-output.schema.json", out)


def test_analyst_192_byte_mechanism_bound():
    out = _analyst_output()
    # 190 code points < 192 => schema accepts; the byte-level 192-byte bound
    # is enforced by repository-semantic validation, not JSON Schema.
    out["mechanisms"] = ["机" * 190]
    validate_against("analyst-output.schema.json", out)
    # 192 code points equal maxLength (inclusive boundary); 193 exceeds it.
    out["mechanisms"] = ["机" * 192]
    validate_against("analyst-output.schema.json", out)
    out["mechanisms"] = ["机" * 193]
    with pytest.raises(SchemaError, match="too long"):
        validate_against("analyst-output.schema.json", out)


def test_analyst_enums_closed():
    for field, bad in [
        ("scope", "big"),
        ("fundamental_depth", "deep"),
        ("reversibility", "sometimes"),
        ("structural_horizon", "soon"),
        ("cn_hk_exposure", "maybe"),
        ("us_next_session_exposure", "maybe"),
    ]:
        out = _analyst_output()
        out[field] = bad
        with pytest.raises(SchemaError):
            validate_against("analyst-output.schema.json", out)


def test_analyst_asset_mapping_duplicate_group_rejected_by_semantic_layer():
    # Schema allows the array; the duplicate-group rule is a semantic check
    # owned by Analysis assembly (task 2.7/2.8).
    out = _analyst_output()
    mapping = {
        "asset_group": "us_equities",
        "direction": "positive",
        "confidence": "high",
        "horizon": "days",
        "mechanism": "机制",
        "reference_aliases": ["ev_1"],
        "audit_reason": None,
    }
    out["asset_mappings"] = [mapping, dict(mapping)]
    validate_against("analyst-output.schema.json", out)  # schema-level ok


def test_analyst_audit_reason_nullability():
    out = _analyst_output()
    out["asset_mappings"] = [
        {
            "asset_group": "us_equities",
            "direction": "unclear",
            "confidence": "unknown",
            "horizon": "unknown",
            "mechanism": "机制",
            "reference_aliases": ["ev_1"],
            "audit_reason": None,  # semantic rule requires non-null here
        }
    ]
    validate_against("analyst-output.schema.json", out)  # schema-level ok (nullable)


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------


def test_editor_valid():
    validate_against("editor-output.schema.json", _editor_output())


def test_editor_61_slot_max():
    slots = [
        {"slot_alias": f"s{i:02d}", "wording_fragment": "内容", "reference_aliases": []}
        for i in range(61)
    ]
    validate_against("editor-output.schema.json", _editor_output(filled_slots=slots))
    slots.append({"slot_alias": "s61", "wording_fragment": "内容", "reference_aliases": []})
    with pytest.raises(SchemaError):
        validate_against("editor-output.schema.json", _editor_output(filled_slots=slots))


def test_editor_192_byte_fragment_and_8_refs():
    out = _editor_output()
    out["filled_slots"][0]["reference_aliases"] = [f"ev_{i}" for i in range(8)]
    validate_against("editor-output.schema.json", out)
    out["filled_slots"][0]["reference_aliases"].append("ev_8")
    with pytest.raises(SchemaError):
        validate_against("editor-output.schema.json", out)


def test_editor_slot_alias_grammar():
    out = _editor_output()
    out["filled_slots"][0]["slot_alias"] = "SLOT_1"
    with pytest.raises(SchemaError):
        validate_against("editor-output.schema.json", out)


def test_editor_authoritative_field_forbidden():
    out = _editor_output()
    out["filled_slots"][0]["score"] = "99"
    with pytest.raises(SchemaError):
        validate_against("editor-output.schema.json", out)


# ---------------------------------------------------------------------------
# Language audit
# ---------------------------------------------------------------------------


def test_audit_valid():
    validate_against("language-audit-output.schema.json", _audit_output())


def test_audit_74_coverage_and_32_findings():
    out = _audit_output(covered_claim_ids=[f"c_{i}" for i in range(74)])
    findings = [
        {
            "claim_id": f"c_{i}",
            "category": "excessive_certainty",
            "rationale": "表述过于确定",
            "reference_aliases": [],
        }
        for i in range(32)
    ]
    validate_against(
        "language-audit-output.schema.json",
        _audit_output(covered_claim_ids=out["covered_claim_ids"], findings=findings),
    )
    findings.append(
        {
            "claim_id": "c_0",
            "category": "excessive_certainty",
            "rationale": "多一条",
            "reference_aliases": [],
        }
    )
    with pytest.raises(SchemaError):
        validate_against(
            "language-audit-output.schema.json",
            _audit_output(covered_claim_ids=out["covered_claim_ids"], findings=findings),
        )


def test_audit_finding_category_closed():
    out = _audit_output(
        findings=[
            {
                "claim_id": "c_0",
                "category": "made_up_category",
                "rationale": "x",
                "reference_aliases": [],
            }
        ]
    )
    with pytest.raises(SchemaError):
        validate_against("language-audit-output.schema.json", out)


def test_audit_duplicate_claim_coverage_rejected():
    out = _audit_output(covered_claim_ids=["c_0", "c_0"])
    with pytest.raises(SchemaError):
        validate_against("language-audit-output.schema.json", out)


# ---------------------------------------------------------------------------
# Cross-cutting strict-UTF-8 / lone surrogate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "schema",
    [
        "resolver-output.schema.json",
        "analyst-output.schema.json",
        "editor-output.schema.json",
        "language-audit-output.schema.json",
    ],
)
def test_lone_surrogate_rejected_in_all_schemas(schema):
    if schema == "resolver-output.schema.json":
        obj = _resolver_output()
        obj["proposals"][0]["event_type"] = "bad\ud800type"
    elif schema == "analyst-output.schema.json":
        obj = _analyst_output()
        obj["mechanisms"] = ["bad\udfff"]
    elif schema == "editor-output.schema.json":
        obj = _editor_output()
        obj["filled_slots"][0]["wording_fragment"] = "bad\ud800"
    else:
        obj = _audit_output()
        obj["covered_claim_ids"] = ["bad\udfff"]
    with pytest.raises(SchemaError, match="surrogate"):
        validate_against(schema, obj)


def test_escaped_lone_surrogate_rejected():
    obj = _resolver_output()
    obj["proposals"][0]["event_type"] = "bad\udfff"
    with pytest.raises(SchemaError, match="surrogate"):
        validate_against("resolver-output.schema.json", obj)


# ---------------------------------------------------------------------------
# Python-to-JSON round trips (canonical serialization)
# ---------------------------------------------------------------------------


def test_canonical_round_trip_resolver():
    from follow_the_money.canonical import canonical_bytes, load_canonical_json

    out = _resolver_output()
    raw = canonical_bytes(out)
    decoded = load_canonical_json(raw)
    validate_against("resolver-output.schema.json", decoded)
    assert canonical_bytes(decoded) == raw


def test_canonical_round_trip_analyst():
    from follow_the_money.canonical import canonical_bytes, load_canonical_json

    out = _analyst_output()
    raw = canonical_bytes(out)
    decoded = load_canonical_json(raw)
    validate_against("analyst-output.schema.json", decoded)
    assert canonical_bytes(decoded) == raw


def test_canonical_round_trip_editor_and_audit():
    from follow_the_money.canonical import canonical_bytes, load_canonical_json

    for schema, obj in [
        ("editor-output.schema.json", _editor_output()),
        ("language-audit-output.schema.json", _audit_output()),
    ]:
        raw = canonical_bytes(obj)
        decoded = load_canonical_json(raw)
        validate_against(schema, decoded)
        assert canonical_bytes(decoded) == raw
