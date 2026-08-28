"""Task 2.3/2.4 — ledger and canonical Event fixtures.

Covers pre-resolver stable fact IDs, seed designation, canonical fact keys,
swapped-subject/value discrimination, staggered knowledge times,
``fully_known_at = max(key_fact knowledge)``, script-owned key_fact_ids,
story-family derivation, display-label templates, and schema validation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from follow_the_money.events import (
    build_event,
    canonical_event_id,
    display_label,
    key_fact_ids_from,
    max_knowledge_time,
    story_family_id,
    unordered_pair,
)
from follow_the_money.ledger import (
    Ledger,
    LedgerEntry,
    build_ledger_entry,
    canonical_fact_key,
)

EVENT_KEYS = {
    "schema_version",
    "event_id",
    "event_type",
    "evidence_ids",
    "key_fact_ids",
    "fully_known_at",
    "story_family_id",
    "coexistence_pair_ids",
    "display_label",
    "economic_effective_time",
    "common_effective_time",
    "multiple_effective_times",
    "key_fact_effective_times",
}

T1 = "2026-08-11T01:00:00Z"
T2 = "2026-08-11T02:30:00Z"
T3 = "2026-08-11T03:00:00Z"


def _fact(
    ledger: Ledger,
    *,
    origin: str = "macro_release",
    subject: str = "ent_fed",
    predicate: str = "policy_rate",
    value: str = "5.0",
    unit: str = "percent",
    effective_time: str = T1,
    precision: str = "instant",
    knowledge: str = T1,
    evidence: str = "ev-1",
    entry_type: str = "FACT",
    families: tuple[str, ...] = ("fam_fed",),
    tiers: dict | None = None,
) -> LedgerEntry:
    return ledger.add(
        build_ledger_entry(
            entry_type=entry_type,
            origin_payload=origin,
            evidence_id=evidence,
            subject=subject,
            predicate=predicate,
            effective_time=effective_time,
            effective_precision=precision,
            value=value,
            unit=unit,
            knowledge_available_at=knowledge,
            source_families=families,
            tier_counts=tiers or {"Tier 1": 1},
        )
    )


# ---------------------------------------------------------------------------
# Stable fact IDs and seed designation
# ---------------------------------------------------------------------------


def test_stable_fact_id_deterministic():
    ledger = Ledger()
    a = _fact(ledger)
    b = _fact(ledger, predicate="rate_hike")  # different fact => different ID
    assert a.fact_id != b.fact_id
    assert a.fact_id.startswith("fact_")
    assert len(a.fact_id) == 37  # "fact_" + 32 hex
    # Same inputs => same ID across fresh ledgers.
    ledger2 = Ledger()
    c = _fact(ledger2)
    assert c.fact_id == a.fact_id


def test_fact_key_binds_subject_value_unit():
    ledger = Ledger()
    a = _fact(ledger, subject="ent_a", value="10", unit="usd")
    b = _fact(ledger, subject="ent_b", value="10", unit="usd")
    assert canonical_fact_key(a) != canonical_fact_key(b)


def test_swapped_values_between_subjects_differ():
    ledger = Ledger()
    a1 = _fact(ledger, subject="ent_a", value="10")
    a2 = _fact(ledger, subject="ent_a", value="20")
    b1 = _fact(ledger, subject="ent_b", value="20")
    b2 = _fact(ledger, subject="ent_b", value="10")
    # a1 (10) vs b2 (10) differ by subject; a2 (20) vs b1 (20) differ by subject.
    assert canonical_fact_key(a1) != canonical_fact_key(b2)
    assert canonical_fact_key(a2) != canonical_fact_key(b1)


def test_seed_designation_exact_origins():
    ledger = Ledger()
    seeds = []
    for origin in ("news", "macro_release", "policy", "filing", "flow", "positioning"):
        seeds.append(_fact(ledger, origin=origin))
    # market_data/calendar/OBSERVATION/INFERENCE are never seeds.
    _fact(ledger, origin="market_data", predicate="close")
    _fact(ledger, origin="calendar", predicate="scheduled")
    _fact(ledger, origin="news", predicate="observed", entry_type="OBSERVATION")
    _fact(ledger, origin="news", predicate="inferred", entry_type="INFERENCE", families=())
    seed_ids = set(ledger.seed_fact_ids())
    for s in seeds:
        assert s.fact_id in seed_ids
    assert len(seed_ids) == 6


# ---------------------------------------------------------------------------
# fully_known_at and key_fact_ids
# ---------------------------------------------------------------------------


def test_fully_known_at_is_max_knowledge():
    ledger = Ledger()
    f1 = _fact(ledger, knowledge=T1)
    f2 = _fact(ledger, predicate="rate_hike", knowledge=T2)
    assert max_knowledge_time([f1, f2]) == T2


def test_key_fact_ids_sorted_unique():
    assert key_fact_ids_from(["b", "a", "a", "c"]) == ("a", "b", "c")


def test_build_event_fully_known_and_key_facts():
    ledger = Ledger()
    f1 = _fact(ledger, knowledge=T1, predicate="policy_rate")
    f2 = _fact(ledger, knowledge=T2, predicate="rate_hike")
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[f2.fact_id, f1.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )
    assert event["fully_known_at"] == T2
    assert event["key_fact_ids"] == sorted([f1.fact_id, f2.fact_id])
    assert event["schema_version"] == 1
    assert set(event) == EVENT_KEYS  # closed structured contract, no free text


def test_event_id_discriminates_fact_time_and_value():
    ledger = Ledger()
    a = _fact(ledger, value="5.0", effective_time=T1, predicate="rate")
    b = _fact(ledger, value="5.5", effective_time=T1, predicate="rate")
    id_a = canonical_event_id(
        evidence_ids=["ev-1"],
        event_type="policy",
        entity_ids=["ent_fed"],
        defining_fact_keys=[canonical_fact_key(a)],
    )
    id_b = canonical_event_id(
        evidence_ids=["ev-1"],
        event_type="policy",
        entity_ids=["ent_fed"],
        defining_fact_keys=[canonical_fact_key(b)],
    )
    assert id_a != id_b


def test_event_id_stable_under_input_order():
    ledger = Ledger()
    f1 = _fact(ledger, predicate="p1")
    f2 = _fact(ledger, predicate="p2")
    id1 = canonical_event_id(
        evidence_ids=["ev-1", "ev-2"],
        event_type="news",
        entity_ids=["ent_a"],
        defining_fact_keys=[canonical_fact_key(f2), canonical_fact_key(f1)],
    )
    id2 = canonical_event_id(
        evidence_ids=["ev-2", "ev-1"],
        event_type="news",
        entity_ids=["ent_a"],
        defining_fact_keys=[canonical_fact_key(f1), canonical_fact_key(f2)],
    )
    assert id1 == id2


def test_multi_fact_distinct_effective_times():
    ledger = Ledger()
    f1 = _fact(ledger, effective_time=T1, precision="instant")
    f2 = _fact(ledger, effective_time=T3, precision="instant", predicate="rate_hike")
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[f1.fact_id, f2.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )
    assert event["multiple_effective_times"] is True
    assert event["common_effective_time"] is None
    assert event["economic_effective_time"]["value"] == T1


def test_first_canonical_effective_time_value_can_be_null():
    ledger = Ledger()
    null_fact = _fact(ledger, predicate="z_null", effective_time=None, precision="date")
    known_fact = _fact(ledger, predicate="a_known", effective_time=T1, precision="date")
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[known_fact.fact_id, null_fact.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )

    assert event["key_fact_ids"][0] == null_fact.fact_id
    assert event["economic_effective_time"] == {"value": None, "precision": "date"}
    assert event["common_effective_time"] is None


def test_all_null_effective_times_use_first_canonical_precision():
    ledger = Ledger()
    first_candidate = _fact(ledger, predicate="first_null", effective_time=None, precision="date")
    second_candidate = _fact(ledger, predicate="second_null", effective_time=None, precision="year")
    first = min((first_candidate, second_candidate), key=lambda fact: fact.fact_id)
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[second_candidate.fact_id, first_candidate.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )

    assert event["key_fact_ids"][0] == first.fact_id
    assert event["economic_effective_time"] == {
        "value": None,
        "precision": first.effective_precision,
    }
    assert event["common_effective_time"] is None


def test_partially_known_effective_times_have_no_common_projection():
    ledger = Ledger()
    null_fact = _fact(ledger, predicate="nullable", effective_time=None, precision="date")
    known_one = _fact(ledger, predicate="known_one", effective_time=T1, precision="date")
    known_two = _fact(ledger, predicate="known_two", effective_time=T1, precision="date")
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[known_two.fact_id, null_fact.fact_id, known_one.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )

    assert event["key_fact_ids"] == sorted(
        [null_fact.fact_id, known_one.fact_id, known_two.fact_id]
    )
    assert event["common_effective_time"] is None


def test_mixed_effective_precision_uses_one_first_canonical_fact():
    ledger = Ledger()
    first_candidate = _fact(
        ledger,
        predicate="annual_rate",
        value="5",
        effective_time="2026",
        precision="year",
    )
    second_candidate = _fact(
        ledger,
        predicate="monthly_rate",
        value="5.0",
        effective_time="2026-08",
        precision="month",
        evidence="ev-2",
    )
    first = min((first_candidate, second_candidate), key=lambda fact: fact.fact_id)
    event = build_event(
        event_type="macro_release",
        evidence_ids=["ev-1", "ev-2"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[first_candidate.fact_id, second_candidate.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )

    assert first.effective_time == "2026-08"
    assert first.effective_precision == "month"
    assert event["economic_effective_time"] == {"value": "2026-08", "precision": "month"}


def test_mixed_effective_precision_is_stable_across_hash_seeds():
    script = """
