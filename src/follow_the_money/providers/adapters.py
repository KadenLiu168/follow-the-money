"""Concrete credential-free Provider adapters for the Evidence Feed.

Each adapter implements ``fetch`` and ``normalize`` per the small Provider
protocol and validates every emitted source URL against its owning manifest's
``source_link_hosts`` rules. Adapters remain usable from fixtures with
injected clients; they never dereference source URLs.

The shipped Feed coverage rows are backed by these adapters:

- ``us_official_macro_policy``: federal_reserve + bls
- ``us_company_filings``: sec_edgar (watched-company filing contract)
- ``china_official_macro_policy``: pboc + nbs
- ``china_exchange_evidence``: sse + szse
- ``cftc_positioning``: cftc
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
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from ..config.model import ProviderEntry
from ..schema import SchemaError
from ..semantic.macro import build_macro_context
from ..semantic.news import build_news_context
from ..semantic.policy import build_policy_context
from .base import Provider, ProviderRegistry
from .cftc_cot import compare_reports, publication_boundary, select_report_dates
from .http import (
    FetchError,
    bounded_fetch,
    safe_parse_rss,
    stable_item_id,
    validate_provider_url,
)
from .manifest import load_manifest, manifest_to_provider_entry
from .sec_13f import compare_holdings, parse_complete_submission, select_filings
from .sec_beneficial_ownership import (
    BeneficialOwnershipListingCandidate,
    build_shared_historical_candidate_index,
    compare_beneficial_ownership,
    declared_beneficial_ownership_history_files,
    derive_beneficial_ownership_historical_url,
    derive_beneficial_ownership_xml_url,
    is_unsupported_historical_document,
    parse_beneficial_ownership_document,
    select_beneficial_ownership_filings,
    select_historical_beneficial_ownership_filings_with_status,
)
from .sec_form4 import (
    Form4ListingCandidate,
    derive_form4_xml_url,
    form4_feed_item,
    parse_form4_document,
    select_form4_filings,
)
from .urls import UrlValidationError, sec_archive_cik


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
        request_headers = {
            key: value for key, value in (headers or {}).items() if key.lower() != "user-agent"
        }
        request_headers["User-Agent"] = self._contract.user_agent
        return bounded_fetch(
            client,
            url,
            headers=request_headers,
            timeout=self._contract.attempt_timeout_seconds,
            max_bytes=self._contract.response_limit_bytes,
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
        kind: str = "news",
    ) -> dict[str, Any]:
        return {
            "id": source_id,
            "name": name,
            "tier": tier,
            "kind": kind,
            "url": self._validate_url(url),
            "published_at": _normalize_timestamp(published_at) if published_at else None,
            "knowledge_available_at": _normalize_timestamp(knowledge),
        }

    def _attach_semantic_context(
        self, item: dict[str, Any], *, source_record: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = item.get("payload")
        source = item.get("source")
        if not isinstance(payload, Mapping) or not isinstance(source, Mapping):
            raise SchemaError("normalized item cannot construct semantic context")
        payload_type = payload.get("type")
        if payload_type == "news":
            context = build_news_context(self.provider_id, payload, source)
        elif payload_type == "macro_release":
            context = build_macro_context(self.provider_id, payload, source_record or {})
        elif payload_type == "policy":
            context = build_policy_context(self.provider_id, payload, source)
        else:
            return item
        item["semantic_context"] = context.to_dict()
        return item

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
            item = {
                "id": stable_item_id(self.provider_id, entry.get("id", link)),
                "provider_id": self.provider_id,
                "source": source,
                "payload": payload,
            }
            items.append(self._attach_semantic_context(item))
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
    """SEC EDGAR acquisition unit for one watched company.

    The v1 compatibility path retains the historical submissions-only reader
    for fixture consumers. A v2 unit acquires submissions, the selected
    current complete submission, and an optional previous comparable complete
    submission, then delegates all semantic work to :mod:`sec_13f`.
    """

    provider_id: str = "sec_edgar"

    def __init__(
        self,
        manifest: Mapping[str, Any] | ProviderEntry | None = None,
        watched_ciks: Sequence[str] = (),
        watched_company: Any | None = None,
    ) -> None:
        super().__init__(manifest)
        self._watched_ciks = tuple(str(c) for c in watched_ciks)
        self._watched_company = watched_company
        self._semantic_v2 = watched_company is not None and self._contract.contract_version == 2
        self._semantic_v3 = watched_company is not None and self._contract.contract_version in {
            3,
            4,
        }
        self._semantic_13f = self._semantic_v2 or self._semantic_v3
        if self._contract.contract_version in {2, 3, 4} and self._contract.units != {
            "13f_value_before_2023_01_03": "usd_thousands",
            "13f_value_from_2023_01_03": "usd",
            "reported_value_usd_thousands": "usd_thousands",
        }:
            raise ValueError("SEC semantic units are not the closed contract")

    def _complete_url(self, candidate: Any) -> str:
        cik = sec_archive_cik(str(candidate.cik).zfill(10))
        accession = candidate.accession_number
        return self._validate_url(
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{accession}.txt"
        )

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        if self._semantic_13f:
            assert self._watched_company is not None
            cik = str(self._watched_company.cik).zfill(10)
        else:
            cik = self._watched_ciks[0] if self._watched_ciks else "0001067983"
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        if not self._semantic_13f:
            return self._fetch(client, submissions_url)
        assert self._watched_company is not None
        submissions_raw = self._fetch(client, submissions_url)
        submissions = self._json_body(submissions_raw)
        if not isinstance(submissions, Mapping):
            raise FetchError("SEC submissions response is not an object")
        current, previous = select_filings(submissions, window["end"])
        current_url = self._complete_url(current)
        current_raw = self._fetch(client, current_url)
        previous_raw = None
        previous_url = None
        if previous is not None:
            previous_url = self._complete_url(previous)
            previous_raw = self._fetch(client, previous_url)
        return {
            "submissions": submissions,
            "current": current,
            "current_url": current_url,
            "current_body": current_raw.body_bytes,
            "previous": previous,
            "previous_url": previous_url,
            "previous_body": previous_raw.body_bytes if previous_raw is not None else None,
        }

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        if not self._semantic_13f:
            return self._normalize_v1(raw, window)
        if not isinstance(raw, Mapping):
            raise FetchError("SEC acquisition result is invalid")
        assert self._watched_company is not None
        submissions = raw.get("submissions")
        if not isinstance(submissions, Mapping):
            raise FetchError("SEC submissions response is invalid")
        configured_cik = str(self._watched_company.cik).zfill(10)
        official_cik = str(submissions.get("cik") or "").zfill(10)
        official_name = submissions.get("name")
        if (
            official_cik != configured_cik
            or not isinstance(official_name, str)
            or not official_name.strip()
        ):
            raise FetchError("SEC official company identity is missing or mismatched")
        current = parse_complete_submission(
            raw["current_body"],
            raw["current"],
            source_url=str(raw["current_url"]),
            require_submission_header=True,
        )
        previous = None
        if raw.get("previous") is not None:
            previous = parse_complete_submission(
                raw["previous_body"],
                raw["previous"],
                source_url=str(raw["previous_url"]),
                require_submission_header=True,
            )
        comparison_rows = compare_holdings(current, previous)
        accepted_at = current.candidate.accepted_at
        item_id = stable_item_id(self.provider_id, current.candidate.accession_number)
        source = self._source(
            source_id=f"sec-{item_id}",
            name="SEC EDGAR",
            tier="Tier 1",
            kind="filing",
            url=current.source_url,
            published_at=accepted_at,
            knowledge=accepted_at,
        )
        comparison = {
            "status": "available" if previous is not None else "unavailable",
            "previous_accession_number": previous.candidate.accession_number if previous else None,
            "previous_report_period": previous.candidate.report_period if previous else None,
            "previous_accepted_at": previous.candidate.accepted_at if previous else None,
            "previous_filed_at": previous.candidate.filed_at if previous else None,
            "previous_source_url": previous.source_url if previous else None,
            "previous_value_normalization": previous.value_normalization if previous else None,
            "reason": None if previous else "no_previous_comparable_filing",
        }
        tickers = submissions.get("tickers")
        official_tickers = (
            sorted(str(ticker).strip() for ticker in tickers if str(ticker).strip())
            if isinstance(tickers, list)
            else []
        )
        payload = {
            "type": "filing",
            "form": current.candidate.form,
            "company": configured_cik,
            "accession_number": current.candidate.accession_number,
            "filed_at": current.candidate.filed_at,
            "raw_metadata": {},
            "company_identity": {
                "cik": official_cik,
                "name": official_name.strip(),
                "tickers": official_tickers,
            },
            "report_period": current.candidate.report_period,
            "accepted_at": accepted_at,
            "value_normalization": current.value_normalization,
            "comparison": comparison,
            "holdings": comparison_rows,
        }
        if self._semantic_v3:
            payload["filing_subtype"] = "form13f"
        return [
            {
                "id": item_id,
                "provider_id": self.provider_id,
                "source": source,
                "payload": payload,
            }
        ]

    def _normalize_v1(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
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
                f"https://www.sec.gov/Archives/edgar/data/{sec_archive_cik(str(cik).zfill(10))}/"
                f"{accession.replace('-', '')}/{doc}"
                if doc
                else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F"
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


class SecForm4Adapter(BaseAdapter):
    """SEC EDGAR acquisition unit for one watched issuer's Form 4 events."""

    provider_id: str = "sec_edgar"

    def __init__(
        self,
        manifest: Mapping[str, Any] | ProviderEntry | None = None,
        watched_issuer: Any | None = None,
        watched_cik: str | None = None,
    ) -> None:
        super().__init__(manifest)
        if self._contract.contract_version not in {3, 4}:
            raise ValueError("SEC Form 4 requires contract version 3 or 4")
        if (
            self._contract.max_filings_per_window != 20
            or not self._contract.ownership_xml_schema_versions
        ):
            raise ValueError("SEC Form 4 contract bounds are not closed")
        self._watched_cik = str(getattr(watched_issuer, "cik", None) or watched_cik or "0001067983")
        self.selected_accessions: tuple[str, ...] = ()
        self.selection_complete = False

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        submissions_url = f"https://data.sec.gov/submissions/CIK{self._watched_cik}.json"
        submissions_raw = self._fetch(client, submissions_url)
        submissions = self._json_body(submissions_raw)
        if not isinstance(submissions, Mapping):
            raise FetchError("SEC Form 4 submissions response is not an object")
        filing_bound = self._contract.max_filings_per_window
        if not isinstance(filing_bound, int):
            raise FetchError("SEC Form 4 filing bound is missing")
        candidates = select_form4_filings(
            submissions,
            window,
            max_filings_per_window=filing_bound,
        )
        documents: list[dict[str, Any]] = []
        for candidate in candidates:
            url = derive_form4_xml_url(
                candidate.issuer_cik,
                candidate.accession_number,
                candidate.primary_document,
            )
            raw = self._fetch(client, url)
            documents.append(
                {
                    "candidate": candidate,
                    "source_url": self._validate_url(url),
                    "body": raw.body_bytes,
                }
            )
        self.selected_accessions = tuple(candidate.accession_number for candidate in candidates)
        self.selection_complete = True
        return {"submissions": submissions, "documents": documents}

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("submissions"), Mapping):
            raise FetchError("SEC Form 4 acquisition result is invalid")
        official_cik = str(raw["submissions"].get("cik") or "")
        if official_cik != self._watched_cik:
            raise FetchError("SEC Form 4 official issuer CIK is mismatched")
        documents = raw.get("documents")
        if not isinstance(documents, list):
            raise FetchError("SEC Form 4 documents are invalid")
        if not self.selection_complete:
            raise FetchError("SEC Form 4 selection was not completed")
        candidates = [
            document.get("candidate") for document in documents if isinstance(document, Mapping)
        ]
        document_accessions = [
            candidate.accession_number
            for candidate in candidates
            if isinstance(candidate, Form4ListingCandidate)
        ]
        if document_accessions != list(self.selected_accessions):
            raise FetchError("SEC Form 4 documents do not equal the selected accession set")
        items: list[dict[str, Any]] = []
        for document in documents:
            if not isinstance(document, Mapping):
                raise FetchError("SEC Form 4 document record is invalid")
            candidate = document.get("candidate")
            body = document.get("body")
            source_url = document.get("source_url")
            if not isinstance(candidate, Form4ListingCandidate):
                raise FetchError("SEC Form 4 candidate record is invalid")
            if not isinstance(body, (bytes, str)) or not isinstance(source_url, str):
                raise FetchError("SEC Form 4 document record is incomplete")
            normalized = parse_form4_document(
                body,
                candidate,
                source_url=source_url,
                allowed_schema_versions=self._contract.ownership_xml_schema_versions,
            )
            accepted_at = normalized.candidate.accepted_at
            source = self._source(
                source_id=f"sec-{stable_item_id(self.provider_id, normalized.candidate.accession_number)}",
                name="SEC EDGAR",
                tier="Tier 1",
                kind="filing",
                url=normalized.source_url,
                published_at=accepted_at,
                knowledge=accepted_at,
            )
            items.append(form4_feed_item(normalized, source=source))
        return items


