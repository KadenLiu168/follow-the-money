"""Strict Feed-only configuration loading and typed models."""

from .load import ConfigError, load_config
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
