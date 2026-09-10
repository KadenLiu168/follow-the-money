"""Typed, Feed-only configuration models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFamily:
    """Provider provenance family."""

    id: str
    name: str
    tier: str


@dataclass(frozen=True)
class WatchCompany:
    """SEC EDGAR watched-company filter."""

    cik: str
    name: str
    tickers: tuple[str, ...]


@dataclass(frozen=True)
class RatePolicy:
    """Closed per-scope token-bucket rate policy."""

    scope_id: str
    capacity: int
    refill_period_seconds: int
    minimum_interval_seconds: int
    unlimited: bool = False
    shared_host: str | None = None


@dataclass(frozen=True)
class SourceLinkRule:
    """Provider-bound source-link host rule."""

    host: str
    allow_subdomains: bool
    allowed_ports: tuple[int, ...]
    allowed_query_params: tuple[str, ...]
    query_value_grammar: str
    drop_query_params: tuple[str, ...]


@dataclass(frozen=True)
class FetchRule:
    """Fetch/redirect allowlist entry."""

    host: str
    allow_subdomains: bool
    allowed_ports: tuple[int, ...]


@dataclass(frozen=True)
class FreshnessContract:
    """Provider-owned cadence contract."""

    cadence: str
    reference_time: str
    valid_for_seconds: int | None = None


@dataclass(frozen=True)
class ProviderEntry:
    """One resolved verified Provider contract."""

    id: str
    name: str
    enabled: bool
    verified: bool
    default_enabled: bool
    source_family_id: str
    tier: str
    user_agent: str
    fetch_hosts: tuple[FetchRule, ...]
    redirect_hosts: tuple[FetchRule, ...]
    source_link_hosts: tuple[SourceLinkRule, ...]
    rate_policy: RatePolicy | None
    allowed_charset: str
    allowed_bom: bool
    allowed_content_type_header: str | None
    pagination: str
    empty_valid_for_window: bool
    response_limit_bytes: int
    credentials_required: bool
    verification_date: str | None
    contract_url: str | None
    notes: str | None
    contract_version: int
    authentication: str
    protocol: str
    attempt_timeout_seconds: int
    request_limit_bytes: int
    time_knowledge_time: str
    payload_types: tuple[str, ...]
    identity_stable_record_id: str
    units: Mapping[str, str]
    freshness: FreshnessContract
    fixture_provenance_source: str
    fixture_files: tuple[str, ...]
    coverage_groups: tuple[str, ...]


@dataclass(frozen=True)
class CoverageRow:
    """One mandatory Feed coverage row."""

    group: str
    members: tuple[str, ...]
    minimum: int
    capability: str
    optional: bool


@dataclass(frozen=True)
class CoverageMatrix:
    rows: tuple[CoverageRow, ...]
    version: str = "v1"

    def row(self, group: str) -> CoverageRow:
        for row in self.rows:
            if row.group == group:
                return row
        raise KeyError(group)


@dataclass(frozen=True)
class FeedLimits:
    """Normative runtime limits used by the Evidence Feed."""

    bootstrap_lookback_hours: int
    gap_threshold_hours: int
    pre_commit_deadline_seconds: int
    commit_reserve_seconds: int
    global_concurrency: int
    per_host_concurrency: int
    http_attempt_timeout_seconds: int
    max_attempts: int
    max_decompressed_response_bytes: int
    max_items_per_provider: int
    max_title_code_points: int
    max_snippet_code_points: int
    max_url_characters: int
    max_serialized_feed_bytes: int
    lock_timeout_seconds: int


@dataclass(frozen=True)
class RateRegistry:
    """Persistent runtime-state rate registry contract."""

    version: str
    crash_cooldown_hours: int
    schema_file: str


@dataclass(frozen=True)
class AppConfig:
    """Fully validated Feed-only application configuration."""

    schema_version: int
    name: str
    providers: tuple[ProviderEntry, ...]
    coverage: CoverageMatrix
    source_families: tuple[SourceFamily, ...]
    watched_companies: tuple[WatchCompany, ...]
    feed: FeedLimits
    rate_registry: RateRegistry
    runtime_state_root: str
    output_root: str
    runs_root: str
    timezone: str

    def provider(self, provider_id: str) -> ProviderEntry:
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        raise KeyError(provider_id)


REQUIRED_PROVIDER_IDS: tuple[str, ...] = (
    "federal_reserve",
    "bls",
    "pboc",
    "nbs",
    "sse",
    "szse",
    "sec_edgar",
    "cftc",
)

SUPPORTED_FEED_PAYLOAD_TYPES: tuple[str, ...] = (
    "news",
    "macro_release",
    "policy",
    "positioning",
    "filing",
)

REQUIRED_COVERAGE_GROUPS = frozenset(
    {
        "us_official_macro_policy",
        "us_company_filings",
        "china_official_macro_policy",
        "china_exchange_evidence",
        "cftc_positioning",
    }
)
