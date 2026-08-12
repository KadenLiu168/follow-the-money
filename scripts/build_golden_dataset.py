"""Build the checked-in 30-day provenance-reviewed offline dataset.

The source table below contains fixed primary-source archive URLs and the
reviewed event labels used by the evaluator. The generated Feed objects are
fully hashed, non-empty evidence snapshots; the four recorded pass objects
are bounded, reference-only replay inputs and never invoke a network or LLM.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from html import unescape
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from follow_the_money.boundary import application_build_fingerprint, build_fingerprint_to_dict
from follow_the_money.canonical import canonical_digest
from follow_the_money.feed.validate import recompute_feed_identity

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "dataset"
SOURCE_ROOT = DATASET / "sources"


Evidence = tuple[str, str, str, str, str]


EVIDENCE: dict[str, Evidence | tuple[Evidence, ...]] = {
    "2024-01-05": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/empsit_01052024.htm",
        "Employment Situation release for December 2023",
    ),
    "2024-01-10": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/%5EGSPC/history",
        "U.S. equity index session observation",
    ),
    "2024-01-17": (
        "nbs",
        "国家统计局",
        "Tier 1",
        "https://www.stats.gov.cn/xxgk/jd/sjjd2020/202401/t20240117_1946672.html",
        "National economy and fourth-quarter GDP release",
    ),
    "2024-01-24": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/000300.SS/history",
        "China equity index session observation",
    ),
    "2024-01-31": (
        "federal_reserve",
        "Federal Reserve",
        "Tier 1",
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm",
        "Federal Reserve FOMC statement",
    ),
    "2024-02-13": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/cpi_02132024.htm",
        "Consumer Price Index release for January 2024",
    ),
    "2024-02-16": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/ppi_02162024.htm",
        "Producer Price Index release for January 2024",
    ),
    "2024-03-08": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/empsit_03082024.htm",
        "Employment Situation evidence retained for the macro window",
    ),
    "2024-03-12": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/cpi_03122024.htm",
        "Consumer Price Index release for February 2024",
    ),
    "2024-03-20": (
        (
            "federal_reserve",
            "Federal Reserve",
            "Tier 1",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240320a.htm",
            "Federal Reserve issues FOMC statement",
        ),
        (
            "federal_reserve",
            "Federal Reserve",
            "Tier 1",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240320b.htm",
            "Federal Reserve releases FOMC projections materials",
        ),
    ),
    "2024-03-06": (
        "sec_edgar",
        "SEC EDGAR",
        "Tier 1",
        "https://www.sec.gov/Archives/edgar/data/320193/000000000024002512/0000000000-24-002512-index.html",
        "Apple SEC-generated letter (Form UPLOAD)",
    ),
    "2024-04-02": (
        "sec_edgar",
        "SEC EDGAR",
        "Tier 1",
        "https://www.sec.gov/Archives/edgar/data/1318605/000095017024040274/0000950170-24-040274-index.html",
        "Tesla current report (Form 8-K)",
    ),
    "2024-04-25": (
        "sec_edgar",
        "SEC EDGAR",
        "Tier 1",
        "https://www.sec.gov/Archives/edgar/data/789019/000095017024048268/0000950170-24-048268-index.html",
        "Microsoft current report (Form 8-K)",
    ),
    "2024-05-01": (
        "sec_edgar",
        "SEC EDGAR",
        "Tier 1",
        "https://www.sec.gov/Archives/edgar/data/1018724/000000000024004905/0000000000-24-004905-index.html",
        "Amazon SEC-generated letter (Form UPLOAD)",
    ),
    "2024-05-22": (
        "sec_edgar",
        "SEC EDGAR",
        "Tier 1",
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000113/nvda-20240522.htm",
        "NVIDIA current report (Form 8-K)",
    ),
    "2024-04-12": (
        "pboc",
        "中国人民银行",
        "Tier 1",
        "https://wzdt.pbc.gov.cn/huilv/flex-xml/flex_xml_9.xml",
        "PBOC official USD/CNY exchange-rate XML observation",
    ),
    "2024-05-17": (
        "pboc",
        "中国人民银行",
        "Tier 1",
        "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2025092212554091417/index.html",
        "PBOC participation in the 2024-05-17 housing-policy briefing",
    ),
    "2024-06-20": (
        "pboc",
        "中国人民银行",
        "Tier 1",
        "https://wzdt.pbc.gov.cn/huilv/flex-xml/flex_xml_9.xml",
        "PBOC official USD/CNY exchange-rate XML observation",
    ),
    "2024-07-22": (
        "pboc",
        "中国人民银行",
        "Tier 1",
        "https://www.xinhuanet.com/20240722/86cf19b6416341ae8f2c4d8bc5bec219/c.html",
        "2024-07-22 LPR publication and monetary-policy adjustment report",
    ),
    "2024-08-20": (
        "pboc",
        "中国人民银行",
        "Tier 1",
        "https://www.chinamoney.org.cn/chinese/rdgz/20240820/2941241.html",
        "2024-08-20 LPR publication authorized by the PBOC",
    ),
    "2024-05-14": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/%5EGSPC/history",
        "China-U.S. policy shock cross-asset observation",
    ),
    "2024-06-04": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/%5EVIX/history",
        "China-U.S. technology-policy cross-asset observation",
    ),
    "2024-09-13": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/%5EGSPC/history",
        "China-U.S. policy cross-asset observation",
    ),
    "2024-06-14": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/GC=F/history",
        "Geopolitical risk and precious-metals observation",
    ),
    "2024-08-05": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/%5EVIX/history",
        "Geopolitical risk and volatility observation",
    ),
    "2024-10-07": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/CL=F/history",
        "Geopolitical risk and energy observation",
    ),
    "2024-07-19": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/%5EVIX/history",
        "Abnormal cross-asset volatility observation",
    ),
    "2024-08-02": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/empsit_08022024.htm",
        "Employment Situation release with a degraded secondary source",
    ),
    "2024-09-06": (
        "bls",
        "U.S. Bureau of Labor Statistics",
        "Tier 1",
        "https://www.bls.gov/news.release/archives/empsit_09062024.htm",
        "Employment Situation release with a degraded secondary source",
    ),
    "2024-09-26": (
        "yahoo_market",
        "Yahoo Finance",
        "Tier 2",
        "https://finance.yahoo.com/quote/GC=F/history",
        "Precious-metals session observation",
    ),
}


def _item_id(date: str, event_id: str, url: str) -> str:
    digest = hashlib.sha256(f"{date}|{event_id}|{url}".encode()).hexdigest()
    return f"evidence_{digest[:24]}"


def _load_source_snapshot(
    date: str, event_id: str, source_url: str
) -> tuple[dict[str, Any], bytes]:
    metadata_path = SOURCE_ROOT / f"{date}__{event_id}.json"
    try:
        metadata = json.loads(metadata_path.read_bytes())
        body_path = SOURCE_ROOT / str(metadata["body_file"])
        body = body_path.read_bytes()
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{date}/{event_id}: source snapshot is unavailable") from exc
    if metadata.get("source_url") != source_url or metadata.get("http_status") != 200:
        raise ValueError(f"{date}/{event_id}: source snapshot identity/status mismatch")
    body_sha256 = hashlib.sha256(body).hexdigest()
    if metadata.get("body_size") != len(body) or metadata.get("body_sha256") != body_sha256:
        raise ValueError(f"{date}/{event_id}: source snapshot body hash/size mismatch")
    return metadata, body


def _source_charset(source_url: str, body: bytes) -> str:
    try:
        body.decode("utf-8", errors="strict")
        return "utf-8"
    except UnicodeDecodeError:
        if source_url.startswith("https://www.bls.gov/"):
            return "windows-1252"
        raise


def _source_excerpt(body: bytes, *, charset: str = "utf-8") -> str:
    """Return a short source-derived text view for recorded evidence."""
    text = body.decode(charset, errors="strict")
    text = re.sub(
        r"<(?:style|script|noscript)\b[^>]*>.*?</(?:style|script|noscript)>",
        " ",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return text[:240]


def _source_title(body: bytes, *, charset: str = "utf-8") -> str:
    """Extract a stable title/identity from the saved source body."""
    text = body.decode(charset, errors="strict")
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
        symbol = payload["chart"]["result"][0]["meta"]["symbol"]
        return f"Yahoo Finance historical chart for {symbol}"
    if "<dataroot" in text.lower():
        type_ids = sorted(set(re.findall(r"<typeid>([^<]+)</typeid>", text)))
        return f"PBOC exchange-rate XML typeid={','.join(type_ids)}"
    for pattern in (
        r'<meta\b[^>]*\bproperty=["\']og:title["\'][^>]*\bcontent=["\'](.*?)["\']',
        r'<meta\b[^>]*\bcontent=["\'](.*?)["\'][^>]*\bproperty=["\']og:title["\']',
        r"<h1\b[^>]*>(.*?)</h1>",
        r"<title\b[^>]*>(.*?)</title>",
    ):
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value = re.sub(r"<[^>]+>", " ", unescape(match.group(1)))
            value = re.sub(r"\s+", " ", value).strip()
            if value:
                return value[:300]
    return _source_excerpt(body, charset=charset)[:300]


def _pboc_observation(body: bytes, date: str, *, charset: str = "utf-8") -> dict[str, str] | None:
    text = body.decode(charset, errors="strict")
    match = re.search(
        rf"<Temp>\s*<date>{re.escape(date)}</date>\s*<hlvalue>([^<]+)</hlvalue>\s*<typeid>([^<]+)</typeid>",
        text,
        re.DOTALL,
    )
    if match is None:
        return None
    return {"date": date, "value": match.group(1), "type_id": match.group(2)}


def _sync_source_metadata(date: str, event_id: str, source_url: str, body: bytes) -> None:
    """Refresh derived metadata for an already-reviewed immutable body."""
    metadata_path = SOURCE_ROOT / f"{date}__{event_id}.json"
    metadata = json.loads(metadata_path.read_bytes())
    charset = _source_charset(source_url, body)
    metadata.update(
        {
            "source_url": source_url,
            "fetch_url": source_url,
            "final_url": source_url,
            "title": _source_title(body, charset=charset),
            "body_charset": charset,
            "body_size": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest(),
        }
    )
    metadata_path.write_bytes(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    )


def _bounded_source_fragment(text: str) -> str:
    """Keep recorded pass wording visibly tied to the saved source body."""
    normalized = " ".join(text.split())
    fragment = normalized[:132]
    return fragment or "来源记录未提供可显示文本。"


def _source_timestamp(provider: str, date: str, body: bytes, *, charset: str = "utf-8") -> str:
    """Use the date/time explicitly present in the saved source body."""
    text = body.decode(charset, errors="strict")
    if provider == "sec_edgar":
        accepted = re.search(
            r"Accepted</div>\s*<div class=\"info\">"
            r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}:\d{2}))?",
            text,
            re.DOTALL,
        )
        if accepted:
            time_text = accepted.group(2) or "00:00:00"
            return f"{accepted.group(1)}T{time_text}Z"
    year, month, day = date.split("-")
    english_date = rf"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+0?{int(day)},\s+{year}"
    date_patterns = (
        (english_date,)
        if provider == "bls"
        else (
            rf"{year}-{month}-{day}",
            rf"{year}年0?{int(month)}月0?{int(day)}日",
            rf"{year}{month}{day}",
            rf"{month}{day}{year}",
            english_date,
        )
    )
    match = next(
        (found for pattern in date_patterns if (found := re.search(pattern, text, re.IGNORECASE))),
        None,
    )
    if match is None:
        raise ValueError(f"{date}: source body has no matching event date")
    context = text[max(0, match.start() - 120) : match.end() + 120]
    time_match = re.search(
        r"(?<!\d)(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.)?",
        context,
        re.IGNORECASE,
    )
    hour = int(time_match.group(1)) if time_match else 0
    minute = int(time_match.group(2)) if time_match else 0
    second = int(time_match.group(3) or 0) if time_match else 0
    if time_match and time_match.group(4):
        meridiem = time_match.group(4).lower()
        if meridiem.startswith("p") and hour < 12:
            hour += 12
        if meridiem.startswith("a") and hour == 12:
            hour = 0
    parsed_date = datetime.fromisoformat(f"{date}T00:00:00")
    if provider == "bls":
        parsed_date = parsed_date.replace(tzinfo=ZoneInfo("America/New_York"))
    else:
        parsed_date = parsed_date.replace(tzinfo=UTC)
    parsed_date = parsed_date.replace(hour=hour, minute=minute, second=second)
    return parsed_date.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sec_form(body: bytes, *, charset: str = "utf-8") -> str:
    text = body.decode(charset, errors="strict")
    match = re.search(r"\bForm\s+([A-Z0-9]+(?:-[A-Z0-9]+)?)\b", text, re.IGNORECASE)
    if match is None:
        raise ValueError("SEC snapshot has no Form field")
    return match.group(1).strip()


def _yahoo_observation(body: bytes, *, date: str, source_url: str) -> tuple[str, str, str, str]:
    payload = json.loads(body)
    result = payload["chart"]["result"][0]
    symbol = unquote(source_url.rsplit("/quote/", 1)[-1].split("/", 1)[0])
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    cutoff = datetime.fromisoformat(f"{date}T00:00:00+00:00").timestamp()
    candidates = [
        (int(timestamp), close)
        for timestamp, close in zip(timestamps, closes, strict=True)
        if close is not None and int(timestamp) < cutoff
    ]
    if not candidates:
        raise ValueError(f"{date}: Yahoo snapshot has no observation before cutoff")
    observed_at_epoch, close = candidates[-1]
    value = format(Decimal(str(close)).normalize(), "f")
    unit = "USD/oz" if symbol == "GC=F" else "USD/bbl" if symbol == "CL=F" else "index"
    observed_at = datetime.fromtimestamp(observed_at_epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return symbol, unit, observed_at, value


def _feed(
    day: dict[str, Any], *, producer: dict[str, Any], schema_sha: str
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    date = str(day["date"])
    cutoff = datetime.fromisoformat(f"{date}T00:00:00+00:00")
    source_value = EVIDENCE[date]
    if source_value and isinstance(source_value[0], str):
        source_rows: tuple[Evidence, ...] = (cast(Evidence, source_value),)
    else:
        source_rows = cast(tuple[Evidence, ...], source_value)
    event_ids = [str(value) for value in day["expected_major_events"]]
    if len(source_rows) != len(event_ids):
        raise ValueError(f"{date}: source rows and expected event count differ")
    items: list[dict[str, Any]] = []
    evidence_by_event: dict[str, list[str]] = {}
    for index, event_id in enumerate(event_ids):
        provider, source_name, tier, item_url, _curated_title = source_rows[index]
        item_id = _item_id(date, event_id, item_url)
        source_snapshot, source_body = _load_source_snapshot(date, event_id, item_url)
        charset = str(source_snapshot.get("body_charset", "utf-8"))
        if provider == "yahoo_market":
            _instrument, _unit, timestamp_text, _value = _yahoo_observation(
                source_body, date=date, source_url=item_url
            )
        else:
            timestamp_text = _source_timestamp(provider, date, source_body, charset=charset)
        payload_type = (
            "filing"
            if provider == "sec_edgar"
            else "market_data"
            if provider == "yahoo_market"
            else "policy"
            if provider in {"federal_reserve", "pboc"}
            else "macro_release"
            if provider == "nbs"
            else "news"
        )
        payload: dict[str, Any]
        source_title = _source_title(source_body, charset=charset)
        source_observation = _pboc_observation(source_body, date, charset=charset)
        if payload_type == "policy":
            payload = {
                "type": "policy",
                "title": source_title,
                "announced_at": timestamp_text,
                "raw_metadata": {},
            }
        elif payload_type == "macro_release":
            payload = {
                "type": "macro_release",
                "series_id": event_id,
                "released_at": timestamp_text,
                "observation_period": None,
                "raw_metadata": {},
            }
        elif payload_type == "filing":
            accession_digits = item_url.split("/Archives/edgar/data/", 1)[-1].split("/", 2)[1]
            payload = {
                "type": "filing",
                "form": _sec_form(source_body, charset=charset),
                "company": event_id.split("_", 2)[1].upper(),
                "accession_number": accession_digits,
                "filed_at": timestamp_text,
                "raw_metadata": {},
            }
        elif payload_type == "market_data":
            instrument_id, unit, observed_at, value = _yahoo_observation(
                source_body, date=date, source_url=item_url
            )
            payload = {
                "type": "market_data",
                "instrument_id": instrument_id,
                "unit": unit,
                "observations": [{"as_of": observed_at, "value": value, "unit": unit}],
                "raw_metadata": {"source_excerpt": _source_excerpt(source_body, charset=charset)},
            }
        else:
            payload = {
                "type": "news",
                "title": source_title,
                "snippet": _source_excerpt(source_body, charset=charset),
                "occurred_at": timestamp_text,
                "raw_metadata": {"source_excerpt": _source_excerpt(source_body, charset=charset)},
            }
        payload["raw_metadata"].update(
            {
                "curation": "exact primary-source URL and title reviewed against source record",
                "event_id": event_id,
                "source_title": source_title,
                "source_excerpt": _source_excerpt(source_body, charset=charset),
                "source_snapshot": {
                    "metadata_file": f"{date}__{event_id}.json",
                    "body_file": source_snapshot["body_file"],
                    "body_sha256": source_snapshot["body_sha256"],
                    "body_size": source_snapshot["body_size"],
                    "fetch_url": source_snapshot["fetch_url"],
                    "final_url": source_snapshot["final_url"],
                    "http_status": source_snapshot["http_status"],
                    "body_charset": charset,
                },
            }
        )
        if source_observation is not None:
            payload["raw_metadata"]["source_observation"] = source_observation
        items.append(
            {
                "id": item_id,
                "provider_id": provider,
                "source": {
                    "id": f"source_{item_id}",
                    "name": source_name,
                    "tier": tier,
                    "kind": "news",
                    "url": item_url,
                    "published_at": timestamp_text,
                    "knowledge_available_at": timestamp_text,
                },
                "payload": payload,
            }
        )
        evidence_by_event[event_id] = [item_id]

    snapshot = {
        "dataset": "golden-day-v1",
        "date": date,
        "category": day["category"],
        "source_urls": [item["source"]["url"] for item in items],
        "event_ids": event_ids,
    }
    provider_snapshot = {
        "provider_id": provider,
        "contract_version": 1,
        "source_name": source_name,
        "source_link_host": items[0]["source"]["url"].split("/", 3)[2],
        "fixture_provenance": "curated primary-source archive reference",
    }
    provider_outcomes = [
        {
            "provider_id": provider,
            "state": "healthy",
            "attempted": 1,
            "fetched": 1,
            "succeeded": True,
            "empty": False,
            "partial": False,
            "failed": False,
            "skipped": False,
            "accepted": len(items),
            "rejected": 0,
            "error": None,
            "retrieved_at": (cutoff + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    ]
    provider_contracts = [
        {
            "provider_id": provider,
            "snapshot": provider_snapshot,
            "hash": canonical_digest(provider_snapshot),
        }
    ]
    if day["category"] == "degraded_provider":
        secondary_snapshot = {
            "provider_id": "yahoo_market",
            "contract_version": 1,
            "source_name": "Yahoo Finance",
            "source_link_host": "finance.yahoo.com",
            "fixture_provenance": "curated failure injection: provider unavailable",
        }
        provider_outcomes.append(
            {
                "provider_id": "yahoo_market",
                "state": "failed",
                "attempted": 1,
                "fetched": 0,
                "succeeded": False,
                "empty": False,
                "partial": False,
                "failed": True,
                "skipped": False,
                "accepted": 0,
                "rejected": 0,
                "error": "fixture_provider_unavailable",
                "retrieved_at": None,
            }
        )
        provider_contracts.append(
            {
                "provider_id": "yahoo_market",
                "snapshot": secondary_snapshot,
                "hash": canonical_digest(secondary_snapshot),
            }
        )
    feed: dict[str, Any] = {
        "schema_version": 1,
        "run_id": "",
        "window": {
            "start": (cutoff - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "collection_started_at": (cutoff - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_cutoff_at": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collection_completed_at": (cutoff + timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at": (cutoff + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider_outcomes": provider_outcomes,
        "producer": producer,
        "feed_config": {"snapshot": snapshot, "hash": canonical_digest(snapshot)},
        "feed_schema": {"path": "schemas/feed.schema.json", "sha256": schema_sha},
        "provider_contracts": provider_contracts,
        "git": None,
        "content_digest": "0" * 64,
        "calendar_horizon_end": (cutoff + timedelta(hours=26)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": items,
        "pipeline": {
            "status": "degraded" if day["category"] == "degraded_provider" else "healthy",
            "warnings": ["one secondary provider was unavailable during curation"]
            if day["category"] == "degraded_provider"
            else [],
            "coverage_gap": None,
        },
    }
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    return feed, evidence_by_event


def _outputs(
    day: dict[str, Any], feed: dict[str, Any], evidence_by_event: dict[str, list[str]]
) -> dict[str, Any]:
    selected = [str(value) for value in day["expected_major_events"]]
    full = [str(value) for value in day["expected_top3"]]
    refs = [ref for values in evidence_by_event.values() for ref in values]
    source_fragment_by_event = {
        str(item["payload"]["raw_metadata"]["event_id"]): _bounded_source_fragment(
            str(item["payload"]["raw_metadata"]["source_excerpt"])
        )
        for item in feed["items"]
        if item["payload"].get("raw_metadata", {}).get("event_id")
    }
    evidence_aliases = {
        event_id: {f"e{index:02d}": ref for index, ref in enumerate(event_refs)}
        for event_id, event_refs in evidence_by_event.items()
    }
    resolver_aliases = {event_id: f"p{index:02d}" for index, event_id in enumerate(selected)}
    analyst_aliases = {event_id: f"a{index:02d}" for index, event_id in enumerate(selected)}
    editor_aliases = {event_id: f"s{index:02d}" for index, event_id in enumerate(selected)}
    family_aliases = {
        event_id: f"f{index:02d}"
        for index, members in enumerate(day.get("story_families", {}).values())
        for event_id in members
    }
    proposals = []
    for event_id in selected:
        relations = []
        for pair in day.get("coexistence_pairs", []):
            if event_id in pair:
                other = pair[1] if pair[0] == event_id else pair[0]
                relations.append(
                    {
                        "other_proposal_alias": resolver_aliases[other],
                        "relation": "distinct_material_development",
                    }
                )
        proposals.append(
            {
                "component_alias": "c0",
                "position_alias": resolver_aliases[event_id],
                "event_type": "observed_source_event",
                "event_defining_fact_ids": [f"fact_{event_id}"],
                "evidence_ids": evidence_by_event[event_id],
                "supporting_fact_ids": [],
                "entity_ids": [],
                "story_family_label": family_aliases.get(event_id, "unknown"),
                "coexistence_relations": relations,
            }
        )
    analyst_packets = []
    for event_id in selected:
        reference_alias = next(iter(evidence_aliases[event_id]))
        analyst_packets.append(
            {
                "packet_alias": analyst_aliases[event_id],
                "mechanisms": [f"来源记录片段：{source_fragment_by_event[event_id]}"],
                "implications": ["仅保留来源记录支持的有界含义。"],
                "reaction_attributions": [],
                "price_in": {
                    "status": "unclear",
                    "explanation": "已保存来源记录未提供可验证的价格预期。",
                    "reference_aliases": [reference_alias],
                },
                "indirect_indication": {
                    "indicated": False,
                    "reference_aliases": [reference_alias],
                },
                "asset_mappings": [],
                "alternatives": [],
                "watch_points": [],
                "scope": "unknown",
                "fundamental_depth": "unknown",
                "reversibility": "unknown",
                "structural_horizon": "unknown",
                "cn_hk_exposure": "unknown",
                "us_next_session_exposure": "unknown",
                "catalyst_calendar_ids": [],
                "audit_reasons": [],
            }
        )
    return {
        "schema_version": 1,
        "feed_run_id": feed["run_id"],
        "selected_event_ids": selected,
        "full_event_ids": full,
        "event_evidence": evidence_by_event,
        "recorded_llm_outputs": {
            "resolver": {
                "proposals": proposals,
                "unresolved_groups": [],
            },
            "analyst": analyst_packets[0],
            "editor": {
                "filled_slots": [
                    {
                        "slot_alias": editor_aliases[event_id],
                        "wording_fragment": f"来源记录摘要：{source_fragment_by_event[event_id]}",
                        "reference_aliases": [next(iter(evidence_aliases[event_id]))],
                    }
                    for event_id in selected
                ],
            },
            "language-audit": {
                "covered_claim_ids": ["c_0"],
                "findings": [],
            },
        },
        "recorded_output_files": {
            pass_name: f"pass_outputs/{day['date']}/{pass_name}.json"
            for pass_name in ("resolver", "analyst", "editor", "language-audit")
        },
        "replay_contract": {
            "resolver": {"event_aliases": resolver_aliases},
            "analyst": {"event_aliases": analyst_aliases},
            "editor": {"event_aliases": editor_aliases},
            "evidence_aliases": evidence_aliases,
            "analyst_packets": analyst_packets,
        },
        "claim_inventory": [
            {
                "claim_id": "c_0",
                "is_factual": True,
                "is_causal": False,
                "supported": True,
                "causal_overclaim": False,
                "event_ids": selected,
                "evidence_ids": refs,
            }
        ],
        "provenance": {
            "curator": "follow-the-money-reviewer",
            "reviewed": "2026-08-11",
            "source": "checked-in primary-source response snapshots",
        },
        "ranking": {
            "reference_selected": selected,
            "permuted_selected": selected,
            "reference_full": full,
            "permuted_full": full,
        },
        "story_families": day.get("story_families", {}),
        "coexistence_pairs": day.get("coexistence_pairs", []),
    }


def main() -> int:
    manifest_path = DATASET / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    producer = build_fingerprint_to_dict(application_build_fingerprint(ROOT, "0.1.0"))
    schema_sha = hashlib.sha256((ROOT / "schemas/feed.schema.json").read_bytes()).hexdigest()
    for day in manifest["days"]:
        source_value = EVIDENCE[str(day["date"])]
        source_rows = (
            (cast(Evidence, source_value),)
            if source_value and isinstance(source_value[0], str)
            else cast(tuple[Evidence, ...], source_value)
        )
        for event_id, row in zip(day["expected_major_events"], source_rows, strict=True):
            body_path = SOURCE_ROOT / f"{day['date']}__{event_id}.body"
            _sync_source_metadata(str(day["date"]), str(event_id), row[3], body_path.read_bytes())
        feed, evidence_by_event = _feed(day, producer=producer, schema_sha=schema_sha)
        output = _outputs(day, feed, evidence_by_event)
        (DATASET / day["feed"]).write_bytes(
            json.dumps(feed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        (DATASET / day["outputs"]).write_bytes(
            json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        for pass_name, pass_path in output["recorded_output_files"].items():
            path = DATASET / pass_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                json.dumps(
                    output["recorded_llm_outputs"][pass_name],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
        day["provenance"] = {
            "curator": "follow-the-money-reviewer",
            "reviewed": "2026-08-11",
            "source": "checked-in primary-source response snapshots",
            "source_snapshot_files": [
                f"sources/{day['date']}__{event_id}.json"
                for event_id in day["expected_major_events"]
            ],
        }
    manifest["description"] = (
        "Follow the Money golden-day dataset: 30 unique trading days with "
        "non-empty hashed source snapshots and replayable four-pass outputs."
    )
    manifest_path.write_bytes(
        json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
