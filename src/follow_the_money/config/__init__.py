"""Closed versioned configuration for Follow the Money.

Config loading is strict and explicit:

- Files must be valid UTF-8 with only Unicode scalar values (lone surrogates
  are rejected before any further processing).
- Every closed categorical enum is validated against its versioned allowed
  values; unknown members are rejected, never silently defaulted.
- Numeric/reference unknown values are represented as ``null`` plus a required
  closed ``unknown_reason``; categorical unknowns use the literal ``unknown``
  enum plus a required bounded ``audit_reason``.
- Cross-field invariants (duplicate provider IDs, unverified enabled
  adapters, coverage-matrix rows, role mappings, weight sums) are validated.
"""

from .load import ConfigError, load_config
from .model import (
    V1_ROLE_IDS,
    AppConfig,
    CoverageMatrix,
    CoverageRow,
    FeedLimits,
    FreshnessContract,
    MarketRole,
    MarketState,
    ProviderEntry,
    RatePolicy,
    Scoring,
    Session,
    SourceFamily,
    SurpriseScale,
)

__all__ = [
    "V1_ROLE_IDS",
    "AppConfig",
    "ConfigError",
    "CoverageMatrix",
    "CoverageRow",
    "FeedLimits",
    "FreshnessContract",
    "MarketRole",
    "MarketState",
    "ProviderEntry",
    "RatePolicy",
    "Scoring",
    "Session",
    "SourceFamily",
    "SurpriseScale",
    "load_config",
]
