"""Normative v1 formula contract with isolated Decimal context.

Design section 10:

- Fresh local Decimal context: precision 50, ``ROUND_HALF_EVEN``,
  ``Emin = -999999``, ``Emax = 999999``, ``clamp = 0``, with
  ``InvalidOperation``/``DivisionByZero``/``Overflow``/``FloatOperation``
  trapped — never the process-global context.
- Normative operation order: mean = stable-order ``sum(x_i)/n``; sample
  variance = ``sum((x_i-mean)^2)/(n-1)``; std and annualization use
  ``Decimal.sqrt()`` in the same context; z = ``(current-mean)/std``.
- Simple return ``(current/previous - 1)``; yield change
  ``(current_percent - previous_percent) * 100`` bps; volume change
  ``(current/previous - 1)``; rolling volatility over the preceding 20
  consecutive completed-session returns annualized by sqrt(252) or sqrt(365);
  price/yield abnormal-move z-scores exclude the current change; directional
  breadth ``(positive - negative)/observable``.
- Missing sessions are never skipped/filled; unavailable metrics become
  ``unknown`` with a reason.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import (
    ROUND_HALF_EVEN,
    Decimal,
    DivisionByZero,
    FloatOperation,
    InvalidOperation,
    Overflow,
    localcontext,
)

PRECISION = 50
ROUNDING = ROUND_HALF_EVEN
EMIN = -999999
EMAX = 999999
CLAMP = 0


@contextmanager
def normative_decimal_context():
    """Fresh isolated Decimal context per the v1 contract."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUNDING
        ctx.Emin = EMIN
        ctx.Emax = EMAX
        ctx.clamp = CLAMP
        ctx.traps[InvalidOperation] = True
        ctx.traps[DivisionByZero] = True
        ctx.traps[Overflow] = True
        ctx.traps[FloatOperation] = True
        yield ctx


def dec(value: str | int | Decimal) -> Decimal:
    return Decimal(str(value))


def stable_mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("mean of empty sequence")
    total = Decimal(0)
    for v in values:
        total += v
    return total / Decimal(len(values))


def sample_variance(values: Sequence[Decimal]) -> Decimal:
    n = len(values)
    if n < 2:
        raise ValueError("sample variance requires n >= 2")
    mean = stable_mean(values)
    total = Decimal(0)
    for v in values:
        d = v - mean
        total += d * d
    return total / Decimal(n - 1)


def sample_std(values: Sequence[Decimal]) -> Decimal:
    return sample_variance(values).sqrt()


def simple_return(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        raise ZeroDivisionError("simple return requires non-zero previous")
    return current / previous - 1


def yield_change_bps(current_percent: Decimal, previous_percent: Decimal) -> Decimal:
    return (current_percent - previous_percent) * 100


def volume_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        raise ZeroDivisionError("volume change requires non-zero previous")
    return current / previous - 1


def annualized_volatility(returns: Sequence[Decimal], factor: str = "252") -> Decimal:
    """Sample std of the preceding returns annualized by sqrt(factor)."""
    std = sample_std(list(returns))
    return std * Decimal(factor).sqrt()


def price_z_score(current_return: Decimal, reference_returns: Sequence[Decimal]) -> Decimal:
    """z of the current return vs mean/std of preceding reference returns."""
    mean = stable_mean(list(reference_returns))
    std = sample_std(list(reference_returns))
    if std == 0:
        raise ZeroDivisionError("zero reference standard deviation")
    return (current_return - mean) / std


def directional_breadth(positive: int, negative: int, observable: int) -> Decimal:
    if observable <= 0:
        raise ZeroDivisionError("breadth requires positive observable count")
    return (Decimal(positive) - Decimal(negative)) / Decimal(observable)


def quantize6(value: Decimal) -> Decimal:
    """Output-only quantization to 6 decimal places (round half even)."""
    with normative_decimal_context():
        return value.quantize(Decimal("0.000001"), rounding=ROUNDING)


def quantize2(value: Decimal) -> Decimal:
    """Yield-change serialization to 2 basis-point decimals."""
    with normative_decimal_context():
        return value.quantize(Decimal("0.01"), rounding=ROUNDING)


@dataclass(frozen=True)
class MetricResult:
    value: Decimal | None
    unknown_reason: str | None = None

    @property
    def is_unknown(self) -> bool:
        return self.value is None


def rolling_volatility(
    returns: Sequence[Decimal],
    *,
    window: int = 20,
    annualization_factor: str = "252",
) -> MetricResult:
    """Sample rolling volatility over the preceding ``window`` returns."""
    if len(returns) < window:
        return MetricResult(None, "insufficient_history")
    window_returns = returns[-window:]
    try:
        with normative_decimal_context():
            vol = annualized_volatility(window_returns, annualization_factor)
    except (InvalidOperation, ZeroDivisionError, Overflow):
        return MetricResult(None, "invalid_reference_window")
    return MetricResult(vol)


def abnormal_move_z(
    current: Decimal,
    reference_changes: Sequence[Decimal],
) -> MetricResult:
    """Current-excluded z-score over preceding changes."""
    if len(reference_changes) < 20:
        return MetricResult(None, "insufficient_history")
    ref = reference_changes[-20:]
    try:
        with normative_decimal_context():
            z = price_z_score(current, list(ref))
    except (InvalidOperation, ZeroDivisionError, Overflow):
        return MetricResult(None, "zero_reference_std")
    return MetricResult(z)
