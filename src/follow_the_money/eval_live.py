"""Credentialed live-evaluation budget controller (task 11.7/11.8).

- Opt-in live mode re-runs golden inputs through the configured prompts/model
  under declared repetition, request-attempt, monotonic-time, and Decimal USD
  cost budgets that cover the entire invocation.
- Requires an explicit local versioned/fingerprinted exact-model price table
  (source URL/effective date, allowed returned canonical model IDs/aliases,
  Decimal USD-per-million input/output token rates); never fetches prices at
  runtime.
- Concurrency 1; admission in stable day/date, repetition, pass, object,
  logical-attempt order.
- Before every attempt: atomically debit a worst-case reservation
  (one-token-per-complete-request-byte + max output tokens); no send when
  committed + reservation > budget (equality allowed). Pre-send failure
  releases; post-dispatch loss/timeout/HTTP error retains full reservation.
- A received Responses object must return an allowed exact model, valid usage
  within the reservation, and zero reasoning tokens; only then does actual
  spend replace the reservation (no cache discounts). Violations retain the
  reservation and become ``budget_integrity_failure``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

RATE_PER_MILLION = Decimal(1000000)


class LiveEvalError(ValueError):
    """Live-evaluation budget or integrity failure."""


@dataclass(frozen=True)
class PriceTableEntry:
    model_id: str
    input_usd_per_million: str
    output_usd_per_million: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class PriceTable:
    source_url: str
    effective_date: str
    fingerprint: str
    entries: tuple[PriceTableEntry, ...]

    def allowed_models(self) -> set[str]:
        out: set[str] = set()
        for e in self.entries:
            out.add(e.model_id)
            out.update(e.aliases)
        return out

    def rates_for(self, model_id: str) -> PriceTableEntry | None:
        for e in self.entries:
            if model_id == e.model_id or model_id in e.aliases:
                return e
        return None


def load_price_table(path: Path) -> PriceTable:
    """Load the local versioned/fingerprinted price table."""
    data = json.loads(path.read_bytes())
    if data.get("version") != 1:
        raise LiveEvalError("price table version must be 1")
    fingerprint = data.get("fingerprint", "")
    if not fingerprint:
        raise LiveEvalError("price table missing fingerprint")
    entries = tuple(
        PriceTableEntry(
            model_id=e["model_id"],
            input_usd_per_million=e["input_usd_per_million"],
            output_usd_per_million=e["output_usd_per_million"],
            aliases=tuple(e.get("aliases", [])),
        )
        for e in data.get("entries", [])
    )
    return PriceTable(
        source_url=data["source_url"],
        effective_date=data["effective_date"],
        fingerprint=fingerprint,
        entries=entries,
    )


@dataclass
class BudgetState:
    max_cost_usd: Decimal
    max_requests: int
    max_seconds: float
    committed_spend: Decimal = Decimal(0)
    requests_used: int = 0
    started_monotonic: float = 0.0
    incomplete: bool = False
    integrity_failures: list[str] = field(default_factory=list)

    def reservation(self, *, request_bytes: int, max_output_tokens: int) -> Reservation:
        """Conservative worst-case reservation: one token per request byte
        plus max output tokens (rates applied by caller)."""
        input_tokens = Decimal(request_bytes)
        return Reservation(input_tokens=input_tokens, output_tokens=Decimal(max_output_tokens))

    def can_admit(self, reservation: Reservation, rates: PriceTableEntry) -> bool:
        return (self.committed_spend + reservation.cost(rates)) <= self.max_cost_usd

    def debit(self, reservation: Reservation, rates: PriceTableEntry) -> None:
        cost = reservation.cost(rates)
        if not self.can_admit(reservation, rates):
            raise LiveEvalError("budget exhausted: reservation exceeds remaining cost")
        self.committed_spend += cost
        self.requests_used += 1

    def release(self, reservation: Reservation, rates: PriceTableEntry) -> None:
        """Confirmed pre-send failure releases the reservation."""
        cost = reservation.cost(rates)
        self.committed_spend = max(Decimal(0), self.committed_spend - cost)
        self.requests_used = max(0, self.requests_used - 1)

    def settle(
        self, reservation: Reservation, rates: PriceTableEntry, actual_cost: Decimal
    ) -> None:
        """Replace reservation with actual spend after a valid response."""
        self.committed_spend = self.committed_spend - reservation.cost(rates) + actual_cost

    def reconcile_response(
        self,
        *,
        reservation: Reservation,
        response: Any,
        price_table: PriceTable,
        pass_limits: Mapping[str, Any],
    ) -> Decimal | None:
        """Validate a Responses object and return actual cost, or None on
        integrity failure (reservation retained)."""
        model = getattr(response, "model", None)
        if model not in price_table.allowed_models():
            self.integrity_failures.append(f"returned model {model!r} not in price table allowset")
            return None
        rates = price_table.rates_for(model)
        if rates is None:
            self.integrity_failures.append("no rates for returned model")
            return None
        usage = getattr(response, "usage", None)
        if usage is None:
            self.integrity_failures.append("missing usage")
            return None
        input_tokens = Decimal(getattr(usage, "input_tokens", -1))
        output_tokens = Decimal(getattr(usage, "output_tokens", -1))
        reasoning = getattr(usage, "output_tokens_details", None)
        reasoning_tokens = getattr(reasoning, "reasoning_tokens", 0) if reasoning else 0
        if reasoning_tokens != 0:
            self.integrity_failures.append("nonzero reasoning tokens")
            return None
        if input_tokens < 0 or output_tokens < 0:
            self.integrity_failures.append("invalid usage")
            return None
        if input_tokens > reservation.input_tokens or output_tokens > reservation.output_tokens:
            self.integrity_failures.append("usage exceeds reservation")
            return None
        actual = (
            input_tokens * Decimal(rates.input_usd_per_million) / RATE_PER_MILLION
            + output_tokens * Decimal(rates.output_usd_per_million) / RATE_PER_MILLION
        )
        return actual


@dataclass(frozen=True)
class Reservation:
    input_tokens: Decimal
    output_tokens: Decimal

    def cost(self, rates: PriceTableEntry) -> Decimal:
        return (
            self.input_tokens * Decimal(rates.input_usd_per_million) / RATE_PER_MILLION
            + self.output_tokens * Decimal(rates.output_usd_per_million) / RATE_PER_MILLION
        )
