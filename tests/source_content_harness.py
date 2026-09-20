"""Offline harness for the four v2 two-stage Provider contracts.

Discovery documents are synthetic and carry only the verified production
container shape (RSS items, ``div#r_con`` style-font anchors, the
``div#sse_list_1`` definition list, and the SZSE embedded literals) with
test-controlled publication dates and locators. Detail documents are the
recorded official provider fixtures, so extraction always runs against real
markup. No harness path touches the network.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_ROOT = REPO_ROOT / "providers"

DISCOVERY_URLS = {
    "federal_reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "pboc": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
    "sse": "https://www.sse.com.cn/disclosure/announcement/general/s_list.shtml",
    "szse": "https://www.szse.cn/disclosure/notice/general/index.html",
}
DISCOVERY_FIXTURES = {
    "federal_reserve": "fixtures/press_all.xml",
    "pboc": "fixtures/index.html",
    "sse": "fixtures/s_list.shtml",
    "szse": "fixtures/index.html",
}
DETAIL_FIXTURES = {
    "federal_reserve": "fixtures/detail-monetary20260916a.htm",
    "pboc": "fixtures/detail-2026091815494839605.html",
    "sse": "fixtures/detail-c_20260918_10832703.shtml",
    "szse": "fixtures/detail-t20260917_622911.html",
}
V2_PROVIDERS = tuple(DISCOVERY_URLS)

#: The recorded detail locators, which the synthetic discovery documents reuse
#: so that every served detail body matches its canonical candidate URL.
DETAIL_URLS = {
    "federal_reserve": (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm"
    ),
    "pboc": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026091815494839605/index.html",
    "sse": "https://www.sse.com.cn/disclosure/announcement/general/jjzssgg/c/c_20260918_10832703.shtml",
    "szse": "https://www.szse.cn/disclosure/notice/general/t20260917_622911.html",
}


CANDIDATE_TEMPLATES = {
    "federal_reserve": (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary202608{day:02d}a.htm"
    ),
    "pboc": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026081020000{day:04d}/index.html",
    "sse": "https://www.sse.com.cn/disclosure/announcement/general/jjzssgg/c/c_20260810_{day}.shtml",
    "szse": "https://www.szse.cn/disclosure/notice/general/t20260810_{day}.html",
}
ARCHIVE_TEMPLATES = {
    "federal_reserve": (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary202607{day:02d}a.htm"
    ),
    "pboc": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026070120000{day:04d}/index.html",
    "sse": "https://www.sse.com.cn/disclosure/announcement/general/jjzssgg/c/c_20260701_{day}.shtml",
    "szse": "https://www.szse.cn/disclosure/notice/general/t20260701_{day}.html",
}


def candidate_url(provider_id: str, index: int) -> str:
    """A distinct synthetic in-window locator on the Provider's allowed host."""
    return CANDIDATE_TEMPLATES[provider_id].format(day=index + 1)


def archive_url(provider_id: str, index: int) -> str:
    """A distinct synthetic out-of-window locator on the allowed host."""
    return ARCHIVE_TEMPLATES[provider_id].format(day=index + 1)


def window_discovery(provider_id: str, window: Mapping[str, str], *, count: int = 1) -> bytes:
    """One in-window candidate per index plus the boundary-proving older entry.

    Exchange contracts need a trailing entry that predates the window so their
    sequential traversal can prove the boundary and stop.
    """
    start = datetime.fromisoformat(window["start"])
    end = datetime.fromisoformat(window["end"])
    if provider_id == "federal_reserve":
        published: object = end - timedelta(seconds=1)
        older: object = start - timedelta(days=1)
        noun = "release"
    else:
        published = (end - timedelta(days=1)).date().isoformat()
        older = (start - timedelta(days=1)).date().isoformat()
        noun = "notice"
    rows = [
        (f"Current {noun} {index}", candidate_url(provider_id, index), published)
        for index in range(count)
    ]
    rows.append(("Past the window", archive_url(provider_id, 0), older))
    return discovery_document(provider_id, rows)


def detail_bytes(provider_id: str) -> bytes:
    return (PROVIDER_ROOT / provider_id / DETAIL_FIXTURES[provider_id]).read_bytes()


def discovery_bytes(provider_id: str) -> bytes:
    return (PROVIDER_ROOT / provider_id / DISCOVERY_FIXTURES[provider_id]).read_bytes()


def rfc822(value: datetime) -> str:
    return format_datetime(value.astimezone(UTC))


def page_url(provider_id: str, page: int) -> str:
    """The declared sequential index locator for ``page`` (1-based)."""
    if page == 1:
        return DISCOVERY_URLS[provider_id]
    if provider_id == "sse":
        return f"https://www.sse.com.cn/disclosure/announcement/general/s_list_{page}.shtml"
    if provider_id == "szse":
        return f"https://www.szse.cn/disclosure/notice/general/index_{page - 1}.html"
    raise NotImplementedError(provider_id)