import json
from follow_the_money.events import build_event
from follow_the_money.ledger import Ledger, build_ledger_entry

ledger = Ledger()
for kwargs in (
    {"predicate": "annual_rate", "value": "5", "effective_time": "2026", "effective_precision": "year", "evidence_id": "ev-1"},
    {"predicate": "monthly_rate", "value": "5.0", "effective_time": "2026-08", "effective_precision": "month", "evidence_id": "ev-2"},
):
    ledger.add(build_ledger_entry(
        entry_type="FACT",
        origin_payload="macro_release",
        subject="ent_fed",
        unit="percent",
        knowledge_available_at="2026-08-11T01:00:00Z",
        **kwargs,
    ))
event = build_event(
    event_type="macro_release",
    evidence_ids=["ev-1", "ev-2"],
    entity_ids=["ent_fed"],
    event_defining_fact_ids=[entry.fact_id for entry in ledger.entries()],
    ledger=ledger,
    subject_zh="美联储",
)
print(json.dumps(event["economic_effective_time"], ensure_ascii=False, sort_keys=True))
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str(Path(__file__).resolve().parents[1] / "src"), env.get("PYTHONPATH", ""))
    )
    outputs = []
    for seed in ("1", "2", "3", "4", "5"):
        process_env = {**env, "PYTHONHASHSEED": seed}
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env=process_env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        outputs.append(json.loads(proc.stdout))

    assert outputs == [{"precision": "month", "value": "2026-08"}] * len(outputs)


