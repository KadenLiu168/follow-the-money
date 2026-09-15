"""Task 3.3-3.14 — adapter fixture tests (the eight credential-free Feed Providers).

Uses synthetic fixtures and injected clients only; never touches the network.
Covers supported policy/release/HTML-index date parsing cases, invalid responses,
URL provider-bound validation, and empty-window behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.config.model import FetchRule
from follow_the_money.providers.adapters import (
    BlsAdapter,
    CftcAdapter,
    FedAdapter,
    NbsAdapter,
    PbocAdapter,
    SecEdgarAdapter,
)
from follow_the_money.providers.http import FetchError, bounded_fetch
from follow_the_money.providers.urls import UrlValidationError

NOW = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)
WINDOW = {"start": (NOW - timedelta(hours=72)).isoformat(), "end": NOW.isoformat()}
CFTC_WINDOW = {"start": "2026-08-01T00:20:00Z", "end": NOW.isoformat()}


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        status: int = 200,
        content_type: str | None = None,
        url: str = "https://www.federalreserve.gov/feeds/press_all.xml",
        headers: dict[str, str] | None = None,
    ):
        self.content = body
        self.body_bytes = body
        self.status_code = status
        self._headers = headers or ({"content-type": content_type} if content_type else {})
        self.url = url

    @property
    def headers(self):
        return self._headers

    def json(self):
        import json

        return json.loads(self.body_bytes.decode("utf-8"))


class FakeClient:
    def __init__(self, body: bytes, status: int = 200, content_type: str | None = None):
        self.body = body
        self.status = status
        self.content_type = content_type
        self.requests: list[str] = []
        self.request_headers: list[dict[str, str] | None] = []

    def get(self, url, headers=None, timeout=None, follow_redirects=True):
        self.requests.append(url)
        self.request_headers.append(dict(headers) if headers is not None else None)
        if self.status == 500:
            raise ConnectionError("boom")
        return FakeResponse(self.body, self.status, self.content_type, url=url)


def _rss_feed(entries: list[tuple[str, str, str]]) -> bytes:
    """Build a minimal RSS 2.0 feed from (title, link, pubDate) tuples."""
    items = "\n".join(
        f"<item><title>{t}</title><link>{l}</link><pubDate>{p}</pubDate>"
        f"<guid isPermaLink='false'>{l}</guid></item>"
        for t, l, p in entries
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>test</title>{items}</channel></rss>"
    ).encode()


# ---------------------------------------------------------------------------
# Fed
# ---------------------------------------------------------------------------


def test_fed_normalize_valid_policy_items():
    pub = (NOW - timedelta(minutes=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    body = _rss_feed(
        [
            (
                "Fed Statement",
                "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260811a.htm",
                pub,
            )
        ]
    )
    adapter = FedAdapter()
    items = adapter.normalize(FakeResponse(body), WINDOW)
    assert len(items) == 1
    assert items[0]["payload"]["type"] == "policy"
    assert items[0]["source"]["url"].startswith("https://www.federalreserve.gov/")
    assert items[0]["source"]["tier"] == "Tier 1"


def test_fed_rejects_off_manifest_url():
    pub = (NOW - timedelta(minutes=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    body = _rss_feed([("Bad Link", "https://evil.example.com/x", pub)])
    adapter = FedAdapter()
    with pytest.raises(UrlValidationError):
        adapter.normalize(FakeResponse(body), WINDOW)


def test_fed_invalid_rss_raises():
    adapter = FedAdapter()
    with pytest.raises(FetchError):
        adapter.normalize(FakeResponse(b"<html>not rss</html>"), WINDOW)


def test_fed_empty_feed_ok():
    body = _rss_feed([])
    adapter = FedAdapter()
    assert adapter.normalize(FakeResponse(body), WINDOW) == []


def test_rss_normalize_uses_half_open_knowledge_window():
    before = (NOW - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    at_cutoff = NOW.strftime("%a, %d %b %Y %H:%M:%S +0000")
    body = _rss_feed(
        [
            (
                "In window",
                "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260811a.htm",
                before,
            ),
            (
                "At cutoff",
                "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260811b.htm",
                at_cutoff,
            ),
        ]
    )
    items = FedAdapter().normalize(FakeResponse(body), WINDOW)
    assert [item["payload"]["title"] for item in items] == ["In window"]


def test_fed_transport_failure_typed():
    adapter = FedAdapter()
    with pytest.raises(FetchError, match="fetch failed"):
        adapter.fetch(WINDOW, FakeClient(b"", status=500))


def test_shared_fetch_uses_resolved_provider_user_agent():
    adapter = FedAdapter()
    client = FakeClient(b"{}")

    adapter.fetch(WINDOW, client)

    assert client.request_headers == [{"User-Agent": adapter._contract.user_agent}]


def test_shared_fetch_merges_non_identity_headers_and_rejects_case_variants():
    adapter = FedAdapter()
    client = FakeClient(b"{}")

    adapter._fetch(
        client,
        "https://www.federalreserve.gov/feeds/press_all.xml",
        headers={"X-Trace": "fixture", "user-agent": "caller", "uSeR-aGeNt": "override"},
    )

    assert client.request_headers == [
        {"X-Trace": "fixture", "User-Agent": adapter._contract.user_agent}
    ]


def test_bounded_fetch_rejects_non_success_status_and_preserves_retry_after():
    class StatusClient:
        def get(self, url, **kwargs):
            return FakeResponse(
                b"busy",
                status=429,
                url=url,
                headers={"retry-after": "17"},
            )

    with pytest.raises(FetchError, match="HTTP 429") as exc_info:
        bounded_fetch(
            StatusClient(),
            "https://www.federalreserve.gov/feeds/press_all.xml",
            fetch_rules=[
                FetchRule("federalreserve.gov", allow_subdomains=True, allowed_ports=(443,))
            ],
            redirect_rules=[
                FetchRule("federalreserve.gov", allow_subdomains=True, allowed_ports=(443,))
            ],
        )
    error = exc_info.value
    assert error.status_code == 429
    assert error.retry_after_seconds == 17
    assert error.retryable


def test_bounded_fetch_does_not_retry_arbitrary_client_exception():
    class BuggyClient:
        def get(self, url, **kwargs):
            raise RuntimeError("client programming error")

    with pytest.raises(FetchError, match="fetch failed") as exc_info:
        bounded_fetch(
            BuggyClient(),
            "https://www.federalreserve.gov/feeds/press_all.xml",
            fetch_rules=[
                FetchRule("federalreserve.gov", allow_subdomains=True, allowed_ports=(443,))
            ],
            redirect_rules=[
                FetchRule("federalreserve.gov", allow_subdomains=True, allowed_ports=(443,))
            ],
        )
    assert not exc_info.value.retryable


def test_bounded_fetch_rejects_redirect_outside_manifest():
    class RedirectClient:
        def get(self, url, **kwargs):
            return FakeResponse(b"redirected", url="https://evil.example/response")

    with pytest.raises(FetchError, match="redirect_url outside"):
        bounded_fetch(
            RedirectClient(),
            "https://www.federalreserve.gov/feeds/press_all.xml",
            fetch_rules=[
                FetchRule("federalreserve.gov", allow_subdomains=True, allowed_ports=(443,))
            ],
            redirect_rules=[
                FetchRule("federalreserve.gov", allow_subdomains=True, allowed_ports=(443,))
            ],
        )


# ---------------------------------------------------------------------------
# BLS
# ---------------------------------------------------------------------------


def test_bls_normalize_valid_news():
    pub = (NOW - timedelta(minutes=1)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    body = _rss_feed([("CPI Release", "https://www.bls.gov/news.release/cpi.nr0.htm", pub)])
    adapter = BlsAdapter()
    items = adapter.normalize(FakeResponse(body), CFTC_WINDOW)
    assert len(items) == 1
    assert items[0]["payload"]["type"] == "news"
    assert items[0]["source"]["url"].startswith("https://www.bls.gov/")


def test_bls_empty_window():
    adapter = BlsAdapter()
    assert adapter.normalize(FakeResponse(_rss_feed([])), WINDOW) == []


# ---------------------------------------------------------------------------
# SEC
# ---------------------------------------------------------------------------


def test_sec_manifest_requires_user_agent():
    from follow_the_money.providers.manifest import load_manifest

    manifest = load_manifest("sec_edgar")
    assert manifest["user_agent"]  # EDGAR requires a descriptive UA
    assert "kaden@" in manifest["user_agent"]


def test_sec_fetch_uses_json_submissions_endpoint():
    adapter = SecEdgarAdapter(watched_ciks=("0001067983",))
    client = FakeClient(b"{}")

    adapter.fetch(WINDOW, client)

    assert client.requests == ["https://data.sec.gov/submissions/CIK0001067983.json"]
    assert client.request_headers == [{"User-Agent": adapter._contract.user_agent}]


def test_sec_normalize_filters_filing_date_at_cutoff():
    body = {
        "filings": {
            "recent": {
                "form": ["13F-HR", "13F-HR"],
                "filingDate": ["2026-08-10", "2026-08-11"],
                "accessionNumber": ["0001067983-26-000001", "0001067983-26-000002"],
                "primaryDocument": ["one.xml", "two.xml"],
                "cik": ["0001067983", "0001067983"],
            }
        }
    }
    response = FakeResponse(__import__("json").dumps(body).encode())
    items = SecEdgarAdapter(watched_ciks=("0001067983",)).normalize(response, WINDOW)
    assert [item["payload"]["accession_number"] for item in items] == ["0001067983-26-000001"]


def test_nbs_html_index_is_supported():
    body = b"""
    <html><body><ul>
      <li><a href='/sj/zxfb/202608/t20260810_1.html'>2026-08-10 industrial production</a></li>
    </ul></body></html>
    """
    response = FakeResponse(body)
    response.url = "https://www.stats.gov.cn/sj/zxfb/index.html"
    items = NbsAdapter().normalize(response, WINDOW)
    assert len(items) == 1
    assert items[0]["source"]["url"] == "https://www.stats.gov.cn/sj/zxfb/202608/t20260810_1.html"
    assert items[0]["payload"]["type"] == "news"


@pytest.mark.parametrize(
    ("adapter", "fixture", "base_url", "titles"),
    [
        (
            PbocAdapter(),
            "pboc-index.html",
            "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
            [
                "2026年8月10日 货币政策公告",
                "2026-02-30 2026-08-09 公开市场公告",
                "政策公告",
                "统计公告",
            ],
        ),
        (
            NbsAdapter(),
            "nbs-index.html",
            "https://www.stats.gov.cn/sj/zxfb/index.html",
            [
                "2026年8月10日 国民经济统计发布",
                "2026-02-30 2026-08-09 统计公报",
                "统计发布",
                "统计数据",
            ],
        ),
    ],
)
def test_production_shaped_html_indexes_skip_invalid_candidates_and_keep_first_valid(
    adapter, fixture, base_url, titles
):
    response = FakeResponse(
        (Path(__file__).parent / "fixtures" / "provider-indexes" / fixture).read_bytes(),
    )
    response.url = base_url

    items = adapter.normalize(response, WINDOW)

    assert [item["payload"]["title"] for item in items] == titles
    assert [item["source"]["published_at"] for item in items] == [
        "2026-08-10T00:00:00.000Z",
        "2026-08-09T00:00:00.000Z",
        "2026-08-11T00:00:00.000Z",
        "2026-08-11T00:00:00.000Z",
    ]


def test_html_index_undecodable_response_remains_typed_fetch_failure():
    response = FakeResponse(b"\xff")
    response.url = "https://www.stats.gov.cn/sj/zxfb/index.html"

    with pytest.raises(FetchError, match="not decodable"):
        NbsAdapter().normalize(response, WINDOW)


def test_sec_unknown_response_is_empty():
    adapter = SecEdgarAdapter()
    assert adapter.normalize(FakeResponse(b"{}"), WINDOW) == []


def test_cftc_fetch_and_normalize_positioning_fixture():
    body = (
        b"["
        b'{"id":"cot-1","market_and_exchange_names":"GOLD - COMMODITY EXCHANGE, INC.",'
        b'"report_date_as_yyyy_mm_dd":"2026-08-04T00:00:00.000",'
        b'"cftc_contract_market_code":"088691",'
        b'"contract_market_name":"GOLD","open_interest_all":"455123",'
        b'"noncomm_positions_long_all":"245,678",'
        b'"noncomm_positions_short_all":"198765",'
        b'"noncomm_positions_spread_all":"1234"}'
        b"]"
    )
    client = FakeClient(body)
    adapter = CftcAdapter()
    raw = adapter.fetch(WINDOW, client)
    assert len(client.requests) == 2
    assert "$select=report_date_as_yyyy_mm_dd" in client.requests[0]
    items = adapter.normalize(raw, CFTC_WINDOW)
    assert len(items) == 1
    payload = items[0]["payload"]
    assert payload["type"] == "positioning"
    assert payload["instrument_id"] == "GOLD"
    assert payload["position"] == {"value": "245678", "unit": "contracts"}
    assert payload["as_of"] == "2026-08-04T00:00:00.000Z"
    assert items[0]["source"]["knowledge_available_at"] == "2026-08-07T19:30:00.000Z"


def test_cftc_invalid_numeric_value_fails_closed():
    raw = {
        "current_date": "2026-08-04",
        "previous_date": None,
        "current_rows": [
            {
                "id": "cot-1",
                "cftc_contract_market_code": "088691",
                "contract_market_name": "GOLD",
                "report_date_as_yyyy_mm_dd": "2026-08-04",
                "open_interest_all": "455123",
                "noncomm_positions_long_all": "not-a-number",
                "noncomm_positions_short_all": "198765",
                "noncomm_positions_spread_all": "1234",
            }
        ],
        "previous_rows": None,
    }
    from follow_the_money.providers.cftc_cot import CotError

    with pytest.raises(CotError, match="numeric field is invalid"):
        CftcAdapter().normalize(raw, CFTC_WINDOW)


# ---------------------------------------------------------------------------
# Manifest/registry invariants
# ---------------------------------------------------------------------------


def test_production_sec_uses_one_acquisition_unit_per_watched_company():
    from follow_the_money.config import load_config
    from follow_the_money.feed.cli import _production_adapters
    from follow_the_money.providers.adapters import build_registry

    cfg = load_config(
        Path(__file__).parents[1] / "config" / "config.yaml",
        Path(__file__).parents[1] / "config" / "providers.yaml",
        manifest_root=Path(__file__).parents[1] / "providers",
        require_verified_enabled=True,
    )
    adapters = _production_adapters(cfg, build_registry({p.id: p for p in cfg.providers}))
    assert len(adapters["sec_edgar"]) == len(cfg.watched_companies)
    assert {adapter.provider_id for adapter in adapters["sec_edgar"]} == {"sec_edgar"}
    assert [adapter._watched_company.cik for adapter in adapters["sec_edgar"]] == sorted(
        company.cik for company in cfg.watched_companies
    )


def test_all_manifests_load_and_provider_id_matches():
    from follow_the_money.providers.manifest import load_all_manifests

    manifests = load_all_manifests()
    assert set(manifests) == {
        "federal_reserve",
        "bls",
        "sec_edgar",
        "cftc",
        "pboc",
        "nbs",
        "sse",
        "szse",
    }
    for pid, m in manifests.items():
        assert m["provider_id"] == pid
        assert m["contract_version"] == (2 if pid in {"sec_edgar", "cftc"} else 1)


def test_no_manifest_claims_verified_without_date():
    from follow_the_money.providers.manifest import load_all_manifests

    for m in load_all_manifests().values():
        if m["verification"]["verified"]:
            assert m["verification"]["verification_date"] is not None


def test_manifest_entries_are_credential_free_and_closed():
    from follow_the_money.providers.manifest import load_all_manifests, manifest_to_provider_entry

    for pid, manifest in load_all_manifests().items():
        entry = manifest_to_provider_entry(manifest)
        assert entry.id == pid
        assert entry.authentication == "none"
        assert set(entry.payload_types) <= {
            "news",
            "macro_release",
            "policy",
            "positioning",
            "filing",
        }


def test_cftc_v2_paginates_pinned_current_and_previous_dates_in_order():
    discovery = (
        b'[{"report_date_as_yyyy_mm_dd":"2026-08-04"},{"report_date_as_yyyy_mm_dd":"2026-07-28"}]'
    )
    current = (
        b'[{"id":"current-1","report_date_as_yyyy_mm_dd":"2026-08-04",'
        b'"cftc_contract_market_code":"001","contract_market_name":"X",'
        b'"noncomm_positions_long_all":"10","noncomm_positions_short_all":"4",'
        b'"noncomm_positions_spread_all":"2","open_interest_all":"100"}]'
    )
    previous = (
        b'[{"id":"previous-1","report_date_as_yyyy_mm_dd":"2026-07-28",'
        b'"cftc_contract_market_code":"001","contract_market_name":"X",'
        b'"noncomm_positions_long_all":"9","noncomm_positions_short_all":"3",'
        b'"noncomm_positions_spread_all":"1","open_interest_all":"90"}]'
    )

    class Pages:
        def __init__(self):
            self.responses = [discovery, current, previous]
            self.urls: list[str] = []

        def get(self, url, **_kwargs):
            self.urls.append(url)
            body = self.responses.pop(0)
            return FakeResponse(body, url=url)

    client = Pages()
    adapter = CftcAdapter()
    raw = adapter.fetch(WINDOW, client)
    items = adapter.normalize(raw, CFTC_WINDOW)
    assert len(client.urls) == 3
    assert "$select=report_date_as_yyyy_mm_dd" in client.urls[0]
    assert all("$limit=100" in url and "$offset=0" in url for url in client.urls[1:])
    assert items[0]["payload"]["comparison"]["status"] == "available"
    assert items[0]["payload"]["delta_metrics"]["net_noncommercial"] == {
        "value": "0",
        "unit": "contracts",
    }


def test_cftc_v2_first_resource_denial_is_typed_and_later_page_denial_is_typed():
    class Denied:
        def __init__(self, statuses):
            self.statuses = list(statuses)

        def get(self, url, **_kwargs):
            return FakeResponse(b"[]", status=self.statuses.pop(0), url=url)

    with pytest.raises(FetchError, match="HTTP 403"):
        CftcAdapter().fetch(WINDOW, Denied([403]))

    class DiscoveryThenDenied:
        def __init__(self):
            self.responses = [
                FakeResponse(
                    b'[{"report_date_as_yyyy_mm_dd":"2026-08-04"}]',
                    url="https://publicreporting.cftc.gov/a",
                ),
                FakeResponse(b"", status=403, url="https://publicreporting.cftc.gov/b"),
            ]

        def get(self, url, **_kwargs):
            return self.responses.pop(0)

    with pytest.raises(FetchError, match="HTTP 403"):
        CftcAdapter().fetch(WINDOW, DiscoveryThenDenied())


def test_cftc_v2_rejects_pinned_page_with_wrong_report_date():
    class WrongPage:
        def __init__(self):
            self.responses = [
                b'[{"report_date_as_yyyy_mm_dd":"2026-08-04"}]',
                (
                    b'[{"id":"wrong","report_date_as_yyyy_mm_dd":"2026-07-28",'
                    b'"cftc_contract_market_code":"001","contract_market_name":"X",'
                    b'"noncomm_positions_long_all":"1","noncomm_positions_short_all":"1",'
                    b'"noncomm_positions_spread_all":"0","open_interest_all":"1"}]'
                ),
            ]

        def get(self, url, **_kwargs):
            return FakeResponse(self.responses.pop(0), url=url)

    with pytest.raises(FetchError, match="pinned query"):
        CftcAdapter().fetch(WINDOW, WrongPage())
