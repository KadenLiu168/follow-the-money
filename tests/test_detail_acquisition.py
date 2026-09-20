"""Bounded detail-document acquisition regressions.

The detail path reuses the existing managed-send boundary: it adds only an
explicit document byte bound and final-canonical-URL equality. Every request
still carries the manifest-owned user agent and attempt timeout, still passes
the fetch/redirect host allowlists, and still reports an observed response.
"""

from __future__ import annotations

from typing import Any

import pytest

from follow_the_money.providers.adapters import FedAdapter
from follow_the_money.providers.http import FetchError

CANDIDATE = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm"
DISCOVERY_URL = "https://www.federalreserve.gov/feeds/press_all.xml"


class FakeResponse:
    def __init__(
        self, body: bytes, *, url: str, status: int = 200, content_type: str = "text/html"
    ):
        self.content = body
        self.body_bytes = body
        self.status_code = status
        self.url = url
        self._headers = {"content-type": content_type}

    @property
    def headers(self):
        return self._headers


class FakeClient:
    """Records every request and replays one scripted response."""

    def __init__(self, response: FakeResponse):
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self._response


@pytest.fixture
def adapter() -> FedAdapter:
    return FedAdapter()


def _bound(adapter: FedAdapter) -> int:
    content = adapter._contract.source_content
    assert content is not None
    return content.max_document_bytes


def test_detail_acquisition_uses_the_declared_document_bound(adapter: FedAdapter):
    document_bound = _bound(adapter)
    assert document_bound < adapter._contract.response_limit_bytes

    oversized = FakeClient(FakeResponse(b"x" * (document_bound + 1), url=CANDIDATE))
    with pytest.raises(FetchError, match="exceeds"):
        adapter._fetch_detail(oversized, CANDIDATE, max_bytes=document_bound)
    assert oversized.calls[0]["url"] == CANDIDATE

    admitted = FakeClient(FakeResponse(b"x" * document_bound, url=CANDIDATE))
    result = adapter._fetch_detail(admitted, CANDIDATE, max_bytes=document_bound)
    assert result.body_bytes == b"x" * document_bound


def test_detail_acquisition_preserves_managed_request_shape(adapter: FedAdapter):
    client = FakeClient(FakeResponse(b"<html></html>", url=CANDIDATE))
    adapter._fetch_detail(client, CANDIDATE, max_bytes=_bound(adapter))

    call = client.calls[0]
    assert call["headers"]["User-Agent"] == adapter._contract.user_agent
    assert call["timeout"] == adapter._contract.attempt_timeout_seconds
    assert call["follow_redirects"] is True


def test_detail_acquisition_requires_final_canonical_url_equality(adapter: FedAdapter):
    document_bound = _bound(adapter)

    # An allowlisted redirect that changes the document locator changes identity.
    moved = FakeClient(FakeResponse(b"<html></html>", url="https://federalreserve.gov/other.htm"))
    with pytest.raises(FetchError, match="changed the canonical source URL"):
        adapter._fetch_detail(moved, CANDIDATE, max_bytes=document_bound)

    # A canonical-preserving response is admitted.
    same = FakeClient(FakeResponse(b"<html></html>", url=CANDIDATE))
    assert adapter._fetch_detail(same, CANDIDATE, max_bytes=document_bound).url == CANDIDATE

    # An undeclared redirect host is rejected by the redirect allowlist first.
    elsewhere = FakeClient(FakeResponse(b"<html></html>", url="https://example.com/moved.htm"))
    with pytest.raises(FetchError, match="redirect_url"):
        adapter._fetch_detail(elsewhere, CANDIDATE, max_bytes=document_bound)


def test_detail_acquisition_reports_observed_responses_and_host_allowlist(adapter: FedAdapter):
    document_bound = _bound(adapter)

    blocked = FakeClient(FakeResponse(b"", url=CANDIDATE, status=403))
    with pytest.raises(FetchError) as failure:
        adapter._fetch_detail(blocked, CANDIDATE, max_bytes=document_bound)
    assert failure.value.status_code == 403
    assert failure.value.response_observed is True

    undeclared = "https://example.com/not-allowed.htm"
    with pytest.raises(FetchError, match="fetch_url"):
        adapter._fetch_detail(
            FakeClient(FakeResponse(b"", url=undeclared)), undeclared, max_bytes=1024
        )


def test_discovery_fetch_keeps_the_provider_response_limit(adapter: FedAdapter):
    """The default discovery fetch is unchanged by the detail override."""
    client = FakeClient(
        FakeResponse(
            b"<rss version='2.0'><channel></channel></rss>",
            url=DISCOVERY_URL,
            content_type="application/xml",
        )
    )
    result = adapter._fetch(client, DISCOVERY_URL)
    assert result.status == 200
    assert client.calls[0]["url"] == DISCOVERY_URL
    assert adapter._contract.response_limit_bytes == 10485760
