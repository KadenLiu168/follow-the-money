"""Two-stage acquisition plans for the four Provider v2 contracts.

Every case drives ``fetch`` with an injected URL-aware client, asserts the
exact request plan (which locators were requested and how often), and then
normalizes the acquisition without any further I/O.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from follow_the_money.providers.adapters import (
    FedAdapter,
    PbocAdapter,
    SseAdapter,
    SzseAdapter,
)
from follow_the_money.providers.document import DocumentError
from follow_the_money.providers.http import FetchError
from tests.source_content_harness import (
    DISCOVERY_URLS,
    SourceContentFixtureClient,
    detail_bytes,
    discovery_document,
    page_url,
)
from tests.source_content_harness import archive_url as _archive_url
from tests.source_content_harness import candidate_url as _current_url

CUTOFF = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
WINDOW = {
    "start": (CUTOFF - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "end": CUTOFF.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
}
ARCHIVE_STAMP = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
ARCHIVE_DATE = "2026-07-01"


def _stamp(minutes_ago: int) -> datetime:
    return CUTOFF - timedelta(minutes=minutes_ago)


def _date(minutes_ago: int = 1) -> str:
    return _stamp(minutes_ago).strftime("%Y-%m-%d")


def _entries(provider_id: str, count: int, *, title: str) -> list[tuple[str, str, object]]:
    if provider_id == "federal_reserve":
        return [
            (f"{title} {index}", _current_url(provider_id, index), _stamp(index + 1))
            for index in range(count)
        ]
    # Exchange and PBOC indexes publish a date, not an instant.
    return [
        (f"{title} {index}", _current_url(provider_id, index), _date()) for index in range(count)
    ]


def _archive_entries(provider_id: str, count: int) -> list[tuple[str, str, object]]:
    if provider_id == "federal_reserve":
        return [
            (
                f"Archived {index}",
                _archive_url(provider_id, index),
                ARCHIVE_STAMP - timedelta(days=index),
            )
            for index in range(count)
        ]
    return [
        (f"Archived {index}", _archive_url(provider_id, index), ARCHIVE_DATE)
        for index in range(count)
    ]


def _client(
    provider_id: str, current: int = 3, *, archive: int = 197, **kwargs
) -> SourceContentFixtureClient:
    discovery = discovery_document(
        provider_id,
        _entries(provider_id, current, title="Current") + _archive_entries(provider_id, archive),
    )
    pages = kwargs.pop("pages", {DISCOVERY_URLS[provider_id]: discovery})
    return SourceContentFixtureClient(provider_id, pages=pages, **kwargs)


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [
        (FedAdapter, "federal_reserve"),
        (PbocAdapter, "pboc"),
    ],
)
def test_two_of_two_hundred_entries_select_and_fetch_each_current_detail_once(
    adapter_cls, provider_id
):
    adapter = adapter_cls()
    client = _client(provider_id)
    acquisition = adapter.fetch(WINDOW, client)

    assert client.discovery_requests == [DISCOVERY_URLS[provider_id]]
    expected = {_current_url(provider_id, index) for index in range(3)}
    assert set(client.detail_requests) == expected
    assert len(client.detail_requests) == 3
    assert {candidate.url for candidate in acquisition.candidates} == expected
    for document in acquisition.documents:
        assert document.body == detail_bytes(provider_id)
        assert document.final_url == document.candidate.url
        assert document.document_sha256 == document.document_sha256.lower()

    items = adapter.normalize(acquisition, WINDOW)
    assert len(items) == 3
    for item in items:
        content = item["payload"]["source_content"]
        assert content["format"] == "plain_text"
        assert content["extraction_method"] == "official_html_text_v1"
        assert content["truncated"] is False
        assert content["text"]
        assert item["payload"]["type"] in {"news", "policy"}


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(FedAdapter, "federal_reserve"), (PbocAdapter, "pboc")],
)
def test_selected_candidate_count_exceeding_the_bound_fails_before_detail_requests(
    adapter_cls, provider_id
):
    adapter = adapter_cls()
    contract = adapter._contract.source_content
    assert contract is not None
    client = _client(provider_id, current=contract.max_detail_documents_per_window + 1, archive=0)

    with pytest.raises(DocumentError, match="exceeds the declared bound"):
        adapter.fetch(WINDOW, client)
    assert client.detail_requests == []


def test_federal_reserve_identity_uses_the_guid_then_the_link():
    adapter = FedAdapter()
    guid_url = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260810a.htm"
    link_url = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260810b.htm"
    body = _rss_with_identity(guid_url, link_url)
    candidates = adapter._rss_candidates(_response(body, DISCOVERY_URLS["federal_reserve"]))

    assert [candidate.identity for candidate in candidates] == [
        "urn:guid:release-1",
        link_url,
    ]
    assert [candidate.url for candidate in candidates] == [guid_url, link_url]


def _rss_with_identity(guid_url: str, link_url: str) -> bytes:
    stamp = _stamp(1)
    from tests.source_content_harness import rfc822

    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        "<title>identity</title>"
        f"<item><title>With guid</title><link>{guid_url}</link>"
        f"<guid isPermaLink='false'>urn:guid:release-1</guid>"
        f"<pubDate>{rfc822(stamp)}</pubDate></item>"
        f"<item><title>Without guid</title><link>{link_url}</link>"
        f"<pubDate>{rfc822(stamp - timedelta(minutes=1))}</pubDate></item>"
        "</channel></rss>"
    ).encode()


def _response(body: bytes, url: str):
    from tests.test_adapters import FakeResponse

    return FakeResponse(body, 200, "text/xml", url=url)


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(FedAdapter, "federal_reserve"), (PbocAdapter, "pboc")],
)
def test_required_detail_documents_must_resolve_to_the_selected_canonical_url(
    adapter_cls, provider_id
):
    adapter = adapter_cls()
    client = _client(
        provider_id,
        current=1,
        archive=0,
        response_urls={_current_url(provider_id, 0): _archive_url(provider_id, 0)},
    )
    with pytest.raises(FetchError, match="canonical source URL|redirect_url"):
        adapter.fetch(WINDOW, client)


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(FedAdapter, "federal_reserve"), (PbocAdapter, "pboc")],
)
def test_normalize_performs_no_network_access(adapter_cls, provider_id):
    adapter = adapter_cls()
    client = _client(provider_id, current=2, archive=0)
    acquisition = adapter.fetch(WINDOW, client)
    requests_after_fetch = list(client.requests)

    class _NoNetwork:
        def get(self, *_args, **_kwargs):  # pragma: no cover - must never run
            raise AssertionError("normalize must not perform I/O")

    adapter.normalize(acquisition, WINDOW)
    assert client.requests == requests_after_fetch
    assert len(adapter.normalize(acquisition, WINDOW)) == 2


def test_pboc_collapses_exact_duplicates_and_rejects_conflicting_ones():
    adapter = PbocAdapter()
    same_url = _current_url("pboc", 0)
    duplicate = discovery_document(
        "pboc", [("Same", same_url, _date()), ("Same", same_url, _date())]
    )
    client = SourceContentFixtureClient(
        "pboc", pages={DISCOVERY_URLS["pboc"]: duplicate}, detail=detail_bytes("pboc")
    )
    acquisition = adapter.fetch(WINDOW, client)
    assert len(acquisition.candidates) == 1
    assert client.detail_requests == [same_url]

    conflicting = discovery_document(
        "pboc",
        [("Original", same_url, _date()), ("Rewritten", same_url, _date())],
    )
    with pytest.raises(DocumentError, match="conflicting duplicate"):
        adapter.fetch(
            WINDOW,
            SourceContentFixtureClient("pboc", pages={DISCOVERY_URLS["pboc"]: conflicting}),
        )


# ---------------------------------------------------------------------------
# Exchange discovery
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(SseAdapter, "sse"), (SzseAdapter, "szse")],
)
def test_exchange_discovery_stops_once_a_page_proves_the_window_boundary(adapter_cls, provider_id):
    adapter = adapter_cls()
    pages = {
        page_url(provider_id, 1): discovery_document(
            provider_id,
            _entries(provider_id, 2, title="Current") + _archive_entries(provider_id, 2),
        )
    }
    client = SourceContentFixtureClient(provider_id, pages=pages)
    acquisition = adapter.fetch(WINDOW, client)

    assert client.discovery_requests == [page_url(provider_id, 1)]
    expected = {_current_url(provider_id, index) for index in range(2)}
    assert set(client.detail_requests) == expected
    assert len(acquisition.candidates) == 2
    assert len(acquisition.documents) == 2


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(SseAdapter, "sse"), (SzseAdapter, "szse")],
)
def test_exchange_discovery_traverses_sequential_pages_in_order(adapter_cls, provider_id):
    adapter = adapter_cls()
    pages = {
        page_url(provider_id, 1): discovery_document(
            provider_id,
            [
                ("Newest", _current_url(provider_id, 0), _date()),
                ("Also current", _current_url(provider_id, 1), _date(60 * 24)),
            ],
        ),
        page_url(provider_id, 2): discovery_document(
            provider_id,
            [
                ("Still current", _current_url(provider_id, 2), _date(60 * 48)),
                ("Past the boundary", _archive_url(provider_id, 0), ARCHIVE_DATE),
            ],
        ),
    }
    client = SourceContentFixtureClient(provider_id, pages=pages)
    acquisition = adapter.fetch(WINDOW, client)

    assert client.discovery_requests == [page_url(provider_id, 1), page_url(provider_id, 2)]
    expected = {_current_url(provider_id, index) for index in range(3)}
    assert set(client.detail_requests) == expected
    assert len(acquisition.candidates) == 3


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(SseAdapter, "sse"), (SzseAdapter, "szse")],
)
def test_exchange_discovery_rejects_non_descending_order(adapter_cls, provider_id):
    adapter = adapter_cls()
    pages = {
        page_url(provider_id, 1): discovery_document(
            provider_id,
            [
                ("Older first", _archive_url(provider_id, 0), _date(60 * 24 * 30)),
                ("Newer second", _current_url(provider_id, 0), _date()),
            ],
        )
    }
    with pytest.raises(FetchError, match="descending publication order"):
        adapter.fetch(WINDOW, SourceContentFixtureClient(provider_id, pages=pages))


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(SseAdapter, "sse"), (SzseAdapter, "szse")],
)
def test_exchange_discovery_fails_when_the_page_bound_cannot_prove_the_boundary(
    adapter_cls, provider_id
):
    adapter = adapter_cls()
    contract = adapter._contract.source_content
    assert contract is not None
    # Every page stays inside the window, so the boundary is never proved.
    pages = {
        page_url(provider_id, page): discovery_document(
            provider_id,
            [
                (
                    f"Current {page}-{index}",
                    _current_url(provider_id, page * 10 + index),
                    _date(),
                )
                for index in range(2)
            ],
        )
        for page in range(1, int(contract.max_discovery_pages_per_window) + 1)
    }
    client = SourceContentFixtureClient(provider_id, pages=pages)
    with pytest.raises(FetchError, match="could not prove the window boundary"):
        adapter.fetch(WINDOW, client)
    assert len(client.discovery_requests) == contract.max_discovery_pages_per_window
    assert client.detail_requests == []


@pytest.mark.parametrize(
    ("adapter_cls", "provider_id"),
    [(SseAdapter, "sse"), (SzseAdapter, "szse")],
)
def test_exchange_acquisition_extracts_official_notice_content(adapter_cls, provider_id):
    adapter = adapter_cls()
    pages = {
        page_url(provider_id, 1): discovery_document(
            provider_id,
            _entries(provider_id, 1, title="Current notice") + _archive_entries(provider_id, 1),
        )
    }
    client = SourceContentFixtureClient(provider_id, pages=pages)
    acquisition = adapter.fetch(WINDOW, client)
    assert client.detail_requests == [_current_url(provider_id, 0)]

    items = adapter.normalize(acquisition, WINDOW)
    assert len(items) == 1
    item = items[0]
    assert item["payload"]["type"] == "news"
    assert item["payload"]["snippet"] == ""
    assert item["source"]["url"] == _current_url(provider_id, 0)
    content = item["payload"]["source_content"]
    assert content["text"]
    assert content["truncated"] is False
    assert content["document_sha256"]


def test_selected_candidates_are_deterministically_ordered():
    from follow_the_money.providers.document import DocumentCandidate, select_candidates

    window = WINDOW
    candidates = (
        DocumentCandidate("b", "older", "https://x/b", "2026-08-09T00:00:00.000Z"),
        DocumentCandidate("c", "newest", "https://x/c", "2026-08-10T00:00:00.000Z"),
        DocumentCandidate("a", "newest tie", "https://x/a", "2026-08-10T00:00:00.000Z"),
        DocumentCandidate("out", "archived", "https://x/out", "2026-07-01T00:00:00.000Z"),
    )
    selected = select_candidates(candidates, window=window, limit=50)
    assert [candidate.identity for candidate in selected] == ["c", "a", "b"]
    assert select_candidates(tuple(reversed(candidates)), window=window, limit=50) == selected


def test_exchange_identity_is_the_canonical_source_url():
    adapter = SseAdapter()
    current = _current_url("sse", 0)
    pages = {
        page_url("sse", 1): discovery_document(
            "sse", [("Notice", current, _date()), ("Old", _archive_url("sse", 0), ARCHIVE_DATE)]
        )
    }
    acquisition = adapter.fetch(WINDOW, SourceContentFixtureClient("sse", pages=pages))
    candidate = acquisition.candidates[0]
    assert candidate.identity == current
    assert candidate.identity == candidate.url


# ---------------------------------------------------------------------------
# Feed identity
# ---------------------------------------------------------------------------


def _policy_feed_item(provider_id: str, *, source_content: dict, body: bytes) -> dict:
    """One validated-v5 policy item carrying the given source-content object."""
    from tests.test_feed_bundle import TARGET_V2_PROVIDERS, _feed

    assert provider_id in TARGET_V2_PROVIDERS
    item = {
        "id": "identity-item",
        "provider_id": provider_id,
        "source": {
            "id": "identity-source",
            "name": "Federal Reserve",
            "tier": "Tier 1",
            "kind": "policy",
            "url": _current_url(provider_id, 0),
            "published_at": "2026-08-10T16:59:00.000Z",
            "knowledge_available_at": "2026-08-10T16:59:00.000Z",
        },
        "payload": {
            "type": "policy",
            "title": "Identity",
            "announced_at": "2026-08-10T16:59:00.000Z",
            "raw_metadata": {},
            "source_content": source_content,
        },
    }
    from follow_the_money.semantic.policy import build_policy_context

    item["semantic_context"] = build_policy_context(
        provider_id, item["payload"], item["source"]
    ).to_dict()
    return _feed([item], target_v2=True)


def _content_for(body: bytes) -> dict:
    from follow_the_money.providers.document import (
        SOURCE_CONTENT_MAX_CODE_POINTS,
        assemble_source_content,
        document_digest,
        extract_federal_reserve,
    )

    return assemble_source_content(
        extract_federal_reserve(body),
        max_text_chars=SOURCE_CONTENT_MAX_CODE_POINTS,
        document_sha256=document_digest(body),
    ).to_payload()


def test_identical_detail_bytes_produce_byte_identical_source_content_and_feed():
    from follow_the_money.canonical import canonical_bytes
    from follow_the_money.feed.bundle import build_bundle

    body = detail_bytes("federal_reserve")
    first = _policy_feed_item("federal_reserve", source_content=_content_for(body), body=body)
    second = _policy_feed_item("federal_reserve", source_content=_content_for(body), body=body)
    assert canonical_bytes(first) == canonical_bytes(second)
    assert build_bundle(first).manifest_bytes == build_bundle(second).manifest_bytes
    assert build_bundle(first).artifact_bytes == build_bundle(second).artifact_bytes


def test_changed_body_bytes_preserve_item_identity_but_change_digests():
    from follow_the_money.feed.validate import semantic_feed_projection

    body = detail_bytes("federal_reserve")
    changed = body.replace(b"<p>The Committee", b"<p>The committee", 1)
    assert changed != body

    original = _policy_feed_item("federal_reserve", source_content=_content_for(body), body=body)
    revised = _policy_feed_item(
        "federal_reserve", source_content=_content_for(changed), body=changed
    )

    assert original["items"][0]["id"] == revised["items"][0]["id"]
    original_content = original["items"][0]["payload"]["source_content"]
    revised_content = revised["items"][0]["payload"]["source_content"]
    assert original_content["document_sha256"] != revised_content["document_sha256"]
    assert original_content["text"] != revised_content["text"]
    assert original["content_digest"] != revised["content_digest"]
    assert original["run_id"] != revised["run_id"]
    # Only the evidence-sensitive projections differ.
    assert semantic_feed_projection(original)["items"] != semantic_feed_projection(revised)["items"]


def test_chrome_only_raw_byte_change_alters_feed_identity_with_equal_text():
    body = detail_bytes("federal_reserve")
    # A non-extracted page byte inside the shared chrome, outside the
    # verified content container.
    chrome_changed = body.replace(b"<title>", b"<title >", 1)
    assert chrome_changed != body
    assert _content_for(chrome_changed)["text"] == _content_for(body)["text"]

    original = _policy_feed_item("federal_reserve", source_content=_content_for(body), body=body)
    revised = _policy_feed_item(
        "federal_reserve", source_content=_content_for(chrome_changed), body=chrome_changed
    )
    assert (
        original["items"][0]["payload"]["source_content"]["text"]
        == (revised["items"][0]["payload"]["source_content"]["text"])
    )
    assert (
        original["items"][0]["payload"]["source_content"]["document_sha256"]
        != (revised["items"][0]["payload"]["source_content"]["document_sha256"])
    )
    assert original["items"][0]["id"] == revised["items"][0]["id"]
    assert original["content_digest"] != revised["content_digest"]
    assert original["run_id"] != revised["run_id"]
