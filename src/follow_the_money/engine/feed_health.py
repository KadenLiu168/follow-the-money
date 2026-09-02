"""Feed loading and health assessment for the daily Skill.

Design section 5:

- The daily Skill consumes only ``feeds/latest.json``; runtime continuity is
  owned by checkpoint state, not by additional Feed products.
- V1 stale boundary: lag > 30 minutes is stale; normal mode refuses lag > 2
  hours. ``brief_generated_at < evidence_cutoff_at`` or ``< feed.generated_at``
  fails closed with ``clock_before_feed``.
- The calendar snapshot must satisfy ``calendar_horizon_end >= brief_generated_at + 24h``
  for a normal watchlist contract.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..canonical import load_canonical_json
from ..feed.validate import assert_feed_identity, validate_feed


class FeedLoadError(ValueError):
    """Latest Feed failed loading/health assessment."""


@dataclass
class FeedHealth:
    status: str  # healthy | degraded
    warnings: list[str] = field(default_factory=list)
    lag_minutes: float | None = None
    feed_generated_at: str | None = None


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_latest_feed(path: Path) -> dict[str, Any]:
    """Load and fully validate ``feeds/latest.json``."""
    if not path.exists():
        raise FeedLoadError(f"latest Feed not found: {path}")
    try:
        feed = load_canonical_json(path.read_bytes(), where="latest.json")
        validate_feed(feed)
        assert_feed_identity(feed)
    except Exception as exc:
        raise FeedLoadError(f"invalid latest Feed: {exc}") from exc
    return feed


def assess_health(
    feed: Mapping[str, Any],
    *,
    brief_generated_at: str | None = None,
    now: Callable[[], datetime] | None = None,
    freshness_limit_minutes: int = 30,
    normal_lag_hours: int = 2,
) -> FeedHealth:
    """Assess Feed freshness/coverage; raise on hard-lag and clock violations."""
    now_dt = now() if now else datetime.now(UTC)
    cutoff = parse_utc(feed["evidence_cutoff_at"])
    generated = parse_utc(feed["generated_at"])

    warnings: list[str] = []
    status = "healthy"

    if brief_generated_at is not None:
        brief_dt = parse_utc(brief_generated_at)
        if brief_dt < cutoff:
            raise FeedLoadError("clock_before_feed: brief_generated_at < evidence_cutoff_at")
        if brief_dt < generated:
            raise FeedLoadError("clock_before_feed: brief_generated_at < feed.generated_at")
        lag = (brief_dt - cutoff).total_seconds() / 60
    else:
        lag = (now_dt - cutoff).total_seconds() / 60

    if lag > normal_lag_hours * 60:
        raise FeedLoadError(
            f"Feed lag {lag:.0f} minutes exceeds normal-mode maximum {normal_lag_hours}h"
        )
    if lag > freshness_limit_minutes:
        warnings.append(f"stale Feed: lag {lag:.0f} minutes > {freshness_limit_minutes} minutes")
        status = "degraded"

    pipeline = feed.get("pipeline", {})
    pipeline_status = pipeline.get("status")
    if pipeline_status == "failure":
        raise FeedLoadError("pipeline.status=failure: Feed is not consumable")
    if pipeline_status == "degraded":
        warnings.extend(pipeline.get("warnings", []))
        status = "degraded"

    return FeedHealth(
        status=status,
        warnings=warnings,
        lag_minutes=lag,
        feed_generated_at=feed.get("generated_at"),
    )


def check_calendar_horizon(feed: Mapping[str, Any], brief_generated_at: str) -> None:
    """Fail if the 26h calendar snapshot cannot cover [brief_generated_at, +24h)."""
    horizon = feed.get("calendar_horizon_end")
    if not horizon:
        raise FeedLoadError("Feed missing calendar_horizon_end; normal watchlist contract fails")
    horizon_dt = parse_utc(horizon)
    brief_dt = parse_utc(brief_generated_at)
    if horizon_dt < brief_dt + timedelta(hours=24):
        raise FeedLoadError(
            "calendar_horizon_end shorter than brief_generated_at + 24h; "
            "normal watchlist coverage cannot be claimed"
        )
