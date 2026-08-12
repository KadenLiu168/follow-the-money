"""Task 11.1-11.8 — evaluation metrics, dataset, offline runner, and live budget."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from follow_the_money.config import load_config
from follow_the_money.eval_live import (
    BudgetState,
    LiveEvalError,
    PriceTable,
    PriceTableEntry,
    load_price_table,
)
from follow_the_money.eval_metrics import (
    Metric,
    aggregate,
    causal_overclaim_rate,
    check_offline_gates,
    compare_ranking_stability,
    duplicate_story_rate,
    recall_at_10,
    top3_precision,
    unsupported_claim_rate,
)
from follow_the_money.eval_offline import (
    GoldenDatasetError,
    _validate_recorded_outputs,
    load_golden_dataset,
    run_offline_evaluation,
)
from follow_the_money.events import story_family_id
from follow_the_money.schema import validate_against
from follow_the_money.selection import SelectionInput, select_events

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "evals" / "dataset"


# ---------------------------------------------------------------------------
# Metric oracles
# ---------------------------------------------------------------------------


def test_recall_at_10():
    m = recall_at_10(["a", "b", "c"], ["a", "x", "y", "z", "q", "w", "e", "r", "t", "u"])
    assert m.numerator == 1
    assert m.denominator == 3
    assert m.value == pytest.approx(1 / 3)


def test_recall_at_10_zero_expected_not_applicable():
    m = recall_at_10([], ["a"])
    assert not m.applicable
    assert m.numerator == 0 and m.denominator == 0


def test_top3_precision_actual_count():
    # Actual count in the up-to-three full-event set is the denominator.
    m = top3_precision(["a", "b"], ["a"])  # only 1 full event selected
    assert m.denominator == 1
    assert m.numerator == 1
    assert m.value == 1.0


def test_top3_precision_no_full_events():
    m = top3_precision(["a"], [])
    assert not m.applicable


def test_duplicate_story_rate():
    m = duplicate_story_rate(["a", "b", "c", "d"], non_allowed_excess=1)
    assert m.value == 0.25


def test_unsupported_and_causal_rates():
    u = unsupported_claim_rate(factual_denominator=10, unsupported_numerator=0)
    assert u.value == 0.0
    c = causal_overclaim_rate(causal_denominator=5, overclaim_numerator=2)
    assert c.value == 0.4


def test_zero_denominator_not_silently_dropped():
    m = Metric("x", 0, 0)
    report = m.as_report()
    assert report["not_applicable"] is True
    assert report["denominator"] == 0


def test_aggregate_sums_and_counts():
    d1 = {
        "recall_at_10": Metric("recall_at_10", 1, 2),
        "top3_precision": Metric("top3_precision", 0, 0),  # non-applicable day
    }
    d2 = {
        "recall_at_10": Metric("recall_at_10", 2, 2),
        "top3_precision": Metric("top3_precision", 1, 1),
    }
    agg = aggregate([_day("d1", d1), _day("d2", d2)])
    assert agg.metrics["recall_at_10"].numerator == 3
    assert agg.metrics["recall_at_10"].denominator == 4
    assert agg.applicable_days["top3_precision"] == 1
    assert agg.non_applicable_days["top3_precision"] == 1


def _day(date: str, metrics: dict) -> object:
    from follow_the_money.eval_metrics import DayReport

    return DayReport(date=date, metrics=metrics)


# ---------------------------------------------------------------------------
# Ranking stability
# ---------------------------------------------------------------------------


def test_ranking_stability_identity_drift():
    s = compare_ranking_stability(["a", "b"], ["a", "c"], ["a"], ["a"])
    assert s.identity_drift
    assert s.selection_order_drift  # different element sets => order differs
    s2 = compare_ranking_stability(["a", "b"], ["b", "a"], ["a"], ["a"])
    assert not s2.identity_drift
    assert s2.selection_order_drift
    assert s2.full_event_order_drift is False


def test_full_event_subset_drift_separate():
    s = compare_ranking_stability(["a", "b"], ["a", "b"], ["a", "b"], ["a"])
    assert not s.identity_drift
    assert not s.selection_order_drift
    assert s.full_event_subset_drift


# ---------------------------------------------------------------------------
# Offline gates
# ---------------------------------------------------------------------------


def test_offline_gates_recall_decrease_fails():
    violations = check_offline_gates(
        {"recall_at_10": 0.8, "top3_precision": 0.7},
        {"recall_at_10": 0.6, "top3_precision": 0.7},
    )
    assert len(violations) == 1
    assert "recall_at_10 decreased" in violations[0]


def test_offline_gates_duplicate_increase_fails():
    violations = check_offline_gates(
        {"duplicate_story_rate": 0.0},
        {"duplicate_story_rate": 0.1},
    )
    assert len(violations) == 1


def test_offline_gates_equal_ok():
    violations = check_offline_gates(
        {"recall_at_10": 0.8},
        {"recall_at_10": 0.8},
    )
    assert violations == []


def test_offline_gates_improvement_ok():
    violations = check_offline_gates(
        {"recall_at_10": 0.6},
        {"recall_at_10": 0.8},
    )
    assert violations == []


# ---------------------------------------------------------------------------
# Golden dataset
# ---------------------------------------------------------------------------


def test_dataset_has_30_days():
    days = load_golden_dataset(DATASET)
    assert len(days) >= 30


def test_dataset_categories_covered():
    days = load_golden_dataset(DATASET)
    categories = {d.category for d in days}
    for required in (
        "ordinary_session",
        "macro_release",
        "company_event",
        "china_policy",
        "china_us_policy",
        "geopolitics",
        "abnormal_cross_asset",
        "degraded_provider",
    ):
        assert required in categories, f"missing category {required}"


def test_dataset_unique_dates():
    days = load_golden_dataset(DATASET)
    dates = [d.date for d in days]
    assert len(dates) == len(set(dates))


def test_recorded_story_family_uses_canonical_pairs_and_selection_trace():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = next(day for day in manifest["days"] if day["date"] == "2024-03-20")
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    members = next(iter(entry["story_families"].values()))
    family = next(iter(entry["story_families"]))
    assert family == story_family_id(members)

    resolver = outputs["recorded_llm_outputs"]["resolver"]
    proposals = {proposal["position_alias"]: proposal for proposal in resolver["proposals"]}
    assert {proposal["story_family_label"] for proposal in proposals.values()} == {"f00"}
    assert proposals["p00"]["coexistence_relations"] == [
        {"other_proposal_alias": "p01", "relation": "distinct_material_development"}
    ]
    assert proposals["p01"]["coexistence_relations"] == [
        {"other_proposal_alias": "p00", "relation": "distinct_material_development"}
    ]
    pair = tuple(entry["coexistence_pairs"][0])
    assert pair == tuple(sorted(pair))

    scoring = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=False,
    ).scoring
    recorded = select_events(
        [
            SelectionInput(
                event_id=members[0],
                fully_known_at="2024-03-20T00:00:00Z",
                base_priority=Decimal(80),
                confidence="high",
                component_coverage=Decimal(1),
                story_family_id=family,
                coexistence_pairs=frozenset({pair}),
            ),
            SelectionInput(
                event_id=members[1],
                fully_known_at="2024-03-20T00:00:00Z",
                base_priority=Decimal(75),
                confidence="high",
                component_coverage=Decimal(1),
                story_family_id=family,
                coexistence_pairs=frozenset({pair}),
            ),
        ],
        scoring,
    )
    assert [selected.event_id for selected in recorded.selected] == list(members)
    assert [selected.final_priority for selected in recorded.selected] == [
        Decimal(80),
        Decimal(75),
    ]

    routine_family = story_family_id(["routine_first", "routine_later"])
    penalized = select_events(
        [
            SelectionInput(
                event_id="routine_first",
                fully_known_at="2024-03-20T00:00:00Z",
                base_priority=Decimal(80),
                confidence="high",
                component_coverage=Decimal(1),
                story_family_id=routine_family,
            ),
            SelectionInput(
                event_id="routine_later",
                fully_known_at="2024-03-20T00:00:00Z",
                base_priority=Decimal(54),
                confidence="high",
                component_coverage=Decimal(1),
                story_family_id=routine_family,
            ),
        ],
        scoring,
    )
    assert [selected.event_id for selected in penalized.selected] == ["routine_first"]
    assert penalized.ineligible_reasons == {}


def test_recorded_three_member_story_family_replay_exercises_non_transitive_pairs():
    fixture = json.loads((DATASET / "story_family_replay.json").read_bytes())
    validate_against("resolver-output.schema.json", fixture["resolver"])
    events = fixture["events"]
    family = fixture["story_family_id"]
    pairs = {tuple(pair) for pair in fixture["coexistence_pairs"]}
    assert family == story_family_id([event["event_id"] for event in events])

    proposals = fixture["resolver"]["proposals"]
    assert [proposal["position_alias"] for proposal in proposals] == ["p00", "p01", "p02"]
    assert {proposal["story_family_label"] for proposal in proposals} == {"f0"}
    declared_pairs = {
        tuple(sorted((proposal["position_alias"], relation["other_proposal_alias"])))
        for proposal in proposals
        for relation in proposal["coexistence_relations"]
    }
    assert declared_pairs == {("p00", "p01"), ("p01", "p02")}

    scoring = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=False,
    ).scoring
    result = select_events(
        [
            SelectionInput(
                event_id=event["event_id"],
                fully_known_at=event["fully_known_at"],
                base_priority=Decimal(event["base_priority"]),
                confidence="high",
                component_coverage=Decimal(1),
                story_family_id=family,
                coexistence_pairs=frozenset(pairs),
            )
            for event in events
        ],
        scoring,
    )
    by_id = {selected.event_id: selected for selected in result.selected}
    assert {selected.event_id for selected in result.selected} == set(
        fixture["expected"]["selected_event_ids"]
    )
    assert {event_id: str(selected.final_priority) for event_id, selected in by_id.items()} == {
        event_id: priority
        for event_id, priority in fixture["expected"]["final_priorities"].items()
        if event_id in by_id
    }
    assert events[2]["event_id"] not in by_id


def test_dataset_invalid_fixture_rejected(tmp_path):
    # A day with an unknown category must fail setup before scoring.
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    manifest["days"][0]["category"] = "bogus_category"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(manifest))

    try:
        # load_golden_dataset reads its own manifest path; simulate by
        # pointing at a temp dir with the bad manifest.
        bad_dir = tmp_path / "bad_dataset"
        bad_dir.mkdir()
        (bad_dir / "manifest.json").write_text(json.dumps(manifest))
        with pytest.raises(GoldenDatasetError, match="unknown category"):
            load_golden_dataset(bad_dir)
    finally:
        pass


def test_dataset_rejects_tampered_event_evidence_reference():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    outputs["event_evidence"][entry["expected_major_events"][0]] = ["missing-evidence"]
    with pytest.raises(GoldenDatasetError, match="invalid Feed evidence refs"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


def test_dataset_rejects_empty_recorded_llm_pass():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    outputs["recorded_llm_outputs"]["resolver"] = {}
    with pytest.raises(GoldenDatasetError, match="resolver output is empty"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


def test_dataset_rejects_tampered_referenced_pass_output():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    outputs["recorded_output_files"]["resolver"] = "pass_outputs/missing.json"
    with pytest.raises(GoldenDatasetError, match="fixture missing for recorded resolver"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


def test_dataset_rejects_tampered_source_snapshot_reference():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    item = feed["items"][0]
    item["payload"]["raw_metadata"]["source_snapshot"]["body_sha256"] = "0" * 64
    with pytest.raises(GoldenDatasetError, match="source snapshot does not match"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


def test_dataset_rejects_source_unbound_recorded_pass_prose():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    outputs["replay_contract"]["analyst_packets"][0]["mechanisms"] = ["固定模板文本"]
    with pytest.raises(GoldenDatasetError, match="analyst output is not source-bound"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


def test_dataset_rejects_recorded_pass_outside_strict_schema():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    outputs["recorded_llm_outputs"]["resolver"]["event_ids"] = entry["expected_major_events"]
    with pytest.raises(GoldenDatasetError, match="resolver schema invalid"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


def test_dataset_rejects_tampered_claim_evidence_reference():
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    entry = manifest["days"][0]
    feed = json.loads((DATASET / entry["feed"]).read_bytes())
    outputs = json.loads((DATASET / entry["outputs"]).read_bytes())
    outputs["claim_inventory"][0]["evidence_ids"] = ["missing-evidence"]
    with pytest.raises(GoldenDatasetError, match="invalid cross-references"):
        _validate_recorded_outputs(
            date=entry["date"],
            dataset_dir=DATASET,
            feed=feed,
            outputs=outputs,
            expected_major=entry["expected_major_events"],
            expected_top3=entry["expected_top3"],
            claim_labels=entry["claim_labels"],
            story_families=entry["story_families"],
            coexistence_pairs=entry["coexistence_pairs"],
        )


# ---------------------------------------------------------------------------
# Offline runner
# ---------------------------------------------------------------------------


def test_offline_runner_valid():
    days = load_golden_dataset(DATASET)
    selected = {d.date: list(d.expected_major_events) + ["extra_evt"] for d in days}
    full = {d.date: list(d.expected_top3) for d in days}
    extras = {
        d.date: {
            "factual_denominator": 5,
            "unsupported_numerator": 0,
            "causal_denominator": 2,
            "overclaim_numerator": 0,
            "reference_selected": selected[d.date],
            "permuted_selected": selected[d.date],
            "reference_full": full[d.date],
            "permuted_full": full[d.date],
        }
        for d in days
    }
    agg, violations = run_offline_evaluation(
        DATASET, selected_by_day=selected, full_by_day=full, extras=extras
    )
    assert violations == []
    assert agg.metrics["recall_at_10"].applicable


def test_offline_runner_stability_drift_fails():
    days = load_golden_dataset(DATASET)
    selected = {d.date: list(d.expected_major_events) for d in days}
    full = {d.date: list(d.expected_top3) for d in days}
    extras = {}
    for i, d in enumerate(days):
        ref = selected[d.date]
        perm = list(reversed(ref)) if ref else []
        extras[d.date] = {
            "reference_selected": ref,
            "permuted_selected": perm,
            "reference_full": full[d.date],
            "permuted_full": list(reversed(full[d.date])),
        }
    with pytest.raises(GoldenDatasetError, match="stability drift"):
        run_offline_evaluation(DATASET, selected_by_day=selected, full_by_day=full, extras=extras)


def test_offline_runner_baseline_gate():
    days = load_golden_dataset(DATASET)
    # Drop the second expected major event from selection => recall < 1.
    selected = {
        d.date: (
            list(d.expected_major_events)[:1]
            if len(d.expected_major_events) > 1
            else list(d.expected_major_events)
        )
        for d in days
    }
    full = {d.date: list(d.expected_top3) for d in days}
    extras = {
        d.date: {
            "factual_denominator": 4,
            "unsupported_numerator": 0,
            "causal_denominator": 2,
            "overclaim_numerator": 0,
        }
        for d in days
    }
    # Baseline claims perfect recall; current recall is lower => gate fails.
    baseline = {"recall_at_10": 1.0, "top3_precision": 1.0, "duplicate_story_rate": 0.0}
    _agg, violations = run_offline_evaluation(
        DATASET, selected_by_day=selected, full_by_day=full, extras=extras, baseline=baseline
    )
    assert violations  # recall decreased vs perfect baseline


# ---------------------------------------------------------------------------
# Live budget controller
# ---------------------------------------------------------------------------


def _price_table(tmp_path: Path) -> Path:
    path = tmp_path / "prices.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "source_url": "https://example.com/pricing",
                "effective_date": "2026-08-01",
                "fingerprint": "a" * 64,
                "entries": [
                    {
                        "model_id": "gpt-test",
                        "input_usd_per_million": "1.0",
                        "output_usd_per_million": "2.0",
                        "aliases": ["gpt-test-2026"],
                    },
                ],
            }
        )
    )
    return path


def test_price_table_load_and_allowset(tmp_path):
    table = load_price_table(_price_table(tmp_path))
    assert "gpt-test" in table.allowed_models()
    assert "gpt-test-2026" in table.allowed_models()
    assert table.rates_for("gpt-test-2026").model_id == "gpt-test"


def test_price_table_missing_fingerprint_rejected(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"version": 1, "entries": []}))
    with pytest.raises(LiveEvalError, match="fingerprint"):
        load_price_table(path)


def _rates():
    return PriceTableEntry("gpt-test", "1.0", "2.0")


def test_budget_admission_equality_allowed():
    budget = BudgetState(max_cost_usd=Decimal(10), max_requests=100, max_seconds=300)
    reservation = budget.reservation(request_bytes=1_000_000, max_output_tokens=72_000)
    # 1M tokens input at $1/M + 72k output at $2/M = 1.0 + 0.144 = 1.144
    assert budget.can_admit(reservation, _rates())
    budget.debit(reservation, _rates())
    assert budget.committed_spend == reservation.cost(_rates())


def test_budget_release_on_pre_send_failure():
    budget = BudgetState(max_cost_usd=Decimal(1), max_requests=100, max_seconds=300)
    r = budget.reservation(request_bytes=10_000, max_output_tokens=1_000)
    budget.debit(r, _rates())
    budget.release(r, _rates())
    assert budget.committed_spend == 0
    assert budget.requests_used == 0


def test_budget_exhaustion_blocks():
    budget = BudgetState(max_cost_usd=Decimal("0.5"), max_requests=100, max_seconds=300)
    r = budget.reservation(request_bytes=1_000_000, max_output_tokens=72_000)  # > 0.5
    assert not budget.can_admit(r, _rates())
    with pytest.raises(LiveEvalError, match="budget exhausted"):
        budget.debit(r, _rates())


def test_budget_integrity_model_mismatch():
    from types import SimpleNamespace

    budget = BudgetState(max_cost_usd=Decimal(10), max_requests=100, max_seconds=300)
    table = PriceTable(
        source_url="u",
        effective_date="d",
        fingerprint="f" * 64,
        entries=(PriceTableEntry("gpt-test", "1.0", "2.0"),),
    )
    r = budget.reservation(request_bytes=1000, max_output_tokens=100)
    resp = SimpleNamespace(
        model="other-model",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )
    cost = budget.reconcile_response(
        reservation=r, response=resp, price_table=table, pass_limits={}
    )
    assert cost is None
    assert "not in price table allowset" in budget.integrity_failures[0]


def test_budget_integrity_reasoning():
    from types import SimpleNamespace

    budget = BudgetState(max_cost_usd=Decimal(10), max_requests=100, max_seconds=300)
    table = PriceTable(
        source_url="u",
        effective_date="d",
        fingerprint="f" * 64,
        entries=(PriceTableEntry("gpt-test", "1.0", "2.0"),),
    )
    r = budget.reservation(request_bytes=1000, max_output_tokens=100)
    resp = SimpleNamespace(
        model="gpt-test",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            output_tokens_details=SimpleNamespace(reasoning_tokens=50),
        ),
    )
    cost = budget.reconcile_response(
        reservation=r, response=resp, price_table=table, pass_limits={}
    )
    assert cost is None
    assert "nonzero reasoning" in budget.integrity_failures[0]


def test_budget_settle_actual_cost():
    from types import SimpleNamespace

    budget = BudgetState(max_cost_usd=Decimal(10), max_requests=100, max_seconds=300)
    table = PriceTable(
        source_url="u",
        effective_date="d",
        fingerprint="f" * 64,
        entries=(PriceTableEntry("gpt-test", "1.0", "2.0"),),
    )
    r = budget.reservation(request_bytes=1000, max_output_tokens=100)
    budget.debit(r, table.rates_for("gpt-test"))
    resp = SimpleNamespace(
        model="gpt-test",
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=100,
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )
    actual = budget.reconcile_response(
        reservation=r, response=resp, price_table=table, pass_limits={}
    )
    assert actual is not None
    # 1000 tokens in at $1/M + 100 out at $2/M = 0.001 + 0.0002 = 0.0012
    assert actual == Decimal("0.0012")
    budget.settle(r, table.rates_for("gpt-test"), actual)
    assert budget.committed_spend == Decimal("0.0012")
