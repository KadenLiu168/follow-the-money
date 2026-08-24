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
from typing import Any, cast

import exchange_calendars as xcals
import yaml

from ..providers.manifest import (
    ManifestError,
    load_manifest,
    manifest_to_provider_entry,
    validate_mapping_provenance,
)
from .model import (
    V1_ROLE_IDS,
    AppConfig,
    AssetGroupMapping,
    CalendarPolicy,
    CoverageMatrix,
    CoverageRow,
    Entity,
    FeedLimits,
    FetchRule,
    MarketRole,
    MarketState,
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

DEFAULT_MANIFEST_ROOT = Path(__file__).resolve().parents[3] / "providers"

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
        "scoring",
        "market_state",
        "calendar",
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
ALLOWED_PROVIDER_FILE_KEYS: frozenset[str] = frozenset({"schema_version", "providers", "coverage"})


def _reject_unknown_keys(mapping: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = set(mapping) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown keys: {sorted(unknown)}")


def _closed_section(
    raw: Any,
    *,
    required: frozenset[str],
    allowed: frozenset[str] | None = None,
    where: str,
) -> Mapping[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: must be a mapping")
    _require_keys(raw, set(required), where)
    _reject_unknown_keys(raw, allowed or required, where)
    return raw


FEED_KEYS = frozenset(
    {
        "bootstrap_lookback_hours",
        "gap_threshold_hours",
        "calendar_horizon_hours",
        "pre_commit_deadline_seconds",
        "commit_reserve_seconds",
        "global_concurrency",
        "per_host_concurrency",
        "http_attempt_timeout_seconds",
        "max_attempts",
        "max_decompressed_response_bytes",
        "max_items_per_provider",
        "max_title_code_points",
        "max_snippet_code_points",
        "max_url_characters",
        "max_observations_per_instrument",
        "max_serialized_feed_bytes",
        "lock_timeout_seconds",
    }
)
SCORING_KEYS = frozenset(
    {
        "significance_weights",
        "freshness_bins",
        "freshness_older_score",
        "morning_weights",
        "base_priority_weights",
        "min_component_coverage",
        "full_priority_threshold",
        "compact_priority_threshold",
        "family_penalty",
        "target_count",
        "hard_max_count",
        "max_full_events",
        "anomaly_z_threshold",
        "scope_map",
        "fundamental_depth_map",
        "reversibility_map",
        "structural_horizon_map",
        "surprise_bins",
        "exposure_map",
        "catalyst_map",
        "asset_groups",
        "surprise_scales",
    }
)
MARKET_STATE_KEYS = frozenset(
    {
        "z_supportive",
        "breadth_supportive",
        "regime_sum_threshold",
        "risk_appetite_min_votes",
        "rates_min_votes",
        "liquidity_min_votes",
        "growth_min_votes",
        "inflation_min_votes",
        "required_known_dimensions",
        "rules_order",
    }
)
CALENDAR_KEYS = frozenset(
    {"allowed_priorities", "max_items", "stale_after_minutes", "hard_lag_hours"}
)
SAFETY_KEYS = frozenset({"zh_terms", "en_terms", "descriptive_exceptions"})
RATE_REGISTRY_KEYS = frozenset({"version", "crash_cooldown_hours", "schema_file"})
APPLICATION_REQUIRED_KEYS = frozenset(
    {
        "schema_version",
        "name",
        "timezone",
        "output_root",
        "runs_root",
        "freshness_limit_minutes",
        "normal_lag_hours",
        "feed",
        "scoring",
        "market_state",
        "calendar",
        "safety_lexicon",
        "rate_registry",
        "roles",
        "sessions",
        "source_families",
        "entities",
        "watched_companies",
    }
)


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


def _parse_coverage(raw: Any, where: str, *, strict: bool = False) -> CoverageMatrix:
    rows: list[CoverageRow] = []
    for item in raw or []:
        if strict:
            item = _closed_section(
                item,
                required=frozenset({"group", "members", "minimum", "capability", "optional"}),
                where=f"{where}.row",
            )
            if not isinstance(item["optional"], bool):
                raise ConfigError(f"{where}.row.{item['group']}.optional must be boolean")
        _require_keys(item, {"group", "members", "minimum", "capability"}, f"{where}.row")
        if int(item["minimum"]) <= 0:
            raise ConfigError(f"{where}.row.{item['group']}.minimum must be positive")
        rows.append(
            CoverageRow(
                group=str(item["group"]),
                members=tuple(str(m) for m in item["members"]),
                minimum=int(item["minimum"]),
                capability=str(item["capability"]),
                optional=bool(item.get("optional", False)),
            )
        )
    if len({row.group for row in rows}) != len(rows):
        raise ConfigError(f"{where}: duplicate coverage group")
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


def _parse_roles(raw: Any, where: str, *, strict: bool = False) -> tuple[MarketRole, ...]:
    roles: list[MarketRole] = []
    for item in raw or []:
        if strict:
            item = _closed_section(
                item,
                required=frozenset(
                    {
                        "id",
                        "name",
                        "name_zh",
                        "instrument",
                        "unit",
                        "provider_id",
                        "economic_identity",
                        "daily_close_semantics",
                        "mapping_verified",
                        "availability_lag_seconds",
                        "session_id",
                        "session_class",
                        "kind",
                    }
                ),
                where=f"{where}.role",
            )
        _require_keys(
            item,
            {
                "id",
                "name",
                "instrument",
                "unit",
                "provider_id",
                "economic_identity",
                "daily_close_semantics",
                "mapping_verified",
                "availability_lag_seconds",
                "session_id",
            },
            f"{where}.role",
        )
        session_class = str(item.get("session_class", "exchange_traded"))
        _check_enum(session_class, "session_class", f"{where}.role.{item['id']}")
        availability_lag_seconds = int(item["availability_lag_seconds"])
        if availability_lag_seconds < 0:
            raise ConfigError(
                f"{where}.role.{item['id']}.availability_lag_seconds must be non-negative"
            )
        for field_name in (
            "provider_id",
            "economic_identity",
            "daily_close_semantics",
        ):
            if not str(item[field_name]).strip():
                raise ConfigError(f"{where}.role.{item['id']}.{field_name} must be non-empty")
        if not isinstance(item["mapping_verified"], bool):
            raise ConfigError(f"{where}.role.{item['id']}.mapping_verified must be boolean")
        roles.append(
            MarketRole(
                id=str(item["id"]),
                name=str(item["name"]),
                name_zh=str(item["name_zh"] if strict else item.get("name_zh", item["name"])),
                instrument=str(item["instrument"]),
                unit=str(item["unit"]),
                provider_id=str(item["provider_id"]),
                economic_identity=str(item["economic_identity"]),
                daily_close_semantics=str(item["daily_close_semantics"]),
                mapping_verified=bool(item["mapping_verified"]),
                availability_lag_seconds=availability_lag_seconds,
                session_id=str(item["session_id"]),
                session_class=session_class,
                kind=str(item["kind"] if strict else item.get("kind", "price")),
            )
        )
    return tuple(roles)


def _parse_scoring(raw: Any, where: str, *, strict: bool = False) -> Scoring:
    if strict:
        raw = _closed_section(raw, required=SCORING_KEYS, where=where)
    field = lambda name, default: raw[name] if strict else raw.get(name, default)
    weights = cast(
        tuple[int, int, int, int, int],
        tuple(int(w) for w in field("significance_weights", [30, 20, 20, 20, 10])),
    )
    if sum(weights) != 100:
        raise ConfigError(f"{where}: significance weights must sum to 100, got {sum(weights)}")
    asset_groups_raw = field("asset_groups", [])
    asset_group_list: list[AssetGroupMapping] = []
    for index, g in enumerate(asset_groups_raw):
        if strict:
            g = _closed_section(
                g,
                required=frozenset({"group", "name_zh", "proxies"}),
                where=f"{where}.asset_groups[{index}]",
            )
        asset_group_list.append(
            AssetGroupMapping(
                group=str(g["group"]),
                name_zh=str(g["name_zh"] if strict else g.get("name_zh", g["group"])),
                proxies=tuple(str(p) for p in (g["proxies"] if strict else g.get("proxies", []))),
            )
        )
    asset_groups = tuple(asset_group_list)
    if len(asset_groups) != 9:
        raise ConfigError(f"{where}: exactly nine asset groups required, got {len(asset_groups)}")
    scales_list = []
    for index, s in enumerate(field("surprise_scales", [])):
        if strict:
            s = _closed_section(
                s,
                required=frozenset({"series_id", "scale", "note"}),
                where=f"{where}.surprise_scales[{index}]",
            )
        scales_list.append(
            SurpriseScale(
                series_id=str(s["series_id"]),
                scale=str(s["scale"]),
                note=s["note"] if strict else s.get("note"),
            )
        )
    scales = tuple(scales_list)
    for scale in scales:
        if float(scale.scale) <= 0:
            raise ConfigError(f"{where}: surprise scale for {scale.series_id} must be positive")
    freshness_bins = cast(
        tuple[tuple[int, int], ...],
        tuple(
            tuple(int(v) for v in row) for row in field("freshness_bins", Scoring.freshness_bins)
        ),
    )
    morning_weights = cast(
        tuple[int, int, int, int],
        tuple(int(v) for v in field("morning_weights", Scoring.morning_weights)),
    )
    base_priority_weights = cast(
        tuple[str, str],
        tuple(str(v) for v in field("base_priority_weights", Scoring.base_priority_weights)),
    )
    return Scoring(
        significance_weights=weights,
        freshness_bins=freshness_bins,
        freshness_older_score=int(field("freshness_older_score", 0)),
        morning_weights=morning_weights,
        base_priority_weights=base_priority_weights,
        min_component_coverage=str(field("min_component_coverage", "60")),
        full_priority_threshold=str(field("full_priority_threshold", "60")),
        compact_priority_threshold=str(field("compact_priority_threshold", "40")),
        family_penalty=str(field("family_penalty", "15")),
        target_count=int(field("target_count", 10)),
        hard_max_count=int(field("hard_max_count", 12)),
        max_full_events=int(field("max_full_events", 3)),
        anomaly_z_threshold=str(field("anomaly_z_threshold", "2.0")),
        scope_map={str(k): int(v) for k, v in field("scope_map", Scoring().scope_map).items()},
        fundamental_depth_map={
            str(k): int(v)
            for k, v in field("fundamental_depth_map", Scoring().fundamental_depth_map).items()
        },
        reversibility_map={
            str(k): int(v)
            for k, v in field("reversibility_map", Scoring().reversibility_map).items()
        },
        structural_horizon_map={
            str(k): int(v)
            for k, v in field("structural_horizon_map", Scoring().structural_horizon_map).items()
        },
        surprise_bins=tuple(
            (str(row[0]), str(row[1]), int(row[2]))
            for row in field("surprise_bins", Scoring().surprise_bins)
        ),
        exposure_map={
            str(k): int(v) for k, v in field("exposure_map", Scoring().exposure_map).items()
        },
        catalyst_map={
            str(k): int(v) for k, v in field("catalyst_map", Scoring().catalyst_map).items()
        },
        asset_groups=asset_groups,
        surprise_scales=scales,
    )


def _validate_scoring_domains(scoring: Scoring) -> None:
    expected_maps = {
        "scope_map": SCORING_ENUMS["scope"],
        "fundamental_depth_map": SCORING_ENUMS["fundamental_depth"],
        "reversibility_map": SCORING_ENUMS["reversibility"],
        "structural_horizon_map": SCORING_ENUMS["structural_horizon"],
        "exposure_map": SCORING_ENUMS["exposure"],
        "catalyst_map": {"present", "absent"},
    }
    for name, expected in expected_maps.items():
        actual = set(getattr(scoring, name))
        if actual != expected:
            raise ConfigError(f"scoring.{name}: keys must be exactly {sorted(expected)}")
    if len(scoring.significance_weights) != 5 or len(scoring.morning_weights) != 4:
        raise ConfigError("scoring weight vectors have unsupported lengths")
    if len(scoring.base_priority_weights) != 2:
        raise ConfigError("scoring.base_priority_weights must contain two values")
    if any(len(row) != 2 for row in scoring.freshness_bins):
        raise ConfigError("scoring.freshness_bins rows must contain two values")
    if any(len(row) != 3 or row[1] not in {"<", ">="} for row in scoring.surprise_bins):
        raise ConfigError("scoring.surprise_bins rows are invalid")
    if len({group.group for group in scoring.asset_groups}) != 9:
        raise ConfigError("scoring.asset_groups must have unique groups")
    if len({scale.series_id for scale in scoring.surprise_scales}) != len(scoring.surprise_scales):
        raise ConfigError("scoring.surprise_scales must have unique series ids")


def _validate_role_ids(roles: tuple[MarketRole, ...]) -> None:
    actual = tuple(r.id for r in roles)
    if len(set(actual)) != len(actual):
        duplicates = sorted({role_id for role_id in actual if actual.count(role_id) > 1})
        raise ConfigError(f"duplicate role ownership: {duplicates}")
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


def _validate_market_coverage(
    providers: tuple[ProviderEntry, ...], coverage: CoverageMatrix
) -> None:
    by_id = {provider.id: provider for provider in providers}
    enabled_market_providers = {
        provider.id for provider in providers if provider.enabled and provider.role_mappings
    }
    unsupported_claims = {
        "china_hk_cross_asset_market",
        "market_data_all_13_roles",
        "cross_asset_market",
    }
    covered_market_providers: set[str] = set()
    for row in coverage.rows:
        if row.group in unsupported_claims or row.capability in unsupported_claims:
            raise ConfigError(
                f"coverage row {row.group}: unsupported market coverage claim {row.capability!r}"
            )
        market_members = enabled_market_providers.intersection(row.members)
        declares_market_coverage = (
            row.group == "verified_market_data" or row.capability == "verified_market_data"
        )
        if not market_members and not declares_market_coverage:
            continue
        if row.group != "verified_market_data" or row.capability != "verified_market_data":
            raise ConfigError(
                f"coverage row {row.group}: unsupported market coverage claim {row.capability!r}"
            )
        non_market_members = set(row.members) - enabled_market_providers
        if non_market_members:
            raise ConfigError(
                f"coverage row {row.group}: non-market members cannot satisfy verified runnable "
                f"coverage: {sorted(non_market_members)}"
            )
        covered_market_providers.update(market_members)
        for member in market_members:
            provider = by_id[member]
            if not any(bool(mapping["mapping_verified"]) for mapping in provider.role_mappings):
                raise ConfigError(
                    f"coverage row {row.group}: member {member!r} has no verified runnable mappings"
                )
    missing = enabled_market_providers - covered_market_providers
    if missing:
        raise ConfigError(
            f"enabled market Providers lack verified_market_data coverage: {sorted(missing)}"
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


def _validate_role_mapping_mirrors(provider: ProviderEntry, roles: tuple[MarketRole, ...]) -> None:
    if not provider.role_mappings:
        return
    mapping_ids = [str(item["role_id"]) for item in provider.role_mappings]
    if len(mapping_ids) != len(set(mapping_ids)):
        raise ConfigError(f"{provider.id} role mappings contain duplicate role ids")
    mappings = {str(item["role_id"]): item for item in provider.role_mappings}
    if set(mappings) != {role.id for role in roles}:
        raise ConfigError(f"{provider.id} role mapping set does not match canonical roles")
    for role in roles:
        mapping = mappings[role.id]
        for field_name in ("instrument", "unit", "mapping_verified"):
            if mapping.get(field_name) != getattr(role, field_name):
                raise ConfigError(f"role mapping mirror mismatch for {role.id!r}: {field_name}")


_REGISTRY_PROVIDER_KEYS = frozenset(
    {
        "id",
        "enabled",
        "optional",
        "name",
        "verified",
        "default_enabled",
        "group",
        "source_family_id",
        "tier",
        "user_agent",
        "fetch_hosts",
        "redirect_hosts",
        "source_link_hosts",
        "rate_policy",
        "allowed_charset",
        "allowed_bom",
        "allowed_content_type_header",
        "pagination",
        "empty_valid_for_window",
        "response_limit_bytes",
        "credentials_required",
        "verification_date",
        "contract_url",
        "notes",
    }
)


def _parse_registry_policies(raw: Any, where: str, *, strict: bool) -> tuple[dict[str, Any], ...]:
    policies: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw or []):
        if not isinstance(item, dict):
            raise ConfigError(f"{where}[{index}] must be a mapping")
        if strict:
            _closed_section(
                item,
                required=frozenset({"id", "enabled"}),
                allowed=_REGISTRY_PROVIDER_KEYS,
                where=f"{where}[{index}]",
            )
            if not isinstance(item["enabled"], bool):
                raise ConfigError(f"{where}[{index}].enabled must be boolean")
        else:
            _require_keys(item, {"id", "name", "group"}, f"{where}.provider")
        pid = str(item["id"])
        if pid in seen:
            raise ConfigError(f"{where}: duplicate provider id {pid!r}")
        seen.add(pid)
        policies.append(dict(item))
    return tuple(policies)


def _provider_mirror_matches(policy: Mapping[str, Any], entry: ProviderEntry, where: str) -> None:
    """Validate only explicitly retained legacy mirrors; never use them."""
    scalar_mirrors = {
        "name": entry.name,
        "verified": entry.verified,
        "default_enabled": entry.default_enabled,
        "source_family_id": entry.source_family_id,
        "tier": entry.tier,
        "user_agent": entry.user_agent,
        "allowed_charset": entry.allowed_charset,
        "allowed_bom": entry.allowed_bom,
        "allowed_content_type_header": entry.allowed_content_type_header,
        "pagination": entry.pagination,
        "empty_valid_for_window": entry.empty_valid_for_window,
        "response_limit_bytes": entry.response_limit_bytes,
        "credentials_required": entry.credentials_required,
        "verification_date": entry.verification_date,
        "contract_url": entry.contract_url,
    }
    for field_name, authoritative in scalar_mirrors.items():
        if field_name in policy and policy[field_name] != authoritative:
            raise ConfigError(f"{where}.{field_name}: compatibility mirror mismatch")


def _resolve_provider_entries(
    policies: tuple[dict[str, Any], ...],
    coverage: CoverageMatrix,
    manifest_root: Path,
    *,
    require_verified_enabled: bool,
) -> tuple[ProviderEntry, ...]:
    groups_by_provider: dict[str, list[str]] = {}
    for row in coverage.rows:
        for provider_id in row.members:
            groups_by_provider.setdefault(provider_id, []).append(row.group)

    entries: list[ProviderEntry] = []
    for policy in policies:
        pid = str(policy["id"])
        manifest_path = manifest_root / pid / "manifest.yaml"
        if not manifest_path.exists() and not bool(policy["enabled"]):
            continue
        try:
            manifest = load_manifest(pid, manifest_root)
            for mapping in manifest.get("role_mappings", []):
                validate_mapping_provenance(
                    manifest,
                    mapping,
                    manifest_root=manifest_root,
                    provider_id=pid,
                )
            entry = manifest_to_provider_entry(
                manifest,
                enabled=bool(policy["enabled"]),
                coverage_groups=tuple(sorted(groups_by_provider.get(pid, []))),
            )
        except ManifestError as exc:
            raise ConfigError(str(exc)) from exc
        _provider_mirror_matches(policy, entry, f"providers.{pid}")
        if require_verified_enabled and entry.enabled and not entry.verified:
            raise ConfigError(f"provider {pid!r} is enabled but unverified")
        if (
            entry.enabled
            and entry.role_mappings
            and not any(bool(mapping["mapping_verified"]) for mapping in entry.role_mappings)
        ):
            raise ConfigError(f"provider {pid!r} has zero verified runnable market mappings")
        entries.append(entry)

    if not entries and policies:
        raise ConfigError("provider registry resolved no entries")
    return tuple(entries)


def _parse_source_families(raw: Any, *, strict: bool) -> tuple[SourceFamily, ...]:
    values: list[SourceFamily] = []
    seen: set[str] = set()
    for index, item in enumerate(raw or []):
        if strict:
            item = _closed_section(
                item,
                required=frozenset({"id", "name", "tier"}),
                where=f"source_families[{index}]",
            )
        family = SourceFamily(
            str(item["id"]),
            str(item["name"]),
            str(item["tier"] if strict else item.get("tier", "Tier 2")),
        )
        if family.id in seen:
            raise ConfigError(f"duplicate source family id {family.id!r}")
        seen.add(family.id)
        _check_enum(family.tier, "tier", f"source_families.{family.id}")
        values.append(family)
    return tuple(values)


def _parse_entities_strict(raw: Any) -> tuple[Entity, ...]:
    values: list[Entity] = []
    seen: set[str] = set()
    for index, item in enumerate(raw or []):
        item = _closed_section(
            item,
            required=frozenset({"id", "name", "name_zh", "aliases", "kind"}),
            where=f"entities[{index}]",
        )
        entity = Entity(
            str(item["id"]),
            str(item["name"]),
            str(item["name_zh"]),
            tuple(str(a) for a in item["aliases"]),
            str(item["kind"]),
        )
        if entity.id in seen:
            raise ConfigError(f"duplicate entity id {entity.id!r}")
        seen.add(entity.id)
        values.append(entity)
    return tuple(values)


def _parse_sessions_strict(raw: Any) -> tuple[Session, ...]:
    values: list[Session] = []
    seen: set[str] = set()
    for index, item in enumerate(raw or []):
        item = _closed_section(
            item,
            required=frozenset(
                {
                    "id",
                    "calendar",
                    "session_class",
                    "timezone",
                    "annualization_factor",
                    "availability_lag_seconds",
                }
            ),
            where=f"sessions[{index}]",
        )
        session = Session(
            id=str(item["id"]),
            calendar=str(item["calendar"]),
            session_class=str(item["session_class"]),
            timezone=str(item["timezone"]),
            annualization_factor=str(item["annualization_factor"]),
            availability_lag_seconds=int(item["availability_lag_seconds"]),
        )
        if session.id in seen:
            raise ConfigError(f"duplicate session id {session.id!r}")
        seen.add(session.id)
        _check_enum(session.session_class, "session_class", f"sessions.{session.id}")
        if session.availability_lag_seconds < 0:
            raise ConfigError(
                f"sessions.{session.id}.availability_lag_seconds must be non-negative"
            )
        if session.session_class == "exchange_traded" and session.calendar not in set(
            xcals.get_calendar_names()
        ):
            raise ConfigError(
                f"sessions.{session.id}: unknown exchange calendar {session.calendar!r}"
            )
        values.append(session)
    return tuple(values)


def _parse_watched_strict(raw: Any) -> tuple[WatchCompany, ...]:
    values: list[WatchCompany] = []
    seen: set[str] = set()
    for index, item in enumerate(raw or []):
        item = _closed_section(
            item,
            required=frozenset({"cik", "name", "tickers"}),
            where=f"watched_companies[{index}]",
        )
        company = WatchCompany(
            str(item["cik"]), str(item["name"]), tuple(str(t) for t in item["tickers"])
        )
        if company.cik in seen:
            raise ConfigError(f"duplicate watched company CIK {company.cik!r}")
        seen.add(company.cik)
        values.append(company)
    return tuple(values)


def _parse_feed_limits(raw: Any, *, strict: bool) -> FeedLimits:
    if strict:
        raw = _closed_section(raw, required=FEED_KEYS, where="feed")
    defaults = {
        "bootstrap_lookback_hours": 72,
        "gap_threshold_hours": 72,
        "calendar_horizon_hours": 26,
        "pre_commit_deadline_seconds": 300,
        "commit_reserve_seconds": 15,
        "global_concurrency": 8,
        "per_host_concurrency": 2,
        "http_attempt_timeout_seconds": 20,
        "max_attempts": 3,
        "max_decompressed_response_bytes": 10 * 1024 * 1024,
        "max_items_per_provider": 2000,
        "max_title_code_points": 300,
        "max_snippet_code_points": 1000,
        "max_url_characters": 2048,
        "max_observations_per_instrument": 260,
        "max_serialized_feed_bytes": 50 * 1024 * 1024,
        "lock_timeout_seconds": 60,
    }
    values = {
        name: int(raw[name] if strict else raw.get(name, default))
        for name, default in defaults.items()
    }
    limits = FeedLimits(**values)
    positive = {
        "bootstrap_lookback_hours": limits.bootstrap_lookback_hours,
        "gap_threshold_hours": limits.gap_threshold_hours,
        "calendar_horizon_hours": limits.calendar_horizon_hours,
        "pre_commit_deadline_seconds": limits.pre_commit_deadline_seconds,
        "commit_reserve_seconds": limits.commit_reserve_seconds,
        "global_concurrency": limits.global_concurrency,
        "per_host_concurrency": limits.per_host_concurrency,
        "http_attempt_timeout_seconds": limits.http_attempt_timeout_seconds,
        "max_attempts": limits.max_attempts,
        "max_decompressed_response_bytes": limits.max_decompressed_response_bytes,
        "max_items_per_provider": limits.max_items_per_provider,
        "max_title_code_points": limits.max_title_code_points,
        "max_snippet_code_points": limits.max_snippet_code_points,
        "max_url_characters": limits.max_url_characters,
        "max_observations_per_instrument": limits.max_observations_per_instrument,
        "max_serialized_feed_bytes": limits.max_serialized_feed_bytes,
        "lock_timeout_seconds": limits.lock_timeout_seconds,
    }
    for name, value in positive.items():
        if value <= 0:
            raise ConfigError(f"feed.{name} must be positive, got {value}")
    return limits


def _parse_market_state(raw: Any, *, strict: bool) -> MarketState:
    if strict:
        raw = _closed_section(raw, required=MARKET_STATE_KEYS, where="market_state")
    read = raw.__getitem__ if strict else raw.get
    return MarketState(
        z_supportive=str(read("z_supportive", "0.5") if not strict else read("z_supportive")),
        breadth_supportive=str(
            read("breadth_supportive", "0.20") if not strict else read("breadth_supportive")
        ),
        regime_sum_threshold=str(
            read("regime_sum_threshold", "2") if not strict else read("regime_sum_threshold")
        ),
        risk_appetite_min_votes=int(
            read("risk_appetite_min_votes", 2) if not strict else read("risk_appetite_min_votes")
        ),
        rates_min_votes=int(read("rates_min_votes", 1) if not strict else read("rates_min_votes")),
        liquidity_min_votes=int(
            read("liquidity_min_votes", 1) if not strict else read("liquidity_min_votes")
        ),
        growth_min_votes=int(
            read("growth_min_votes", 1) if not strict else read("growth_min_votes")
        ),
        inflation_min_votes=int(
            read("inflation_min_votes", 1) if not strict else read("inflation_min_votes")
        ),
        required_known_dimensions=int(
            read("required_known_dimensions", 4)
            if not strict
            else read("required_known_dimensions")
        ),
        rules_order=tuple(
            str(v)
            for v in (
                read("rules_order", ("risk_off", "risk_on", "neutral"))
                if not strict
                else read("rules_order")
            )
        ),
    )


def _parse_calendar(raw: Any, *, strict: bool) -> CalendarPolicy:
    if strict:
        raw = _closed_section(raw, required=CALENDAR_KEYS, where="calendar")
    read = raw.__getitem__ if strict else raw.get
    return CalendarPolicy(
        allowed_priorities=tuple(
            str(v)
            for v in (
                read("allowed_priorities", ("critical", "high"))
                if not strict
                else read("allowed_priorities")
            )
        ),
        max_items=int(read("max_items", 6) if not strict else read("max_items")),
        stale_after_minutes=int(
            read("stale_after_minutes", 30) if not strict else read("stale_after_minutes")
        ),
        hard_lag_hours=int(read("hard_lag_hours", 2) if not strict else read("hard_lag_hours")),
    )


def _parse_safety(raw: Any, *, strict: bool) -> SafetyLexicon:
    if strict:
        raw = _closed_section(raw, required=SAFETY_KEYS, where="safety_lexicon")
    read = raw.__getitem__ if strict else raw.get
    return SafetyLexicon(
        zh_terms=tuple(
            str(v)
            for v in (
                read("zh_terms", SafetyLexicon().zh_terms) if not strict else read("zh_terms")
            )
        ),
        en_terms=tuple(
            str(v)
            for v in (
                read("en_terms", SafetyLexicon().en_terms) if not strict else read("en_terms")
            )
        ),
        descriptive_exceptions=tuple(
            str(v)
            for v in (
                read("descriptive_exceptions", SafetyLexicon().descriptive_exceptions)
                if not strict
                else read("descriptive_exceptions")
            )
        ),
    )


def _parse_rate_registry(raw: Any, *, strict: bool) -> RateRegistry:
    if strict:
        raw = _closed_section(raw, required=RATE_REGISTRY_KEYS, where="rate_registry")
    read = raw.__getitem__ if strict else raw.get
    return RateRegistry(
        version=str(read("version", "1") if not strict else read("version")),
        crash_cooldown_hours=int(
            read("crash_cooldown_hours", 24) if not strict else read("crash_cooldown_hours")
        ),
        schema_file=str(
            read("schema_file", "rate-registry.json") if not strict else read("schema_file")
        ),
    )


def load_config(
    config_path: str | Path,
    providers_path: str | Path | None = None,
    *,
    require_verified_enabled: bool = True,
    manifest_root: str | Path | None = None,
    strict: bool | None = None,
) -> AppConfig:
    """Load and strictly validate configuration from YAML files."""
    config_path = Path(config_path)
    data = _load_yaml(config_path)
    _reject_unknown_keys(data, ALLOWED_CONFIG_KEYS, str(config_path))

    if strict is None:
        strict = (
            manifest_root is not None
            or (
                config_path.resolve() == (config_path.parent / "config.yaml").resolve()
                and config_path.parent.name == "config"
                and config_path.parent.parent.resolve() == DEFAULT_MANIFEST_ROOT.parent.resolve()
            )
            or (
                providers_path is not None
                and Path(providers_path).resolve()
                == DEFAULT_MANIFEST_ROOT.parent / "config" / "providers.yaml"
            )
        )
    if (
        manifest_root is None
        and strict
        and config_path.resolve() == DEFAULT_MANIFEST_ROOT.parent / "config" / "config.yaml"
    ):
        manifest_root = DEFAULT_MANIFEST_ROOT
    if (
        manifest_root is None
        and strict
        and providers_path is not None
        and Path(providers_path).resolve()
        == DEFAULT_MANIFEST_ROOT.parent / "config" / "providers.yaml"
    ):
        manifest_root = DEFAULT_MANIFEST_ROOT
    if manifest_root is not None:
        manifest_root = Path(manifest_root)

    providers_file_data: Mapping[str, Any] = {}
    if providers_path is not None:
        providers_path = Path(providers_path)
        providers_file_data = _load_yaml(providers_path)
        _reject_unknown_keys(providers_file_data, ALLOWED_PROVIDER_FILE_KEYS, str(providers_path))

    if strict:
        _require_keys(data, set(APPLICATION_REQUIRED_KEYS), str(config_path))
        if providers_path is None:
            raise ConfigError("provider registry is required for strict resolution")
        _require_keys(
            providers_file_data, {"schema_version", "providers", "coverage"}, str(providers_path)
        )
        if int(providers_file_data["schema_version"]) != 1:
            raise ConfigError(f"{providers_path}: unsupported provider registry schema_version")

    _require_keys(
        data,
        {"schema_version", "name", "feed", "scoring"},
        str(config_path),
    )
    schema_version = int(data["schema_version"])
    if schema_version != 1:
        raise ConfigError(f"{config_path}: unsupported config schema_version {schema_version}")

    providers_raw: list[Any] = []
    providers_raw.extend(providers_file_data.get("providers", []))
    providers_raw.extend(data.get("providers", []))
    policies = _parse_registry_policies(providers_raw, "providers", strict=bool(strict))

    coverage_raw = providers_file_data.get("coverage", data.get("coverage", []))
    coverage = _parse_coverage(coverage_raw, "coverage", strict=bool(strict))

    if strict:
        if manifest_root is None:
            raise ConfigError("manifest root is required for strict provider resolution")
        providers = _resolve_provider_entries(
            policies, coverage, manifest_root, require_verified_enabled=require_verified_enabled
        )
    else:
        providers = _parse_providers(providers_raw, "providers")
        if require_verified_enabled:
            for p in providers:
                if p.enabled and not p.verified:
                    raise ConfigError(f"provider {p.id!r} is enabled but unverified")
            _validate_coverage(providers, coverage)
            _validate_rate_policies(providers)

    feed_raw = data["feed"]
    scoring = _parse_scoring(data["scoring"], "scoring", strict=bool(strict))
    if strict:
        _validate_scoring_domains(scoring)

    roles = _parse_roles(data.get("roles", []), "roles", strict=bool(strict))
    if require_verified_enabled:
        _validate_role_ids(roles)

    entities = (
        _parse_entities_strict(data.get("entities", []))
        if strict
        else _parse_entities(data.get("entities", []), "entities")
    )
    source_families = _parse_source_families(data.get("source_families", []), strict=bool(strict))
    sessions = (
        _parse_sessions_strict(data.get("sessions", []))
        if strict
        else tuple(
            Session(
                id=str(s["id"]),
                calendar=str(s["calendar"]),
                session_class=str(s.get("session_class", "exchange_traded")),
                timezone=str(s.get("timezone", "UTC")),
                annualization_factor=str(s.get("annualization_factor", "252")),
                availability_lag_seconds=int(s.get("availability_lag_seconds", 300)),
            )
            for s in data.get("sessions", [])
        )
    )
    session_by_id: dict[str, Session] = {}
    for session in sessions:
        if session.id in session_by_id:
            raise ConfigError(f"duplicate session id {session.id!r}")
        if session.session_class not in SCORING_ENUMS["session_class"]:
            _check_enum(session.session_class, "session_class", f"sessions.{session.id}")
        if session.availability_lag_seconds < 0:
            raise ConfigError(
                f"sessions.{session.id}.availability_lag_seconds must be non-negative"
            )
        if session.session_class == "exchange_traded" and session.calendar not in set(
            xcals.get_calendar_names()
        ):
            raise ConfigError(
                f"sessions.{session.id}: unknown exchange calendar {session.calendar!r}"
            )
        session_by_id[session.id] = session
    if require_verified_enabled:
        for role in roles:
            role_session = session_by_id.get(role.session_id)
            if role_session is None:
                raise ConfigError(f"role {role.id!r}: unknown session {role.session_id!r}")
            if role_session.session_class != role.session_class:
                raise ConfigError(
                    f"role {role.id!r}: session {role.session_id!r} is incompatible "
                    f"with role session_class {role.session_class!r}"
                )
    watched = (
        _parse_watched_strict(data.get("watched_companies", []))
        if strict
        else tuple(
            WatchCompany(
                cik=str(w["cik"]),
                name=str(w["name"]),
                tickers=tuple(str(t) for t in w.get("tickers", [])),
            )
            for w in data.get("watched_companies", [])
        )
    )

    feed_limits = _parse_feed_limits(feed_raw, strict=bool(strict))
    market_state = (
        _parse_market_state(data["market_state"], strict=bool(strict)) if strict else MarketState()
    )
    calendar = (
        _parse_calendar(data["calendar"], strict=bool(strict)) if strict else CalendarPolicy()
    )
    safety = (
        _parse_safety(data["safety_lexicon"], strict=bool(strict)) if strict else SafetyLexicon()
    )
    rate_registry = (
        _parse_rate_registry(data["rate_registry"], strict=bool(strict))
        if strict
        else RateRegistry()
    )

    if strict:
        provider_ids = {p.id for p in providers}
        family_ids = {family.id for family in source_families}
        session_ids = {session.id for session in sessions}
        for provider in providers:
            if provider.source_family_id not in family_ids:
                raise ConfigError(
                    f"provider {provider.id!r}: unknown source family {provider.source_family_id!r}"
                )
            if (
                provider.enabled
                and provider.response_limit_bytes > feed_limits.max_decompressed_response_bytes
            ):
                raise ConfigError(
                    f"provider {provider.id!r}: response limit exceeds global decompressed-response bound"
                )
        for role in roles:
            if role.provider_id not in provider_ids:
                raise ConfigError(f"role {role.id!r}: unknown provider {role.provider_id!r}")
            if role.session_id not in session_ids:
                raise ConfigError(f"role {role.id!r}: unknown session {role.session_id!r}")
        _validate_coverage(providers, coverage)
        _validate_market_coverage(providers, coverage)
        _validate_rate_policies(providers)
        yahoo = next((p for p in providers if p.id == "yahoo_market"), None)
        if yahoo is not None:
            _validate_role_mapping_mirrors(yahoo, roles)

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
        scoring=scoring,
        market_state=market_state,
        calendar=calendar,
        safety_lexicon=safety,
        rate_registry=rate_registry,
        output_root=str(data["output_root"]) if strict else str(data.get("output_root", "feeds")),
        runs_root=str(data["runs_root"]) if strict else str(data.get("runs_root", "runs")),
        timezone=str(data["timezone"]) if strict else str(data.get("timezone", "Asia/Shanghai")),
        freshness_limit_minutes=int(data["freshness_limit_minutes"])
        if strict
        else int(data.get("freshness_limit_minutes", 30)),
        normal_lag_hours=int(data["normal_lag_hours"])
        if strict
        else int(data.get("normal_lag_hours", 2)),
    )
