"""Bounded HTTP/RSS helpers and source adapters.

Design section 2/3: provider clients contact only configured HTTPS hosts and
allowlisted redirects, enforce response and decompression limits, use safe
XML parsing (feedparser's sanitizer), and never dereference source URLs.
"""

from __future__ import annotations

import hashlib
import ipaddress
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import feedparser

from .urls import canonicalize_url

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB


class FetchError(ValueError):
    """Provider fetch failed (typed at the orchestration boundary)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.retryable = retryable


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    body_bytes: bytes
    content_type: str | None


def bounded_fetch(
    client: Any,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 20.0,
    max_bytes: int = DEFAULT_MAX_BYTES,
    fetch_rules: Sequence[Any] = (),
    redirect_rules: Sequence[Any] = (),
) -> FetchResult:
    """Fetch ``url`` with response and decompression limits.

    ``client`` is an injected httpx.Client (or fake). The requested endpoint
    and the final URL after redirects are checked against separate manifest
    allowlists before the response body is admitted.
    """
    _validate_fetch_url(url, fetch_rules, where="fetch_url")
    try:
        resp = client.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    except Exception as exc:  # httpx.TransportError etc.
        import httpx

        retryable = isinstance(
            exc,
            (
                httpx.TimeoutException,
                httpx.TransportError,
                TimeoutError,
                ConnectionError,
                OSError,
            ),
        )
        raise FetchError(
            f"fetch failed for {urlsplit(url).hostname}: {exc.__class__.__name__}",
            retryable=retryable,
        ) from exc
    final_url = str(getattr(resp, "url", url) or url)
    final_rules = redirect_rules if final_url != url else fetch_rules
    _validate_fetch_url(final_url, final_rules, where="redirect_url")
    status = int(resp.status_code)
    if status < 200 or status >= 300:
        retry_after = _parse_retry_after(resp.headers.get("retry-after"))
        retryable = status in (408, 409, 429) or status >= 500
        detail = f"HTTP {status} from {urlsplit(final_url).hostname}"
        if retry_after is not None:
            detail += f" (Retry-After: {retry_after}s)"
        raise FetchError(
            detail,
            status_code=status,
            retry_after_seconds=retry_after,
            retryable=retryable,
        )
    body = resp.content
    if len(body) > max_bytes:
        raise FetchError(f"response exceeds {max_bytes} bytes")
    return FetchResult(
        url=str(resp.url),
        status=status,
        body_bytes=body,
        content_type=resp.headers.get("content-type"),
    )


def _validate_fetch_url(url: str, rules: Sequence[Any], *, where: str) -> None:
    """Reject unsafe fetch/redirect endpoints against FetchRule hosts."""
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise FetchError(f"{where} is malformed") from exc
    if parts.scheme.lower() != "https":
        raise FetchError(f"{where} must use https")
    if not host or parts.username is not None or parts.password is not None:
        raise FetchError(f"{where} contains forbidden authority")
    if "%" in parts.netloc or parts.fragment:
        raise FetchError(f"{where} contains forbidden authority or fragment")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise FetchError(f"{where} must not use an IP address")
    normalized_host = host.rstrip(".").lower()
    effective_port = port or 443
    for rule in rules:
        rule_host = str(rule.host).rstrip(".").lower()
        host_match = normalized_host == rule_host or (
            bool(rule.allow_subdomains) and normalized_host.endswith(f".{rule_host}")
        )
        if host_match and effective_port in tuple(int(p) for p in rule.allowed_ports):
            return
    raise FetchError(f"{where} outside manifest host allowlist")


def _parse_retry_after(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0, int((parsed.astimezone(UTC) - datetime.now(UTC)).total_seconds()))


def safe_parse_rss(body: bytes, *, charset: str = "utf-8") -> Any:
    """Parse RSS/Atom with feedparser's sanitizer (no raw HTML execution)."""
    try:
        text = body.decode(charset)
    except UnicodeDecodeError as exc:
        raise FetchError(f"response not decodable as {charset}") from exc
    parsed = feedparser.parse(text)
    head = text[:200].lstrip().lower()
    looks_like_feed = (
        head.startswith("<?xml") or "<rss" in head or "<feed" in head or "<rdf" in head
    )
    if not looks_like_feed:
        raise FetchError("response is not an RSS/Atom feed")
    if parsed.get("bozo") and not parsed.get("entries"):
        raise FetchError("RSS parse error with no entries")
    return parsed


def stable_item_id(provider_id: str, record_identity: str) -> str:
    digest = hashlib.sha256(f"{provider_id}|{record_identity}".encode()).hexdigest()
    return f"item_{digest[:32]}"


def validate_provider_url(url: str, *, rules: Any, secrets: Sequence[str] = ()) -> str:
    """Provider-bound URL validation returning the canonical URL."""
    return canonicalize_url(url, rules=rules, secrets=secrets, where="source_url")
