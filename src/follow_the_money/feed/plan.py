"""Feed window planning and health accounting.

Design sections 2/4:

- The evidence window is ``[window.start, evidence_cutoff_at)`` and MUST be
  strictly advancing. After acquiring the exclusive collection lock and
  before any provider call, planning reads ``feeds/latest.json``.
- An actually absent path is a first-run bootstrap (``window.start =
  cutoff - 72h``). A present but invalid latest is typed
  ``invalid_latest_integrity`` with zero provider calls/writes.
- If the captured cutoff <= latest cutoff, planning fails typed
  ``non_advancing_cutoff`` with no call/artifact.
- A gap > 72h uses the bounded bootstrap start and records an uncovered
  interval warning; an exact 72h gap starts at the prior cutoff.
- Group health: a member is healthy for counting only when it succeeds with
  accepted items or returns a manifest-permitted empty result. A deficient
  mandatory group marks the non-empty Feed ``degraded``; zero accepted items
  is failure.
- Outcomes aggregate by stable ``provider_id`` key and serialize exactly one
  entry per planned provider in ascending ``provider_id`` order, so worker
  completion order never changes the Feed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..config.model import AppConfig


class FeedPlanError(ValueError):
    """Feed planning failed closed."""


@dataclass(frozen=True)
class FeedPlan:
    window_start: str
    evidence_cutoff_at: str
    bootstrap: bool
    gap_warning: tuple[str, str] | None = None  # (uncovered_start, uncovered_end)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def fmt_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def plan_window(
    *,
    cutoff: datetime,
    latest_path: Path,
    bootstrap_lookback_hours: int = 72,
    gap_threshold_hours: int = 72,
    validate_latest: Callable[[Path], Any] | None = None,
) -> FeedPlan:
    """Plan the strictly advancing half-open evidence window.

    ``validate_latest`` returns the latest Feed dict or raises on invalid
    integrity. ``None`` means treat any present path as invalid-integrity.
    """
    cutoff_iso = fmt_utc(cutoff)

    if not latest_path.exists():
        start = cutoff - timedelta(hours=bootstrap_lookback_hours)
        return FeedPlan(window_start=fmt_utc(start), evidence_cutoff_at=cutoff_iso, bootstrap=True)

    # Present path: must validate as a complete latest Feed.
    try:
        latest = validate_latest(latest_path) if validate_latest else None
    except Exception as exc:
        raise FeedPlanError(f"invalid_latest_integrity: {exc}") from exc
    if latest is None:
        raise FeedPlanError("invalid_latest_integrity: latest path present but unvalidated")

    latest_cutoff = parse_utc(latest["evidence_cutoff_at"])
    if cutoff <= latest_cutoff:
        raise FeedPlanError(
            "non_advancing_cutoff: new cutoff <= latest cutoff "
            f"({cutoff_iso} <= {fmt_utc(latest_cutoff)})"
        )

    gap = (cutoff - latest_cutoff).total_seconds() / 3600
    if gap > gap_threshold_hours:
        start = cutoff - timedelta(hours=bootstrap_lookback_hours)
        return FeedPlan(
            window_start=fmt_utc(start),
            evidence_cutoff_at=cutoff_iso,
            bootstrap=True,
            gap_warning=(fmt_utc(latest_cutoff), fmt_utc(start)),
        )
    # Exact 72h or less: start at the prior cutoff (strictly advancing).
    return FeedPlan(
        window_start=fmt_utc(latest_cutoff), evidence_cutoff_at=cutoff_iso, bootstrap=False
    )


@dataclass
class ProviderOutcome:
    provider_id: str
    state: str = "skipped"  # healthy | empty | partial | failed | skipped
    attempted: int = 0
    fetched: int = 0
    accepted: int = 0
    rejected: int = 0
    error: str | None = None
    retrieved_at: str | None = None
    execution_failure: bool = False
    non_permitted_empty_observed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "state": self.state,
            "attempted": self.attempted,
            "fetched": self.fetched,
            "succeeded": self.state in ("healthy", "empty", "partial"),
            "empty": self.state == "empty",
            "partial": self.state == "partial",
            "failed": self.state == "failed",
            "skipped": self.state == "skipped",
            "accepted": self.accepted,
            "rejected": self.rejected,
            "error": self.error,
            "retrieved_at": self.retrieved_at,
        }

    @property
    def healthy(self) -> bool:
        """Whether the serialized provider state is explicitly healthy."""
        return self.state == "healthy"

    def contributes_to_coverage(self, *, empty_valid_for_window: bool) -> bool:
        """Return whether this outcome satisfies one mandatory member slot."""
        return self.state == "healthy" or (self.state == "empty" and empty_valid_for_window)


def ordered_outcomes(outcomes: Mapping[str, ProviderOutcome]) -> list[ProviderOutcome]:
    """One outcome per planned provider, ascending ``provider_id``.

    Workers only ever update their stable ``provider_id``-keyed outcome; this
    serialization makes provider completion order irrelevant to the Feed.
    """
    return [outcomes[pid] for pid in sorted(outcomes)]


def assess_pipeline(
    *,
    config: AppConfig,
    outcomes: Mapping[str, ProviderOutcome],
    total_accepted: int,
) -> tuple[str, list[str]]:
    """Return ``(status, warnings)`` from provider outcomes.

    status: healthy | degraded | failure.
    """
    provider_config = {provider.id: provider for provider in config.providers}
    warnings: list[str] = []
    by_group: dict[str, list[ProviderOutcome]] = {}
    for row in config.coverage.rows:
        by_group[row.group] = [outcomes.get(m, ProviderOutcome(m)) for m in row.members]

    degraded_providers: list[str] = []
    for provider_id, provider in provider_config.items():
        if not provider.enabled:
            continue
        outcome = outcomes.get(provider_id, ProviderOutcome(provider_id))
        if outcome.state == "healthy":
            continue
        if outcome.state == "empty" and provider.empty_valid_for_window:
            continue
        degraded_providers.append(provider_id)
    if degraded_providers:
        warnings.append(f"degraded providers: {', '.join(sorted(degraded_providers))}")

    deficient: list[str] = []
    for row in config.coverage.rows:
        healthy_count = sum(
            1
            for member, outcome in zip(row.members, by_group[row.group], strict=True)
            if outcome.contributes_to_coverage(
                empty_valid_for_window=provider_config[member].empty_valid_for_window
            )
        )
        if healthy_count < row.minimum and not row.optional:
            deficient.append(row.group)

    if deficient:
        warnings.append(f"deficient coverage groups: {', '.join(deficient)}")
    if total_accepted == 0:
        warnings.insert(0, "no accepted item from any enabled provider")
        return "failure", warnings
    if degraded_providers or deficient:
        return "degraded", warnings

    return "healthy", warnings
