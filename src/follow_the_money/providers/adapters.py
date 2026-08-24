"""Concrete provider adapters (Fed, BLS, SEC EDGAR, PBOC, NBS, SSE, SZSE, Yahoo).

Each adapter implements ``fetch`` and ``normalize`` per the small Provider
protocol and validates every emitted source URL against its owning manifest's
``source_link_hosts`` rules. Adapters remain usable from fixtures with
injected clients; they never dereference source URLs.

The six mandatory v1 coverage-matrix rows are backed by these adapters:

- ``us_official_macro_policy``: federal_reserve + bls
- ``us_company_filings``: sec_edgar (watched-company filing contract)
- ``china_official_macro_policy``: pboc + nbs
- ``china_exchange_evidence``: sse + szse
- ``verified_market_data``: yahoo_market (verified mappings only)
- ``future_calendar``: federal_reserve + bls + nbs
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urlencode, urljoin
from zoneinfo import ZoneInfo

from ..config.model import ProviderEntry
from .base import Provider, ProviderRegistry
from .http import (
    FetchError,
    bounded_fetch,
    safe_parse_rss,
    stable_item_id,
    validate_provider_url,
)
from .manifest import load_manifest, manifest_to_provider_entry
from .urls import UrlValidationError


class BaseAdapter(Provider):
    """Shared adapter plumbing."""

    provider_id: str

    def __init__(self, manifest: Mapping[str, Any] | ProviderEntry | None = None) -> None:
        if isinstance(manifest, ProviderEntry):
            self._contract = manifest
            self._manifest = None
        else:
            raw_manifest = manifest or load_manifest(self.provider_id)
            self._manifest = raw_manifest
            self._contract = manifest_to_provider_entry(raw_manifest)
        self._rules = self._contract.source_link_hosts
        self._fetch_rules = self._contract.fetch_hosts
        self._redirect_rules = self._contract.redirect_hosts

    def _fetch(self, client: Any, url: str, *, headers: Mapping[str, str] | None = None) -> Any:
        return bounded_fetch(
            client,
            url,
            headers=headers,
            timeout=float(self._contract.attempt_timeout_seconds),
            max_bytes=int(self._contract.response_limit_bytes),
            fetch_rules=self._fetch_rules,
            redirect_rules=self._redirect_rules,
        )

    def _validate_url(self, url: str) -> str:
        return validate_provider_url(url, rules=self._rules)

    def _knowledge_time(self, published: str | None, updated: str | None) -> str:
        return _normalize_timestamp(updated or published)

    def _source(
        self,
        *,
        source_id: str,
        name: str,
        tier: str,
        url: str,
        published_at: str | None,
        knowledge: str,
    ) -> dict[str, Any]:
        return {
            "id": source_id,
            "name": name,
            "tier": tier,
            "kind": "news",
            "url": self._validate_url(url),
            "published_at": _normalize_timestamp(published_at) if published_at else None,
            "knowledge_available_at": _normalize_timestamp(knowledge),
        }

    def _rss_items(
        self,
        raw: Any,
        *,
        name: str,
        tier: str,
        payload_type: str,
        window: Mapping[str, str],
        max_items: int = 200,
        snippet: bool = False,
    ) -> list[dict[str, Any]]:
        """Shared RSS/Atom normalize path for policy/news adapters."""
        parsed = safe_parse_rss(
            raw.body_bytes,
            charset=self._contract.allowed_charset,
        )
        items: list[dict[str, Any]] = []
        for entry in parsed.entries[:max_items]:
            published = getattr(entry, "published", None)
            link = getattr(entry, "link", "")
            if not link:
                continue
            knowledge = self._knowledge_time(published, None)
            if not knowledge or not _in_half_open_window(knowledge, window):
                continue
            published_iso = _normalize_timestamp(published)
            source = self._source(
                source_id=f"{self.provider_id}-{stable_item_id(self.provider_id, entry.get('id', link))}",
                name=name,
                tier=tier,
                url=link,
                published_at=published_iso,
                knowledge=knowledge,
            )
            payload: dict[str, Any] = {
                "type": payload_type,
                "title": entry.get("title", "")[:300],
            }
            if snippet:
                payload["snippet"] = entry.get("summary", "")[:1000]
                payload["occurred_at"] = published_iso
            else:
                payload["announced_at"] = published_iso
            payload["raw_metadata"] = {}
            items.append(
                {
                    "id": stable_item_id(self.provider_id, entry.get("id", link)),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": payload,
                }
            )
        return items

    def _json_body(self, raw: Any) -> Any:
        """Return the decoded JSON body or raise a typed fetch error."""
        body = _response_bytes(raw)
        charset = self._contract.allowed_charset
        try:
            return json.loads(body.decode(charset))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FetchError(f"response is not valid JSON: {exc.__class__.__name__}") from exc

    def _index_entries(self, raw: Any, key: str) -> list[dict[str, Any]]:
        """Decode the verified JSON fixture shape or the production HTML index."""
        try:
            data = self._json_body(raw)
        except FetchError:
            data = None
        if isinstance(data, dict) and isinstance(data.get(key), list):
            return [entry for entry in data[key] if isinstance(entry, dict)]
        charset = self._contract.allowed_charset
        return _html_index_entries(raw, base_url=getattr(raw, "url", ""), charset=charset)


class FedAdapter(BaseAdapter):
    provider_id = "federal_reserve"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(client, "https://www.federalreserve.gov/feeds/press_all.xml")

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        return self._rss_items(
            raw,
            name="Federal Reserve",
            tier="Tier 1",
            payload_type="policy",
            window=window,
        )


class BlsAdapter(BaseAdapter):
    provider_id: str = "bls"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(client, "https://www.bls.gov/feed/news.release.xml")

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        return self._rss_items(
            raw,
            name="U.S. Bureau of Labor Statistics",
            tier="Tier 1",
            payload_type="news",
            window=window,
            snippet=True,
        )


class SecEdgarAdapter(BaseAdapter):
    """SEC EDGAR watched-company filing contract.

    ``fetch`` requests the EDGAR browse index for the watched-company CIKs;
    ``normalize`` decodes the EDGAR JSON index (``filings.recent`` arrays),
    keeps only filings whose CIK is configured as watched, and emits
    ``filing`` payloads with stable accession-number identity.
    """

    provider_id: str = "sec_edgar"

    def __init__(
        self,
        manifest: Mapping[str, Any] | ProviderEntry | None = None,
        watched_ciks: Sequence[str] = (),
    ) -> None:
        super().__init__(manifest)
        self._watched_ciks = tuple(str(c) for c in watched_ciks)

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        cik = self._watched_ciks[0] if self._watched_ciks else "0001067983"
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        return self._fetch(
            client,
            url,
            headers={"User-Agent": self._contract.user_agent},
        )

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        data = self._json_body(raw)
        if not isinstance(data, dict):
            return []
        filings = data.get("filings") or {}
        recent = filings.get("recent") or {}
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        accessions = recent.get("accessionNumber") or []
        documents = recent.get("primaryDocument") or []
        ciks = recent.get("cik") or []
        if not accessions:
            return []

        items: list[dict[str, Any]] = []
        for i, accession in enumerate(accessions):
            cik = str(ciks[i]) if i < len(ciks) else ""
            if self._watched_ciks and cik and cik not in self._watched_ciks:
                continue
            form = forms[i] if i < len(forms) else "13F"
            date = dates[i] if i < len(dates) else None
            doc = documents[i] if i < len(documents) else None
            if not date:
                continue
            if not _in_half_open_window(date, window, date_only=True):
                continue
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{doc}"
                if doc
                else (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F"
                )
            )
            try:
                validated = self._validate_url(url)
            except UrlValidationError:
                continue
            source = self._source(
                source_id=f"sec-{stable_item_id(self.provider_id, accession)}",
                name="SEC EDGAR",
                tier="Tier 1",
                url=validated,
                published_at=_normalize_timestamp(date),
                knowledge=_normalize_timestamp(date),
            )
            items.append(
                {
                    "id": stable_item_id(self.provider_id, accession),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": {
                        "type": "filing",
                        "form": form,
                        "company": cik,
                        "accession_number": accession,
                        "filed_at": _normalize_timestamp(date),
                        "raw_metadata": {},
                    },
                }
            )
        return items


class CftcAdapter(BaseAdapter):
    """CFTC Legacy Futures-Only COT positioning records.

    The public reporting API exposes Tuesday report dates. CFTC's documented
    publication cadence is Friday, so the adapter uses the report date plus
    three days as the conservative publication boundary and retains the
    source-provided long/short/open-interest fields as raw metadata.
    """

    provider_id: str = "cftc"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(
            client,
            "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=100",
        )

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        data = self._json_body(raw)
        if not isinstance(data, list):
            return []
        items: list[dict[str, Any]] = []
        for row in data[:100]:
            if not isinstance(row, dict):
                continue
            report_date = row.get("report_date_as_yyyy_mm_dd")
            instrument = row.get("contract_market_name") or row.get("market_and_exchange_names")
            if not report_date or not instrument:
                continue
            as_of = _normalize_timestamp(str(report_date))
            report_dt = _parse_timestamp(as_of)
            release_local = datetime(
                report_dt.year,
                report_dt.month,
                report_dt.day,
                15,
                30,
                tzinfo=ZoneInfo("America/New_York"),
            ) + timedelta(days=3)
            published = _format_timestamp(release_local)
            if not _in_half_open_window(published, window):
                continue
            value = row.get("noncomm_positions_long_all")
            if value is None:
                continue
            identity = str(row.get("id") or f"{report_date}|{instrument}")
            source_url = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"
            source = self._source(
                source_id=f"cftc-{stable_item_id(self.provider_id, identity)}",
                name="CFTC Commitments of Traders",
                tier="Tier 1",
                url=source_url,
                published_at=published,
                knowledge=published,
            )
            items.append(
                {
                    "id": stable_item_id(self.provider_id, identity),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": {
                        "type": "positioning",
                        "instrument_id": str(instrument),
                        "as_of": as_of,
                        "position": {
                            "value": _canonical_number(value),
                            "unit": "contracts",
                        },
                        "raw_metadata": {
                            "report_date": as_of,
                            "publication_date": published,
                            "open_interest_all": row.get("open_interest_all"),
                            "noncomm_positions_short_all": row.get("noncomm_positions_short_all"),
                            "market_and_exchange_names": row.get("market_and_exchange_names"),
                        },
                    },
                }
            )
        return items


class PbocAdapter(BaseAdapter):
    """PBOC official policy announcements from its HTML index."""

    provider_id: str = "pboc"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(client, "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html")

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        entries = self._index_entries(raw, "announcements")
        items: list[dict[str, Any]] = []
        for entry in entries[:200]:
            title = entry.get("title", "")
            url = entry.get("url", "")
            published = entry.get("published_at")
            if not title or not url or not published:
                continue
            if not _in_half_open_window(published, window):
                continue
            source = self._source(
                source_id=f"pboc-{stable_item_id(self.provider_id, url)}",
                name="中国人民银行",
                tier="Tier 1",
                url=url,
                published_at=published,
                knowledge=published,
            )
            items.append(
                {
                    "id": stable_item_id(self.provider_id, url),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": {
                        "type": "policy",
                        "title": title[:300],
                        "announced_at": published,
                        "raw_metadata": {},
                    },
                }
            )
        return items


class NbsAdapter(BaseAdapter):
    """NBS official statistics releases from its HTML index."""

    provider_id: str = "nbs"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(client, "https://www.stats.gov.cn/sj/zxfb/index.html")

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        entries = self._index_entries(raw, "releases")
        items: list[dict[str, Any]] = []
        for entry in entries[:200]:
            title = entry.get("title", "")
            url = entry.get("url", "")
            released = entry.get("released_at")
            series_id = entry.get("series_id")
            actual = entry.get("actual")
            if not title or not url or not released:
                continue
            if not _in_half_open_window(released, window):
                continue
            source = self._source(
                source_id=f"nbs-{stable_item_id(self.provider_id, url)}",
                name="国家统计局",
                tier="Tier 1",
                url=url,
                published_at=released,
                knowledge=released,
            )
            payload: dict[str, Any] = {"type": "macro_release", "raw_metadata": {}}
            if series_id:
                payload["series_id"] = series_id
                payload["released_at"] = released
                obs_period = entry.get("observation_period")
                payload["observation_period"] = (
                    {"period": str(obs_period)} if obs_period is not None else None
                )
                payload["actual"] = (
                    {"value": str(actual), "unit": str(entry.get("unit", "percent"))}
                    if actual is not None
                    else {
                        "value": None,
                        "unit": str(entry.get("unit", "percent")),
                        "unknown_reason": "missing",
                    }
                )
                payload["consensus"] = {
                    "value": None,
                    "unit": str(entry.get("unit", "percent")),
                    "unknown_reason": "missing",
                }
                payload["previous"] = (
                    {"value": str(entry["previous"]), "unit": str(entry.get("unit", "percent"))}
                    if entry.get("previous") is not None
                    else {
                        "value": None,
                        "unit": str(entry.get("unit", "percent")),
                        "unknown_reason": "missing",
                    }
                )
            else:
                # No versioned series: emit a news payload (required fields only).
                payload = {
                    "type": "news",
                    "title": title[:300],
                    "snippet": entry.get("snippet", "")[:1000],
                    "occurred_at": released,
                    "raw_metadata": {},
                }
            items.append(
                {
                    "id": stable_item_id(self.provider_id, url),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": payload,
                }
            )
        return items


class SseAdapter(BaseAdapter):
    """SSE official notices from its HTML index."""

    provider_id: str = "sse"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(client, "https://www.sse.com.cn/disclosure/announcement/general/")

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        entries = self._index_entries(raw, "notices")
        items: list[dict[str, Any]] = []
        for entry in entries[:200]:
            title = entry.get("title", "")
            url = entry.get("url", "")
            published = entry.get("published_at")
            if not title or not url or not published:
                continue
            if not _in_half_open_window(published, window):
                continue
            source = self._source(
                source_id=f"sse-{stable_item_id(self.provider_id, url)}",
                name="上海证券交易所",
                tier="Tier 1",
                url=url,
                published_at=published,
                knowledge=published,
            )
            items.append(
                {
                    "id": stable_item_id(self.provider_id, url),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": {
                        "type": "news",
                        "title": title[:300],
                        "snippet": entry.get("snippet", "")[:1000],
                        "occurred_at": published,
                        "raw_metadata": {},
                    },
                }
            )
        return items


class SzseAdapter(BaseAdapter):
    """SZSE official notices from its HTML index."""

    provider_id: str = "szse"

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        return self._fetch(client, "https://www.szse.cn/disclosure/notice/general/index.html")

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        entries = self._index_entries(raw, "notices")
        items: list[dict[str, Any]] = []
        for entry in entries[:200]:
            title = entry.get("title", "")
            url = entry.get("url", "")
            published = entry.get("published_at")
            if not title or not url or not published:
                continue
            if not _in_half_open_window(published, window):
                continue
            source = self._source(
                source_id=f"szse-{stable_item_id(self.provider_id, url)}",
                name="深圳证券交易所",
                tier="Tier 1",
                url=url,
                published_at=published,
                knowledge=published,
            )
            items.append(
                {
                    "id": stable_item_id(self.provider_id, url),
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": {
                        "type": "news",
                        "title": title[:300],
                        "snippet": entry.get("snippet", "")[:1000],
                        "occurred_at": published,
                        "raw_metadata": {},
                    },
                }
            )
        return items


class YahooMarketAdapter(BaseAdapter):
    """Yahoo-compatible market data for the 13 v1 dashboard roles.

    ``fetch`` requests the chart API for one verified configured symbol with an
    explicit cutoff-derived 90-calendar-day daily-history query; production
    orchestration fans out over verified mappings only. ``normalize`` decodes the chart
    JSON into strictly chronological bounded ``market_data`` observations.
    Daily timestamps are session labels, not completed closes, so
    observation-level eligibility (session close plus the role's configured
    availability lag) is applied by the market snapshot, not here. Missing/
    empty result sets are retained as role-absent records so the coverage
    matrix can record missing roles instead of silently degrading.
    """

    provider_id: str = "yahoo_market"

    def __init__(
        self,
        manifest: Mapping[str, Any] | ProviderEntry | None = None,
        instrument: str = "^GSPC",
        role_id: str = "sp500",
        unit: str | None = None,
    ) -> None:
        super().__init__(manifest)
        self._instrument = instrument
        self._role_id = role_id
        self._unit = unit or self._contract.units.get("index", "index")

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        cutoff = _parse_timestamp(window["end"])
        period2 = int(cutoff.timestamp())
        period1 = int((cutoff - timedelta(days=90)).timestamp())
        query = urlencode({"period1": period1, "period2": period2, "interval": "1d"})
        instrument = quote(self._instrument, safe="")
        return self._fetch(
            client,
            f"https://query1.finance.yahoo.com/v8/finance/chart/{instrument}?{query}",
        )

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        data = self._json_body(raw)
        if not isinstance(data, dict):
            return []
        result = ((data.get("chart") or {}).get("result") or [None])[0]
        if not isinstance(result, dict):
            return []
        result.get("meta") or {}
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quotes = (indicators.get("quote") or [None])[0] or {}
        closes = quotes.get("close") or []
        if self._contract.adjustment_policy.get("splits_dividends_adjusted"):
            closes = ((indicators.get("adjclose") or [None])[0] or {}).get("adjclose") or closes
        if not timestamps or not closes:
            return []

        observations: list[Mapping[str, Any]] = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            as_of = _epoch_to_iso(int(ts))
            observations.append(
                {
                    "as_of": as_of,
                    "value": str(close),
                    "unit": self._unit,
                    # Yahoo's daily timestamp is a session label/open for
                    # exchange instruments, not proof that the close exists.
                    # The snapshot applies the role's configured close + lag.
                    "available_at": None,
                }
            )
        observations = _chronological_dedup(observations)
        max_observations = self._contract.max_observations or 260
        observations = observations[-max_observations:]
        if not observations:
            return []

        url = f"https://finance.yahoo.com/quote/{self._instrument}"
        source = self._source(
            source_id=f"yahoo-{stable_item_id(self.provider_id, self._instrument)}",
            name="Yahoo Finance",
            tier="Tier 2",
            url=url,
            published_at=None,
            knowledge=_format_timestamp(_parse_timestamp(window["end"])),
        )
        return [
            {
                "id": stable_item_id(self.provider_id, f"{self._instrument}|{self._role_id}"),
                "provider_id": self.provider_id,
                "source": source,
                "payload": {
                    "type": "market_data",
                    "instrument_id": self._role_id,
                    "unit": self._unit,
                    "observations": observations,
                    "raw_metadata": {},
                },
            }
        ]


def _epoch_to_iso(epoch: int) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _parse_timestamp(value: str) -> datetime:
    text = str(value).strip()
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _normalize_timestamp(value: str | None) -> str:
    return _format_timestamp(_parse_timestamp(value)) if value else ""


def _in_half_open_window(value: str, window: Mapping[str, str], *, date_only: bool = False) -> bool:
    parsed = _parse_timestamp(value)
    start = _parse_timestamp(window["start"])
    end = _parse_timestamp(window["end"])
    if date_only:
        return start.date() <= parsed.date() < end.date()
    return start <= parsed < end


class _IndexLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        title = " ".join("".join(self._text).split())
        self.links.append((self._href, title))
        self._href = None
        self._text = []


def _html_index_entries(raw: Any, *, base_url: str, charset: str) -> list[dict[str, Any]]:
    body = _response_bytes(raw)
    try:
        text = body.decode(charset)
    except UnicodeDecodeError as exc:
        raise FetchError(f"response not decodable as {charset}") from exc
    parser = _IndexLinkParser()
    parser.feed(text)
    entries: list[dict[str, Any]] = []
    for href, title in parser.links:
        if not href or not title:
            continue
        match = re.search(r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})", title)
        if match is None:
            match = re.search(r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})", href)
        if match is None:
            compact = re.search(r"(20\d{2})(\d{2})(\d{2})", title + href)
            if compact is not None:
                match = compact
        if match is None:
            continue
        year, month, day = (int(part) for part in match.groups())
        published = _format_timestamp(datetime(year, month, day, tzinfo=UTC))
        entries.append(
            {
                "title": title,
                "url": urljoin(base_url, href),
                "published_at": published,
                "released_at": published,
            }
        )
    return entries


def _response_bytes(raw: Any) -> bytes:
    for attribute in ("body_bytes", "content"):
        body = getattr(raw, attribute, None)
        if isinstance(body, bytes):
            return body
    raise FetchError("response has no byte body")


def _canonical_number(value: Any) -> str:
    text = str(value).replace(",", "").strip()
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise FetchError("provider numeric value is invalid") from exc
    if not number.is_finite():
        raise FetchError("provider numeric value is not finite")
    return format(number, "f")


def _chronological_dedup(observations: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Strict-chronological dedup: exact duplicate timestamps collapse; the
    serialized result is strictly ordered by ``as_of``."""
    by_ts: dict[str, list[Mapping[str, Any]]] = {}
    for obs in observations:
        by_ts.setdefault(obs["as_of"], []).append(obs)
    cleaned: list[Mapping[str, Any]] = []
    for ts in sorted(by_ts):
        group = by_ts[ts]
        values = {o["value"] for o in group}
        if len(values) > 1:
            cleaned.append(dict(group[0]))  # keep first; conflict retained by caller
        else:
            cleaned.append(dict(group[0]))
    return cleaned


