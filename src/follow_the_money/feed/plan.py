"""Feed window planning and health accounting.

Design sections 2/4:

- The evidence window is ``[window.start, evidence_cutoff_at)`` and MUST be
  strictly advancing. After acquiring the exclusive collection lock and
  before any provider call, planning reads the validated runtime checkpoint.
- An explicit null previous success is a first-run bootstrap (``window.start
  = cutoff - 72h``).
- If the captured cutoff <= checkpoint cutoff, planning fails typed
  ``non_advancing_cutoff`` with no call/artifact.
- A gap > 72h uses the bounded bootstrap start and records an uncovered
  interval warning; an exact 72h gap starts at the prior cutoff.
- Group health: a planned member is complete only when it reaches a healthy
  state or returns a manifest-permitted empty result. Incomplete source work
  fails the Feed even when other Providers retain accepted items.
- Outcomes aggregate by stable ``provider_id`` key and serialize exactly one
  entry per planned provider in ascending ``provider_id`` order, so worker
  completion order never changes the Feed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ..config.model import AppConfig
from .checkpoint import PreviousSuccess


class FeedPlanError(ValueError):
    """Feed planning failed closed."""


@dataclass(frozen=True)
class FeedPlan:
    window_start: str
    evidence_cutoff_at: str
    bootstrap: bool
    gap_warning: tuple[str, str] | None = None  # (uncovered_start, uncovered_end)


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FeedPlanError(f"invalid checkpoint cutoff: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise FeedPlanError(f"invalid checkpoint cutoff: {value!r}")
    return parsed


def fmt_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def plan_window(
    *,
    cutoff: datetime,
    previous_success: PreviousSuccess | None,
    bootstrap_lookback_hours: int = 72,
    gap_threshold_hours: int = 72,
) -> FeedPlan:
    """Plan the strictly advancing half-open evidence window.

    ``previous_success`` is validated before it reaches this pure arithmetic
    function; it is deliberately not a path or a Feed document.
    """
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise FeedPlanError("cutoff must be timezone-aware")
    cutoff_iso = fmt_utc(cutoff)

    if previous_success is None:
        start = cutoff - timedelta(hours=bootstrap_lookback_hours)
        return FeedPlan(window_start=fmt_utc(start), evidence_cutoff_at=cutoff_iso, bootstrap=True)

    previous_cutoff = parse_utc(previous_success.evidence_cutoff_at)
    if cutoff <= previous_cutoff:
        raise FeedPlanError(
            "non_advancing_cutoff: new cutoff <= checkpoint cutoff "
            f"({cutoff_iso} <= {fmt_utc(previous_cutoff)})"
        )

    gap = (cutoff - previous_cutoff).total_seconds() / 3600
    if gap > gap_threshold_hours:
        start = cutoff - timedelta(hours=bootstrap_lookback_hours)
        return FeedPlan(
            window_start=fmt_utc(start),
            evidence_cutoff_at=cutoff_iso,
            bootstrap=True,
            gap_warning=(fmt_utc(previous_cutoff), fmt_utc(start)),
        )
    # Exact 72h or less: start at the prior cutoff (strictly advancing).
    return FeedPlan(
        window_start=fmt_utc(previous_cutoff), evidence_cutoff_at=cutoff_iso, bootstrap=False
    )


AVAILABILITY_REASON_LIMIT = 256


def bounded_availability_reason(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    encoded = text.encode("utf-8")
    if len(encoded) <= AVAILABILITY_REASON_LIMIT:
        return text
    return encoded[:AVAILABILITY_REASON_LIMIT].decode("utf-8", errors="ignore")


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
    freshness: dict[str, Any] | None = None
    availability: str | None = None
    availability_reason: str | None = None
    upstream_http_status: int | None = None
    affected_coverage_groups: tuple[str, ...] = ()
    execution_failure: bool = False
    non_permitted_empty_observed: bool = False

    @property
    def resolved_availability(self) -> str:
        if self.availability is not None:
            return self.availability
        return "success" if self.state in {"healthy", "empty"} else "failed"

    @property
    def resolved_availability_reason(self) -> str | None:
        if self.availability_reason is not None:
            return bounded_availability_reason(self.availability_reason)
        if self.resolved_availability == "success":
            return None
        if self.upstream_http_status is not None:
            return f"HTTP {self.upstream_http_status}"
        return bounded_availability_reason(self.error)

    @property
    def blocked_exempt(self) -> bool:
        return (
            self.resolved_availability == "blocked"
            and self.upstream_http_status in {401, 403}
            and self.state == "failed"
            and self.accepted == 0
            and self.rejected == 0
            and not self.non_permitted_empty_observed
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
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
            "availability": self.resolved_availability,
            "availability_reason": self.resolved_availability_reason,
            "upstream_http_status": self.upstream_http_status,
            "affected_coverage_groups": sorted(self.affected_coverage_groups),
            "error": self.error,
            "retrieved_at": self.retrieved_at,
        }
        if self.freshness is not None:
            result["freshness"] = dict(self.freshness)
        return result

    @property
    def healthy(self) -> bool:
        """Whether the serialized provider state is explicitly healthy."""
        return self.state == "healthy"

    def contributes_to_coverage(self, *, empty_valid_for_window: bool) -> bool:
        """Return whether this outcome satisfies one mandatory member slot."""
        return self.resolved_availability == "success" and (
            self.state == "healthy" or (self.state == "empty" and empty_valid_for_window)
        )


def ordered_outcomes(outcomes: Mapping[str, ProviderOutcome]) -> list[ProviderOutcome]:
    """One outcome per planned provider, ascending ``provider_id``.

    Workers only ever update their stable ``provider_id``-keyed outcome; this
    serialization makes provider completion order irrelevant to the Feed.
    """
    return [outcomes[pid] for pid in sorted(outcomes)]


def assess_pipeline(
    *,
    config: AppConfig,
    planned_provider_ids: Sequence[str],
    outcomes: Mapping[str, ProviderOutcome],
) -> tuple[str, list[str]]:
    """Return ``(status, warnings)`` from actual planned Provider outcomes."""
    provider_config = {provider.id: provider for provider in config.providers}
    warnings: list[str] = []

    plan_counts: dict[str, int] = {}
    for provider_id in planned_provider_ids:
        plan_counts[provider_id] = plan_counts.get(provider_id, 0) + 1
    duplicate_plan_ids = sorted(pid for pid, count in plan_counts.items() if count > 1)
    if duplicate_plan_ids:
        warnings.append(f"duplicate planned providers: {', '.join(duplicate_plan_ids)}")

    terminal_states = {"healthy", "empty", "partial", "failed", "skipped"}
    configured_groups = {
        provider_id: tuple(
            sorted(row.group for row in config.coverage.rows if provider_id in row.members)
        )
        for provider_id in provider_config
    }

    def complete_for(provider: Any, outcome: Any) -> bool:
        return (
            provider is not None
            and isinstance(outcome, ProviderOutcome)
            and outcome.provider_id == provider.id
            and outcome.state in terminal_states
            and outcome.contributes_to_coverage(
                empty_valid_for_window=getattr(provider, "empty_valid_for_window", False)
            )
        )

    complete_by_provider: dict[str, bool] = {}
    blocked_by_provider: dict[str, bool] = {}
    for provider_id in sorted(plan_counts):
        provider = provider_config.get(provider_id)
        candidates = sorted(
            (
                (key, outcome)
                for key, outcome in outcomes.items()
                if isinstance(outcome, ProviderOutcome) and outcome.provider_id == provider_id
            ),
            key=lambda candidate: candidate[0],
        )
        outcome = candidates[0][1] if candidates else outcomes.get(provider_id)

        reason: str | None = None
        if provider is None:
            reason = "missing resolved provider contract"
        elif len(candidates) != 1:
            if isinstance(outcome, ProviderOutcome) and outcome.provider_id != provider_id:
                reason = "provider identity mismatch"
            else:
                reason = (
                    "missing terminal outcome" if not candidates else "ambiguous terminal outcome"
                )
        elif candidates[0][0] != provider_id:
            reason = "provider identity mismatch"
        elif not isinstance(outcome, ProviderOutcome) or outcome.state not in terminal_states:
            reason = "unknown state"
        elif not complete_for(provider, outcome):
            reason = (
                "empty result is not permitted for window"
                if outcome.state == "empty"
                else "terminal state is incomplete"
            )

        valid_terminal_outcome = (
            provider is not None
            and len(candidates) == 1
            and candidates[0][0] == provider_id
            and isinstance(outcome, ProviderOutcome)
            and outcome.provider_id == provider_id
            and outcome.state in terminal_states
        )
        blocked_exempt = (
            valid_terminal_outcome
            and isinstance(outcome, ProviderOutcome)
            and outcome.blocked_exempt
        )
        blocked_by_provider[provider_id] = blocked_exempt
        complete = reason is None and complete_for(provider, outcome)
        complete_by_provider[provider_id] = complete
        if blocked_exempt:
            assert isinstance(outcome, ProviderOutcome)
            groups = ",".join(configured_groups.get(provider_id, ())) or "none"
            warnings.append(
                "blocked Provider exempted: "
                f"provider_id={provider_id} availability={outcome.resolved_availability} "
                f"reason={outcome.resolved_availability_reason or 'none'} "
                f"affected_coverage_groups={groups}"
            )
        elif not complete:
            state = getattr(outcome, "state", "missing")
            detail = f"source incomplete: provider_id={provider_id} state={state}"
            availability = getattr(outcome, "resolved_availability", None)
            if availability:
                detail += f" availability={availability}"
            error = getattr(outcome, "error", None)
            message = getattr(outcome, "message", None)
            if error or message:
                detail += f" error={error or message}"
            if reason:
                detail += f" reason={reason}"
            warnings.append(detail)

    deficient: list[str] = []
    for row in config.coverage.rows:
        blocked_count = sum(1 for member in row.members if blocked_by_provider.get(member, False))
        effective_minimum = max(0, row.minimum - blocked_count)
        complete_count = sum(1 for member in row.members if complete_by_provider.get(member))
        if complete_count < effective_minimum and not row.optional:
            deficient.append(row.group)

    if deficient:
        warnings.append(f"deficient coverage groups: {', '.join(deficient)}")
    if duplicate_plan_ids or any(
        not complete and not blocked_by_provider.get(provider_id, False)
        for provider_id, complete in complete_by_provider.items()
    ):
        return "failure", warnings
    if deficient:
        return "failure", warnings
    if any(blocked_by_provider.values()):
        return "degraded", warnings
    return "healthy", warnings
