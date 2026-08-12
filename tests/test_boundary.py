"""Task 2.11/2.12 — verified-event-packet and run-manifest boundary fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from follow_the_money.boundary import (
    application_build_fingerprint,
    assemble_verified_packet,
    build_fingerprint_to_dict,
    recompute_build_fingerprint,
    validate_packet_references,
)
from follow_the_money.canonical import canonical_bytes, load_canonical_json
from follow_the_money.schema import SchemaError, validate_against

REPO_ROOT = Path(__file__).resolve().parents[1]


def _event() -> dict:
    return {
        "schema_version": 1,
        "event_id": "evt_1",
        "event_type": "policy",
        "evidence_ids": ["evidence_1"],
        "key_fact_ids": ["fact_a", "fact_b"],
        "fully_known_at": "2026-08-11T02:30:00Z",
        "story_family_id": "fam_single_evt_1",
        "coexistence_pair_ids": [],
        "display_label": "美联储政策",
        "economic_effective_time": {"value": "2026-08-11T01:00:00Z", "precision": "instant"},
        "common_effective_time": None,
        "multiple_effective_times": True,
        "key_fact_effective_times": [
            {"fact_id": "fact_a", "value": "2026-08-11T01:00:00Z", "precision": "instant"},
            {"fact_id": "fact_b", "value": "2026-08-11T01:30:00Z", "precision": "instant"},
        ],
    }


def _ledger_entries() -> list[dict]:
    return [
        {
            "fact_id": "fact_a",
            "entry_type": "FACT",
            "origin_payload": "policy",
            "evidence_id": "evidence_1",
            "subject": "ent_fed",
            "predicate": "policy_rate",
            "effective_time": "2026-08-11T01:00:00Z",
            "effective_precision": "instant",
            "value": "5.0",
            "unit": "percent",
            "knowledge_available_at": "2026-08-11T01:00:00Z",
            "source_families": ["fam_fed"],
            "tier_counts": {"Tier 1": 1},
            "conflicts": [],
        },
        {
            "fact_id": "fact_b",
            "entry_type": "FACT",
            "origin_payload": "policy",
            "evidence_id": "evidence_2",
            "subject": "ent_fed",
            "predicate": "rate_hike",
            "effective_time": "2026-08-11T01:30:00Z",
            "effective_precision": "instant",
            "value": "25",
            "unit": "bps",
            "knowledge_available_at": "2026-08-11T02:30:00Z",
            "source_families": ["fam_fed"],
            "tier_counts": {"Tier 1": 1},
            "conflicts": [],
        },
    ]


def _evidence_refs() -> list[dict]:
    return [
        {
            "evidence_id": "evidence_1",
            "provider_id": "prov_a",
            "source_url": "https://a.example.com/1",
            "tier": "Tier 1",
            "knowledge_available_at": "2026-08-11T01:00:00Z",
        },
        {
            "evidence_id": "evidence_2",
            "provider_id": "prov_a",
            "source_url": "https://a.example.com/2",
            "tier": "Tier 1",
            "knowledge_available_at": "2026-08-11T02:30:00Z",
        },
    ]


# ---------------------------------------------------------------------------
# Verified packet
# ---------------------------------------------------------------------------


def test_packet_valid():
    packet = assemble_verified_packet(
        packet_id="pkt_1",
        event=_event(),
        feed_run_id="feed_run_1",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
        eligible_catalyst_calendar_ids=["cal_1", "cal_2"],
    )
    validate_against("verified-event-packet.schema.json", packet)
    assert packet["verification_status"] == "passed"


def test_packet_stable_ordered_catalyst_ids():
    packet = assemble_verified_packet(
        packet_id="pkt_2",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
        eligible_catalyst_calendar_ids=["cal_2", "cal_1", "cal_1"],
    )
    assert packet["eligible_catalyst_calendar_ids"] == ["cal_2", "cal_1"]


def test_packet_catalyst_max_six():
    with pytest.raises(SchemaError, match="exceeds 6"):
        assemble_verified_packet(
            packet_id="p",
            event=_event(),
            feed_run_id="r",
            ledger_entries=_ledger_entries(),
            evidence_refs=_evidence_refs(),
            eligible_catalyst_calendar_ids=[f"cal_{i}" for i in range(7)],
        )


def test_packet_unknown_key_fact_rejected():
    packet = assemble_verified_packet(
        packet_id="p",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
    )
    packet["key_fact_ids"] = ["fact_ghost"]
    with pytest.raises(SchemaError, match="missing from frozen ledger"):
        validate_packet_references(packet)


def test_packet_duplicate_evidence_rejected():
    packet = assemble_verified_packet(
        packet_id="p",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
    )
    packet["evidence"].append(dict(packet["evidence"][0]))
    with pytest.raises(SchemaError, match="duplicate evidence"):
        validate_packet_references(packet)


def test_packet_non_https_source_rejected():
    packet = assemble_verified_packet(
        packet_id="p",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
    )
    packet["evidence"][0]["source_url"] = "http://a.example.com/1"
    with pytest.raises(SchemaError, match="https"):
        validate_packet_references(packet)


def test_packet_unknown_version_rejected():
    packet = assemble_verified_packet(
        packet_id="p",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
    )
    packet["schema_version"] = 2
    with pytest.raises(SchemaError):
        validate_against("verified-event-packet.schema.json", packet)


def test_packet_field_ownership_unknown_field_rejected():
    packet = assemble_verified_packet(
        packet_id="p",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
    )
    packet["score"] = 99
    with pytest.raises(SchemaError, match="Additional properties"):
        validate_against("verified-event-packet.schema.json", packet)


def test_packet_round_trip():
    packet = assemble_verified_packet(
        packet_id="pkt_rt",
        event=_event(),
        feed_run_id="r",
        ledger_entries=_ledger_entries(),
        evidence_refs=_evidence_refs(),
    )
    raw = canonical_bytes(packet)
    decoded = load_canonical_json(raw)
    validate_against("verified-event-packet.schema.json", decoded)
    assert canonical_bytes(decoded) == raw


# ---------------------------------------------------------------------------
# Application build fingerprint (mandatory non-Git)
# ---------------------------------------------------------------------------


def test_build_fingerprint_deterministic():
    a = application_build_fingerprint(REPO_ROOT, "0.1.0")
    b = application_build_fingerprint(REPO_ROOT, "0.1.0")
    assert a.fingerprint == b.fingerprint
    assert a.files  # src/ + pyproject.toml + uv.lock must exist


def test_build_fingerprint_changes_with_version():
    a = application_build_fingerprint(REPO_ROOT, "0.1.0")
    b = application_build_fingerprint(REPO_ROOT, "0.1.1")
    assert a.fingerprint != b.fingerprint


def test_build_fingerprint_covers_uv_lock():
    a = application_build_fingerprint(REPO_ROOT, "0.1.0")
    paths = {f["path"] for f in a.files}
    assert "uv.lock" in paths
    assert "pyproject.toml" in paths
    assert not any("__pycache__" in path or path.endswith((".pyc", ".pyo")) for path in paths)


def test_build_fingerprint_recompute_matches():
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    payload = build_fingerprint_to_dict(build)
    assert recompute_build_fingerprint(payload, REPO_ROOT) == payload["fingerprint"]


def test_build_fingerprint_reject_mismatch():
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    payload = build_fingerprint_to_dict(build)
    payload["files"] = list(payload["files"]) + [
        {"path": "injected.py", "size": 1, "sha256": "0" * 64}
    ]
    assert recompute_build_fingerprint(payload, REPO_ROOT) != payload["fingerprint"]


def test_build_fingerprint_git_metadata_optional():
    build = application_build_fingerprint(REPO_ROOT, "0.1.0", git={"sha": "x" * 40, "dirty": False})
    assert build.git == {"sha": "x" * 40, "dirty": False}


# ---------------------------------------------------------------------------
# Run manifest
# ---------------------------------------------------------------------------


def _manifest() -> dict:
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    return {
        "schema_version": 1,
        "brief_run_id": "run_1",
        "bundle_digest": "a" * 64,
        "directory_id": "dir_1",
        "attempt_id": "att_1",
        "feed_run_id": "feed_run_1",
        "mode": "normal",
        "brief_generated_at": "2026-08-11T00:25:00Z",
        "brief_completed_at": "2026-08-11T00:26:00Z",
        "application_build": build_fingerprint_to_dict(build),
        "schema_fingerprints": {"feed": "b" * 64},
        "config_fingerprint": "c" * 64,
        "prompt_fingerprints": {"resolver": "d" * 64},
        "model_fingerprint": "gpt-test",
        "members": [
            {"path": "input/feed.json", "size": 100, "sha256": "e" * 64},
            {"path": "output/brief.json", "size": 200, "sha256": "f" * 64},
        ],
        "generation_status": "ready_for_commit",
    }


def test_manifest_valid():
    validate_against("run-manifest.schema.json", _manifest())


def test_manifest_indexed_member_rejects_brief_run_id_field():
    m = _manifest()
    m["members"][0]["brief_run_id"] = "leak"
    with pytest.raises(SchemaError):
        validate_against("run-manifest.schema.json", m)


def test_manifest_indexed_member_rejects_bundle_digest_field():
    m = _manifest()
    m["members"][0]["bundle_digest"] = "leak"
    with pytest.raises(SchemaError):
        validate_against("run-manifest.schema.json", m)


def test_manifest_unsafe_relative_path_rejected():
    m = _manifest()
    m["members"][0]["path"] = "../outside/feed.json"
    with pytest.raises(SchemaError):
        validate_against("run-manifest.schema.json", m)


def test_manifest_symlink_like_path_rejected_by_pattern():
    m = _manifest()
    m["members"][0]["path"] = "input/feed.json/../../evil"
    with pytest.raises(SchemaError):
        validate_against("run-manifest.schema.json", m)


def test_manifest_generation_status_fixed():
    m = _manifest()
    m["generation_status"] = "committed"
    with pytest.raises(SchemaError):
        validate_against("run-manifest.schema.json", m)


def test_manifest_unknown_version_rejected():
    m = _manifest()
    m["schema_version"] = 3
    with pytest.raises(SchemaError):
        validate_against("run-manifest.schema.json", m)


def test_manifest_round_trip():
    m = _manifest()
    raw = canonical_bytes(m)
    decoded = load_canonical_json(raw)
    validate_against("run-manifest.schema.json", decoded)
    assert canonical_bytes(decoded) == raw