def discovery_locators(provider_id: str) -> set[str]:
    if provider_id in {"sse", "szse"}:
        return {page_url(provider_id, page) for page in range(1, 12)}
    return {DISCOVERY_URLS[provider_id]}


def _rss(entries: list[tuple[str, str, datetime, str | None]]) -> bytes:
    items = "\n".join(
        f"<item><title>{title}</title><link>{url}</link>"
        + (f"<guid isPermaLink='false'>{guid}</guid>" if guid else "")
        + f"<pubDate>{rfc822(published)}</pubDate></item>"
        for title, url, published, guid in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>synthetic</title>{items}</channel></rss>"
    ).encode()


def _pboc(entries: list[tuple[str, str, str]]) -> bytes:
    rows = "\n".join(
        "<tr><td height='22' align='left'>"
        '<font class="newslist_style" style="margin-right:10px;">'
        f'<a href="{url}" onclick="void(0)" target="_blank" title="{title}" '
        f'istitle="true">{title}</a></font>'
        f'<span class="hui12">{published}</span></td></tr>'
        for title, url, published in entries
    )
    return (
        "<!doctype html><html><body>"
        '<div id="r_con" class="column"><table><tbody>'
        f"{rows}"
        "</tbody></table></div></body></html>"
    ).encode()


def _sse(entries: list[tuple[str, str, str]]) -> bytes:
    rows = "\n".join(
        f"<dd><span>{published}</span>"
        f'<a href="{url}" title="{title}" target="_blank">{title}</a></dd>'
        for title, url, published in entries
    )
    return (
        "<!doctype html><html><body>"
        '<div class="sse_list_1 js_listPage" id="sse_list_1">'
        f"<dl>{rows}</dl></div></body></html>"
    ).encode()


def _szse(entries: list[tuple[str, str, str]]) -> bytes:
    rows = "\n".join(
        f'<li><div class="title"><script>\n'
        f"    var curHref = '{url}';\n"
        f"    var curTitle = '{title}';\n"
        "</script></div>"
        f'<span class="time">{published}</span></li>'
        for title, url, published in entries
    )
    return (
        f'<!doctype html><html><body><ul class="newslist date-right">{rows}</ul></body></html>'
    ).encode()


def discovery_document(
    provider_id: str,
    entries: list[tuple[str, str, object]],
    *,
    guid: bool = True,
) -> bytes:
    """Build one synthetic discovery document with the verified container shape."""
    if provider_id == "federal_reserve":
        return _rss(
            [
                (title, url, published, url if guid else None)  # type: ignore[arg-type]
                for title, url, published in entries
            ]
        )
    text_rows = [(title, url, str(published)) for title, url, published in entries]
    return {"pboc": _pboc, "sse": _sse, "szse": _szse}[provider_id](text_rows)


class SourceContentFixtureClient:
    """Serves scripted discovery pages and detail responses by URL."""

    def __init__(
        self,
        provider_id: str,
        *,
        pages: dict[str, bytes] | None = None,
        detail: bytes | None = None,
        failures: dict[str, int] | object | None = None,
        response_urls: dict[str, str] | None = None,
        content_type: str = "text/html",
    ) -> None:
        self.provider_id = provider_id
        self.pages = pages if pages is not None else {}
        self.detail = detail if detail is not None else detail_bytes(provider_id)
        self.failures = failures or {}
        self.response_urls = response_urls or {}
        self.content_type = content_type
        self.requests: list[str] = []
        self.last_response_at = None
        self.successful_resource_observed = False

    def get(self, url, headers=None, timeout=None, follow_redirects=True):
        from tests.test_adapters import FakeResponse

        self.requests.append(url)
        failure = self.failures.get(url) if isinstance(self.failures, dict) else None
        if isinstance(failure, BaseException):
            raise failure
        if isinstance(failure, int):
            return FakeResponse(b"", failure, "text/html", url=url)
        # Every served response is a successful managed send, which is the
        # observed-acquisition-progress fact the orchestration reads.
        self.successful_resource_observed = True
        if url in self.pages:
            return FakeResponse(self.pages[url], 200, "text/html", url=url)
        if url in discovery_locators(self.provider_id):
            raise AssertionError(f"unscripted discovery page requested: {url}")
        return FakeResponse(
            self.detail,
            200,
            self.content_type,
            url=self.response_urls.get(url, url),
        )

    @property
    def discovery_requests(self) -> list[str]:
        discovery = discovery_locators(self.provider_id)
        return [url for url in self.requests if url in discovery]

    @property
    def detail_requests(self) -> list[str]:
        discovery = discovery_locators(self.provider_id)
        return [url for url in self.requests if url not in discovery]