def test_single_fact_common_effective_time():
    ledger = Ledger()
    f1 = _fact(ledger, effective_time=T1, precision="instant")
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[f1.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )
    assert event["multiple_effective_times"] is False
    assert event["common_effective_time"] == {"value": T1, "precision": "instant"}


# ---------------------------------------------------------------------------
# Story families
# ---------------------------------------------------------------------------


def test_story_family_id_from_sorted_members():
    a = "evt_aaa"
    b = "evt_bbb"
    assert story_family_id([b, a]) == story_family_id([a, b])
    assert story_family_id([a]) != story_family_id([b])


def test_singleton_family_is_event_specific():
    assert story_family_id(["evt_x"]) == "fam_single_evt_x"


def test_unordered_pair():
    assert unordered_pair("b", "a") == ("a", "b")


def test_event_family_and_pairs_schema():
    ledger = Ledger()
    f1 = _fact(ledger, predicate="p1")
    _fact(ledger, predicate="p2")
    e1 = build_event(
        event_type="news",
        evidence_ids=["ev-1"],
        entity_ids=["ent_a"],
        event_defining_fact_ids=[f1.fact_id],
        ledger=ledger,
        subject_zh="主体甲",
        member_events=["evt_a", "evt_b"],
        coexistence_pairs=[("evt_b", "evt_a")],
    )
    assert set(e1) == EVENT_KEYS
    assert e1["story_family_id"] == story_family_id(["evt_a", "evt_b"])
    assert e1["coexistence_pair_ids"] == [["evt_a", "evt_b"]]


# ---------------------------------------------------------------------------
# Display labels
# ---------------------------------------------------------------------------


def test_display_label_macro_release_template():
    ledger = Ledger()
    f = _fact(ledger, value="3.2", unit="percent")
    label = display_label(event_type="macro_release", subject_zh="美国", key_facts=[f])
    assert label == "美国发布宏观数据：3.2percent"


def test_display_label_filing_template():
    ledger = Ledger()
    f = _fact(ledger, origin="filing", predicate="filed", value="13F", unit="form")
    label = display_label(
        event_type="filing", subject_zh="公司", key_facts=[f], company="Acme", form="13F"
    )
    assert label == "Acme提交13F申报"


def test_display_label_rejects_free_text():
    # Label is derived only from closed structured facts; there is no LLM
    # title field, and unknown free text never enters the template.
    ledger = Ledger()
    f = _fact(ledger, predicate="p", value="1", unit="u")
    label = display_label(event_type="news", subject_zh="主体", key_facts=[f])
    assert "invented" not in label
    assert label == "主体：p"


# ---------------------------------------------------------------------------
# Ledger immutability
# ---------------------------------------------------------------------------


def test_ledger_rejects_duplicate_fact_id():
    ledger = Ledger()
    _fact(ledger)
    with pytest.raises(ValueError, match="duplicate"):
        _fact(ledger)


def test_ledger_unknown_fact_rejected():
    ledger = Ledger()
    with pytest.raises(KeyError, match="unknown fact id"):
        ledger.get("fact_nope")


def test_invalid_entry_type_rejected():
    with pytest.raises(ValueError, match="invalid ledger entry type"):
        build_ledger_entry(
            entry_type="MADEUP",
            origin_payload="news",
            evidence_id="e",
            subject="s",
            predicate="p",
            effective_time=None,
            effective_precision="instant",
            value=None,
            unit=None,
            knowledge_available_at=T1,
        )


def test_event_never_carries_free_text_fields():
    # Events are script-derived from closed structured facts only; no free-text
    # or LLM title field can enter the object.
    ledger = Ledger()
    f = _fact(ledger)
    event = build_event(
        event_type="policy",
        evidence_ids=["ev-1"],
        entity_ids=["ent_fed"],
        event_defining_fact_ids=[f.fact_id],
        ledger=ledger,
        subject_zh="美联储",
    )
    assert set(event) == EVENT_KEYS
    assert all(isinstance(v, (list, dict, str, int, type(None))) for v in event.values())
