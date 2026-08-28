"""Credential-free canonical URL validation bound to provider contracts.

Design section 2 (source-link policy):

- Only HTTPS, no userinfo, no IP literals, no percent-encoding in the
  authority/host, no undeclared non-default port, no suffix-lookalike hosts.
- Fragment is dropped; declared tracking parameters are dropped; remaining
  query pairs follow the manifest's stable ordering/value grammar.
- Every raw percent escape must be a complete ``%HH`` triplet; a bare or
  truncated ``%`` rejects the item.
- Before and after canonicalization the exactly-once percent-decoded path
  segments plus query names/values are scanned for loaded secrets
  (case-sensitive substring match). Residual ``%HH`` after that single
  decode is rejected as ambiguous double-encoding.
- Only the validated credential-free canonical URL is hashed/retained.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Sequence
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from ..config.model import SourceLinkRule

_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_BARE_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_PLAIN_QUERY_VALUE = re.compile(r"[A-Za-z0-9._~-]*")
_NUMERIC_QUERY_VALUE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_CREDENTIAL_QUERY_NAMES = {
    "token",
    "api_key",
    "apikey",
    "key",
    "secret",
    "access_token",
    "password",
    "passwd",
    "auth",
    "authorization",
    "signature",
    "sig",
    "credential",
    "credentials",
}


class UrlValidationError(ValueError):
    """Source URL failed provider-bound validation."""


def _looks_like_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _idna_normalize(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UrlValidationError(f"malformed IDNA host {host!r}") from exc


def _host_matches(host: str, rule: SourceLinkRule) -> bool:
    if host == rule.host:
        return True
    if rule.allow_subdomains:
        return host.endswith("." + rule.host)
    return False


def canonicalize_url(
    raw_url: str,
    *,
    rules: Sequence[SourceLinkRule],
    secrets: Sequence[str] = (),
    where: str = "url",
) -> str:
    """Validate and canonicalize a source URL against provider rules.

    Returns the credential-free canonical URL. Raises :class:`UrlValidationError`
    on any violation; rejected raw/decoded material is never logged.
    """
    if not raw_url.startswith("https://"):
        raise UrlValidationError(f"{where}: URL must be https")
    try:
        parts = urlsplit(raw_url)
    except ValueError as exc:
        raise UrlValidationError(f"{where}: malformed URL") from exc

    if parts.username is not None or parts.password is not None:
        raise UrlValidationError(f"{where}: userinfo rejected")
    host_raw = (parts.hostname or "").rstrip(".")
    if _looks_like_ip(host_raw):
        raise UrlValidationError(f"{where}: IP-literal host rejected")
    if "%" in host_raw:
        raise UrlValidationError(f"{where}: percent-encoding in authority rejected")
    host = _idna_normalize(host_raw).lower()
    matched_rules = [rule for rule in rules if _host_matches(host, rule)]
    if not matched_rules:
        raise UrlValidationError(f"{where}: host {host!r} outside source_link_hosts rules")

    port = parts.port
    if port is not None:
        allowed_ports: set[int] = set()
        for rule in matched_rules:
            allowed_ports.update(rule.allowed_ports)
        if port not in allowed_ports:
            raise UrlValidationError(f"{where}: undeclared port {port}")

    # Path percent-escape validation.
    path = parts.path or "/"
    if _BARE_PERCENT.search(path):
        raise UrlValidationError(f"{where}: bare/truncated/non-hex percent escape in path")

    # Query validation: split once, drop tracking params, keep allowed ones.
    query_pairs: list[tuple[str, str]] = []
    if parts.query:
        try:
            raw_pairs = parse_qsl(parts.query, keep_blank_values=True)
        except ValueError:
            raise UrlValidationError(f"{where}: malformed query")
        allowed_names: set[str] = set()
        grammars_by_name: dict[str, set[str]] = {}
        drop_names: set[str] = set()
        for rule in matched_rules:
            allowed_names.update(rule.allowed_query_params)
            for name in rule.allowed_query_params:
                grammars_by_name.setdefault(name, set()).add(rule.query_value_grammar)
            drop_names.update(rule.drop_query_params)
        for name, value in raw_pairs:
            if _BARE_PERCENT.search(name) or _BARE_PERCENT.search(value):
                raise UrlValidationError(f"{where}: bare percent escape in query")
            if name.lower() in _CREDENTIAL_QUERY_NAMES:
                raise UrlValidationError(f"{where}: credential-named query parameter {name!r}")
            if name in drop_names:
                continue
            if name not in allowed_names:
                raise UrlValidationError(f"{where}: unlisted query parameter {name!r}")
            grammars = grammars_by_name[name]
            grammar_matches = "any" in grammars or (
                "plain" in grammars and _PLAIN_QUERY_VALUE.fullmatch(value) is not None
            )
            grammar_matches = grammar_matches or (
                "numeric" in grammars and _NUMERIC_QUERY_VALUE.fullmatch(value) is not None
            )
            if not grammar_matches:
                raise UrlValidationError(f"{where}: query value grammar rejected {name!r}")
            query_pairs.append((name, value))

    # Build canonical URL: lowercase scheme/host, drop default port, drop
    # fragment, stable query ordering (sorted by name then value).
    canonical_host = host
    netloc = canonical_host
    if port is not None and port != 443:
        netloc = f"{canonical_host}:{port}"
    ordered_pairs = sorted(query_pairs, key=lambda kv: (kv[0], kv[1]))
    query = urlencode(ordered_pairs, doseq=True)
    canonical = urlunsplit(("https", netloc, path, query, ""))

    # Secret scan: exactly-once percent-decode of path segments + query
    # names/values; residual %HH after that decode is rejected as ambiguous.
    decoded_path = unquote(path)
    if _PERCENT_ESCAPE.search(decoded_path):
        raise UrlValidationError(f"{where}: residual %HH after one decode (double-encoding)")
    material = decoded_path + "|" + "&".join(f"{k}={v}" for k, v in query_pairs)
    for secret in secrets:
        if not secret:
            continue
        if secret in material:
            raise UrlValidationError(f"{where}: secret material found in URL")

    return canonical