class SecBeneficialOwnershipAdapter(BaseAdapter):
    """SEC EDGAR acquisition unit for one watched Schedule 13D/G filer."""

    provider_id: str = "sec_edgar"
    selection_kind: str = "beneficial_ownership"

    def __init__(
        self,
        manifest: Mapping[str, Any] | ProviderEntry | None = None,
        watched_filer: Any | None = None,
        watched_cik: str | None = None,
    ) -> None:
        super().__init__(manifest)
        if self._contract.contract_version != 4:
            raise ValueError("SEC beneficial ownership requires contract version 4")
        if (
            self._contract.beneficial_ownership_max_filings_per_window != 7
            or self._contract.beneficial_ownership_max_history_files != 1
            or self._contract.beneficial_ownership_max_historical_candidate_documents != 64
            or self._contract.beneficial_ownership_max_reporting_positions != 32
            or self._contract.beneficial_ownership_structured_formats != ("edgarSubmission",)
            or self._contract.beneficial_ownership_schema_versions != ("X0202",)
        ):
            raise ValueError("SEC beneficial-ownership contract bounds are not closed")
        self._watched_cik = str(getattr(watched_filer, "cik", None) or watched_cik or "0001067983")
        self.selected_accessions: tuple[str, ...] = ()
        self.selection_complete = False

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        submissions_raw = self._fetch(
            client, f"https://data.sec.gov/submissions/CIK{self._watched_cik}.json"
        )
        submissions = self._json_body(submissions_raw)
        if not isinstance(submissions, Mapping):
            raise FetchError("SEC beneficial-ownership submissions response is not an object")
        if str(submissions.get("cik") or "") != self._watched_cik:
            raise FetchError("SEC beneficial-ownership official filer CIK is mismatched")
        current_bound = self._contract.beneficial_ownership_max_filings_per_window
        history_bound = self._contract.beneficial_ownership_max_history_files
        candidate_bound = self._contract.beneficial_ownership_max_historical_candidate_documents
        if current_bound is None or history_bound is None or candidate_bound is None:
            raise FetchError("SEC beneficial-ownership request bounds are incomplete")
        current = select_beneficial_ownership_filings(
            submissions, window, max_filings_per_window=current_bound
        )
        current_documents: list[dict[str, Any]] = []
        for candidate in current:
            url = derive_beneficial_ownership_xml_url(
                candidate.filer_cik,
                candidate.accession_number,
                candidate.primary_document,
                allowed_locator_prefixes=self._contract.beneficial_ownership_locator_prefixes,
            )
            response = self._fetch(client, url)
            current_documents.append(
                {
                    "candidate": candidate,
                    "source_url": self._validate_url(url),
                    "body": response.body_bytes,
                }
            )
        history_names = declared_beneficial_ownership_history_files(
            submissions, max_history_files=history_bound
        )
        self.selected_accessions = tuple(candidate.accession_number for candidate in current)
        self.selection_complete = True
        if not current:
            return {
                "submissions": submissions,
                "current_documents": current_documents,
                "historical_candidates": (),
                "historical_documents": [],
                "history_evaluated": False,
                "history_complete": False,
                "history_bound_exhausted": False,
            }

        history_submissions: list[Mapping[str, Any]] = []
        for name in history_names:
            response = self._fetch(client, f"https://data.sec.gov/submissions/{name}")
            history = self._json_body(response)
            if not isinstance(history, Mapping):
                raise FetchError("SEC beneficial-ownership history response is not an object")
            history_submissions.append(history)
        history_candidates, history_bound_exhausted = (
            select_historical_beneficial_ownership_filings_with_status(
                submissions,
                history_submissions,
                window["end"],
                max_history_files=history_bound,
                max_candidate_documents=candidate_bound,
            )
        )
        current_accessions = {candidate.accession_number for candidate in current}
        historical_documents: list[dict[str, Any]] = []
        loaded_historical: dict[str, dict[str, Any]] = {}

        def load_historical_document(candidate: Any) -> dict[str, Any]:
            accession = candidate.accession_number
            cached = loaded_historical.get(accession)
            if cached is not None:
                return cached
            try:
                url = derive_beneficial_ownership_xml_url(
                    candidate.filer_cik,
                    candidate.accession_number,
                    candidate.primary_document,
                    allowed_locator_prefixes=self._contract.beneficial_ownership_locator_prefixes,
                )
            except SchemaError:
                url = derive_beneficial_ownership_historical_url(
                    candidate.filer_cik,
                    candidate.accession_number,
                    candidate.primary_document,
                    allowed_locator_prefixes=self._contract.beneficial_ownership_locator_prefixes,
                )
            response = self._fetch(client, url)
            document = {
                "candidate": candidate,
                "source_url": self._validate_url(url),
                "body": response.body_bytes,
            }
            loaded_historical[accession] = document
            historical_documents.append(document)
            return document

        return {
            "submissions": submissions,
            "current_documents": current_documents,
            "historical_candidates": history_candidates,
            "historical_documents": historical_documents,
            "historical_loader": load_historical_document,
            "history_evaluated": bool(history_names),
            "history_complete": bool(history_names) and not history_bound_exhausted,
            "history_bound_exhausted": history_bound_exhausted,
            "current_accessions": current_accessions,
        }

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("submissions"), Mapping):
            raise FetchError("SEC beneficial-ownership acquisition result is invalid")
        submissions = raw["submissions"]
        if str(submissions.get("cik") or "") != self._watched_cik:
            raise FetchError("SEC beneficial-ownership official filer CIK is mismatched")
        if not self.selection_complete:
            raise FetchError("SEC beneficial-ownership selection was not completed")
        current_documents = raw.get("current_documents")
        historical_candidates = raw.get("historical_candidates")
        historical_documents = raw.get("historical_documents")
        historical_loader = raw.get("historical_loader")
        if not isinstance(current_documents, list) or not isinstance(historical_candidates, tuple):
            raise FetchError("SEC beneficial-ownership current selection is invalid")
        if not isinstance(historical_documents, list):
            raise FetchError("SEC beneficial-ownership historical selection is invalid")
        if historical_loader is not None and not callable(historical_loader):
            raise FetchError("SEC beneficial-ownership historical loader is invalid")
        history_complete = raw.get("history_complete", False)
        history_evaluated = raw.get("history_evaluated", True)
        history_bound_exhausted = raw.get("history_bound_exhausted", False)
        if not all(
            isinstance(value, bool)
            for value in (history_complete, history_evaluated, history_bound_exhausted)
        ):
            raise FetchError("SEC beneficial-ownership history status is invalid")
        candidate_bound = self._contract.beneficial_ownership_max_historical_candidate_documents
        if candidate_bound is None:
            raise FetchError("SEC beneficial-ownership request bounds are incomplete")
        for candidate in historical_candidates:
            if not isinstance(candidate, BeneficialOwnershipListingCandidate):
                raise FetchError("SEC beneficial-ownership historical candidate is invalid")
        current: list[Any] = []
        by_accession: dict[str, Any] = {}
        current_accessions: list[str] = []
        for document in current_documents:
            if not isinstance(document, Mapping):
                raise FetchError("SEC beneficial-ownership current document is invalid")
            candidate = document.get("candidate")
            body = document.get("body")
            source_url = document.get("source_url")
            if not isinstance(candidate, BeneficialOwnershipListingCandidate):
                raise FetchError("SEC beneficial-ownership current candidate is invalid")
            if not isinstance(source_url, str) or not isinstance(body, (bytes, str)):
                raise FetchError("SEC beneficial-ownership current document is incomplete")
            current_accessions.append(candidate.accession_number)
            normalized = parse_beneficial_ownership_document(
                body,
                candidate,
                source_url=source_url,
                allowed_schema_versions=self._contract.beneficial_ownership_schema_versions,
                allowed_locator_prefixes=self._contract.beneficial_ownership_locator_prefixes,
            )
            current.append(normalized)
            by_accession[normalized.candidate.accession_number] = normalized
        if current_accessions != list(self.selected_accessions):
            raise FetchError(
                "SEC beneficial-ownership documents do not equal the selected accession set"
            )

        expected_historical = [
            candidate.accession_number
            for candidate in historical_candidates
            if candidate.accession_number not in set(self.selected_accessions)
        ]
        actual_historical: list[str] = []
        historical_urls: dict[str, str] = {}

        def parse_historical(document: Mapping[str, Any]) -> Any:
            candidate = document.get("candidate")
            body = document.get("body")
            source_url = document.get("source_url")
            if not isinstance(candidate, BeneficialOwnershipListingCandidate):
                raise FetchError("SEC beneficial-ownership historical candidate is invalid")
            if not isinstance(source_url, str) or not isinstance(body, (bytes, str)):
                raise FetchError("SEC beneficial-ownership historical document is incomplete")
            actual_historical.append(candidate.accession_number)
            if candidate.accession_number not in expected_historical:
                raise FetchError("SEC beneficial-ownership historical document is not selected")
            if candidate.accession_number in historical_urls:
                raise FetchError("SEC beneficial-ownership historical document is duplicated")
            historical_urls[candidate.accession_number] = source_url
            if is_unsupported_historical_document(
                body,
                candidate,
                allowed_schema_versions=self._contract.beneficial_ownership_schema_versions,
            ):
                return None
            return parse_beneficial_ownership_document(
                body,
                candidate,
                source_url=source_url,
                allowed_schema_versions=self._contract.beneficial_ownership_schema_versions,
                allowed_locator_prefixes=self._contract.beneficial_ownership_locator_prefixes,
            )

        for document in historical_documents:
            if not isinstance(document, Mapping):
                raise FetchError("SEC beneficial-ownership historical document is invalid")
            normalized = parse_historical(document)
            if normalized is not None:
                by_accession[normalized.candidate.accession_number] = normalized
        if historical_loader is None and actual_historical != expected_historical:
            raise FetchError("SEC beneficial-ownership historical documents are incomplete")

        def load(candidate: Any) -> Any:
            accession = candidate.accession_number
            existing = by_accession.get(accession)
            if existing is not None:
                return existing
            if historical_loader is None:
                return None
            document = historical_loader(candidate)
            if not isinstance(document, Mapping):
                raise FetchError("SEC beneficial-ownership historical loader returned invalid data")
            normalized = parse_historical(document)
            if normalized is not None:
                by_accession[accession] = normalized
            return normalized

        index = build_shared_historical_candidate_index(
            current,
            historical_candidates,
            load,
            max_candidate_documents=candidate_bound,
            history_complete=history_complete,
            history_evaluated=history_evaluated,
            history_bound_exhausted=history_bound_exhausted,
        )
        items: list[dict[str, Any]] = []
        for normalized in sorted(
            current,
            key=lambda value: (value.candidate.accepted_at, value.candidate.accession_number),
        ):
            resolution = index.resolutions.get(normalized.candidate.accession_number)
            if resolution is None:
                compared = compare_beneficial_ownership(
                    normalized, None, unavailable_reason="missing_operand"
                )
            elif resolution.previous is not None:
                compared = compare_beneficial_ownership(normalized, resolution.previous)
            else:
                compared = compare_beneficial_ownership(
                    normalized,
                    None,
                    unavailable_reason=resolution.reason,
                    previous_reference=(
                        resolution.candidate
                        if resolution.reason == "previous_format_unsupported"
                        else None
                    ),
                    previous_reference_url=(
                        historical_urls.get(resolution.candidate.accession_number)
                        if resolution.candidate is not None
                        else None
                    ),
                )
            accession = compared.candidate.accession_number
            item_id = stable_item_id(self.provider_id, accession)
            accepted_at = compared.candidate.accepted_at
            items.append(
                {
                    "id": item_id,
                    "provider_id": self.provider_id,
                    "source": self._source(
                        source_id=f"sec-{item_id}",
                        name="SEC EDGAR",
                        tier="Tier 1",
                        kind="filing",
                        url=compared.source_url,
                        published_at=accepted_at,
                        knowledge=accepted_at,
                    ),
                    "payload": compared.payload,
                }
            )
        return items


