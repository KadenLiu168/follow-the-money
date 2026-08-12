"""Deterministic surprise calculation (task 6.3/6.4).

- Raw surprise = ``actual - consensus`` only for compatible units.
- Normalized surprise = ``raw / configured_positive_scale`` only when a
  versioned per-series scale exists; otherwise ``unknown``.
- V1 scales: 0.1 percentage point for exact US CPI-all-items-SA-MoM,
  core-PCE-MoM, and PPI-final-demand-SA-MoM series identities. Series
  identity, seasonal adjustment, and frequency must match exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..config.model import Scoring

V1_SERIES = {
    "us_cpi_all_items_sa_mom": "0.1",
    "us_core_pce_mom": "0.1",
    "us_ppi_final_demand_sa_mom": "0.1",
}


@dataclass(frozen=True)
class SurpriseResult:
    raw: Decimal | None
    normalized: Decimal | None
    unknown_reason: str | None = None

    @property
    def is_unknown(self) -> bool:
        return self.normalized is None


def raw_surprise(actual: Decimal, consensus: Decimal) -> Decimal:
    return actual - consensus


def normalized_surprise(actual: Decimal, consensus: Decimal, scale: Decimal) -> Decimal:
    if scale <= 0:
        raise ValueError("scale must be positive")
    return (actual - consensus) / scale


def surprise_for_series(
    *,
    series_id: str,
    actual: Decimal | None,
    consensus: Decimal | None,
    unit: str | None = None,
    compatible_unit: str = "percent",
    scales: Scoring | None = None,
) -> SurpriseResult:
    """Compute surprise for one series under the v1 contract."""
    if actual is None or consensus is None:
        return SurpriseResult(None, None, "missing_consensus_or_actual")
    if unit and unit != compatible_unit:
        return SurpriseResult(None, None, "incompatible_unit")
    scale = (
        scales and {s.series_id: s.scale for s in scales.surprise_scales}.get(series_id)
    ) or V1_SERIES.get(series_id)
    if scale is None:
        return SurpriseResult(None, None, "no_versioned_scale")
    raw = actual - consensus
    norm = raw / Decimal(scale)
    return SurpriseResult(raw=raw, normalized=norm)
