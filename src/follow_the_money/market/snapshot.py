"""Immutable, deterministic market snapshot construction.

This module is deliberately independent from the Feed collector and the
classifier.  It consumes the already-normalized Feed, aligns observations to
the configured role session, and exposes one typed result for dashboard and
Market State consumers.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

import exchange_calendars as xcals

from ..config.model import AppConfig, MarketRole, Session
from .formulas import (
    abnormal_move_z,
    normative_decimal_context,
    quantize2,
    quantize6,
    simple_return,
    yield_change_bps,
)
from .surprise import surprise_for_series


@dataclass(frozen=True)
class RoleMetric:
    role_id: str
    unit: str
    change_kind: str  # return | yield_bps
    current_change: Decimal | None
    changes: tuple[Decimal, ...] = ()
    reference_changes: tuple[Decimal, ...] = ()
    z_score: Decimal | None = None
    available: bool = False
    unknown_reason: str | None = None
    evidence_ids: tuple[str, ...] = ()
    anomaly_threshold: str = "2.0"

    @property
    def anomalous(self) -> bool | None:
        if self.z_score is None:
            return None
        return abs(self.z_score) >= Decimal(self.anomaly_threshold)

    @property
    def output_change(self) -> Decimal | None:
        if self.current_change is None:
            return None
        return (
            quantize2(self.current_change)
            if self.change_kind == "yield_bps"
            else quantize6(self.current_change)
        )

    def dashboard_value(self, role: MarketRole) -> dict[str, Any]:
        value: dict[str, Any] = {
            "role_id": self.role_id,
            "available": self.available,
            "display": role.name_zh,
            "change_kind": self.change_kind,
            "anomalous": self.anomalous,
        }
        if self.change_kind == "yield_bps":
            value["yield_change_bps"] = (
                str(self.output_change) if self.output_change is not None else None
            )
        else:
            value["return_pct"] = (
                str(self.output_change) if self.output_change is not None else None
            )
        if self.unknown_reason:
            value["unknown_reason"] = self.unknown_reason
        return value


@dataclass(frozen=True)
class MarketSnapshot:
    metrics: Mapping[str, RoleMetric]
    dashboard: tuple[Mapping[str, Any], ...]
    role_zs: Mapping[str, Decimal]
    role_return_zs: Mapping[str, Decimal]
    yield_change_zs: Mapping[str, Decimal]
    equity_breadth: Decimal | None
    surprise_votes: tuple[int, ...] = ()
    surprise_vote_by_series: Mapping[str, int] = MappingProxyType({})
    missing_roles: tuple[str, ...] = ()
    unknown_reasons: Mapping[str, str] = MappingProxyType({})
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard": [dict(row) for row in self.dashboard],
            "role_zs": {key: str(value) for key, value in self.role_zs.items()},
            "role_return_zs": {key: str(value) for key, value in self.role_return_zs.items()},
            "yield_change_zs": {key: str(value) for key, value in self.yield_change_zs.items()},
            "equity_breadth": str(self.equity_breadth) if self.equity_breadth is not None else None,
            "surprise_votes": list(self.surprise_votes),
            "surprise_vote_by_series": dict(self.surprise_vote_by_series),
            "missing_roles": list(self.missing_roles),
            "unknown_reasons": dict(self.unknown_reasons),
            "evidence_ids": list(self.evidence_ids),
        }


def build_market_snapshot(feed: Mapping[str, Any], config: AppConfig) -> MarketSnapshot:
    """Build one cutoff-safe snapshot in canonical role order."""
    cutoff = _parse_ts(str(feed.get("evidence_cutoff_at", "")))
    by_role: dict[str, list[tuple[str, Mapping[str, Any]]]] = {role.id: [] for role in config.roles}
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        role_id = payload.get("instrument_id")
        if payload.get("type") == "market_data" and role_id in by_role:
            by_role[role_id].append((str(item.get("id", "")), payload))

    metrics: dict[str, RoleMetric] = {}
    for role in config.roles:
        session = _session_for(config, role)
        metrics[role.id] = _build_role_metric(
            role=role,
            session=session,
            records=by_role[role.id],
            cutoff=cutoff,
            anomaly_threshold=config.scoring.anomaly_z_threshold,
        )

    role_zs = {
        role_id: metric.z_score for role_id, metric in metrics.items() if metric.z_score is not None
    }
    role_return_zs = {
        role_id: metric.z_score
        for role_id, metric in metrics.items()
        if metric.z_score is not None and metric.change_kind == "return"
    }
    yield_change_zs = {
        role_id: metric.z_score
        for role_id, metric in metrics.items()
        if metric.z_score is not None and metric.change_kind == "yield_bps"
    }
    breadth = _equity_breadth(metrics)
    surprise_votes, surprise_by_series, surprise_evidence_ids = _macro_surprises(
        feed, config, cutoff
    )
    dashboard = tuple(
        MappingProxyType(metrics[role.id].dashboard_value(role)) for role in config.roles
    )
    missing = tuple(role.id for role in config.roles if metrics[role.id].z_score is None)
    reasons_dict: dict[str, str] = {}
    for role in config.roles:
        reason = metrics[role.id].unknown_reason
        if reason:
            reasons_dict[role.id] = reason
    reasons = MappingProxyType(reasons_dict)
    role_evidence_ids = [
        evidence_id for role in config.roles for evidence_id in metrics[role.id].evidence_ids
    ]
    evidence_ids = tuple(dict.fromkeys((*role_evidence_ids, *surprise_evidence_ids)))
    return MarketSnapshot(
        metrics=MappingProxyType(metrics),
        dashboard=dashboard,
        role_zs=MappingProxyType(role_zs),
        role_return_zs=MappingProxyType(role_return_zs),
        yield_change_zs=MappingProxyType(yield_change_zs),
        equity_breadth=breadth,
        surprise_votes=tuple(surprise_votes),
        surprise_vote_by_series=MappingProxyType(surprise_by_series),
        missing_roles=missing,
        unknown_reasons=reasons,
        evidence_ids=evidence_ids,
    )


def _build_role_metric(
    *,
    role: MarketRole,
    session: Session,
    records: Sequence[tuple[str, Mapping[str, Any]]],
    cutoff: datetime,
    anomaly_threshold: str,
) -> RoleMetric:
    change_kind = "yield_bps" if role.kind == "yield" else "return"
    if not role.mapping_verified:
        return _unknown(role, change_kind, "unverified_mapping")
    if not records:
        return _unknown(role, change_kind, "no_observations")
    if any(payload.get("unit") != role.unit for _item_id, payload in records):
        return _unknown(role, change_kind, "incompatible_unit")

    labels: dict[str, tuple[datetime, Decimal, str]] = {}
    cutoff_excluded = False
    for item_id, payload in records:
        for observation in payload.get("observations", []):
            if observation.get("unit") != role.unit:
                return _unknown(role, change_kind, "incompatible_unit")
            try:
                as_of = _parse_ts(str(observation["as_of"]))
                value = Decimal(str(observation["value"]))
            except (KeyError, InvalidOperation, ValueError):
                return _unknown(role, change_kind, "invalid_observation")
            if not value.is_finite():
                continue
            if as_of > cutoff:
                return _unknown(
                    role,
                    change_kind,
                    "post_cutoff_observation",
                    evidence_ids=_record_ids(records),
                )
            label = _session_label(as_of, session)
            if label is None:
                continue
            available = _completed_at(label, session, role.availability_lag_seconds)
            if available > cutoff:
                cutoff_excluded = True
                continue
            if label in labels:
                return _unknown(role, change_kind, "duplicate_session_label")
            labels[label] = (as_of, value, item_id)

    if not labels:
        return _unknown(role, change_kind, "no_completed_observations")
    latest_label = _latest_expected_label(session, cutoff, role.availability_lag_seconds)
    if latest_label is None:
        return _unknown(role, change_kind, "no_expected_session")
    expected = _expected_labels(session, latest_label, count=22)
    if cutoff_excluded and len(labels) < 22:
        return _unknown(
            role, change_kind, "current_partial_session", evidence_ids=_record_ids(records)
        )
    # Fewer than 20 labels can never form a 22-session window; 20-21 labels
    # fall through to the expected-session check and fail closed there with a
    # precise missing-session reason.
    if len(labels) < 20:
        return _unknown(
            role, change_kind, "insufficient_history", evidence_ids=_record_ids(records)
        )
    if not set(expected) <= set(labels):
        return _unknown(
            role, change_kind, "missing_expected_session", evidence_ids=_record_ids(records)
        )

    closes = [labels[label][1] for label in expected]
    evidence_ids = tuple(dict.fromkeys(labels[label][2] for label in expected))
    try:
        with normative_decimal_context():
            changes = tuple(
                (
                    yield_change_bps(closes[i], closes[i - 1])
                    if change_kind == "yield_bps"
                    else simple_return(closes[i], closes[i - 1])
                )
                for i in range(1, len(closes))
            )
        z_result = abnormal_move_z(changes[-1], changes[:-1])
    except (InvalidOperation, ZeroDivisionError, ValueError):
        return _unknown(role, change_kind, "invalid_reference_window", evidence_ids=evidence_ids)
    if z_result.value is None:
        return RoleMetric(
            role_id=role.id,
            unit=role.unit,
            change_kind=change_kind,
            current_change=changes[-1],
            changes=changes,
            reference_changes=changes[:-1],
            available=True,
            unknown_reason=z_result.unknown_reason,
            evidence_ids=evidence_ids,
            anomaly_threshold=anomaly_threshold,
        )
    return RoleMetric(
        role_id=role.id,
        unit=role.unit,
        change_kind=change_kind,
        current_change=changes[-1],
        changes=changes,
        reference_changes=changes[:-1],
        z_score=z_result.value,
        available=True,
        evidence_ids=evidence_ids,
        anomaly_threshold=anomaly_threshold,
    )


def _unknown(
    role: MarketRole,
    change_kind: str,
    reason: str,
    *,
    evidence_ids: Sequence[str] = (),
) -> RoleMetric:
    return RoleMetric(
        role_id=role.id,
        unit=role.unit,
        change_kind=change_kind,
        current_change=None,
        unknown_reason=reason,
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
    )


def _session_for(config: AppConfig, role: MarketRole) -> Session:
    for session in config.sessions:
        if session.id == role.session_id:
            return session
    raise ValueError(f"role {role.id!r} references unknown session {role.session_id!r}")


def _session_label(timestamp: datetime, session: Session) -> str | None:
    local_date = timestamp.astimezone(_timezone(session.timezone)).date()
    if session.session_class == "continuous_247":
        return local_date.isoformat()
    if session.session_class == "continuous_245":
        return local_date.isoformat() if local_date.weekday() < 5 else None
    try:
        label = local_date.isoformat()
        return label if label in _session_labels_in_range(session, label, label) else None
    except (KeyError, ValueError):
        return None


def _expected_labels(session: Session, latest_label: str, *, count: int) -> list[str]:
    latest = date.fromisoformat(latest_label)
    if session.session_class == "continuous_247":
        return [(latest - timedelta(days=i)).isoformat() for i in range(count - 1, -1, -1)]
    if session.session_class == "continuous_245":
        labels: list[str] = []
        cursor = latest
        while len(labels) < count:
            if cursor.weekday() < 5:
                labels.append(cursor.isoformat())
            cursor -= timedelta(days=1)
        return list(reversed(labels))
    start = latest - timedelta(days=count * 4)
    return _session_labels_in_range(session, start.isoformat(), latest.isoformat())[-count:]


def _latest_expected_label(session: Session, cutoff: datetime, lag_seconds: int) -> str | None:
    local_cutoff = cutoff.astimezone(_timezone(session.timezone))
    if session.session_class == "continuous_247":
        candidate = local_cutoff.date() - timedelta(days=1)
        if _completed_at(candidate.isoformat(), session, lag_seconds) > cutoff:
            candidate -= timedelta(days=1)
        return candidate.isoformat()
    if session.session_class == "continuous_245":
        candidate = local_cutoff.date() - timedelta(days=1)
        if _completed_at(candidate.isoformat(), session, lag_seconds) > cutoff:
            candidate -= timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
        return candidate.isoformat()
    start = local_cutoff.date() - timedelta(days=14)
    labels = _session_labels_in_range(session, start.isoformat(), local_cutoff.date().isoformat())
    for label in reversed(labels):
        close = _session_close(session, label)
        if close + timedelta(seconds=lag_seconds) <= cutoff:
            return label
    return None


def _completed_at(label: str, session: Session, lag_seconds: int) -> datetime:
    """Return when the labelled daily close is conservatively observable."""
    if session.session_class in {"continuous_247", "continuous_245"}:
        boundary = datetime.combine(
            date.fromisoformat(label) + timedelta(days=1),
            datetime.min.time(),
            tzinfo=_timezone(session.timezone),
        )
        return boundary.astimezone(UTC) + timedelta(seconds=lag_seconds)
    close = _session_close(session, label)
    return close.astimezone(UTC) + timedelta(seconds=lag_seconds)


def _equity_breadth(metrics: Mapping[str, RoleMetric]) -> Decimal | None:
    observed: list[Decimal] = []
    for role_id in ("sp500", "csi300", "hsi"):
        value = metrics[role_id].current_change
        if value is not None:
            observed.append(value)
    if not observed:
        return None
    positive = sum(1 for value in observed if value > 0)
    negative = sum(1 for value in observed if value < 0)
    with normative_decimal_context():
        return (Decimal(positive) - Decimal(negative)) / Decimal(len(observed))


def _macro_surprises(
    feed: Mapping[str, Any], config: AppConfig, cutoff: datetime
) -> tuple[list[int], dict[str, int], tuple[str, ...]]:
    selected: dict[str, tuple[datetime, str, Mapping[str, Any]]] = {}
    allowed = tuple(scale.series_id for scale in config.scoring.surprise_scales)
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        if payload.get("type") != "macro_release" or payload.get("series_id") not in allowed:
            continue
        source = item.get("source", {})
        knowledge_raw = source.get("knowledge_available_at")
        if not knowledge_raw:
            continue
        knowledge = _parse_ts(str(knowledge_raw))
        if knowledge > cutoff:
            continue
        series_id = str(payload["series_id"])
        candidate = (knowledge, str(item.get("id", "")), payload)
        current = selected.get(series_id)
        if current is None or (candidate[0], candidate[1]) > (current[0], current[1]):
            selected[series_id] = candidate

    votes: list[int] = []
    by_series: dict[str, int] = {}
    evidence_ids: list[str] = []
    for series_id in allowed:
        chosen = selected.get(series_id)
        if chosen is None:
            continue
        payload = chosen[2]
        actual = payload.get("actual") or {}
        consensus = payload.get("consensus") or {}
        if actual.get("unit") != consensus.get("unit"):
            continue
        try:
            with normative_decimal_context():
                result = surprise_for_series(
                    series_id=series_id,
                    actual=(
                        Decimal(str(actual["value"])) if actual.get("value") is not None else None
                    ),
                    consensus=(
                        Decimal(str(consensus["value"]))
                        if consensus.get("value") is not None
                        else None
                    ),
                    unit=actual.get("unit"),
                    scales=config.scoring,
                )
        except (InvalidOperation, ValueError):
            continue
        if result.normalized is None:
            continue
        with normative_decimal_context():
            if result.normalized >= Decimal("0.5"):
                vote = -1
            elif result.normalized <= Decimal("-0.5"):
                vote = 1
            else:
                vote = 0
        votes.append(vote)
        by_series[series_id] = vote
        evidence_ids.append(chosen[1])
    return votes, by_series, tuple(evidence_ids)


def _record_ids(records: Sequence[tuple[str, Mapping[str, Any]]]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item_id for item_id, _payload in records if item_id))


def _parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timezone(name: str):
    from zoneinfo import ZoneInfo

    return ZoneInfo(name)


def _get_calendar(name: str):
    """Load a real exchange calendar without leaking dependency warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return xcals.get_calendar(name)


def _session_labels_in_range(session: Session, start: str, end: str) -> list[str]:
    """Session labels (ISO dates) in [start, end] from the real calendar.

    Calendar method calls share the same warning suppression as
    ``_get_calendar`` so pytest's error-on-DeprecationWarning policy cannot
    divert tests onto a different code path than production.
    """
    calendar = _get_calendar(session.calendar)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return [str(value.date()) for value in calendar.sessions_in_range(start, end)]


def _session_close(session: Session, label: str) -> datetime:
    """Configured-calendar close instant for one session label (UTC)."""
    calendar = _get_calendar(session.calendar)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return calendar.schedule.loc[label, "close"].to_pydatetime()
