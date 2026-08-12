"""Provider contract-manifest loading.

Each enabled adapter must have a checked-in contract manifest recording
fetch/redirect hosts, source-link rules, rate policy, charset, identity,
units, freshness, pagination, and fixture provenance. This module loads and
validates those manifests; an adapter whose manifest is missing or
inconsistent cannot be enabled.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from ..config.model import FetchRule, ProviderEntry, RatePolicy, SourceLinkRule

MANIFEST_ROOT = Path(__file__).resolve().parents[3] / "providers"


class ManifestError(ValueError):
    """Provider manifest missing or invalid."""


def load_manifest(provider_id: str, root: Path | None = None) -> Mapping[str, Any]:
    root = root or MANIFEST_ROOT
    path = root / provider_id / "manifest.yaml"
    if not path.exists():
        raise ManifestError(f"missing contract manifest for provider {provider_id!r}")
    try:
        data = yaml.safe_load(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ManifestError(f"invalid manifest {path}: {exc}") from exc
    if data.get("provider_id") != provider_id:
        raise ManifestError(f"manifest {path}: provider_id mismatch")
    if data.get("contract_version") != 1:
        raise ManifestError(f"manifest {path}: unsupported contract_version")
    return data


def manifest_to_provider_entry(manifest: Mapping[str, Any]) -> ProviderEntry:
    """Derive a ProviderEntry from a manifest (for registry assembly)."""
    verification = manifest.get("verification", {})
    rate = manifest.get("rate_policy")
    rate_policy = None
    if rate and not rate.get("unlimited"):
        rate_policy = RatePolicy(
            scope_id=str(rate["scope_id"]),
            capacity=int(rate["capacity"]),
            refill_period_seconds=int(rate["refill_period_seconds"]),
            minimum_interval_seconds=int(rate.get("minimum_interval_seconds", 0)),
        )
    elif rate and rate.get("unlimited"):
        rate_policy = RatePolicy(
            scope_id=str(rate["scope_id"]),
            capacity=0,
            refill_period_seconds=0,
            minimum_interval_seconds=0,
            unlimited=True,
        )
    return ProviderEntry(
        id=str(manifest["provider_id"]),
        name=str(manifest["name"]),
        enabled=bool(
            verification.get("verified", False) and manifest.get("default_enabled", False)
        ),
        verified=bool(verification.get("verified", False)),
        default_enabled=bool(manifest.get("default_enabled", False)),
        group=str(manifest.get("group", "")),
        source_family_id=str(manifest.get("source_family_id", manifest["provider_id"])),
        tier=str(manifest.get("tier", "Tier 2")),
        user_agent=str(manifest.get("user_agent", "")),
        fetch_hosts=tuple(
            FetchRule(
                str(f["host"]).lower(),
                bool(f.get("allow_subdomains", False)),
                tuple(int(p) for p in f.get("allowed_ports", [443])),
            )
            for f in manifest.get("fetch_hosts", [])
        ),
        redirect_hosts=tuple(
            FetchRule(
                str(f["host"]).lower(),
                bool(f.get("allow_subdomains", False)),
                tuple(int(p) for p in f.get("allowed_ports", [443])),
            )
            for f in manifest.get("redirect_hosts", [])
        ),
        source_link_hosts=tuple(
            SourceLinkRule(
                host=str(r["host"]).lower(),
                allow_subdomains=bool(r.get("allow_subdomains", False)),
                allowed_ports=tuple(int(p) for p in r.get("allowed_ports", [443])),
                allowed_query_params=tuple(r.get("allowed_query_params", [])),
                query_value_grammar=str(r.get("query_value_grammar", "any")),
                drop_query_params=tuple(r.get("drop_query_params", [])),
            )
            for r in manifest.get("source_link_hosts", [])
        ),
        rate_policy=rate_policy,
        allowed_charset=str(manifest.get("charset", {}).get("allowed", ["utf-8"])[0]),
        allowed_bom=bool(manifest.get("charset", {}).get("bom_allowed", False)),
        allowed_content_type_header=manifest.get("charset", {}).get("content_type_header"),
        pagination=str(manifest.get("pagination", "none")),
        empty_valid_for_window=bool(manifest.get("empty_valid_for_window", False)),
        response_limit_bytes=int(manifest.get("response_limit_bytes", 10 * 1024 * 1024)),
        credentials_required=bool(manifest.get("authentication") not in (None, "none")),
        verification_date=verification.get("verification_date"),
        contract_url=verification.get("contract_url"),
        notes=verification.get("usage_note"),
    )


def load_all_manifests(root: Path | None = None) -> dict[str, Mapping[str, Any]]:
    root = root or MANIFEST_ROOT
    manifests: dict[str, Mapping[str, Any]] = {}
    for path in sorted(root.glob("*/manifest.yaml")):
        pid = path.parent.name
        manifests[pid] = load_manifest(pid, root)
    return manifests
