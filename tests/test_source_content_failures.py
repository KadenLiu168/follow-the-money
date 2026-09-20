"""Atomic Provider-boundary failure semantics for the four v2 contracts.

No boundary case may emit a healthy title-only item or a partial publishable
slice: enrichment is one atomic Provider obligation, so a failed required
detail document leaves the Provider incomplete.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from follow_the_money.feed.validate import _is_blocked_exempt
from follow_the_money.providers.adapters import FedAdapter, PbocAdapter, SseAdapter, SzseAdapter
from follow_the_money.providers.document import DocumentError
from follow_the_money.providers.http import FetchError
from tests.source_content_harness import (
    DISCOVERY_URLS,
    SourceContentFixtureClient,
    candidate_url,
    window_discovery,
)

CUTOFF = datetime(2026, 8, 10, 17, 0, 0, tzinfo=UTC)
WINDOW = {
    "start": "2026-08-07T17:00:00.000Z",
    "end": CUTOFF.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
}
ATTACHMENT_ONLY = {
    "federal_reserve": (
        b'<!doctype html><html><body><div id="article">'
        b'<div class="col-xs-12 col-sm-8 col-md-8">'
        b'<a href="/files/notice.pdf">\xe9\x99\x84\xe4\xbb\xb6</a>'
        b"</div></div></body></html>"
    ),
    "pboc": (
        b'<!doctype html><html><body><div id="zoom">'
        b'<a href="/files/notice.pdf">\xe9\x99\x84\xe4\xbb\xb6</a>'
        b"</div></body></html>"
    ),
    "sse": (
        b'<!doctype html><html><body><div class="allZoom">'
        b'<a href="/files/notice.pdf">\xe9\x99\x84\xe4\xbb\xb6</a>'
        b"</div></body></html>"
    ),
    "szse": (
        b'<!doctype html><html><body><div id="desContent">'
        b'<a href="/files/notice.pdf">\xe9\x99\x84\xe4\xbb\xb6</a>'
        b"</div></body></html>"
    ),
}
MISSING_CONTAINER = b"<html><body><p>no verified container</p></body></html>"


def _adapter(provider_id: str):
    return {
        "federal_reserve": FedAdapter,
        "pboc": PbocAdapter,
        "sse": SseAdapter,
        "szse": SzseAdapter,
    }[provider_id]()


def _client(provider_id: str, **kwargs) -> SourceContentFixtureClient:
    return SourceContentFixtureClient(
        provider_id,
        pages={
            DISCOVERY_URLS[provider_id]: window_discovery(provider_id, WINDOW, count=3),
        },
        **kwargs,
    )


CASE_BUILDERS = {
    "401": lambda url: ({"failures": {url: 401}}, "HTTP 401"),
    "403": lambda url: ({"failures": {url: 403}}, "HTTP 403"),
    "404": lambda url: ({"failures": {url: 404}}, "HTTP 404"),
    "timeout": lambda url: ({"failures": {url: TimeoutError("slow")}}, "fetch failed"),
    "invalid-charset": lambda url: ({"detail": b"\xff"}, "not decodable"),
    "oversized-response": lambda url: ({"detail": b"x" * (2097152 + 1)}, "exceeds"),
    "unsafe-redirect": lambda url: (
        {"response_urls": {url: "https://example.com/moved.htm"}},
        "redirect_url",
    ),
    "unsupported-media-type": lambda url: ({"content_type": "application/pdf"}, "media type"),
    "non-html-body": lambda url: ({"detail": b"%PDF-1.7 attachment"}, "not HTML"),
    "missing-container": lambda url: (
        {"detail": MISSING_CONTAINER},
        "lacks the verified content container",
    ),
}


@pytest.mark.parametrize("provider_id", ["federal_reserve", "pboc", "sse", "szse"])
@pytest.mark.parametrize("case", [*sorted(CASE_BUILDERS), "attachment-only"])
def test_every_detail_boundary_failure_leaves_no_healthy_slice(provider_id: str, case: str):
    adapter = _adapter(provider_id)
    failure: dict[str, object]
    message: str
    if case == "attachment-only":
        failure, message = {"detail": ATTACHMENT_ONLY[provider_id]}, "attachment-only"
    else:
        built_failure, built_message = CASE_BUILDERS[case](candidate_url(provider_id, 0))
        failure = cast(dict[str, object], built_failure)
        message = cast(str, built_message)
    client = _client(provider_id, **failure)
    # Either the managed detail request or the network-free extraction fails
    # closed; no case may return a title-only or partial slice.
    with pytest.raises((FetchError, DocumentError), match=message):
        adapter.normalize(adapter.fetch(WINDOW, client), WINDOW)
    assert client.detail_requests


@pytest.mark.parametrize("provider_id", ["federal_reserve", "pboc", "sse", "szse"])
def test_a_later_detail_failure_aborts_the_whole_atomic_slice(provider_id: str):
    adapter = _adapter(provider_id)
    client = _client(provider_id, failures={candidate_url(provider_id, 1): 500})
    with pytest.raises(FetchError, match="HTTP 500"):
        adapter.normalize(adapter.fetch(WINDOW, client), WINDOW)
    # Only the selections before the failing document were requested, and no
    # partial acquisition is returned.
    assert len(client.detail_requests) == 2
    assert candidate_url(provider_id, 1) in client.detail_requests
    assert set(client.detail_requests) <= {candidate_url(provider_id, index) for index in range(3)}


def _run_with_failing_detail(tmp_path, provider_id: str, *, generation: str):
    from tests.test_cftc_activation import CUTOFF_1, _fixture_registry, run_feed

    root = tmp_path / generation
    return run_feed(
        output_root=str(root / "out"),
        runtime_state_root=str(root / "state"),
        cutoff=CUTOFF_1,
        providers_fn=lambda: _fixture_registry(detail_failures={provider_id: 403}),
    )


@pytest.mark.parametrize("provider_id", ["federal_reserve", "pboc", "sse", "szse"])
def test_first_detail_block_is_partial_non_exempt_and_not_carried(tmp_path, provider_id: str):
    result = _run_with_failing_detail(tmp_path, provider_id, generation="first")
    feed = result.feed
    assert feed is not None

    assert result.status == "failure"
    assert result.exit_code == 1
    outcome = next(
        entry for entry in feed["provider_outcomes"] if entry["provider_id"] == provider_id
    )
    # Discovery succeeded, so acquisition progress is observed and the
    # first-resource blocked exemption does not apply.
    assert outcome["state"] == "partial"
    assert outcome["partial"] is True
    assert outcome["succeeded"] is True
    assert outcome["failed"] is False
    assert outcome["availability"] == "blocked"
    assert outcome["upstream_http_status"] == 403
    assert not _is_blocked_exempt(outcome)
    assert outcome["accepted"] == 0
    assert outcome["freshness"]["status"] == "not_evaluated"
    assert outcome["freshness"]["carried_forward_from_run_id"] is None
    assert outcome["freshness"]["origin_contract_hash"] is None
    assert not [item for item in feed["items"] if item["provider_id"] == provider_id]

    # Required coverage is unmet, so the run is not publishable.
    assert feed["pipeline"]["status"] == "failure"
    coverage = next(
        row for row in feed["feed_config"]["snapshot"]["coverage"] if provider_id in row["members"]
    )
    assert coverage["optional"] is False
    assert coverage["group"] in outcome["affected_coverage_groups"]


@pytest.mark.parametrize("provider_id", ["federal_reserve", "pboc", "sse", "szse"])
def test_prior_slice_substitution_is_forbidden_for_a_blocked_detail(tmp_path, provider_id: str):
    first = _run_with_failing_detail(tmp_path, provider_id, generation="first")
    feed = first.feed
    assert feed is not None
    outcome = next(
        entry for entry in feed["provider_outcomes"] if entry["provider_id"] == provider_id
    )
    assert outcome["freshness"]["status"] == "not_evaluated"

    # The published product is the failure generation: no healthy slice exists
    # for the incomplete Provider, so a later run cannot carry one forward.
    assert feed["pipeline"]["status"] == "failure"
    assert not [item for item in feed["items"] if item["provider_id"] == provider_id]
