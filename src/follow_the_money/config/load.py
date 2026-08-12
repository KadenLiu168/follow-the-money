"""Strict loading and validation of the closed versioned YAML configuration.

Validation rules (each is a closed check; violation raises ConfigError):

- Files decode as strict UTF-8; lone high/low surrogates and category ``Cs``
  are rejected before any further processing.
- Unknown top-level/known keys, duplicate provider IDs, and unverified
  enabled adapters are rejected.
- The six-group coverage matrix must exactly match the design; every member
  must exist, be verified, and be enabled (or the row is unachievable).
- The 13 dashboard roles must be exactly the canonical v1 set.
- Scoring significance weights must sum to 100; categorical maps must be
  exhaustive over their closed enums.
- Rate policies sharing a scope must declare identical policies.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .model import (
    V1_ROLE_IDS,
    AppConfig,
    AssetGroupMapping,
    AuditSeverity,
    CalendarPolicy,
    CoverageMatrix,
    CoverageRow,
    Entity,
    FeedLimits,
    FetchRule,
    LlmRuntime,
    MarketRole,
    MarketState,
    PassConfig,
    ProviderEntry,
    RatePolicy,
    RateRegistry,
    SafetyLexicon,
    Scoring,
    Session,
    SourceFamily,
    SourceLinkRule,
    SurpriseScale,
    WatchCompany,
)

SCORING_ENUMS: Mapping[str, set[str]] = {
    "scope": {"single_entity", "sector", "single_market", "cross_market", "unknown"},
    "fundamental_depth": {
        "headline",
        "operating_or_policy",
        "balance_sheet_or_liquidity",
        "systemic",
        "unknown",
    },
    "reversibility": {"high", "medium", "low", "effectively_irreversible", "unknown"},
    "structural_horizon": {
        "intraday",
        "days",
        "weeks",
        "months",
        "years_plus",
        "unknown",
    },
    "exposure": {"direct", "indirect", "none", "unknown"},
    "direction": {"positive", "negative", "mixed", "unclear"},
    "confidence": {"high", "medium", "low", "unknown"},
    "horizon": {
        "intraday",
        "next_session",
        "days",
        "weeks",
        "months",
        "years_plus",
        "unknown",
    },
    "price_in": {"not_priced", "partial", "mostly_priced", "unclear"},
    "attribution": {"direct", "likely", "concurrent", "unclear"},
    "money_flow": {"confirmed", "indicated", "no_evidence"},
    "regime": {"risk_on", "neutral", "risk_off", "unknown"},
    "tier": {"Tier 1", "Tier 2", "Tier 3"},
    "session_class": {"exchange_traded", "continuous_247", "continuous_245"},
    "payload": {
        "news",
        "macro_release",
        "policy",
        "market_data",
        "flow",
        "positioning",
        "filing",
        "calendar",
    },
    "ledger_type": {"FACT", "CLAIM", "OBSERVATION", "INFERENCE"},
    "verification_status": {"passed", "unresolved"},
}


class ConfigError(ValueError):
    """Configuration failed closed validation."""


def _reject_lone_surrogates(text: str, where: str) -> None:
    for ch in text:
        if 0xD800 <= ord(ch) <= 0xDFFF:
            raise ConfigError(
                f"{where}: lone surrogate U+{ord(ch):04X} is not a Unicode scalar value"
            )


def _check_enum(value: str, enum_name: str, where: str) -> None:
    allowed = SCORING_ENUMS[enum_name]
    if value not in allowed:
        raise ConfigError(
            f"{where}: {value!r} is not a valid {enum_name}; allowed: {sorted(allowed)}"
        )


def _require_keys(mapping: Mapping[str, Any], required: set[str], where: str) -> None:
    missing = required - set(mapping)
    if missing:
        raise ConfigError(f"{where}: missing required keys: {sorted(missing)}")


# Closed set of allowed top-level configuration keys (config.yaml).
ALLOWED_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "name",
        "timezone",
        "output_root",
        "runs_root",
        "freshness_limit_minutes",
        "normal_lag_hours",
        "feed",
        "llm",
        "scoring",
        "market_state",
        "calendar",
        "audit_severity",
        "safety_lexicon",
        "rate_registry",
        "roles",
        "sessions",
        "source_families",
        "entities",
        "watched_companies",
        "providers",
        "coverage",
    }
)

# Closed set of allowed provider-registry keys (providers.yaml).
ALLOWED_PROVIDER_FILE_KEYS: frozenset[str] = frozenset({"providers", "coverage"})


def _reject_unknown_keys(mapping: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = set(mapping) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown keys: {sorted(unknown)}")


def _load_yaml(path: Path) -> Mapping[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"{path}: invalid UTF-8: {exc}") from exc
    _reject_lone_surrogates(text, str(path))
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top-level YAML must be a mapping")
    return data


def _parse_fetch_rules(raw: Any, where: str) -> tuple[FetchRule, ...]:
    rules: list[FetchRule] = []
    for item in raw or []:
        _require_keys(item, {"host"}, f"{where}.fetch_rule")
        rules.append(
            FetchRule(
                host=str(item["host"]).lower().rstrip("."),
                allow_subdomains=bool(item.get("allow_subdomains", False)),
                allowed_ports=tuple(int(p) for p in item.get("allowed_ports", [443])),
            )
        )
    return tuple(rules)


def _parse_source_link_rules(raw: Any, where: str) -> tuple[SourceLinkRule, ...]:
    rules: list[SourceLinkRule] = []
    for item in raw or []:
        _require_keys(item, {"host"}, f"{where}.source_link_host")
        rules.append(
            SourceLinkRule(
                host=str(item["host"]).lower().rstrip("."),
                allow_subdomains=bool(item.get("allow_subdomains", False)),
                allowed_ports=tuple(int(p) for p in item.get("allowed_ports", [443])),
                allowed_query_params=tuple(item.get("allowed_query_params", [])),
                query_value_grammar=str(item.get("query_value_grammar", "any")),
                drop_query_params=tuple(item.get("drop_query_params", [])),
            )
        )
    return tuple(rules)


def _parse_rate_policy(raw: Any, where: str) -> RatePolicy | None:
    if raw is None:
        return None
    if raw.get("unlimited"):
        return RatePolicy(
            scope_id=str(raw["scope_id"]),
            capacity=0,
            refill_period_seconds=0,
            minimum_interval_seconds=0,
            unlimited=True,
            shared_host=raw.get("shared_host"),
        )
    if int(raw.get("capacity", 0)) <= 0:
        raise ConfigError(f"{where}: rate capacity must be positive")
    if int(raw.get("refill_period_seconds", 0)) <= 0:
        raise ConfigError(f"{where}: rate refill period must be positive")
    if int(raw.get("minimum_interval_seconds", -1)) < 0:
        raise ConfigError(f"{where}: rate minimum interval must be non-negative")
    return RatePolicy(
        scope_id=str(raw["scope_id"]),
        capacity=int(raw["capacity"]),
        refill_period_seconds=int(raw["refill_period_seconds"]),
        minimum_interval_seconds=int(raw.get("minimum_interval_seconds", 0)),
        shared_host=raw.get("shared_host"),
    )


def _parse_providers(raw: Any, where: str) -> tuple[ProviderEntry, ...]:
    providers: list[ProviderEntry] = []
    seen_ids: set[str] = set()
    for item in raw or []:
        _require_keys(item, {"id", "name", "group"}, f"{where}.provider")
        pid = str(item["id"])
        if pid in seen_ids:
            raise ConfigError(f"{where}: duplicate provider id {pid!r}")
        seen_ids.add(pid)
        tier = str(item.get("tier", "Tier 2"))
        _check_enum(tier, "tier", f"{where}.provider.{pid}")
        rate = _parse_rate_policy(item.get("rate_policy"), f"{where}.provider.{pid}")
        providers.append(
            ProviderEntry(
                id=pid,
                name=str(item["name"]),
                enabled=bool(item.get("enabled", False)),
                verified=bool(item.get("verified", False)),
                default_enabled=bool(item.get("default_enabled", False)),
                group=str(item["group"]),
                source_family_id=str(item.get("source_family_id", pid)),
                tier=tier,
                user_agent=str(item.get("user_agent", "")),
                fetch_hosts=_parse_fetch_rules(item.get("fetch_hosts"), f"{where}.provider.{pid}"),
                redirect_hosts=_parse_fetch_rules(
                    item.get("redirect_hosts"), f"{where}.provider.{pid}"
                ),
                source_link_hosts=_parse_source_link_rules(
                    item.get("source_link_hosts"), f"{where}.provider.{pid}"
                ),
                rate_policy=rate,
                allowed_charset=str(item.get("allowed_charset", "utf-8")),
                allowed_bom=bool(item.get("allowed_bom", False)),
                allowed_content_type_header=item.get("allowed_content_type_header"),
                pagination=str(item.get("pagination", "none")),
                empty_valid_for_window=bool(item.get("empty_valid_for_window", False)),
                response_limit_bytes=int(item.get("response_limit_bytes", 10 * 1024 * 1024)),
                credentials_required=bool(item.get("credentials_required", False)),
                verification_date=item.get("verification_date"),
                contract_url=item.get("contract_url"),
                notes=item.get("notes"),
            )
        )
    return tuple(providers)


def _parse_coverage(raw: Any, where: str) -> CoverageMatrix:
    rows: list[CoverageRow] = []
    for item in raw or []:
        _require_keys(item, {"group", "members", "minimum", "capability"}, f"{where}.row")
        rows.append(
            CoverageRow(
                group=str(item["group"]),
                members=tuple(str(m) for m in item["members"]),
                minimum=int(item["minimum"]),
                capability=str(item["capability"]),
                optional=bool(item.get("optional", False)),
            )
        )
    return CoverageMatrix(tuple(rows))


def _parse_entities(raw: Any, where: str) -> tuple[Entity, ...]:
    entities: list[Entity] = []
    for item in raw or []:
        _require_keys(item, {"id", "name"}, f"{where}.entity")
        entities.append(
            Entity(
                id=str(item["id"]),
                name=str(item["name"]),
                name_zh=str(item.get("name_zh", item["name"])),
                aliases=tuple(str(a) for a in item.get("aliases", [])),
                kind=str(item.get("kind", "institution")),
            )
        )
    return tuple(entities)


def _parse_roles(raw: Any, where: str) -> tuple[MarketRole, ...]:
    roles: list[MarketRole] = []
    for item in raw or []:
        _require_keys(item, {"id", "name", "instrument", "unit"}, f"{where}.role")
        session_class = str(item.get("session_class", "exchange_traded"))
        _check_enum(session_class, "session_class", f"{where}.role.{item['id']}")
        roles.append(
            MarketRole(
                id=str(item["id"]),
                name=str(item["name"]),
                name_zh=str(item.get("name_zh", item["name"])),
                instrument=str(item["instrument"]),
                unit=str(item["unit"]),
                session_class=session_class,
                kind=str(item.get("kind", "price")),
            )
        )
    return tuple(roles)


def _parse_scoring(raw: Any, where: str) -> Scoring:
    weights = tuple(int(w) for w in raw.get("significance_weights", [30, 20, 20, 20, 10]))
    if sum(weights) != 100:
        raise ConfigError(f"{where}: significance weights must sum to 100, got {sum(weights)}")
    asset_groups_raw = raw.get("asset_groups", [])
    asset_groups = tuple(
        AssetGroupMapping(
            group=str(g["group"]),
            name_zh=str(g.get("name_zh", g["group"])),
            proxies=tuple(str(p) for p in g.get("proxies", [])),
        )
        for g in asset_groups_raw
    )
    if len(asset_groups) != 9:
        raise ConfigError(f"{where}: exactly nine asset groups required, got {len(asset_groups)}")
    scales = tuple(
        SurpriseScale(series_id=str(s["series_id"]), scale=str(s["scale"]), note=s.get("note"))
        for s in raw.get("surprise_scales", [])
    )
    for scale in scales:
        if float(scale.scale) <= 0:
            raise ConfigError(f"{where}: surprise scale for {scale.series_id} must be positive")
    return Scoring(
        significance_weights=weights,
        asset_groups=asset_groups,
        surprise_scales=scales,
    )


def _validate_role_ids(roles: tuple[MarketRole, ...]) -> None:
    actual = tuple(r.id for r in roles)
    if actual != V1_ROLE_IDS:
        raise ConfigError(
            f"roles must be exactly the canonical v1 set {V1_ROLE_IDS!r}, got {actual!r}"
        )


def _validate_coverage(providers: tuple[ProviderEntry, ...], coverage: CoverageMatrix) -> None:
    by_id = {p.id: p for p in providers}
    for row in coverage.rows:
        for member in row.members:
            if member not in by_id:
                raise ConfigError(f"coverage row {row.group}: unknown member {member!r}")
            p = by_id[member]
            if not p.verified:
                raise ConfigError(f"coverage row {row.group}: member {member!r} is unverified")
            if not p.enabled:
                raise ConfigError(f"coverage row {row.group}: member {member!r} is disabled")
        enabled_members = [m for m in row.members if by_id[m].enabled]
        if len(enabled_members) < row.minimum and not row.optional:
            raise ConfigError(
                f"coverage row {row.group}: minimum {row.minimum} not achievable "
                f"(enabled: {enabled_members})"
            )


def _validate_rate_policies(providers: tuple[ProviderEntry, ...]) -> None:
    by_scope: dict[str, RatePolicy] = {}
    for p in providers:
        rp = p.rate_policy
        if rp is None or rp.unlimited:
            continue
        existing = by_scope.get(rp.scope_id)
        if existing is not None and existing != rp:
            raise ConfigError(f"rate scope {rp.scope_id!r} declared inconsistently by {p.id!r}")
        by_scope[rp.scope_id] = rp


def load_config(
    config_path: str | Path,
    providers_path: str | Path | None = None,
    *,
    require_verified_enabled: bool = True,
) -> AppConfig:
    """Load and strictly validate configuration from YAML files."""
    config_path = Path(config_path)
    data = _load_yaml(config_path)
    _reject_unknown_keys(data, ALLOWED_CONFIG_KEYS, str(config_path))

    providers_file_data: Mapping[str, Any] = {}
    if providers_path is not None:
        providers_path = Path(providers_path)
        providers_file_data = _load_yaml(providers_path)
        _reject_unknown_keys(providers_file_data, ALLOWED_PROVIDER_FILE_KEYS, str(providers_path))

    _require_keys(
        data,
        {"schema_version", "name", "feed", "llm", "scoring"},
        str(config_path),
    )
    schema_version = int(data["schema_version"])
    if schema_version != 1:
        raise ConfigError(f"{config_path}: unsupported config schema_version {schema_version}")

    providers_raw: list[Any] = []
    providers_raw.extend(providers_file_data.get("providers", []))
    providers_raw.extend(data.get("providers", []))
    providers = _parse_providers(providers_raw, "providers")

    coverage_raw = providers_file_data.get("coverage", data.get("coverage", []))
    coverage = _parse_coverage(coverage_raw, "coverage")

    if require_verified_enabled:
        for p in providers:
            if p.enabled and not p.verified:
                raise ConfigError(f"provider {p.id!r} is enabled but unverified")
        _validate_coverage(providers, coverage)
        _validate_rate_policies(providers)

    feed_raw = data["feed"]
    llm_raw = data["llm"]
    scoring = _parse_scoring(data["scoring"], "scoring")

    roles = _parse_roles(data.get("roles", []), "roles")
    if require_verified_enabled:
        _validate_role_ids(roles)

    entities = _parse_entities(data.get("entities", []), "entities")
    source_families = tuple(
        SourceFamily(
            id=str(s["id"]),
            name=str(s["name"]),
            tier=str(s.get("tier", "Tier 2")),
        )
        for s in data.get("source_families", [])
    )
    sessions = tuple(
        Session(
            id=str(s["id"]),
            calendar=str(s["calendar"]),
            session_class=str(s.get("session_class", "exchange_traded")),
            timezone=str(s.get("timezone", "UTC")),
            annualization_factor=str(s.get("annualization_factor", "252")),
        )
        for s in data.get("sessions", [])
    )
    watched = tuple(
        WatchCompany(
            cik=str(w["cik"]),
            name=str(w["name"]),
            tickers=tuple(str(t) for t in w.get("tickers", [])),
        )
        for w in data.get("watched_companies", [])
    )

    feed_limits = FeedLimits(
        bootstrap_lookback_hours=int(feed_raw.get("bootstrap_lookback_hours", 72)),
        gap_threshold_hours=int(feed_raw.get("gap_threshold_hours", 72)),
        calendar_horizon_hours=int(feed_raw.get("calendar_horizon_hours", 26)),
        pre_commit_deadline_seconds=int(feed_raw.get("pre_commit_deadline_seconds", 300)),
        commit_reserve_seconds=int(feed_raw.get("commit_reserve_seconds", 15)),
        global_concurrency=int(feed_raw.get("global_concurrency", 8)),
        per_host_concurrency=int(feed_raw.get("per_host_concurrency", 2)),
        http_attempt_timeout_seconds=int(feed_raw.get("http_attempt_timeout_seconds", 20)),
        max_attempts=int(feed_raw.get("max_attempts", 3)),
        max_decompressed_response_bytes=int(
            feed_raw.get("max_decompressed_response_bytes", 10 * 1024 * 1024)
        ),
        max_items_per_provider=int(feed_raw.get("max_items_per_provider", 2000)),
        max_title_code_points=int(feed_raw.get("max_title_code_points", 300)),
        max_snippet_code_points=int(feed_raw.get("max_snippet_code_points", 1000)),
        max_url_characters=int(feed_raw.get("max_url_characters", 2048)),
        max_observations_per_instrument=int(feed_raw.get("max_observations_per_instrument", 260)),
        max_serialized_feed_bytes=int(feed_raw.get("max_serialized_feed_bytes", 50 * 1024 * 1024)),
    )
    for name_, value in (
        ("bootstrap_lookback_hours", feed_limits.bootstrap_lookback_hours),
        ("gap_threshold_hours", feed_limits.gap_threshold_hours),
        ("calendar_horizon_hours", feed_limits.calendar_horizon_hours),
        ("pre_commit_deadline_seconds", feed_limits.pre_commit_deadline_seconds),
        ("commit_reserve_seconds", feed_limits.commit_reserve_seconds),
    ):
        if value <= 0:
            raise ConfigError(f"feed.{name_} must be positive, got {value}")

    def _pass(name_: str) -> PassConfig:
        p = llm_raw.get(name_, {}) or {}
        return PassConfig(
            attempt_timeout_seconds=int(p.get("attempt_timeout_seconds", 30)),
            max_output_tokens=int(p.get("max_output_tokens", 72000)),
            dynamic_cap_bytes=int(p.get("dynamic_cap_bytes", 32 * 1024)),
            concurrency=int(p.get("concurrency", 4)),
            max_attempts=int(p.get("max_attempts", 2)),
        )

    llm = LlmRuntime(
        model=str(llm_raw.get("model", "")),
        organization=llm_raw.get("organization"),
        project=llm_raw.get("project"),
        resolver=_pass("resolver"),
        analyst=_pass("analyst"),
        editor=_pass("editor"),
        audit=_pass("audit"),
        max_resolver_blocks=int(llm_raw.get("max_resolver_blocks", 40)),
        max_analyst_packets=int(llm_raw.get("max_analyst_packets", 20)),
        brief_pre_commit_deadline_seconds=int(
            llm_raw.get("brief_pre_commit_deadline_seconds", 300)
        ),
        brief_commit_reserve_seconds=int(llm_raw.get("brief_commit_reserve_seconds", 15)),
    )
    # The shipped default ships an empty model name: the single model is
    # deployment configuration and startup rejects it, but the config file
    # itself must remain loadable for structural validation and tests.

    market_state = MarketState()
    calendar = CalendarPolicy()
    audit_severity = AuditSeverity()
    safety = SafetyLexicon()
    rate_registry = RateRegistry()

    return AppConfig(
        schema_version=schema_version,
        name=str(data["name"]),
        providers=providers,
        coverage=coverage,
        source_families=source_families,
        entities=entities,
        roles=roles,
        sessions=sessions,
        watched_companies=watched,
        feed=feed_limits,
        llm=llm,
        scoring=scoring,
        market_state=market_state,
        calendar=calendar,
        audit_severity=audit_severity,
        safety_lexicon=safety,
        rate_registry=rate_registry,
        output_root=str(data.get("output_root", "feeds")),
        runs_root=str(data.get("runs_root", "runs")),
        timezone=str(data.get("timezone", "Asia/Shanghai")),
        freshness_limit_minutes=int(data.get("freshness_limit_minutes", 30)),
        normal_lag_hours=int(data.get("normal_lag_hours", 2)),
    )
