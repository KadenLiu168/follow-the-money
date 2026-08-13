"""Market State Vector and regime classification.

Design section 14:

- Dashboard roles (13, exact order): S&P 500, CSI 300, Hang Seng, VIX,
  US 2y, US 10y, China 10y, DXY, USD/CNH, copper, WTI, gold, BTC.
- A move is anomalous when |current-excluded z| >= 2.0.
- Votes: z >= 0.5 => supportive +1; -0.5 < z < 0.5 => neutral 0; z <= -0.5
  => adverse -1. Exact +/-0.5 belongs to supportive/adverse.
- Dimensions (each known with minimum votes): Risk Appetite (S&P 500, CSI 300,
  Hang Seng z natural + inverted VIX z; min 2/4), Rates (inverted US 2y/10y,
  China 10y yield-change z; min 1/3), Liquidity (inverted DXY, USD/CNH
  return z; min 1/2), Growth (copper return z + directional cross-market
  equity breadth >=0.20 / <=-0.20; min 1/2), Inflation (inverted WTI return
  z + inverted CPI/PCE/PPI normalized surprise votes; min 1/4).
- Regime: unknown unless Risk Appetite known and >=4/5 dimensions known;
  risk_off when RA=-1 and sum <= -2; risk_on when RA=+1 and sum >= 2;
  neutral otherwise. Informational: never changes scoring/selection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from .config.model import AppConfig, MarketState

DIMENSIONS = ("risk_appetite", "rates", "liquidity", "growth", "inflation")


class MarketStateError(ValueError):
    """Invalid/overlapping regime rules."""


@dataclass(frozen=True)
class DimensionVote:
    supportive: int = 0
    neutral: int = 0
    adverse: int = 0

    @property
    def sum(self) -> int:
        return self.supportive - self.adverse

    @property
    def known(self) -> bool:
        return self.sum != 0 or (self.supportive == self.adverse == self.neutral > 0)


@dataclass(frozen=True)
class MarketStateResult:
    regime: str  # risk_on | neutral | risk_off | unknown
    vector: Mapping[str, str]  # dimension -> supportive|neutral|adverse|unknown
    known_dimensions: int
    missing_roles: tuple[str, ...] = ()


def z_vote(z: Decimal, threshold: str) -> int:
    """Map a z-score to a vote; exact +/-threshold belongs to supportive/adverse."""
    t = Decimal(threshold)
    if z >= t:
        return 1
    if z <= -t:
        return -1
    return 0


def breadth_vote(breadth: Decimal, threshold: str) -> int:
    t = Decimal(threshold)
    if breadth >= t:
        return 1
    if breadth <= -t:
        return -1
    return 0


def _invert(vote: int) -> int:
    return -vote if vote != 0 else 0


def classify_market_state(
    *,
    config: AppConfig,
    role_zs: Mapping[str, Decimal],  # role_id -> current-excluded z
    role_return_zs: Mapping[str, Decimal],  # role_id -> return z (liquidity)
    yield_change_zs: Mapping[str, Decimal],  # role_id -> yield bps-change z
    equity_breadth: Decimal | None,
    surprise_votes: Sequence[int] | None = None,  # inverted CPI/PCE/PPI surprise votes
) -> MarketStateResult:
    """Classify the v1 Market State Vector from deterministic z inputs."""
    ms: MarketState = config.market_state
    vector: dict[str, str] = {}
    known = 0

    # Risk Appetite: S&P 500, CSI 300, Hang Seng z natural + inverted VIX z.
    ra_votes = [
        z_vote(role_zs["sp500"], ms.z_supportive) if "sp500" in role_zs else None,
        z_vote(role_zs["csi300"], ms.z_supportive) if "csi300" in role_zs else None,
        z_vote(role_zs["hsi"], ms.z_supportive) if "hsi" in role_zs else None,
        _invert(z_vote(role_zs["vix"], ms.z_supportive)) if "vix" in role_zs else None,
    ]
    ra = _dimension([v for v in ra_votes if v is not None], ms.risk_appetite_min_votes)
    vector["risk_appetite"] = _vote_label(ra)
    known += 1 if ra is not None else 0

    # Rates: inverted US 2y/10y, China 10y yield-change z; min 1/3.
    rates_votes = [
        _invert(z_vote(yield_change_zs["us2y"], ms.z_supportive))
        if "us2y" in yield_change_zs
        else None,
        _invert(z_vote(yield_change_zs["us10y"], ms.z_supportive))
        if "us10y" in yield_change_zs
        else None,
        _invert(z_vote(yield_change_zs["cn10y"], ms.z_supportive))
        if "cn10y" in yield_change_zs
        else None,
    ]
    rates = _dimension([v for v in rates_votes if v is not None], ms.rates_min_votes)
    vector["rates"] = _vote_label(rates)
    known += 1 if rates is not None else 0

    # Liquidity: inverted DXY, USD/CNH return z; min 1/2.
    liq_votes = [
        _invert(z_vote(role_return_zs["dxy"], ms.z_supportive))
        if "dxy" in role_return_zs
        else None,
        _invert(z_vote(role_return_zs["usdcnh"], ms.z_supportive))
        if "usdcnh" in role_return_zs
        else None,
    ]
    liq = _dimension([v for v in liq_votes if v is not None], ms.liquidity_min_votes)
    vector["liquidity"] = _vote_label(liq)
    known += 1 if liq is not None else 0

    # Growth: copper return z + directional equity breadth; min 1/2.
    growth_votes = [
        z_vote(role_return_zs.get("copper", Decimal(0)), ms.z_supportive)
        if "copper" in role_return_zs
        else None,
        breadth_vote(equity_breadth, ms.breadth_supportive) if equity_breadth is not None else None,
    ]
    growth = _dimension([v for v in growth_votes if v is not None], ms.growth_min_votes)
    vector["growth"] = _vote_label(growth)
    known += 1 if growth is not None else 0

    # Inflation: inverted WTI return z + inverted surprise votes; min 1/4.
    inflation_votes: list[int | None] = [
        _invert(z_vote(role_return_zs.get("wti", Decimal(0)), ms.z_supportive))
        if "wti" in role_return_zs
        else None,
    ]
    inflation_votes.extend(surprise_votes or [])
    inflation = _dimension([v for v in inflation_votes if v is not None], ms.inflation_min_votes)
    vector["inflation"] = _vote_label(inflation)
    known += 1 if inflation is not None else 0

    # Regime.
    regime = "unknown"
    if ra is not None and known >= ms.required_known_dimensions:
        dimension_sum = sum(v or 0 for v in [ra, rates, liq, growth, inflation])
        rules = list(ms.rules_order)
        # Validate non-overlap.
        if "risk_off" in rules and "risk_on" in rules:
            if ra == -1 and dimension_sum <= -int(ms.regime_sum_threshold):
                regime = "risk_off"
            elif ra == 1 and dimension_sum >= int(ms.regime_sum_threshold):
                regime = "risk_on"
            else:
                regime = "neutral"

    available_roles = set(role_zs) | set(role_return_zs) | set(yield_change_zs)
    missing = tuple(r for r in config.role_ids if r not in available_roles)
    return MarketStateResult(
        regime=regime, vector=vector, known_dimensions=known, missing_roles=missing
    )


def _dimension(votes: Sequence[int], minimum: int) -> int | None:
    """Sign of the vote sum when at least ``minimum`` votes are present;
    exact zero sum is neutral (0); insufficient votes => unknown (None)."""
    if len(votes) < minimum:
        return None
    total = sum(votes)
    if total > 0:
        return 1
    if total < 0:
        return -1
    return 0


def _vote_label(vote: int | None) -> str:
    if vote is None:
        return "unknown"
    if vote > 0:
        return "supportive"
    if vote < 0:
        return "adverse"
    return "neutral"
