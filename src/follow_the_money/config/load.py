"""Strict loading and validation of the Feed-only YAML configuration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from ..providers.manifest import ManifestError, load_manifest, manifest_to_provider_entry
from .model import (
    REQUIRED_COVERAGE_GROUPS,
    REQUIRED_PROVIDER_IDS,
    AppConfig,
    CoverageMatrix,
    CoverageRow,
    FeedLimits,
    ProviderEntry,
    RatePolicy,
    RateRegistry,
    SourceFamily,
    WatchCompany,
)


class ConfigError(ValueError):
    """Configuration failed closed validation."""


ALLOWED_CONFIG_KEYS = frozenset(
    {
        "schema_version",
        "name",
        "timezone",
        "output_root",
        "runtime_state_root",
        "runs_root",
        "feed",
        "rate_registry",
        "source_families",
        "watched_companies",
    }
)
ALLOWED_PROVIDER_FILE_KEYS = frozenset({"schema_version", "providers", "coverage"})
APPLICATION_REQUIRED_KEYS = frozenset(ALLOWED_CONFIG_KEYS)
FEED_KEYS = frozenset(
    {
        "bootstrap_lookback_hours",
        "gap_threshold_hours",
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
        "max_serialized_feed_bytes",
        "lock_timeout_seconds",
    }
)
RATE_REGISTRY_KEYS = frozenset({"version", "crash_cooldown_hours", "schema_file"})
_PROVIDER_POLICY_KEYS = frozenset({"id", "enabled"})
_COVERAGE_KEYS = frozenset({"group", "members", "minimum", "capability", "optional"})

_REMOVED_CONFIG_TERMS = (
    "audit",
    "event",
    "entity",
    "market",
    "role",
    "session",
    "watchlist",
    "scoring",
    "ranking",
    "calendar",
    "flow",
    "brief",
    "yahoo",
)


def _reject_lone_surrogates(text: str, where: str) -> None:
    for char in text:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise ConfigError(f"{where}: lone surrogate U+{ord(char):04X} is not a Unicode scalar")


def _require_keys(mapping: Mapping[str, Any], required: set[str], where: str) -> None:
    missing = required - set(mapping)
    if missing:
        raise ConfigError(f"{where}: missing required keys: {sorted(missing)}")


def _reject_unknown_keys(mapping: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = set(mapping) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown keys: {sorted(unknown)}")


def _closed_section(
    raw: Any,
    *,
    required: frozenset[str],
    where: str,
    allowed: frozenset[str] | None = None,
) -> Mapping[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: must be a mapping")
    _require_keys(raw, set(required), where)
    _reject_unknown_keys(raw, allowed or required, where)
    return raw


def _as_int(value: Any, where: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{where} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{where} must be an integer") from exc


def _as_nonempty_str(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} must be a non-empty string")
    _reject_lone_surrogates(value, where)
    return value


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


def _parse_feed_limits(raw: Any) -> FeedLimits:
    values = _closed_section(raw, required=FEED_KEYS, where="feed")
    parsed = {key: _as_int(values[key], f"feed.{key}") for key in FEED_KEYS}
    for key, value in parsed.items():
        if value <= 0:
            raise ConfigError(f"feed.{key} must be positive, got {value}")
    if parsed["commit_reserve_seconds"] >= parsed["pre_commit_deadline_seconds"]:
        raise ConfigError(
            "feed.commit_reserve_seconds must be less than pre_commit_deadline_seconds"
        )
    return FeedLimits(**parsed)


def _parse_rate_registry(raw: Any) -> RateRegistry:
    values = _closed_section(raw, required=RATE_REGISTRY_KEYS, where="rate_registry")
    version = _as_nonempty_str(values["version"], "rate_registry.version")
    schema_file = _as_nonempty_str(values["schema_file"], "rate_registry.schema_file")
    cooldown = _as_int(values["crash_cooldown_hours"], "rate_registry.crash_cooldown_hours")
    if cooldown <= 0:
        raise ConfigError("rate_registry.crash_cooldown_hours must be positive")
    return RateRegistry(version=version, crash_cooldown_hours=cooldown, schema_file=schema_file)


def _parse_registry_policies(raw: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        raise ConfigError("providers must be a list")
    policies: list[dict[str, Any]] = []
    seen: set[str] = set()
    supported = set(REQUIRED_PROVIDER_IDS)
    for index, item in enumerate(raw):
        where = f"providers[{index}]"
        values = _closed_section(
            item,
            required=_PROVIDER_POLICY_KEYS,
            allowed=_PROVIDER_POLICY_KEYS,
            where=where,
        )
        provider_id = _as_nonempty_str(values["id"], f"{where}.id")
        if provider_id not in supported:
            raise ConfigError(
                f"{where}.id names a removed or unsupported Provider: {provider_id!r}"
            )
        if provider_id in seen:
            raise ConfigError(f"providers: duplicate provider id {provider_id!r}")
        if not isinstance(values["enabled"], bool):
            raise ConfigError(f"{where}.enabled must be boolean")
        seen.add(provider_id)
        policies.append({"id": provider_id, "enabled": values["enabled"]})
    return tuple(policies)


def _parse_coverage(raw: Any) -> CoverageMatrix:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("coverage must be a non-empty list")
    rows: list[CoverageRow] = []
    seen_groups: set[str] = set()
    for index, item in enumerate(raw):
        where = f"coverage[{index}]"
        values = _closed_section(item, required=_COVERAGE_KEYS, where=where)
        group = _as_nonempty_str(values["group"], f"{where}.group")
        capability = _as_nonempty_str(values["capability"], f"{where}.capability")
        lowered = f"{group} {capability}".lower()
        if any(term in lowered for term in ("market_data", "calendar", "flow", "yahoo")):
            raise ConfigError(f"{where}: removed Feed coverage claim")
        if group in seen_groups:
            raise ConfigError(f"coverage: duplicate group {group!r}")
        members = values["members"]
        if (
            not isinstance(members, list)
            or not members
            or any(not isinstance(member, str) or not member.strip() for member in members)
        ):
            raise ConfigError(f"{where}.members must be a non-empty list of Provider IDs")
        member_ids = tuple(str(member) for member in members)
        if len(set(member_ids)) != len(member_ids):
            raise ConfigError(f"{where}.members contains duplicates")
        minimum = _as_int(values["minimum"], f"{where}.minimum")
        if minimum <= 0 or minimum > len(member_ids):
            raise ConfigError(f"{where}.minimum must be in 1..len(members)")
        if not isinstance(values["optional"], bool):
            raise ConfigError(f"{where}.optional must be boolean")
        seen_groups.add(group)
        rows.append(
            CoverageRow(
                group=group,
                members=member_ids,
                minimum=minimum,
                capability=capability,
                optional=values["optional"],
            )
        )
    return CoverageMatrix(tuple(rows))


def _parse_source_families(raw: Any) -> tuple[SourceFamily, ...]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("source_families must be a non-empty list")
    values: list[SourceFamily] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        where = f"source_families[{index}]"
        data = _closed_section(
            item,
            required=frozenset({"id", "name", "tier"}),
            where=where,
        )
        family_id = _as_nonempty_str(data["id"], f"{where}.id")
        name = _as_nonempty_str(data["name"], f"{where}.name")
        tier = _as_nonempty_str(data["tier"], f"{where}.tier")
        if tier not in {"Tier 1", "Tier 2", "Tier 3"}:
            raise ConfigError(f"{where}.tier is invalid")
        if family_id in seen:
            raise ConfigError(f"source_families: duplicate id {family_id!r}")
        seen.add(family_id)
        values.append(SourceFamily(family_id, name, tier))
    return tuple(values)


def _parse_watched_companies(raw: Any) -> tuple[WatchCompany, ...]:
    if not isinstance(raw, list):
        raise ConfigError("watched_companies must be a list")
    values: list[WatchCompany] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        where = f"watched_companies[{index}]"
        data = _closed_section(
            item,
            required=frozenset({"cik", "name", "tickers"}),
            where=where,
        )
        cik = _as_nonempty_str(data["cik"], f"{where}.cik")
        name = _as_nonempty_str(data["name"], f"{where}.name")
        tickers = data["tickers"]
        if not isinstance(tickers, list) or any(
            not isinstance(ticker, str) or not ticker.strip() for ticker in tickers
        ):
            raise ConfigError(f"{where}.tickers must be a list of strings")
        if cik in seen:
            raise ConfigError(f"watched_companies: duplicate CIK {cik!r}")
        seen.add(cik)
        values.append(WatchCompany(cik, name, tuple(tickers)))
    return tuple(values)


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
        provider_id = str(policy["id"])
        try:
            manifest = load_manifest(provider_id, manifest_root)
            entry = manifest_to_provider_entry(
                manifest,
                enabled=bool(policy["enabled"]),
                coverage_groups=tuple(sorted(groups_by_provider.get(provider_id, []))),
            )
        except ManifestError as exc:
            raise ConfigError(str(exc)) from exc
        if entry.enabled and not entry.verified and require_verified_enabled:
            raise ConfigError(f"provider {provider_id!r} is enabled but unverified")
        if entry.credentials_required:
            raise ConfigError(f"provider {provider_id!r} requires a credential")
        entries.append(entry)
    if not entries:
        raise ConfigError("provider registry resolved no entries")
    return tuple(entries)


def _validate_provider_set(
    providers: tuple[ProviderEntry, ...], *, require_verified_enabled: bool
) -> None:
    actual = tuple(provider.id for provider in providers)
    if len(set(actual)) != len(actual):
        raise ConfigError("provider registry contains duplicate IDs")
    if require_verified_enabled and set(actual) != set(REQUIRED_PROVIDER_IDS):
        missing = sorted(set(REQUIRED_PROVIDER_IDS) - set(actual))
        extra = sorted(set(actual) - set(REQUIRED_PROVIDER_IDS))
        raise ConfigError(
            f"production Provider set is not exactly required: missing={missing}, extra={extra}"
        )
    if require_verified_enabled:
        disabled = sorted(provider.id for provider in providers if not provider.enabled)
        if disabled:
            raise ConfigError(f"required Providers are disabled: {disabled}")


def _validate_coverage(
    providers: tuple[ProviderEntry, ...], coverage: CoverageMatrix, *, strict: bool
) -> None:
    by_id = {provider.id: provider for provider in providers}
    members_seen: set[str] = set()
    for row in coverage.rows:
        for member in row.members:
            provider = by_id.get(member)
            if provider is None:
                raise ConfigError(f"coverage row {row.group}: unknown Provider {member!r}")
            if not provider.verified:
                raise ConfigError(f"coverage row {row.group}: Provider {member!r} is unverified")
            if not provider.enabled and not row.optional:
                raise ConfigError(f"coverage row {row.group}: Provider {member!r} is disabled")
            members_seen.add(member)
        enabled_members = [member for member in row.members if by_id[member].enabled]
        if not row.optional and len(enabled_members) < row.minimum:
            raise ConfigError(
                f"coverage row {row.group}: minimum {row.minimum} is not achievable "
                f"(enabled: {enabled_members})"
            )
    if strict:
        groups = {row.group for row in coverage.rows}
        if groups != REQUIRED_COVERAGE_GROUPS:
            raise ConfigError("production coverage groups are not exactly the required Feed groups")
        missing = sorted(set(REQUIRED_PROVIDER_IDS) - members_seen)
        if missing:
            raise ConfigError(f"required Providers have no coverage membership: {missing}")
        cftc_rows = [row for row in coverage.rows if "cftc" in row.members]
        if not cftc_rows or any(row.minimum < 1 or row.optional for row in cftc_rows):
            raise ConfigError("CFTC must be a minimum-one required coverage member")


def _validate_rate_policies(providers: tuple[ProviderEntry, ...]) -> None:
    by_scope: dict[str, RatePolicy] = {}
    for provider in providers:
        policy = provider.rate_policy
        if policy is None or policy.unlimited:
            continue
        existing = by_scope.get(policy.scope_id)
        if existing is not None and existing != policy:
            raise ConfigError(f"rate scope {policy.scope_id!r} has inconsistent policies")
        by_scope[policy.scope_id] = policy


def _validate_provider_sources(
    providers: tuple[ProviderEntry, ...],
    source_families: tuple[SourceFamily, ...],
    feed: FeedLimits,
) -> None:
    families = {family.id: family for family in source_families}
    for provider in providers:
        family = families.get(provider.source_family_id)
        if family is None:
            raise ConfigError(
                f"provider {provider.id!r}: unknown source family {provider.source_family_id!r}"
            )
        if family.tier != provider.tier:
            raise ConfigError(f"provider {provider.id!r}: source-family tier mismatch")
        if provider.response_limit_bytes > feed.max_decompressed_response_bytes:
            raise ConfigError(
                f"provider {provider.id!r}: response limit exceeds global decompressed-response bound"
            )


def load_config(
    config_path: str | Path,
    providers_path: str | Path,
    *,
    manifest_root: str | Path,
    require_verified_enabled: bool = True,
) -> AppConfig:
    """Load and strictly validate the closed Feed configuration."""
    config_path = Path(config_path)
    providers_path = Path(providers_path)
    manifest_root = Path(manifest_root)
    data = _load_yaml(config_path)
    _reject_unknown_keys(data, ALLOWED_CONFIG_KEYS, str(config_path))
    _require_keys(data, set(APPLICATION_REQUIRED_KEYS), str(config_path))

    providers_data = _load_yaml(providers_path)
    _reject_unknown_keys(providers_data, ALLOWED_PROVIDER_FILE_KEYS, str(providers_path))
    _require_keys(providers_data, set(ALLOWED_PROVIDER_FILE_KEYS), str(providers_path))
    if _as_int(providers_data["schema_version"], f"{providers_path}.schema_version") != 1:
        raise ConfigError(f"{providers_path}: unsupported provider registry schema_version")
    if _as_int(data["schema_version"], f"{config_path}.schema_version") != 1:
        raise ConfigError(f"{config_path}: unsupported config schema_version")

    policies = _parse_registry_policies(providers_data["providers"])
    coverage = _parse_coverage(providers_data["coverage"])
    providers = _resolve_provider_entries(
        policies,
        coverage,
        manifest_root,
        require_verified_enabled=require_verified_enabled,
    )
    _validate_provider_set(providers, require_verified_enabled=require_verified_enabled)
    feed = _parse_feed_limits(data["feed"])
    rate_registry = _parse_rate_registry(data["rate_registry"])
    source_families = _parse_source_families(data["source_families"])
    watched_companies = _parse_watched_companies(data["watched_companies"])
    _validate_coverage(providers, coverage, strict=require_verified_enabled)
    _validate_rate_policies(providers)
    _validate_provider_sources(providers, source_families, feed)

    scalar_paths = ("name", "timezone", "output_root", "runtime_state_root", "runs_root")
    values = {path: _as_nonempty_str(data[path], f"{config_path}.{path}") for path in scalar_paths}
    for key in data:
        if key.lower() in _REMOVED_CONFIG_TERMS:
            raise ConfigError(f"{config_path}: removed configuration field {key!r}")

    return AppConfig(
        schema_version=1,
        name=values["name"],
        providers=providers,
        coverage=coverage,
        source_families=source_families,
        watched_companies=watched_companies,
        feed=feed,
        rate_registry=rate_registry,
        runtime_state_root=values["runtime_state_root"],
        output_root=values["output_root"],
        runs_root=values["runs_root"],
        timezone=values["timezone"],
    )
