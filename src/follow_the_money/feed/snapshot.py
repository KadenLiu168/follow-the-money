"""Validation-gated Provider slice selection for Feed assembly."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..canonical import canonical_bytes, canonical_digest
from ..config.model import FreshnessContract
from .bundle import MANIFEST_FILENAME, BundleError, validate_bundle
from .dedupe import item_total_order_key
from .freshness import FreshnessError, evaluate_freshness
from .plan import ProviderOutcome


class SnapshotError(ValueError):
    """Snapshot selection failed closed."""


@dataclass(frozen=True)
class SnapshotSelection:
    items: tuple[dict[str, Any], ...]
    active_feed: Mapping[str, Any] | None


def load_active_feed(product_root: Path) -> dict[str, Any] | None:
    """Load only a manifest-led, fully validated, consumable active bundle."""
    root = Path(product_root)
    if not (root / MANIFEST_FILENAME).is_file():
        return None
    try:
        feed = validate_bundle(root)
    except BundleError:
        return None
    if feed.get("pipeline", {}).get("status") == "failure":
        return None
    contracts: dict[str, Mapping[str, Any]] = {}
    for entry in feed.get("provider_contracts", []):
        if not isinstance(entry, Mapping):
            return None
        provider_id = entry.get("provider_id")
        snapshot = entry.get("snapshot")
        if (
            not isinstance(provider_id, str)
            or provider_id in contracts
            or not isinstance(snapshot, Mapping)
            or snapshot.get("provider_id") != provider_id
            or entry.get("hash") != canonical_digest(snapshot)
        ):
            return None
        contracts[provider_id] = snapshot
    valid_providers: set[str] = set()
    for outcome in feed.get("provider_outcomes", []):
        if not isinstance(outcome, Mapping) or not isinstance(outcome.get("provider_id"), str):
            return None
        provider_id = outcome["provider_id"]
        snapshot = contracts.get(provider_id)
        if not isinstance(snapshot, Mapping):
            return None
        complete = outcome.get("state") == "healthy" or (
            outcome.get("state") == "empty" and snapshot.get("empty_valid_for_window") is True
        )
        blocked_exempt = (
            outcome.get("availability") == "blocked"
            and outcome.get("upstream_http_status") in {401, 403}
            and outcome.get("state") == "failed"
            and outcome.get("accepted") == 0
            and outcome.get("rejected") == 0
        )
        if complete or blocked_exempt:
            valid_providers.add(provider_id)
        else:
            return None
    if any(item.get("provider_id") not in valid_providers for item in feed.get("items", [])):
        return None
    if set(contracts) != valid_providers:
        return None
    return feed


def _sha256(value: object) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) else None


def _contract_hash(entry: Mapping[str, Any] | None) -> str | None:
    return _sha256(entry.get("hash") if isinstance(entry, Mapping) else None)


def _same_item(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return canonical_bytes(dict(left)) == canonical_bytes(dict(right))


def _freshness_record(
    *,
    contract: FreshnessContract,
    status: str,
    origin_contract_hash: str | None,
    carried_forward_from_run_id: str | None,
) -> dict[str, Any]:
    result = {
        "cadence": contract.cadence,
        "status": status,
        "origin_contract_hash": origin_contract_hash,
        "carried_forward_from_run_id": carried_forward_from_run_id,
    }
    return result


def _set_not_evaluated(outcome: ProviderOutcome, contract: FreshnessContract) -> None:
    outcome.freshness = _freshness_record(
        contract=contract,
        status="not_evaluated",
        origin_contract_hash=None,
        carried_forward_from_run_id=None,
    )


def select_provider_slices(
    *,
    outcomes: Mapping[str, ProviderOutcome],
    current_items: Sequence[Mapping[str, Any]],
    active_feed: Mapping[str, Any] | None,
    contracts: Mapping[str, FreshnessContract],
    current_contract_hashes: Mapping[str, str],
    empty_valid_for_window: Mapping[str, bool],
    evidence_cutoff_at: str,
    strict_identity_provider_ids: Sequence[str] | None = None,
) -> SnapshotSelection:
    """Select one bounded current/prior slice per Provider deterministically."""
    current_by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    planned = set(outcomes)
    fallback_provider = next(iter(planned)) if len(planned) == 1 else None
    for raw in current_items:
        item = dict(raw)
        provider_id = item.get("provider_id")
        if provider_id in planned:
            current_by_provider[str(provider_id)].append(item)
        elif fallback_provider is not None:
            # Synthetic fixture adapters may return records without a resolved
            # Provider identity; production adapters are checked at the
            # normalization boundary before this seam.
            current_by_provider[fallback_provider].append(item)

    prior_by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    prior_contracts: dict[str, Mapping[str, Any]] = {}
    prior_origins: dict[str, str] = {}
    prior_run_id: str | None = None
    if active_feed is not None:
        prior_run_id = (
            active_feed.get("run_id") if isinstance(active_feed.get("run_id"), str) else None
        )
        for item in active_feed.get("items", []):
            if isinstance(item, Mapping) and isinstance(item.get("provider_id"), str):
                prior_by_provider[item["provider_id"]].append(dict(item))
        for entry in active_feed.get("provider_contracts", []):
            if isinstance(entry, Mapping) and isinstance(entry.get("provider_id"), str):
                prior_contracts[entry["provider_id"]] = entry
        for prior_outcome in active_feed.get("provider_outcomes", []):
            if not isinstance(prior_outcome, Mapping):
                continue
            freshness = prior_outcome.get("freshness")
            origin = (
                _sha256(freshness.get("origin_contract_hash"))
                if isinstance(freshness, Mapping)
                else None
            )
            if isinstance(prior_outcome.get("provider_id"), str) and origin is not None:
                prior_origins[prior_outcome["provider_id"]] = origin

    strict_ids = (
        set(strict_identity_provider_ids)
        if strict_identity_provider_ids is not None
        else set(outcomes)
    )
    selected: list[dict[str, Any]] = []
    for provider_id in sorted(outcomes):
        outcome = outcomes[provider_id]
        contract = contracts.get(provider_id)
        if contract is None:
            raise SnapshotError(f"missing freshness contract for provider {provider_id!r}")
        current = current_by_provider.get(provider_id, [])
        prior = prior_by_provider.get(provider_id, [])
        _set_not_evaluated(outcome, contract)

        complete = outcome.state == "healthy" or (
            outcome.state == "empty" and empty_valid_for_window.get(provider_id, False)
        )
        if not complete:
            selected.extend(current)
            continue

        current_ids: set[str] = set()
        invalid_reason: str | None = None
        for item in current:
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                invalid_reason = "current item has no stable identity"
                break
            if item_id in current_ids:
                invalid_reason = f"duplicate current item identity {item_id!r}"
                break
            current_ids.add(item_id)
            if provider_id in strict_ids and item.get("provider_id") != provider_id:
                invalid_reason = "current item provider identity mismatch"
                break
        if invalid_reason is not None:
            outcome.state = "failed"
            outcome.error = invalid_reason
            selected.extend(current)
            continue

        prior_by_id = {item.get("id"): item for item in prior}
        changed = any(
            item.get("id") not in prior_by_id or not _same_item(item, prior_by_id[item.get("id")])
            for item in current
        )
        current_hash = current_contract_hashes.get(provider_id)
        if changed or (current and not prior):
            selected.extend(current)
            if not current:
                continue
            if not current_hash:
                raise SnapshotError(f"missing current contract hash for provider {provider_id!r}")
            try:
                status = evaluate_freshness(
                    current,
                    contract,
                    evidence_cutoff_at,
                    checked_at=outcome.retrieved_at,
                )
            except FreshnessError as exc:
                raise SnapshotError(f"{provider_id}: {exc}") from exc
            outcome.freshness = _freshness_record(
                contract=contract,
                status=status,
                origin_contract_hash=current_hash,
                carried_forward_from_run_id=None,
            )
            continue

        if prior:
            origin_hash = (
                prior_origins.get(provider_id)
                if active_feed is not None and active_feed.get("schema_version") == 2
                else _contract_hash(prior_contracts.get(provider_id))
            )
            if prior_run_id is None or origin_hash is None:
                # The active bundle is not usable as a provenance authority;
                # current complete empty acquisition remains an explicit
                # no_snapshot rather than becoming a hidden failure fallback.
                selected.extend(current)
                outcome.freshness = _freshness_record(
                    contract=contract,
                    status="no_snapshot",
                    origin_contract_hash=None,
                    carried_forward_from_run_id=None,
                )
                continue
            selected.extend(prior)
            try:
                status = evaluate_freshness(
                    prior,
                    contract,
                    evidence_cutoff_at,
                    carried_forward=True,
                    checked_at=outcome.retrieved_at,
                )
            except FreshnessError as exc:
                raise SnapshotError(f"{provider_id}: {exc}") from exc
            outcome.freshness = _freshness_record(
                contract=contract,
                status=status,
                origin_contract_hash=origin_hash,
                carried_forward_from_run_id=prior_run_id,
            )
            continue

        # Complete, contract-permitted empty acquisition without a prior slice.
        outcome.freshness = _freshness_record(
            contract=contract,
            status="no_snapshot",
            origin_contract_hash=None,
            carried_forward_from_run_id=None,
        )

    return SnapshotSelection(
        tuple(sorted(selected, key=item_total_order_key)),
        active_feed,
    )
