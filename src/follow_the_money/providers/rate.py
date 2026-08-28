"""Closed durable output-root rate-state registry.

Design section 2 (rate policy / crash safety):

- The output root holds a versioned durable rate-state registry plus one
  per-``scope_id`` state, protected by the collection lock, updated by
  same-directory atomic replace plus file/parent ``fsync``.
- A genuinely new output root creates its registry once with atomic
  no-replace.
- A new scope initializes through ``initializing -> full-capacity-state ->
  active``; recovery may complete an ``initializing`` entry only after
  validating no request was admitted. An ``active`` entry with missing/
  corrupt state, or a marked persistent root with missing/corrupt registry,
  fails closed.
- Wall-clock rollback grants no tokens; refill uses only non-negative
  injected UTC elapsed time.
- Before every possible send the orchestration durably debits one token and
  installs the 24-hour provisional crash cooldown. Confirmed pre-send
  failure may refund; controlled terminal outcomes retain the debit but
  reconcile the provisional to policy/``Retry-After``.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

REGISTRY_VERSION = "1"
REGISTRY_FILENAME = "rate-registry.json"
PERSISTENCE_MARKER = ".follow-the-money-persistent"


class RateStateError(ValueError):
    """Rate-state registry or scope state failed closed."""


@dataclass
class ScopeState:
    scope_id: str
    status: str  # initializing | active
    tokens: str  # Decimal string
    capacity: str
    refill_period_seconds: int
    minimum_interval_seconds: int
    refill_wall_anchor: str  # UTC ISO
    last_dispatch_wall: str | None
    cooldown_until: str | None  # UTC ISO, provisional crash cooldown
    policy_fingerprint: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _atomic_write(path: Path, data: bytes, *, no_replace: bool = False, fsync: bool = True) -> None:
    """Write bytes atomically via a same-directory temp + os.replace."""
    tmp_name = f".{path.name}.tmp-{os.getpid()}-{tempfile.mktemp(dir='').split('/')[-1]}"
    tmp = path.with_name(tmp_name)
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, data)
            if fsync:
                os.fsync(fd)
        finally:
            os.close(fd)
        if no_replace:
            try:
                os.link(tmp, path)  # atomic no-replace via hard link
                os.unlink(tmp)
            except FileExistsError:
                raise RateStateError(f"refusing to overwrite existing {path}")
        else:
            os.replace(tmp, path)
            if fsync:
                dir_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _scope_file(root: Path, scope_id: str) -> Path:
    safe = hashlib.sha256(scope_id.encode("utf-8")).hexdigest()[:16]
    return root / f"scope-{safe}.json"


class RateRegistry:
    """Durable per-output-root rate-state registry."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.registry_path = self.root / REGISTRY_FILENAME

    # -- registry -----------------------------------------------------------

    def ensure_registry(self, *, now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        """Create the registry once with atomic no-replace; fail closed if the
        root is marked persistent but the registry is missing/corrupt."""
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / PERSISTENCE_MARKER
        if self.registry_path.exists():
            try:
                self._read_registry()
            except (OSError, ValueError) as exc:
                raise RateStateError(f"corrupt registry under persistent root: {exc}") from exc
            return
        if marker.exists():
            raise RateStateError("persistent root is marked but rate registry is missing")
        # New root: create registry with no-replace.
        payload = {
            "version": REGISTRY_VERSION,
            "root_identity": str(self.root.resolve()),
            "scopes": {},
        }
        _atomic_write(
            self.registry_path,
            json.dumps(payload, sort_keys=True).encode("utf-8"),
            no_replace=True,
        )
        marker.touch(exist_ok=False) if not marker.exists() else None

    def _read_registry(self) -> dict[str, Any]:
        data = json.loads(self.registry_path.read_bytes())
        if data.get("version") != REGISTRY_VERSION:
            raise RateStateError(f"unknown registry schema {data.get('version')!r}")
        return data

    def _write_registry(self, data: dict[str, Any]) -> None:
        _atomic_write(self.registry_path, json.dumps(data, sort_keys=True).encode("utf-8"))

    # -- scope lifecycle ----------------------------------------------------

    def initialize_scope(
        self,
        scope_id: str,
        capacity: int,
        refill_period_seconds: int,
        minimum_interval_seconds: int,
        *,
        now: Callable[[], datetime],
    ) -> None:
        """Recoverable two-phase ``initializing -> active`` first-use sequence."""
        data = self._read_registry()
        scopes = data.setdefault("scopes", {})
        if scope_id in scopes:
            raise RateStateError(f"scope {scope_id!r} already initialized")
        # Phase 1: mark initializing in the registry.
        scopes[scope_id] = {"status": "initializing"}
        self._write_registry(data)
        # Phase 2: create/fsync full-capacity state.
        anchor = now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        state = ScopeState(
            scope_id=scope_id,
            status="initializing",
            tokens=str(capacity),
            capacity=str(capacity),
            refill_period_seconds=refill_period_seconds,
            minimum_interval_seconds=minimum_interval_seconds,
            refill_wall_anchor=anchor,
            last_dispatch_wall=None,
            cooldown_until=None,
        )
        _atomic_write(_scope_file(self.root, scope_id), _encode_state(state), no_replace=True)
        # Phase 3: atomically mark active in the registry.
        data["scopes"][scope_id] = {"status": "active", "policy_fingerprint": _policy_fp(state)}
        self._write_registry(data)

    def recover_or_load(self, scope_id: str) -> ScopeState:
        """Load an active scope state, or recover an ``initializing`` entry.

        Fails closed on missing/partial/corrupt/unknown-schema state for an
        active scope.
        """
        data = self._read_registry()
        entry = data.get("scopes", {}).get(scope_id)
        if entry is None:
            raise RateStateError(f"scope {scope_id!r} not in registry")
        status = entry.get("status")
        state = self._read_scope_state(scope_id)
        if status == "initializing":
            # Recovery may complete an initializing entry only after
            # validating that no request was admitted (last_dispatch is None).
            if state is not None and state.last_dispatch_wall is None:
                data["scopes"][scope_id] = {
                    "status": "active",
                    "policy_fingerprint": _policy_fp(state),
                }
                self._write_registry(data)
                state.status = "active"
                return state
            raise RateStateError(
                f"scope {scope_id!r} initializing with admitted request; fail closed"
            )
        if status != "active":
            raise RateStateError(f"scope {scope_id!r} unknown registry status {status!r}")
        if state is None:
            raise RateStateError(f"scope {scope_id!r} active but state missing/partial")
        state.status = "active"
        return state

    def _read_scope_state(self, scope_id: str) -> ScopeState | None:
        path = _scope_file(self.root, scope_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_bytes())
        except (OSError, ValueError):
            return None
        if raw.get("version") != REGISTRY_VERSION:
            return None
        try:
            return ScopeState(
                scope_id=raw["scope_id"],
                status=raw["status"],
                tokens=raw["tokens"],
                capacity=raw["capacity"],
                refill_period_seconds=int(raw["refill_period_seconds"]),
                minimum_interval_seconds=int(raw["minimum_interval_seconds"]),
                refill_wall_anchor=raw["refill_wall_anchor"],
                last_dispatch_wall=raw.get("last_dispatch_wall"),
                cooldown_until=raw.get("cooldown_until"),
                policy_fingerprint=raw.get("policy_fingerprint"),
            )
        except (KeyError, TypeError, ValueError):
            return None

    # -- state transitions --------------------------------------------------

    def debit_and_cooldown(
        self, state: ScopeState, *, now: Callable[[], datetime], cooldown_hours: int = 24
    ) -> ScopeState:
        """Durably debit one token and install the crash cooldown before send."""
        now_dt = now()
        if state.cooldown_until is not None and now_dt < _parse_iso(state.cooldown_until):
            raise RateStateError(f"scope {state.scope_id!r} is not yet eligible")
        if state.last_dispatch_wall is not None:
            last_dispatch = _parse_iso(state.last_dispatch_wall)
            if (now_dt - last_dispatch).total_seconds() < state.minimum_interval_seconds:
                raise RateStateError(f"scope {state.scope_id!r} minimum interval not elapsed")
        if _dec(state.tokens) < 1:
            raise RateStateError(f"scope {state.scope_id!r} has no available token")
        now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        tokens = _dec(state.tokens) - 1
        state.tokens = _fmt_tokens(tokens)
        state.last_dispatch_wall = now_iso
        state.cooldown_until = (now_dt + timedelta(hours=cooldown_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"
        _atomic_write(_scope_file(self.root, state.scope_id), _encode_state(state))
        return state

    def refund(self, state: ScopeState, *, now: Callable[[], datetime]) -> ScopeState:
        """Durably refund a confirmed pre-send failure."""
        state.tokens = _fmt_tokens(_dec(state.tokens) + 1)
        state.cooldown_until = None
        state.last_dispatch_wall = None
        _atomic_write(_scope_file(self.root, state.scope_id), _encode_state(state))
        return state

    def reconcile(
        self,
        state: ScopeState,
        *,
        now: Callable[[], datetime],
        retry_after_seconds: int | None = None,
    ) -> ScopeState:
        """After a controlled terminal outcome: retain debit, replace the
        24-hour provisional with the policy next-eligible time."""
        next_eligible = now()
        if state.last_dispatch_wall is not None:
            next_eligible = max(
                next_eligible,
                _parse_iso(state.last_dispatch_wall)
                + timedelta(seconds=state.minimum_interval_seconds),
            )
        if retry_after_seconds:
            next_eligible = max(next_eligible, now() + timedelta(seconds=retry_after_seconds))
        state.cooldown_until = next_eligible.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        _atomic_write(_scope_file(self.root, state.scope_id), _encode_state(state))
        return state


def _encode_state(state: ScopeState) -> bytes:
    return json.dumps(
        {
            "version": REGISTRY_VERSION,
            "scope_id": state.scope_id,
            "status": state.status,
            "tokens": state.tokens,
            "capacity": state.capacity,
            "refill_period_seconds": state.refill_period_seconds,
            "minimum_interval_seconds": state.minimum_interval_seconds,
            "refill_wall_anchor": state.refill_wall_anchor,
            "last_dispatch_wall": state.last_dispatch_wall,
            "cooldown_until": state.cooldown_until,
            "policy_fingerprint": state.policy_fingerprint,
        },
        sort_keys=True,
    ).encode("utf-8")


def _policy_fp(state: ScopeState) -> str:
    payload = {
        "capacity": state.capacity,
        "refill_period_seconds": state.refill_period_seconds,
        "minimum_interval_seconds": state.minimum_interval_seconds,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _dec(value: str) -> Decimal:
    return Decimal(value)


def _fmt_tokens(value: Decimal) -> str:
    """Canonical plain decimal string without exponent or trailing zeros."""
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def refill_tokens(state: ScopeState, *, now: Callable[[], datetime]) -> ScopeState:
    """Refill from non-negative injected UTC elapsed time; rollback grants no
    tokens and returns the state unchanged."""
    anchor = _parse_iso(state.refill_wall_anchor)
    current = now()
    elapsed = (current - anchor).total_seconds()
    if elapsed < 0:
        return state  # wall-clock rollback: no refill
    capacity = Decimal(state.capacity)
    rate = (
        capacity / Decimal(state.refill_period_seconds)
        if state.refill_period_seconds
        else Decimal(0)
    )
    gained = Decimal(str(elapsed)) * rate
    new_tokens = min(capacity, Decimal(state.tokens) + gained)
    state.tokens = _fmt_tokens(new_tokens)
    state.refill_wall_anchor = current.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return state


def eligibility_delay(state: ScopeState, *, now: Callable[[], datetime]) -> float:
    """Return seconds until a scope may admit its next dispatch."""
    eligible = now()
    if state.cooldown_until is not None:
        eligible = max(eligible, _parse_iso(state.cooldown_until))
    if state.last_dispatch_wall is not None:
        eligible = max(
            eligible,
            _parse_iso(state.last_dispatch_wall)
            + timedelta(seconds=state.minimum_interval_seconds),
        )
    return max(0.0, (eligible - now()).total_seconds())