class CftcAdapter(BaseAdapter):
    """CFTC Legacy Futures-Only COT positioning adapter."""

    provider_id: str = "cftc"
    PAGE_SIZE = 100
    MAX_PAGES = 100
    MAX_ROWS = PAGE_SIZE * MAX_PAGES

    def __init__(self, manifest: Mapping[str, Any] | ProviderEntry | None = None) -> None:
        super().__init__(manifest)
        self._semantic_v2 = self._contract.contract_version == 2
        if self._semantic_v2 and self._contract.units != {"contracts": "contracts"}:
            raise ValueError("CFTC v2 units are not the closed contract")
        if self._semantic_v2 and (
            self._contract.pagination != "page_number"
            or not isinstance(self._contract.empty_valid_for_window, bool)
            or self._contract.empty_valid_for_window
        ):
            raise ValueError("CFTC v2 requires page-number complete-report acquisition")

    def _url(self, query: str) -> str:
        # Fetch URLs are governed by fetch_hosts, not source_link_hosts;
        # SoQL query parameters are intentionally not published as evidence.
        return f"https://publicreporting.cftc.gov/resource/6dca-aqww.json?{query}"

    @staticmethod
    def _query(params: Mapping[str, Any]) -> str:
        from urllib.parse import urlencode

        # Keep SoQL's dollar-prefixed names and commas readable while encoding
        # values (including spaces) deterministically.
        return urlencode(params, doseq=True, safe="$,")

    def _page_url(self, report_date: str, offset: int) -> str:
        # ``id`` is the Socrata stable row identifier used as the final
        # deterministic tie-breaker after market code.
        return self._url(
            self._query(
                {
                    "$where": f"report_date_as_yyyy_mm_dd='{report_date}'",
                    "$order": "cftc_contract_market_code ASC, id ASC",
                    "$limit": self.PAGE_SIZE,
                    "$offset": offset,
                }
            )
        )

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        if not self._semantic_v2:
            return self._fetch(
                client,
                "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=100",
            )
        # Date discovery is separately managed, then each selected date is
        # retrieved through a bounded sequential page plan.
        discovery = self._fetch(
            client,
            self._url(
                self._query(
                    {
                        "$select": "report_date_as_yyyy_mm_dd",
                        "$group": "report_date_as_yyyy_mm_dd",
                        "$order": "report_date_as_yyyy_mm_dd DESC",
                        "$limit": 3,
                    }
                )
            ),
        )
        discovery_rows = self._json_body(discovery)
        if not isinstance(discovery_rows, list):
            raise FetchError("CFTC date discovery response is not a list")
        current_date, previous_date = select_report_dates(discovery_rows, window["end"])
        reports: dict[str, list[dict[str, Any]]] = {}
        for report_date in (current_date, previous_date):
            if report_date is None:
                continue
            rows: list[dict[str, Any]] = []
            offset = 0
            previous_key: tuple[str, str] | None = None
            seen_stable_ids: set[str] = set()
            for page_number in range(self.MAX_PAGES):
                page_raw = self._fetch(client, self._page_url(report_date, offset))
                page = self._json_body(page_raw)
                if not isinstance(page, list) or len(page) > self.PAGE_SIZE:
                    raise FetchError("CFTC pagination page is invalid")
                for row in page:
                    if not isinstance(row, dict):
                        raise FetchError("CFTC pagination row is invalid")
                    actual_date = str(row.get("report_date_as_yyyy_mm_dd", ""))[:10]
                    code = str(row.get("cftc_contract_market_code") or "").strip()
                    stable_id = str(row.get("id") or row.get("_id") or "")
                    if actual_date != report_date or not code or not stable_id:
                        raise FetchError("CFTC pagination row does not match pinned query")
                    if stable_id in seen_stable_ids:
                        raise FetchError("CFTC pagination repeats a stable row identity")
                    seen_stable_ids.add(stable_id)
                    key = (code, stable_id)
                    if previous_key is not None and key <= previous_key:
                        raise FetchError("CFTC pagination ordering is invalid or repeated")
                    previous_key = key
                    rows.append(row)
                if len(rows) > self.MAX_ROWS:
                    raise FetchError("CFTC pagination row bound exceeded")
                if len(page) < self.PAGE_SIZE:
                    break
                offset += self.PAGE_SIZE
            else:
                raise FetchError("CFTC pagination page bound exceeded")
            if not rows:
                raise FetchError("CFTC report is empty and not valid for window")
            reports[report_date] = rows
        return {
            "current_date": current_date,
            "previous_date": previous_date,
            "current_rows": reports[current_date],
            "previous_rows": reports.get(previous_date) if previous_date else None,
        }

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        if not self._semantic_v2:
            return self._normalize_v1(raw, window)
        if not isinstance(raw, Mapping):
            raise FetchError("CFTC acquisition result is invalid")
        current_date = str(raw.get("current_date") or "")
        previous_date = raw.get("previous_date")
        semantic = compare_reports(
            raw.get("current_rows") or [],
            raw.get("previous_rows"),
            current_date=current_date,
            previous_date=str(previous_date) if previous_date else None,
        )
        # Every market points at its own official Socrata row. A single shared
        # dataset landing page would make Feed deduplication collapse all
        # same-URL positioning items into one survivor.
        dataset_url = "https://publicreporting.cftc.gov/resource/6dca-aqww"
        published = publication_boundary(current_date)
        items: list[dict[str, Any]] = []
        for record in semantic:
            item_id = stable_item_id(self.provider_id, record["stable_id"])
            payload = record["payload"]
            source = self._source(
                source_id=f"cftc-{item_id}",
                name="CFTC Commitments of Traders",
                tier="Tier 1",
                kind="positioning",
                url=self._validate_url(f"{dataset_url}/{record['stable_id']}.json"),
                published_at=published,
                knowledge=published,
            )
            items.append(
                {
                    "id": item_id,
                    "provider_id": self.provider_id,
                    "source": source,
                    "payload": payload,
                }
            )
        return items

    def _normalize_v1(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
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
                        "position": {"value": _canonical_number(value), "unit": "contracts"},
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
            item = {
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
            items.append(self._attach_semantic_context(item))
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
            item = {
                "id": stable_item_id(self.provider_id, url),
                "provider_id": self.provider_id,
                "source": source,
                "payload": payload,
            }
            items.append(self._attach_semantic_context(item, source_record=entry))
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
            item = {
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
            items.append(self._attach_semantic_context(item))
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
            item = {
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
            items.append(self._attach_semantic_context(item))
        return items


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
        published: str | None = None
        for source, pattern in (
            (title, r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})"),
            (href, r"(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})"),
            (title + href, r"(20\d{2})(\d{2})(\d{2})"),
        ):
            for match in re.finditer(pattern, source):
                try:
                    year, month, day = (int(part) for part in match.groups())
                    candidate = datetime(year, month, day, tzinfo=UTC)
                except ValueError:
                    continue
                published = _format_timestamp(candidate)
                break
            if published is not None:
                break
        if published is None:
            continue
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


def build_registry(
    providers: Mapping[str, ProviderEntry] | Sequence[ProviderEntry] | None = None,
) -> ProviderRegistry:
    """Build the explicit registry for the eight required Feed Providers."""
    resolved_runtime = providers is not None
    if providers is None:
        from .manifest import load_all_manifests

        providers = {
            pid: manifest_to_provider_entry(manifest)
            for pid, manifest in load_all_manifests().items()
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
    }
    adapters = {
        provider_id: adapter_types[provider_id](provider)
        for provider_id, provider in providers.items()
        if provider_id in adapter_types
    }
    return ProviderRegistry(adapters)
