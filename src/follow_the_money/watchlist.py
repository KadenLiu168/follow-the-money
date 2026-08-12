"""Deterministic next-24-hour watchlist (task 9.5/9.6).

- Prove ``calendar_horizon_end >= brief_generated_at + 24h`` first.
- Select up to six configured ``critical``/``high`` calendar events in
  ``[brief_generated_at, brief_generated_at + 24h)`` using the injected
  clock; sort priority (critical first), then ``scheduled_at`` and stable
  calendar ID ascending; never fill from lower priorities.
- Knowledge-before-cutoff vs future scheduled time: an item whose
  ``announced_at``/knowledge was after cutoff is excluded even if its
  ``scheduled_at`` is in the window.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .config.model import CalendarPolicy


class WatchlistError(ValueError):
    """Watchlist contract violation."""


@dataclass(frozen=True)
class WatchlistEntry:
    calendar_id: str
    priority: str
    scheduled_at: str
    announced_at: str | None
    label: str
    evidence_ids: tuple[str, ...] = ()


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_watchlist(
    *,
    calendar_items: Sequence[Mapping[str, Any]],
    brief_generated_at: str,
    calendar_horizon_end: str,
    policy: CalendarPolicy,
    cutoff: str | None = None,
) -> list[WatchlistEntry]:
    """Deterministic up-to-six watchlist with injected clock semantics."""
    horizon = _parse_ts(calendar_horizon_end)
    brief_dt = _parse_ts(brief_generated_at)
    window_end = brief_dt + timedelta(hours=24)
    if horizon < window_end:
        raise WatchlistError("calendar_horizon_end shorter than brief_generated_at + 24h")

    cutoff_dt = _parse_ts(cutoff) if cutoff else None
    allowed = set(policy.allowed_priorities)
    qualifying: list[WatchlistEntry] = []
    for item in calendar_items:
        priority = item.get("priority", "")
        if priority not in allowed:
            continue
        scheduled = _parse_ts(item["scheduled_at"])
        if not (brief_dt <= scheduled < window_end):
            continue
        # Knowledge-before-cutoff: exclude items announced/known after cutoff.
        if cutoff_dt is not None:
            announced = item.get("announced_at")
            if announced and _parse_ts(announced) > cutoff_dt:
                continue
        qualifying.append(
            WatchlistEntry(
                calendar_id=item["calendar_id"],
                priority=priority,
                scheduled_at=item["scheduled_at"],
                announced_at=item.get("announced_at"),
                label=item.get("title", item["calendar_id"])[:300],
                evidence_ids=tuple(item.get("evidence_ids", [])),
            )
        )

    # critical first, then scheduled_at asc, then calendar ID asc; at most six.
    ordered = sorted(
        qualifying,
        key=lambda e: (
            0 if e.priority == "critical" else 1,
            _parse_ts(e.scheduled_at),
            e.calendar_id,
        ),
    )
    return ordered[: policy.max_items]
