"""Closed continuity checkpoint for the previous successful Feed."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..canonical import canonical_bytes, load_canonical_json
from ..providers.rate import _atomic_write

CHECKPOINT_FILENAME = "feed-checkpoint.json"
CHECKPOINT_VERSION = "1"
CHECKPOINT_FIELDS = frozenset({"previous_success", "version"})
PREVIOUS_SUCCESS_FIELDS = frozenset({"evidence_cutoff_at", "run_id"})
_RUN_ID = re.compile(r"(.+)::([0-9a-f]{32})")
_RFC3339_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)")


class CheckpointError(ValueError):
    """Checkpoint state failed closed validation or persistence."""


@dataclass(frozen=True)
class PreviousSuccess:
    evidence_cutoff_at: str
    run_id: str


@dataclass(frozen=True)
class FeedCheckpoint:
    previous_success: PreviousSuccess | None


def _parse_utc(value: Any) -> None:
    if not isinstance(value, str):
        raise CheckpointError("evidence_cutoff_at must be a string")
    if _RFC3339_UTC.fullmatch(value) is None:
        raise CheckpointError("evidence_cutoff_at must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CheckpointError(f"invalid evidence_cutoff_at: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise CheckpointError("evidence_cutoff_at must be UTC")


def _validate_previous_success(raw: Any) -> PreviousSuccess:
    if not isinstance(raw, dict):
        raise CheckpointError("previous_success must be an object or null")
    if set(raw) != PREVIOUS_SUCCESS_FIELDS:
        raise CheckpointError("previous_success has missing or unknown fields")
    cutoff = raw["evidence_cutoff_at"]
    _parse_utc(cutoff)
    run_id = raw["run_id"]
    if not isinstance(run_id, str):
        raise CheckpointError("run_id must be a string")
    match = _RUN_ID.fullmatch(run_id)
    if match is None or match.group(1) != cutoff:
        raise CheckpointError("run_id does not match evidence_cutoff_at")
    return PreviousSuccess(evidence_cutoff_at=cutoff, run_id=run_id)


def _payload(checkpoint: FeedCheckpoint) -> dict[str, Any]:
    previous = checkpoint.previous_success
    if previous is None:
        previous_payload = None
    else:
        previous_payload = {
            "evidence_cutoff_at": previous.evidence_cutoff_at,
            "run_id": previous.run_id,
        }
        _validate_previous_success(previous_payload)
    return {"previous_success": previous_payload, "version": CHECKPOINT_VERSION}


def read_checkpoint(path: Path) -> FeedCheckpoint:
    """Read and validate one established checkpoint."""
    path = Path(path)
    if not path.exists():
        raise CheckpointError(f"missing checkpoint: {path}")
    try:
        raw = load_canonical_json(path.read_bytes(), where=str(path))
    except (OSError, ValueError) as exc:
        raise CheckpointError(str(exc)) from exc
    if not isinstance(raw, dict):
        raise CheckpointError("checkpoint must be a JSON object")
    if set(raw) != CHECKPOINT_FIELDS:
        raise CheckpointError("checkpoint has missing or unknown fields")
    if raw["version"] != CHECKPOINT_VERSION:
        raise CheckpointError(f"unsupported checkpoint version {raw['version']!r}")
    previous = raw["previous_success"]
    return FeedCheckpoint(
        previous_success=None if previous is None else _validate_previous_success(previous)
    )


def write_checkpoint(path: Path, checkpoint: FeedCheckpoint) -> None:
    """Atomically persist one validated checkpoint."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, canonical_bytes(_payload(checkpoint)))
    except (OSError, ValueError) as exc:
        raise CheckpointError(str(exc)) from exc
