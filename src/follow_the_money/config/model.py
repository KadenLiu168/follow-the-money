"""Configuration data model for Follow the Money.

Frozen dataclasses mirror the closed versioned YAML configuration. No field
is optional at runtime: defaults are explicit v1 values shipped in
``config/*.yaml``, and the loader rejects unknown/absent fields rather than
inventing hidden defaults.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Small closed value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceFamily:
    """One source family (for corroboration counting)."""

    id: str
    name: str
    tier: str  # Tier 1 | Tier 2 | Tier 3


@dataclass(frozen=True)
class Entity:
    """A resolved entity in the deterministic registry."""

    id: str
    name: str
    name_zh: str
    aliases: tuple[str, ...] = ()
    kind: str = "institution"  # institution | company | index | asset | other


@dataclass(frozen=True)
class MarketRole:
    """One of the 13 dashboard roles."""

    id: str
    name: str
    name_zh: str
    instrument: str
    unit: str
    session_class: str = "exchange_traded"  # exchange_traded | continuous_247 | continuous_245
    kind: str = "price"  # price | yield | index | fx | commodity | crypto


@dataclass(frozen=True)
class Session:
    """Configured session policy for an asset class."""

    id: str
    calendar: str  # e.g. XNYS, XSHG, XHKG
    session_class: str
    timezone: str = "UTC"
    annualization_factor: str = "252"  # Decimal string


@dataclass(frozen=True)
class WatchCompany:
    """A watched company for SEC EDGAR filing filtering."""

    cik: str
    name: str
    tickers: tuple[str, ...] = ()


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
    allow_subdomains: bool = False
    allowed_ports: tuple[int, ...] = (443,)
    allowed_query_params: tuple[str, ...] = ()
    query_value_grammar: str = "any"  # any | plain | numeric
    drop_query_params: tuple[str, ...] = ()


@dataclass(frozen=True)
class FetchRule:
    """Fetch/redirect allowlist entry."""

    host: str
    allow_subdomains: bool = False
    allowed_ports: tuple[int, ...] = (443,)


@dataclass(frozen=True)
class ProviderEntry:
    """One enabled/disabled provider and its closed contract."""

    id: str
    name: str
    enabled: bool
    verified: bool
    default_enabled: bool
    group: str  # coverage group id
    source_family_id: str
    tier: str
    user_agent: str
    fetch_hosts: tuple[FetchRule, ...]
    redirect_hosts: tuple[FetchRule, ...]
    source_link_hosts: tuple[SourceLinkRule, ...]
    rate_policy: RatePolicy | None
    allowed_charset: str = "utf-8"
    allowed_bom: bool = False
    allowed_content_type_header: str | None = None
    pagination: str = "none"  # none | cursor | page_number
    empty_valid_for_window: bool = False
    response_limit_bytes: int = 10 * 1024 * 1024
    credentials_required: bool = False
    verification_date: str | None = None
    contract_url: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CoverageRow:
    """One row of the six-group v1 mandatory coverage matrix."""

    group: str
    members: tuple[str, ...]  # provider ids
    minimum: int
    capability: str  # e.g. "release_and_calendar", "watched_company_filings"
    optional: bool = False


@dataclass(frozen=True)
class CoverageMatrix:
    rows: tuple[CoverageRow, ...]
    version: str = "v1"

    def row(self, group: str) -> CoverageRow:
        for r in self.rows:
            if r.group == group:
                return r
        raise KeyError(group)


@dataclass(frozen=True)
class FeedLimits:
    """Shipped v1 Feed runtime limits."""

    bootstrap_lookback_hours: int = 72
    gap_threshold_hours: int = 72
    calendar_horizon_hours: int = 26
    pre_commit_deadline_seconds: int = 300
    commit_reserve_seconds: int = 15
    global_concurrency: int = 8
    per_host_concurrency: int = 2
    http_attempt_timeout_seconds: int = 20
    max_attempts: int = 3
    max_decompressed_response_bytes: int = 10 * 1024 * 1024
    max_items_per_provider: int = 2000
    max_title_code_points: int = 300
    max_snippet_code_points: int = 1000
    max_url_characters: int = 2048
    max_observations_per_instrument: int = 260
    max_serialized_feed_bytes: int = 50 * 1024 * 1024
    lock_timeout_seconds: int = 60


@dataclass(frozen=True)
class PassConfig:
    attempt_timeout_seconds: int
    max_output_tokens: int
    dynamic_cap_bytes: int
    concurrency: int
    max_attempts: int = 2


@dataclass(frozen=True)
class LlmRuntime:
    """Single-model OpenAI Responses API runtime limits."""

    model: str
    organization: str | None = None
    project: str | None = None
    max_attempts_per_invocation: int = 2
    static_request_cap_bytes: int = 16 * 1024
    resolver: PassConfig = PassConfig(30, 72000, 32 * 1024, 4)
    analyst: PassConfig = PassConfig(45, 72000, 48 * 1024, 4)
    editor: PassConfig = PassConfig(45, 72000, 72 * 1024, 1)
    audit: PassConfig = PassConfig(30, 56000, 72 * 1024, 1)
    max_resolver_blocks: int = 40
    max_analyst_packets: int = 20
    max_output_response_bytes: tuple[int, int, int, int] = (64, 64, 64, 48)
    brief_pre_commit_deadline_seconds: int = 300
    brief_commit_reserve_seconds: int = 15
    reasoning_mode: str = "none"


@dataclass(frozen=True)
class SurpriseScale:
    """Versioned per-series normalized-surprise scale (percentage points)."""

    series_id: str
    scale: str  # Decimal string, positive
    note: str | None = None


@dataclass(frozen=True)
class AssetGroupMapping:
    """One of the exact nine asset groups and its deterministic proxies."""

    group: str
    name_zh: str
    proxies: tuple[str, ...]  # dashboard role ids


@dataclass(frozen=True)
class Scoring:
    """Deterministic scoring contract (v1 normative values)."""

    significance_weights: tuple[int, ...] = (30, 20, 20, 20, 10)
    freshness_bins: tuple[tuple[int, int], ...] = ((6, 100), (12, 75), (24, 50), (48, 25))
    freshness_older_score: int = 0
    morning_weights: tuple[int, int, int, int] = (40, 25, 20, 15)
    base_priority_weights: tuple[str, str] = ("0.70", "0.30")
    min_component_coverage: str = "60"
    full_priority_threshold: str = "60"
    compact_priority_threshold: str = "40"
    family_penalty: str = "15"
    target_count: int = 10
    hard_max_count: int = 12
    max_full_events: int = 3
    anomaly_z_threshold: str = "2.0"
    scope_map: Mapping[str, int] = field(
        default_factory=lambda: {
            "single_entity": 25,
            "sector": 50,
            "single_market": 75,
            "cross_market": 100,
            "unknown": 0,
        }
    )
    fundamental_depth_map: Mapping[str, int] = field(
        default_factory=lambda: {
            "headline": 25,
            "operating_or_policy": 50,
            "balance_sheet_or_liquidity": 75,
            "systemic": 100,
            "unknown": 0,
        }
    )
    reversibility_map: Mapping[str, int] = field(
        default_factory=lambda: {
            "high": 25,
            "medium": 50,
            "low": 75,
            "effectively_irreversible": 100,
            "unknown": 0,
        }
    )
    structural_horizon_map: Mapping[str, int] = field(
        default_factory=lambda: {
            "intraday": 0,
            "days": 25,
            "weeks": 50,
            "months": 75,
            "years_plus": 100,
            "unknown": 0,
        }
    )
    surprise_bins: tuple[tuple[str, str, int], ...] = (
        ("0.5", "<", 0),
        ("1", "<", 25),
        ("2", "<", 50),
        ("3", "<", 75),
        ("3", ">=", 100),
    )
    asset_groups: tuple[AssetGroupMapping, ...] = (
        AssetGroupMapping("cn_hk_equities", "中国香港股票", ("csi300", "hsi")),
        AssetGroupMapping("us_equities", "美国股票", ("sp500",)),
        AssetGroupMapping("us_rates", "美国利率", ("us2y", "us10y")),
        AssetGroupMapping("china_rates", "中国利率", ("cn10y",)),
        AssetGroupMapping("usd_fx", "美元汇率", ("dxy", "usdcnh")),
        AssetGroupMapping("industrial_commodities", "工业金属", ("copper",)),
        AssetGroupMapping("energy", "能源", ("wti",)),
        AssetGroupMapping("precious_metals", "贵金属", ("gold",)),
        AssetGroupMapping("crypto", "加密货币", ("btc",)),
    )
    exposure_map: Mapping[str, int] = field(
        default_factory=lambda: {"direct": 100, "indirect": 50, "none": 0, "unknown": 0}
    )
    catalyst_map: Mapping[str, int] = field(default_factory=lambda: {"present": 100, "absent": 0})
    surprise_scales: tuple[SurpriseScale, ...] = field(
        default_factory=lambda: (
            SurpriseScale("us_cpi_all_items_sa_mom", "0.1"),
            SurpriseScale("us_core_pce_mom", "0.1"),
            SurpriseScale("us_ppi_final_demand_sa_mom", "0.1"),
        )
    )


@dataclass(frozen=True)
class MarketState:
    """v1 Market State Vector classification rules."""

    z_supportive: str = "0.5"
    breadth_supportive: str = "0.20"
    regime_sum_threshold: str = "2"
    risk_appetite_min_votes: int = 2
    rates_min_votes: int = 1
    liquidity_min_votes: int = 1
    growth_min_votes: int = 1
    inflation_min_votes: int = 1
    required_known_dimensions: int = 4
    rules_order: tuple[str, ...] = ("risk_off", "risk_on", "neutral")


@dataclass(frozen=True)
class CalendarPolicy:
    """Watchlist calendar policy."""

    allowed_priorities: tuple[str, ...] = ("critical", "high")
    max_items: int = 6
    stale_after_minutes: int = 30
    hard_lag_hours: int = 2


@dataclass(frozen=True)
class AuditSeverity:
    """Language-audit finding severity mapping."""

    critical: tuple[str, ...] = (
        "causal_overclaim",
        "inference_as_fact",
        "unsupported_conclusion",
        "fact_modification",
        "trading_instruction",
        "wrong_language",
    )
    warning: tuple[str, ...] = ("excessive_certainty", "missing_uncertainty")


@dataclass(frozen=True)
class SafetyLexicon:
    """Prohibited trading-instruction patterns (Chinese and English)."""

    zh_terms: tuple[str, ...] = (
        "买入",
        "卖出",
        "加仓",
        "减仓",
        "建仓",
        "清仓",
        "入场",
        "离场",
        "止损",
        "止盈",
        "目标价",
    )
    en_terms: tuple[str, ...] = (
        "buy",
        "sell",
        "add",
        "reduce",
        "position size",
        "entry",
        "exit",
        "stop-loss",
        "target price",
    )
    descriptive_exceptions: tuple[str, ...] = (
        "该政策旨在抑制过热",
        "基金净买入额",
        "净卖出规模",
        "historical",
        "descriptive",
    )


@dataclass(frozen=True)
class RateRegistry:
    """Persistent output-root rate-state registry contract."""

    version: str = "1"
    crash_cooldown_hours: int = 24
    schema_file: str = "rate-registry.json"


@dataclass(frozen=True)
class AppConfig:
    """Fully validated application configuration."""

    schema_version: int
    name: str
    providers: tuple[ProviderEntry, ...]
    coverage: CoverageMatrix
    source_families: tuple[SourceFamily, ...]
    entities: tuple[Entity, ...]
    roles: tuple[MarketRole, ...]
    sessions: tuple[Session, ...]
    watched_companies: tuple[WatchCompany, ...]
    feed: FeedLimits
    llm: LlmRuntime
    scoring: Scoring
    market_state: MarketState
    calendar: CalendarPolicy
    audit_severity: AuditSeverity
    safety_lexicon: SafetyLexicon
    rate_registry: RateRegistry
    output_root: str = "feeds"
    runs_root: str = "runs"
    timezone: str = "Asia/Shanghai"
    freshness_limit_minutes: int = 30
    normal_lag_hours: int = 2

    def provider(self, provider_id: str) -> ProviderEntry:
        for p in self.providers:
            if p.id == provider_id:
                return p
        raise KeyError(provider_id)

    def role(self, role_id: str) -> MarketRole:
        for r in self.roles:
            if r.id == role_id:
                return r
        raise KeyError(role_id)

    @property
    def role_ids(self) -> tuple[str, ...]:
        return tuple(r.id for r in self.roles)


# Canonical order of the 13 v1 dashboard roles (design section 14).
V1_ROLE_IDS: tuple[str, ...] = (
    "sp500",
    "csi300",
    "hsi",
    "vix",
    "us2y",
    "us10y",
    "cn10y",
    "dxy",
    "usdcnh",
    "copper",
    "wti",
    "gold",
    "btc",
)
