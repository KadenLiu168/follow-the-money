"""Task 3.3-3.14 — adapter fixture tests (Fed, BLS, SEC, Yahoo).

Uses synthetic fixtures and injected clients only; never touches the network.
Covers supported policy/release/calendar/macro cases, invalid responses,
URL provider-bound validation, and empty-window behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from follow_the_money.config.model import FetchRule
from follow_the_money.providers.adapters import (
    BlsAdapter,
    CftcAdapter,
    FedAdapter,
    NbsAdapter,
    PbocAdapter,
    SecEdgarAdapter,
    YahooMarketAdapter,
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
            fetch_rules=[FetchRule("federalreserve.gov", allow_subdomains=True)],
            redirect_rules=[FetchRule("federalreserve.gov", allow_subdomains=True)],
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
            fetch_rules=[FetchRule("federalreserve.gov", allow_subdomains=True)],
            redirect_rules=[FetchRule("federalreserve.gov", allow_subdomains=True)],
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
            fetch_rules=[FetchRule("federalreserve.gov", allow_subdomains=True)],
            redirect_rules=[FetchRule("federalreserve.gov", allow_subdomains=True)],
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


def test_yahoo_role_unit_and_availability_time_are_preserved():
    body = (
        __import__("json")
        .dumps(
            {
                "chart": {
                    "result": [
                        {
                            "timestamp": [1786118400],
                            "indicators": {"quote": [{"close": [110.5]}]},
                        }
                    ]
                }
            }
        )
        .encode()
    )
    item = YahooMarketAdapter(instrument="^TNX", role_id="us10y", unit="percent").normalize(
        FakeResponse(body), WINDOW
    )[0]
    observation = item["payload"]["observations"][0]
    assert observation["unit"] == "percent"
    assert item["source"]["knowledge_available_at"] == "2026-08-11T00:20:00.000Z"
    assert observation["available_at"] is None


def test_yahoo_fetch_requests_explicit_cutoff_bounded_daily_history():
    client = FakeClient(b"{}")
    adapter = YahooMarketAdapter(instrument="^GSPC", role_id="sp500")
    end = "2026-08-11T00:20:00Z"
    adapter.fetch({"start": "2026-08-01T00:00:00Z", "end": end}, client)
    assert len(client.requests) == 1
    query = parse_qs(urlsplit(client.requests[0]).query)
    assert query["interval"] == ["1d"]
    assert int(query["period2"][0]) == int(datetime.fromisoformat(end).timestamp())
    assert int(query["period2"][0]) - int(query["period1"][0]) == 90 * 24 * 60 * 60


def test_yahoo_normalize_enforces_260_chronological_observations():
    import json

    start = datetime(2025, 1, 1, tzinfo=UTC)
    body = json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "timestamp": [
                            int((start + timedelta(days=i)).timestamp()) for i in range(300)
                        ],
                        "indicators": {"quote": [{"close": [str(i + 1) for i in range(300)]}]},
                    }
                ]
            }
        }
    ).encode()
    items = YahooMarketAdapter(instrument="^GSPC", role_id="sp500").normalize(
        FakeResponse(body), {"start": "2025-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"}
    )
    observations = items[0]["payload"]["observations"]
    assert len(observations) == 260
    assert [o["as_of"] for o in observations] == sorted(o["as_of"] for o in observations)


def test_yahoo_normalize_preserves_bar_for_session_aware_eligibility():
    import json

    partial = int((NOW - timedelta(seconds=299)).timestamp())
    complete = int((NOW - timedelta(seconds=301)).timestamp())
    body = json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "timestamp": [partial, complete],
                        "indicators": {"quote": [{"close": ["101", "100"]}]},
                    }
                ]
            }
        }
    ).encode()
    items = YahooMarketAdapter(instrument="^GSPC", role_id="sp500").normalize(
        FakeResponse(body), {"start": "2026-08-10T00:00:00Z", "end": NOW.isoformat()}
    )
    assert [row["value"] for row in items[0]["payload"]["observations"]] == ["100", "101"]
    assert all(row["available_at"] is None for row in items[0]["payload"]["observations"])


def test_sec_unknown_response_is_empty():
    adapter = SecEdgarAdapter()
    assert adapter.normalize(FakeResponse(b"{}"), WINDOW) == []


def test_cftc_fetch_and_normalize_positioning_fixture():
    body = (
        b"["
        b'{"id":"cot-1","market_and_exchange_names":"GOLD - COMMODITY EXCHANGE, INC.",'
        b'"report_date_as_yyyy_mm_dd":"2026-08-04T00:00:00.000",'
        b'"contract_market_name":"GOLD","open_interest_all":"455123",'
        b'"noncomm_positions_long_all":"245,678",'
        b'"noncomm_positions_short_all":"198765"}'
        b"]"
    )
    client = FakeClient(body)
    adapter = CftcAdapter()
    adapter.fetch(WINDOW, client)
    assert client.requests == [
        "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=100"
    ]
    items = adapter.normalize(FakeResponse(body), CFTC_WINDOW)
    assert len(items) == 1
    payload = items[0]["payload"]
    assert payload["type"] == "positioning"
    assert payload["instrument_id"] == "GOLD"
    assert payload["position"] == {"value": "245678", "unit": "contracts"}
    assert payload["as_of"] == "2026-08-04T00:00:00.000Z"
    assert items[0]["source"]["knowledge_available_at"] == "2026-08-07T19:30:00.000Z"


def test_cftc_invalid_numeric_value_fails_closed():
    body = (
        b'[{"id":"cot-1","contract_market_name":"GOLD",'
        b'"report_date_as_yyyy_mm_dd":"2026-08-04T00:00:00.000",'
        b'"noncomm_positions_long_all":"not-a-number"}]'
    )
    with pytest.raises(FetchError, match="numeric value is invalid"):
        CftcAdapter().normalize(FakeResponse(body), CFTC_WINDOW)


# ---------------------------------------------------------------------------
# Manifest/registry invariants
# ---------------------------------------------------------------------------


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
        "yahoo_market",
    }
    for pid, m in manifests.items():
        assert m["provider_id"] == pid
        assert m["contract_version"] == 1


def test_no_manifest_claims_verified_without_date():
    from follow_the_money.providers.manifest import load_all_manifests

    for m in load_all_manifests().values():
        if m["verification"]["verified"]:
            assert m["verification"]["verification_date"] is not None


def test_verified_adapters_enabled_optional_disabled():
    # Gate 13.1: verified core adapters are enabled; verified-optional CFTC
    # keeps a default-disabled manifest fallback (shipped activation lives in
    # config/providers.yaml, which this manifest-level seam never sees).
    from follow_the_money.providers.manifest import load_all_manifests, manifest_to_provider_entry

    for pid, m in load_all_manifests().items():
        entry = manifest_to_provider_entry(m)
        if m["verification"]["verified"] and pid != "cftc":
            assert entry.enabled, f"{pid} verified and default-enabled"
            assert entry.verified
        else:
            assert not entry.enabled, f"{pid} must stay disabled"