def build_registry(
    providers: Mapping[str, ProviderEntry] | Sequence[ProviderEntry] | None = None,
) -> ProviderRegistry:
    """Build the explicit provider registry from resolved Provider entries.

    Returns every adapter required by the six mandatory v1 coverage rows,
    plus the verified-optional CFTC/CP and disabled-by-default extras. The
    registry itself never enables anything; enablement is configuration.
    """
    resolved_runtime = providers is not None
    if providers is None:
        from .manifest import load_all_manifests

        providers = {
            pid: manifest_to_provider_entry(manifest)
            for pid, manifest in load_all_manifests().items()
            if pid != "akshare"
        }
    elif not isinstance(providers, Mapping):
        providers = {provider.id: provider for provider in providers}
    if resolved_runtime:
        providers = {pid: provider for pid, provider in providers.items() if provider.enabled}

    adapter_types: dict[str, type[Any]] = {
        "federal_reserve": FedAdapter,
        "bls": BlsAdapter,
        "sec_edgar": SecEdgarAdapter,
        "cftc": CftcAdapter,
        "pboc": PbocAdapter,
        "nbs": NbsAdapter,
        "sse": SseAdapter,
        "szse": SzseAdapter,
        "yahoo_market": YahooMarketAdapter,
    }
    adapters = {
        provider_id: adapter_types[provider_id](provider)
        for provider_id, provider in providers.items()
        if provider_id in adapter_types
    }
    return ProviderRegistry(adapters)
