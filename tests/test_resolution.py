"""Task 7.1/7.3 — fake-client LLM adapter and resolver fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from follow_the_money.engine.candidates import (
    CandidateBlock,
    Component,
)
from follow_the_money.engine.entities import EntityResolver
from follow_the_money.engine.resolution import (
    ResolutionError,
    resolve_component_events,
    validate_seed_coverage,
)
from follow_the_money.ledger import Ledger, build_ledger_entry
from follow_the_money.llm import (
    FakeClientResponse,
    ResponsesAdapter,
    invoke_pass,
)

T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------
# Fake client
# ---------------------------------------------------------------------------


class FakeClient:
    def __init__(
        self,
        response: FakeClientResponse | list[FakeClientResponse] | None = None,
        fail_status: int | None = None,
    ):
        self.responses = (
            response if isinstance(response, list) else [response or FakeClientResponse()]
        )
        self.index = 0
        self.fail_status = fail_status
        self.calls = 0
        self.created = []

    def create(self, **kwargs):
        # Fake the OpenAI client surface: client.responses.create(...)
        self.calls += 1
        self.created.append(kwargs)
        if self.fail_status is not None and self.calls == 1:
            if 400 <= self.fail_status < 500:
                exc = _HttpError()
                exc.status_code = self.fail_status
                raise exc
            raise ConnectionError("boom")
        resp = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return resp

    # Alias for tests that called responses_create directly.
    responses_create = create


class _HttpError(Exception):
    def __init__(self, status_code: int | None = None):
        super().__init__("http error")
        self.status_code = status_code


def _adapter(client=None, model="gpt-test"):
    client = client or FakeClient()
    from types import SimpleNamespace

    namespace = SimpleNamespace(responses=client, create=client.create)
    return ResponsesAdapter(model=model, client=namespace)


# ---------------------------------------------------------------------------
# Pass limit / retry matrix
# ---------------------------------------------------------------------------


def test_success_passthrough():
    client = FakeClient(
        FakeClientResponse(
            output_text=json.dumps(
                {"component_alias": "c0", "proposals": [], "unresolved_groups": []}
            )
        )
    )
    outcome = invoke_pass(
        _adapter(client),
        pass_name="resolver",
        prompt="p",
        response_schema={},
        envelope={},
        canonical_input={},
    )
    assert outcome.status == "success"
    assert outcome.data["component_alias"] == "c0"


def test_refusal_non_retryable():
    client = FakeClient(FakeClientResponse(status="refused", output_text=""))
    outcome = invoke_pass(
        _adapter(client),
        pass_name="resolver",
        prompt="p",
        response_schema={},
        envelope={},
        canonical_input={},
    )
    assert outcome.status == "refused"


def test_nonzero_reasoning_fails():
    client = FakeClient(FakeClientResponse(reasoning_tokens=100))
    outcome = _adapter(client).call(
        pass_name="analyst", prompt="p", response_schema={}, envelope={}
    )
    assert outcome.status == "non_retryable"
    assert "unexpected_reasoning_usage" in outcome.error


def test_transient_5xx_retries_once():

    client = FakeClient(
        FakeClientResponse(
            output_text=json.dumps(
                {"component_alias": "c0", "proposals": [], "unresolved_groups": []}
            )
        )
    )
    client.fail_status = 500
    outcome = invoke_pass(
        _adapter(client),
        pass_name="resolver",
        prompt="p",
        response_schema={},
        envelope={},
        canonical_input={},
    )
    assert outcome.status == "success"
    assert outcome.retried
    assert client.calls == 2


def test_non_retryable_4xx_no_retry():

    client = FakeClient()
    client.fail_status = 403
    outcome = invoke_pass(
        _adapter(client),
        pass_name="resolver",
        prompt="p",
        response_schema={},
        envelope={},
        canonical_input={},
    )
    assert outcome.status == "non_retryable"
    assert client.calls == 1


def test_exhaustion_after_two_transient():
    from types import SimpleNamespace

    client = FakeClient()
    adapter = _adapter(client)

    class _AlwaysFail:
        def __init__(self):
            self.calls = 0

        def create(self, **kw):
            self.calls += 1
            raise ConnectionError("boom")

    failing = _AlwaysFail()
    namespace = SimpleNamespace(responses=failing, create=failing.create)
    adapter.client = namespace
    outcome = adapter.call(pass_name="resolver", prompt="p", response_schema={}, envelope={})
    assert outcome.status == "exhaustion"
    assert outcome.attempts == 2


def test_store_false_no_state():
    client = FakeClient(FakeClientResponse(output_text="{}"))
    _adapter(client).call(pass_name="editor", prompt="p", response_schema={}, envelope={})
    assert client.created[0]["store"] is False


def test_responses_request_uses_strict_json_schema():
    client = FakeClient(FakeClientResponse(output_text="{}"))
    _adapter(client).call(
        pass_name="editor", prompt="p", response_schema={"type": "object"}, envelope={}
    )
    fmt = client.created[0]["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True
    assert fmt["schema"] == {"type": "object"}
    assert client.created[0]["reasoning"] == {"effort": None}


def test_missing_reasoning_detail_fails_closed():
    from types import SimpleNamespace

    client = FakeClient()
    client.responses = [SimpleNamespace(status="completed", output_text="{}")]
    outcome = _adapter(client).call(pass_name="editor", prompt="p", response_schema={}, envelope={})
    assert outcome.status == "non_retryable"
    assert "missing reasoning" in outcome.error


# ---------------------------------------------------------------------------
# Resolver seed coverage
# ---------------------------------------------------------------------------


def _block_with_seeds(*fact_ids: str) -> CandidateBlock:
    facts = tuple(
        build_ledger_entry(
            entry_type="FACT",
            origin_payload="news",
            evidence_id=f"ev_{i}",
            subject=f"ent_{i}",
            predicate=f"p{i}",
            effective_time=None,
            effective_precision="instant",
            value=str(i),
            unit="u",
            knowledge_available_at=_ts(T0),
        )
        for i in range(len(fact_ids))
    )
    component = Component(
        component_id="comp_x",
        mention_ids=tuple(f"mn_{i}" for i in range(len(facts))),
        evidence_ids=tuple(f"ev_{i}" for i in range(len(facts))),
        seed_fact_ids=tuple(f.fact_id for f in facts),
        facts=facts,
    )
    return CandidateBlock(
        block_id="blk_x",
        components=(component,),
        projected_records=len(facts),
        seed_count=len(facts),
    )


def _real_ids(n: int) -> list[str]:
    return [f.fact_id for f in _block_with_seeds(*([""] * n)).components[0].facts]


def test_seed_coverage_exact_once():
    ids = _real_ids(3)
    block = _block_with_seeds(*ids)
    validate_seed_coverage(
        block=block,
        proposals=[{"event_defining_fact_ids": [ids[0], ids[1]]}],
        unresolved=[{"seed_fact_ids": [ids[2]]}],
    )


def test_missing_seed_rejected():
    ids = _real_ids(2)
    block = _block_with_seeds(*ids)
    with pytest.raises(ResolutionError, match="missing"):
        validate_seed_coverage(
            block=block, proposals=[{"event_defining_fact_ids": [ids[0]]}], unresolved=[]
        )


def test_duplicate_seed_rejected():
    ids = _real_ids(2)
    block = _block_with_seeds(*ids)
    with pytest.raises(ResolutionError, match="more than once"):
        validate_seed_coverage(
            block=block,
            proposals=[{"event_defining_fact_ids": [ids[0]]}],
            unresolved=[{"seed_fact_ids": [ids[0]]}],
        )


def test_out_of_block_seed_rejected():
    ids = _real_ids(1)
    block = _block_with_seeds(*ids)
    with pytest.raises(ResolutionError, match="out-of-block"):
        validate_seed_coverage(
            block=block, proposals=[{"event_defining_fact_ids": ["ghost"]}], unresolved=[]
        )


# ---------------------------------------------------------------------------
# Canonical event construction from resolver output
# ---------------------------------------------------------------------------


def test_resolve_component_events():
    ledger = Ledger()
    entries = [
        build_ledger_entry(
            entry_type="FACT",
            origin_payload="news",
            evidence_id="ev_1",
            subject="ent_fed",
            predicate="policy_rate",
            effective_time=_ts(T0),
            effective_precision="instant",
            value="5.0",
            unit="percent",
            knowledge_available_at=_ts(T0),
        ),
        build_ledger_entry(
            entry_type="FACT",
            origin_payload="news",
            evidence_id="ev_2",
            subject="ent_fed",
            predicate="rate_hike",
            effective_time=_ts(T0),
            effective_precision="instant",
            value="25",
            unit="bps",
            knowledge_available_at=_ts(T0 + timedelta(minutes=30)),
        ),
    ]
    for e in entries:
        ledger.add(e)
    {f.fact_id: f for f in ledger.entries()}
    component = Component(
        component_id="comp_1",
        mention_ids=("m1", "m2"),
        evidence_ids=("ev_1", "ev_2"),
        seed_fact_ids=(entries[0].fact_id, entries[1].fact_id),
        facts=tuple(ledger.entries()),
    )
    resolver = EntityResolver([])
    events = resolve_component_events(
        component=component,
        proposals=[
            {
                "event_type": "policy",
                "event_defining_fact_ids": [entries[0].fact_id, entries[1].fact_id],
                "evidence_ids": ["ev_1", "ev_2"],
                "entity_ids": ["ent_fed"],
            }
        ],
        ledger=ledger,
        resolver=resolver,
        subject_zh_by_entity={"ent_fed": "美联储"},
    )
    assert len(events) == 1
    event = events[0]
    assert event["fully_known_at"] == _ts(T0 + timedelta(minutes=30))
    assert event["key_fact_ids"] == sorted([entries[0].fact_id, entries[1].fact_id])
    assert event["display_label"]
    assert event["event_id"].startswith("evt_")


def test_resolve_component_unknown_fact_rejected():
    ledger = Ledger()
    e = build_ledger_entry(
        entry_type="FACT",
        origin_payload="news",
        evidence_id="ev_1",
        subject="s",
        predicate="p",
        effective_time=None,
        effective_precision="instant",
        value="1",
        unit="u",
        knowledge_available_at=_ts(T0),
    )
    ledger.add(e)
    component = Component(
        component_id="comp_1",
        mention_ids=("m1",),
        evidence_ids=("ev_1",),
        seed_fact_ids=(e.fact_id,),
        facts=(e,),
    )
    with pytest.raises(ResolutionError, match="not in this component"):
        resolve_component_events(
            component=component,
            proposals=[
                {
                    "event_type": "news",
                    "event_defining_fact_ids": ["ghost"],
                    "evidence_ids": ["ev_1"],
                }
            ],
            ledger=ledger,
            resolver=EntityResolver([]),
        )


def test_resolve_invented_fact_rejected():
    ledger = Ledger()
    e = build_ledger_entry(
        entry_type="FACT",
        origin_payload="news",
        evidence_id="ev_1",
        subject="s",
        predicate="p",
        effective_time=None,
        effective_precision="instant",
        value="1",
        unit="u",
        knowledge_available_at=_ts(T0),
    )
    ledger.add(e)
    component = Component(
        component_id="comp_1",
        mention_ids=("m1",),
        evidence_ids=("ev_1",),
        seed_fact_ids=(e.fact_id,),
        facts=(e,),
    )
    with pytest.raises(ResolutionError):
        resolve_component_events(
            component=component,
            proposals=[
                {
                    "event_type": "news",
                    "event_defining_fact_ids": [e.fact_id, "invented"],
                    "evidence_ids": ["ev_1"],
                }
            ],
            ledger=ledger,
            resolver=EntityResolver([]),
        )
