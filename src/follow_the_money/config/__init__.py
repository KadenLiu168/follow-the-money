"""Strict Feed-only configuration loading and typed models."""

from .model import (
    REQUIRED_PROVIDER_IDS,
    SUPPORTED_FEED_PAYLOAD_TYPES,
    AppConfig,
    CoverageMatrix,
    CoverageRow,
    FeedLimits,
    FetchRule,
    FreshnessContract,
    ProviderEntry,
    RatePolicy,
    RateRegistry,
    SourceFamily,
    SourceLinkRule,
    WatchCompany,
)


def __getattr__(name: str):
    if name not in {"ConfigError", "load_config"}:
        raise AttributeError(name)

    from .load import ConfigError, load_config

    return {"ConfigError": ConfigError, "load_config": load_config}[name]


__all__ = [
    "REQUIRED_PROVIDER_IDS",
    "SUPPORTED_FEED_PAYLOAD_TYPES",
    "AppConfig",
    "ConfigError",
    "CoverageMatrix",
    "CoverageRow",
    "FeedLimits",
    "FetchRule",
    "FreshnessContract",
    "ProviderEntry",
    "RatePolicy",
    "RateRegistry",
    "SourceFamily",
    "SourceLinkRule",
    "WatchCompany",
    "load_config",
]
