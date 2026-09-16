"""Strict loading and composition of checked-in Provider contracts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml

from ..config.model import (
    FetchRule,
    FreshnessContract,
    ProviderEntry,
    RatePolicy,
    SourceLinkRule,
)

MANIFEST_ROOT = Path(__file__).resolve().parents[3] / "providers"
# Provider contracts evolve independently while the logical Feed remains v4.
SUPPORTED_CONTRACT_VERSIONS: dict[str, frozenset[int]] = {
    "sec_edgar": frozenset({1, 2, 3, 4}),
    "cftc": frozenset({1, 2}),
    "federal_reserve": frozenset({1}),
    "bls": frozenset({1}),
    "pboc": frozenset({1}),
    "nbs": frozenset({1}),
    "sse": frozenset({1}),
    "szse": frozenset({1}),
}
SUPPORTED_PAYLOAD_TYPES = frozenset({"news", "macro_release", "policy", "positioning", "filing"})
IMPLEMENTED_PAYLOAD_TYPES = {
    "federal_reserve": frozenset({"policy"}),
    "bls": frozenset({"news"}),
    "pboc": frozenset({"policy"}),
    "nbs": frozenset({"macro_release", "news"}),
    "sse": frozenset({"news"}),
    "szse": frozenset({"news"}),
    "sec_edgar": frozenset({"filing"}),
    "cftc": frozenset({"positioning"}),
}
_BARE_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")


class ManifestError(ValueError):
    """Provider manifest missing or invalid."""


_ALLOWED_MANIFEST_KEYS = frozenset(
    {
        "contract_version",
        "provider_id",
        "name",
        "source_family_id",
        "tier",
        "verification",
        "authentication",
        "protocol",
        "user_agent",
        "charset",
        "fetch_hosts",
        "redirect_hosts",
        "source_link_hosts",
        "rate_policy",
        "response_limit_bytes",
        "attempt_timeout_seconds",
        "time",
        "identity",
        "units",
        "freshness",
        "empty_valid_for_window",
        "pagination",
        "default_enabled",
        "fixture_provenance",
        "form4",
        "beneficial_ownership",
    }
)


def _require(mapping: Mapping[str, Any], required: set[str], where: str) -> None:
    missing = required - set(mapping)
    if missing:
        raise ManifestError(f"{where}: missing required keys: {sorted(missing)}")


def _unknown(mapping: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    extra = set(mapping) - allowed
    if extra:
        raise ManifestError(f"{where}: unknown keys: {sorted(extra)}")


def _as_int(value: Any, where: str) -> int:
    if isinstance(value, bool):
        raise ManifestError(f"{where} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{where} must be an integer") from exc


def _read_manifest(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifestError(f"invalid manifest {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ManifestError(f"invalid manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"invalid manifest {path}: top-level YAML must be a mapping")
    return data


def _validate_rule_list(raw: Any, where: str, *, source: bool = False) -> None:
    if not isinstance(raw, list):
        raise ManifestError(f"{where} must be a list")
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ManifestError(f"{where}[{index}] must be a mapping")
        allowed = {"host", "allow_subdomains", "allowed_ports"}
        required = set(allowed)
        if source:
            allowed |= {"allowed_query_params", "query_value_grammar", "drop_query_params"}
            required = set(allowed)
        _require(item, required, f"{where}[{index}]")
        _unknown(item, frozenset(allowed), f"{where}[{index}]")
        if not isinstance(item["host"], str) or not item["host"].strip():
            raise ManifestError(f"{where}[{index}].host must be non-empty")
        if not isinstance(item.get("allow_subdomains", False), bool):
            raise ManifestError(f"{where}[{index}].allow_subdomains must be boolean")
        ports = item.get("allowed_ports", [443])
        if not isinstance(ports, list) or not ports or any(not isinstance(p, int) for p in ports):
            raise ManifestError(f"{where}[{index}].allowed_ports must be non-empty integers")
        if source and item["query_value_grammar"] not in {"any", "plain", "numeric"}:
            raise ManifestError(f"{where}[{index}].query_value_grammar is unsupported")


def _validate_rate(raw: Any, where: str) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise ManifestError(f"{where} must be a mapping or null")
    _require(
        raw, {"scope_id", "capacity", "refill_period_seconds", "minimum_interval_seconds"}, where
    )
    _unknown(
        raw,
        frozenset(
            {
                "scope_id",
                "capacity",
                "refill_period_seconds",
                "minimum_interval_seconds",
                "unlimited",
                "shared_host",
            }
        ),
        where,
    )
    if not isinstance(raw["scope_id"], str) or not raw["scope_id"].strip():
        raise ManifestError(f"{where}.scope_id must be non-empty")
    if raw.get("unlimited", False):
        return
    capacity = _as_int(raw["capacity"], f"{where}.capacity")
    refill_period = _as_int(raw["refill_period_seconds"], f"{where}.refill_period_seconds")
    minimum_interval = _as_int(raw["minimum_interval_seconds"], f"{where}.minimum_interval_seconds")
    if capacity <= 0 or refill_period <= 0:
        raise ManifestError(f"{where}: capacity and refill_period_seconds must be positive")
    if minimum_interval < 0:
        raise ManifestError(f"{where}.minimum_interval_seconds must be non-negative")


def _validate_freshness(raw: Any, where: str) -> None:
    if not isinstance(raw, dict):
        raise ManifestError(f"{where} must be a mapping")
    _require(raw, {"cadence", "reference_time"}, where)
    cadence = raw["cadence"]
    reference = raw["reference_time"]
    if not isinstance(cadence, str) or cadence not in {
        "weekly",
        "scheduled",
        "event_driven",
    }:
        raise ManifestError(f"{where}.cadence is unsupported: {cadence!r}")
    if not isinstance(reference, str) or reference not in {
        "data_as_of",
        "source_updated_at",
        "checked_at",
    }:
        raise ManifestError(f"{where}.reference_time is unsupported: {reference!r}")
    if cadence == "event_driven":
        if reference != "checked_at":
            raise ManifestError(f"{where}: event_driven must use checked_at")
        _unknown(raw, frozenset({"cadence", "reference_time"}), where)
        return
    allowed_references = {"data_as_of", "source_updated_at"}
    if reference not in allowed_references:
        raise ManifestError(f"{where}: {cadence} requires a source-semantic reference time")
    _require(raw, {"valid_for_seconds"}, where)
    _unknown(raw, frozenset({"cadence", "reference_time", "valid_for_seconds"}), where)
    value = raw["valid_for_seconds"]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ManifestError(f"{where}.valid_for_seconds must be a positive integer")


def _validate_manifest(data: Mapping[str, Any], path: Path, provider_id: str) -> None:
    _unknown(data, _ALLOWED_MANIFEST_KEYS, str(path))
    _require(
        data,
        {
            "contract_version",
            "provider_id",
            "name",
            "source_family_id",
            "tier",
            "verification",
            "authentication",
            "protocol",
            "user_agent",
            "charset",
            "fetch_hosts",
            "redirect_hosts",
            "source_link_hosts",
            "rate_policy",
            "response_limit_bytes",
            "attempt_timeout_seconds",
            "time",
            "identity",
            "units",
            "freshness",
            "empty_valid_for_window",
            "pagination",
            "default_enabled",
            "fixture_provenance",
        },
        str(path),
    )
    if data["provider_id"] != provider_id:
        raise ManifestError(f"manifest {path}: provider_id mismatch")
    version = data["contract_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise ManifestError(f"manifest {path}: contract_version must be an integer")
    supported = SUPPORTED_CONTRACT_VERSIONS.get(provider_id, frozenset())
    if version not in supported:
        raise ManifestError(
            f"manifest {path}: unsupported contract_version {version} for {provider_id}"
        )
    if data["protocol"] != "https":
        raise ManifestError(f"manifest {path}: protocol must be https")
    if not isinstance(data["authentication"], str) or data["authentication"].lower() not in {
        "none",
        "anonymous",
    }:
        raise ManifestError(f"manifest {path}: Provider authentication must be credential-free")
    if not isinstance(data["user_agent"], str) or not data["user_agent"].strip():
        raise ManifestError(f"manifest {path}: user_agent must be non-empty")

    verification = data["verification"]
    if not isinstance(verification, dict):
        raise ManifestError(f"manifest {path}.verification must be a mapping")
    _require(
        verification,
        {"verified", "verification_date", "contract_url", "usage_note"},
        f"manifest {path}.verification",
    )
    _unknown(
        verification,
        frozenset({"verified", "verification_date", "contract_url", "usage_note"}),
        f"manifest {path}.verification",
    )
    if not isinstance(verification["verified"], bool):
        raise ManifestError(f"manifest {path}.verification.verified must be boolean")
    if verification["verified"] and (
        not verification["verification_date"] or not verification["contract_url"]
    ):
        raise ManifestError(f"manifest {path}: verified manifest needs verification evidence")
    if verification["verified"]:
        contract_url = verification["contract_url"]
        if (
            not isinstance(contract_url, str)
            or _canonical_authoritative_url(contract_url) != contract_url
        ):
            raise ManifestError(
                f"manifest {path}.verification.contract_url must be canonical HTTPS"
            )

    charset = data["charset"]
    if not isinstance(charset, dict):
        raise ManifestError(f"manifest {path}.charset must be a mapping")
    _require(charset, {"allowed", "bom_allowed", "content_type_header"}, f"manifest {path}.charset")
    _unknown(
        charset,
        frozenset({"allowed", "bom_allowed", "content_type_header"}),
        f"manifest {path}.charset",
    )
    if not isinstance(charset["allowed"], list) or not charset["allowed"]:
        raise ManifestError(f"manifest {path}.charset.allowed must be non-empty")
    if not isinstance(charset["bom_allowed"], bool):
        raise ManifestError(f"manifest {path}.charset.bom_allowed must be boolean")

    _validate_rule_list(data["fetch_hosts"], f"manifest {path}.fetch_hosts")
    _validate_rule_list(data["redirect_hosts"], f"manifest {path}.redirect_hosts")
    _validate_rule_list(
        data["source_link_hosts"], f"manifest {path}.source_link_hosts", source=True
    )
    _validate_rate(data["rate_policy"], f"manifest {path}.rate_policy")
    if provider_id == "sec_edgar" and version in {2, 3, 4}:
        rate = data["rate_policy"]
        if not isinstance(rate, Mapping) or {
            rate.get("scope_id"),
            rate.get("capacity"),
            rate.get("refill_period_seconds"),
            rate.get("minimum_interval_seconds"),
        } != {"sec_edgar", 10, 60, 5}:
            raise ManifestError(
                f"manifest {path}: SEC v{version} rate policy is not the unchanged closed contract"
            )
        if set(rate) != {
            "scope_id",
            "capacity",
            "refill_period_seconds",
            "minimum_interval_seconds",
        }:
            raise ManifestError(
                f"manifest {path}: SEC v{version} rate policy contains unsupported fields"
            )
    response_limit = _as_int(data["response_limit_bytes"], f"manifest {path}.response_limit_bytes")
    attempt_timeout = _as_int(
        data["attempt_timeout_seconds"], f"manifest {path}.attempt_timeout_seconds"
    )
    if response_limit <= 0 or attempt_timeout <= 0:
        raise ManifestError(f"manifest {path}: response and timeout limits must be positive")

    for section, required in (
        ("time", {"knowledge_time", "payload_types"}),
        ("identity", {"stable_record_id"}),
        ("freshness", {"cadence", "reference_time"}),
        ("fixture_provenance", {"source", "files"}),
    ):
        value = data[section]
        if not isinstance(value, dict):
            raise ManifestError(f"manifest {path}.{section} must be a mapping")
        _require(value, required, f"manifest {path}.{section}")
    _unknown(
        data["time"],
        frozenset({"knowledge_time", "payload_types"}),
        f"manifest {path}.time",
    )
    _unknown(data["identity"], frozenset({"stable_record_id"}), f"manifest {path}.identity")
    _validate_freshness(data["freshness"], f"manifest {path}.freshness")
    _unknown(
        data["fixture_provenance"],
        frozenset({"source", "files"}),
        f"manifest {path}.fixture_provenance",
    )
    payload_types = data["time"]["payload_types"]
    if not isinstance(payload_types, list) or not payload_types:
        raise ManifestError(f"manifest {path}.time.payload_types must be non-empty")
    if any(not isinstance(payload, str) for payload in payload_types):
        raise ManifestError(f"manifest {path}.time.payload_types must contain strings")
    unsupported = set(payload_types) - SUPPORTED_PAYLOAD_TYPES
    if unsupported:
        raise ManifestError(
            f"manifest {path}.time.payload_types contains removed domains: {sorted(unsupported)}"
        )
    implemented = IMPLEMENTED_PAYLOAD_TYPES.get(provider_id, frozenset())
    overdeclared = set(payload_types) - implemented
    if overdeclared:
        raise ManifestError(
            f"manifest {path}.time.payload_types exceeds adapter output: {sorted(overdeclared)}"
        )
    if not isinstance(data["fixture_provenance"]["files"], list):
        raise ManifestError(f"manifest {path}.fixture_provenance.files must be a list")
    if not isinstance(data["units"], dict):
        raise ManifestError(f"manifest {path}.units must be a mapping")
    if provider_id == "sec_edgar" and version in {2, 3, 4}:
        expected_units = {
            "13f_value_before_2023_01_03": "usd_thousands",
            "13f_value_from_2023_01_03": "usd",
            "reported_value_usd_thousands": "usd_thousands",
        }
        if data["units"] != expected_units:
            raise ManifestError(
                f"manifest {path}: SEC v{version} units are not the closed contract"
            )
    form4 = data.get("form4")
    if provider_id == "sec_edgar" and version in {3, 4}:
        if not isinstance(form4, dict):
            raise ManifestError(f"manifest {path}: SEC v{version} form4 section is required")
        _require(
            form4,
            {"max_filings_per_window", "ownership_xml_schema_versions"},
            f"manifest {path}.form4",
        )
        _unknown(
            form4,
            frozenset({"max_filings_per_window", "ownership_xml_schema_versions"}),
            f"manifest {path}.form4",
        )
        if form4["max_filings_per_window"] != 20:
            raise ManifestError(
                f"manifest {path}: SEC v{version} max_filings_per_window must be 20"
            )
        if form4["ownership_xml_schema_versions"] != ["X0609"]:
            raise ManifestError(
                f"manifest {path}: SEC v{version} ownership_xml_schema_versions must be ['X0609']"
            )
    elif form4 is not None:
        raise ManifestError(f"manifest {path}: form4 section is only supported by SEC v3 or v4")
    beneficial_ownership = data.get("beneficial_ownership")
    if provider_id == "sec_edgar" and version == 4:
        if not isinstance(beneficial_ownership, dict):
            raise ManifestError(f"manifest {path}: SEC v4 beneficial_ownership section is required")
        _require(
            beneficial_ownership,
            {
                "max_filings_per_window",
                "max_history_files",
                "max_historical_candidate_documents",
                "max_reporting_positions_per_filing",
                "structured_formats",
                "schema_versions",
                "locator_prefixes",
            },
            f"manifest {path}.beneficial_ownership",
        )
        _unknown(
            beneficial_ownership,
            frozenset(
                {
                    "max_filings_per_window",
                    "max_history_files",
                    "max_historical_candidate_documents",
                    "max_reporting_positions_per_filing",
                    "structured_formats",
                    "schema_versions",
                    "locator_prefixes",
                }
            ),
            f"manifest {path}.beneficial_ownership",
        )
        for key in (
            "max_filings_per_window",
            "max_history_files",
            "max_historical_candidate_documents",
            "max_reporting_positions_per_filing",
        ):
            if (
                _as_int(beneficial_ownership[key], f"manifest {path}.beneficial_ownership.{key}")
                <= 0
            ):
                raise ManifestError(f"manifest {path}.beneficial_ownership.{key} must be positive")
        for key in ("structured_formats", "schema_versions", "locator_prefixes"):
            value = beneficial_ownership[key]
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(entry, str) or not entry.strip() for entry in value)
            ):
                raise ManifestError(
                    f"manifest {path}.beneficial_ownership.{key} must be a non-empty string list"
                )
        if beneficial_ownership["max_filings_per_window"] != 7:
            raise ManifestError(
                f"manifest {path}: SEC v4 max beneficial-ownership filings must be 7"
            )
        if beneficial_ownership["max_history_files"] != 1:
            raise ManifestError(f"manifest {path}: SEC v4 max history files must be 1")
        if beneficial_ownership["max_historical_candidate_documents"] != 64:
            raise ManifestError(
                f"manifest {path}: SEC v4 max historical candidate documents must be 64"
            )
        if beneficial_ownership["max_reporting_positions_per_filing"] != 32:
            raise ManifestError(f"manifest {path}: SEC v4 max reporting positions must be 32")
        if beneficial_ownership["structured_formats"] != ["edgarSubmission"]:
            raise ManifestError(
                f"manifest {path}: SEC v4 structured_formats are not the closed contract"
            )
        if beneficial_ownership["schema_versions"] != ["X0202"]:
            raise ManifestError(
                f"manifest {path}: SEC v4 schema_versions are not the closed contract"
            )
        if beneficial_ownership["locator_prefixes"] != [
            "xslSCHEDULE_13G_X01",
            "xslSCHEDULE_13G_X02",
        ]:
            raise ManifestError(
                f"manifest {path}: SEC v4 locator_prefixes are not the closed contract"
            )
    elif beneficial_ownership is not None:
        raise ManifestError(
            f"manifest {path}: beneficial_ownership section is only supported by SEC v4"
        )
    if version == 2 and provider_id == "cftc":
        if data["units"] != {"contracts": "contracts"}:
            raise ManifestError(f"manifest {path}: CFTC v2 units are not the closed contract")
        if data["empty_valid_for_window"] or data["pagination"] != "page_number":
            raise ManifestError(
                f"manifest {path}: CFTC v2 requires non-empty complete reports and page-number pagination"
            )
    if not isinstance(data["empty_valid_for_window"], bool) or not isinstance(
        data["default_enabled"], bool
    ):
        raise ManifestError(f"manifest {path}: boolean contract fields are invalid")
    if data["pagination"] not in {"none", "cursor", "page_number"}:
        raise ManifestError(f"manifest {path}: unsupported pagination")


def _source_link_rules(manifest: Mapping[str, Any]) -> tuple[SourceLinkRule, ...]:
    return tuple(
        SourceLinkRule(
            host=str(rule["host"]).lower().rstrip("."),
            allow_subdomains=bool(rule.get("allow_subdomains", False)),
            allowed_ports=tuple(
                _as_int(port, "manifest source-link allowed port")
                for port in rule.get("allowed_ports", [443])
            ),
            allowed_query_params=tuple(rule.get("allowed_query_params", [])),
            query_value_grammar=str(rule.get("query_value_grammar", "any")),
            drop_query_params=tuple(rule.get("drop_query_params", [])),
        )
        for rule in manifest["source_link_hosts"]
    )


def _canonical_authoritative_url(reference: str) -> str | None:
    try:
        parts = urlsplit(reference)
        port = parts.port
    except ValueError:
        return None
    host = parts.hostname
    if host is None or host != host.lower() or host.endswith("."):
        return None
    if _BARE_PERCENT.search(parts.path) or _BARE_PERCENT.search(parts.query):
        return None
    netloc = host if port in (None, 443) else f"{host}:{port}"
    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None
    query = urlencode(sorted(pairs), doseq=True)
    return urlunsplit(("https", netloc, parts.path or "/", query, ""))


def load_manifest(provider_id: str, root: Path | None = None) -> Mapping[str, Any]:
    root = root or MANIFEST_ROOT
    path = root / provider_id / "manifest.yaml"
    if not path.exists():
        raise ManifestError(f"missing contract manifest for provider {provider_id!r}")
    data = _read_manifest(path)
    _validate_manifest(data, path, provider_id)
    return data


def _manifest_rate(manifest: Mapping[str, Any]) -> RatePolicy | None:
    rate = manifest["rate_policy"]
    if rate is None:
        return None
    if rate.get("unlimited", False):
        return RatePolicy(
            scope_id=str(rate["scope_id"]),
            capacity=0,
            refill_period_seconds=0,
            minimum_interval_seconds=0,
            unlimited=True,
            shared_host=rate.get("shared_host"),
        )
    return RatePolicy(
        scope_id=str(rate["scope_id"]),
        capacity=_as_int(rate["capacity"], "manifest rate capacity"),
        refill_period_seconds=_as_int(rate["refill_period_seconds"], "manifest rate refill period"),
        minimum_interval_seconds=_as_int(
            rate["minimum_interval_seconds"], "manifest rate minimum interval"
        ),
        shared_host=rate.get("shared_host"),
    )


def manifest_to_provider_entry(
    manifest: Mapping[str, Any],
    *,
    enabled: bool | None = None,
    coverage_groups: tuple[str, ...] = (),
) -> ProviderEntry:
    """Construct the one typed runtime contract from one validated manifest."""
    verification = manifest["verification"]
    if enabled is None:
        enabled = bool(verification["verified"] and manifest["default_enabled"])
    charset = manifest["charset"]
    time = manifest["time"]
    response_limit = _as_int(manifest["response_limit_bytes"], "manifest response limit")
    contract_version = _as_int(manifest["contract_version"], "manifest contract version")
    attempt_timeout = _as_int(manifest["attempt_timeout_seconds"], "manifest attempt timeout")
    valid_for = (
        _as_int(
            manifest["freshness"]["valid_for_seconds"],
            "manifest freshness valid_for_seconds",
        )
        if "valid_for_seconds" in manifest["freshness"]
        else None
    )
    form4 = manifest.get("form4")
    max_form4_filings = (
        _as_int(form4["max_filings_per_window"], "manifest Form 4 filing bound")
        if isinstance(form4, Mapping)
        else None
    )
    form4_schema_versions = (
        tuple(str(version) for version in form4["ownership_xml_schema_versions"])
        if isinstance(form4, Mapping)
        else ()
    )
    beneficial_ownership = manifest.get("beneficial_ownership")
    beneficial_values = beneficial_ownership if isinstance(beneficial_ownership, Mapping) else {}
    return ProviderEntry(
        id=str(manifest["provider_id"]),
        name=str(manifest["name"]),
        enabled=bool(enabled),
        verified=bool(verification["verified"]),
        default_enabled=bool(manifest["default_enabled"]),
        source_family_id=str(manifest["source_family_id"]),
        tier=str(manifest["tier"]),
        user_agent=str(manifest["user_agent"]),
        fetch_hosts=tuple(
            FetchRule(
                str(f["host"]).lower().rstrip("."),
                bool(f.get("allow_subdomains", False)),
                tuple(
                    _as_int(p, "manifest fetch allowed port") for p in f.get("allowed_ports", [443])
                ),
            )
            for f in manifest["fetch_hosts"]
        ),
        redirect_hosts=tuple(
            FetchRule(
                str(f["host"]).lower().rstrip("."),
                bool(f.get("allow_subdomains", False)),
                tuple(
                    _as_int(p, "manifest redirect allowed port")
                    for p in f.get("allowed_ports", [443])
                ),
            )
            for f in manifest["redirect_hosts"]
        ),
        source_link_hosts=_source_link_rules(manifest),
        rate_policy=_manifest_rate(manifest),
        allowed_charset=str(charset["allowed"][0]),
        allowed_bom=bool(charset["bom_allowed"]),
        allowed_content_type_header=charset["content_type_header"],
        pagination=str(manifest["pagination"]),
        empty_valid_for_window=bool(manifest["empty_valid_for_window"]),
        response_limit_bytes=response_limit,
        credentials_required=str(manifest["authentication"]).lower() not in {"none", "anonymous"},
        verification_date=verification["verification_date"],
        contract_url=verification["contract_url"],
        notes=verification["usage_note"],
        contract_version=contract_version,
        authentication=str(manifest["authentication"]),
        protocol=str(manifest["protocol"]),
        attempt_timeout_seconds=attempt_timeout,
        request_limit_bytes=response_limit,
        time_knowledge_time=str(time["knowledge_time"]),
        payload_types=tuple(str(p) for p in time["payload_types"]),
        identity_stable_record_id=str(manifest["identity"]["stable_record_id"]),
        units={str(k): str(v) for k, v in manifest["units"].items()},
        freshness=FreshnessContract(
            cadence=str(manifest["freshness"]["cadence"]),
            reference_time=str(manifest["freshness"]["reference_time"]),
            valid_for_seconds=valid_for,
        ),
        fixture_provenance_source=str(manifest["fixture_provenance"]["source"]),
        fixture_files=tuple(str(f) for f in manifest["fixture_provenance"]["files"]),
        coverage_groups=tuple(coverage_groups),
        max_filings_per_window=max_form4_filings,
        ownership_xml_schema_versions=form4_schema_versions,
        beneficial_ownership_max_filings_per_window=(
            _as_int(
                beneficial_values["max_filings_per_window"],
                "manifest beneficial-ownership filing bound",
            )
            if "max_filings_per_window" in beneficial_values
            else None
        ),
        beneficial_ownership_max_history_files=(
            _as_int(beneficial_values["max_history_files"], "manifest history-file bound")
            if "max_history_files" in beneficial_values
            else None
        ),
        beneficial_ownership_max_historical_candidate_documents=(
            _as_int(
                beneficial_values["max_historical_candidate_documents"],
                "manifest historical-candidate bound",
            )
            if "max_historical_candidate_documents" in beneficial_values
            else None
        ),
        beneficial_ownership_max_reporting_positions=(
            _as_int(
                beneficial_values["max_reporting_positions_per_filing"],
                "manifest reporting-position bound",
            )
            if "max_reporting_positions_per_filing" in beneficial_values
            else None
        ),
        beneficial_ownership_structured_formats=tuple(
            str(value) for value in beneficial_values.get("structured_formats", [])
        ),
        beneficial_ownership_schema_versions=tuple(
            str(value) for value in beneficial_values.get("schema_versions", [])
        ),
        beneficial_ownership_locator_prefixes=tuple(
            str(value) for value in beneficial_values.get("locator_prefixes", [])
        ),
    )


@dataclass(frozen=True, slots=True)
class SecSendShape:
    """Maximum successful-path sends for one resolved SEC contract."""

    form13f_submissions: int
    form13f_documents: int
    form4_submissions: int
    form4_documents: int
    beneficial_ownership_submissions: int
    beneficial_ownership_current_documents: int
    beneficial_ownership_history_files: int
    beneficial_ownership_candidate_documents: int

    @property
    def total(self) -> int:
        return sum(
            (
                self.form13f_submissions,
                self.form13f_documents,
                self.form4_submissions,
                self.form4_documents,
                self.beneficial_ownership_submissions,
                self.beneficial_ownership_current_documents,
                self.beneficial_ownership_history_files,
                self.beneficial_ownership_candidate_documents,
            )
        )

    @property
    def spacing_floor_seconds(self) -> int:
        return max(0, self.total - 1)


def sec_send_shape(config: Any, contract: Any) -> SecSendShape:
    """Recompute the closed SEC send shape from resolved selections/bounds."""
    form13f_units = len(config.watched_companies)
    form4_submissions = len(config.watched_form4_issuers) if contract.contract_version >= 3 else 0
    form4_bound = contract.max_filings_per_window if form4_submissions else 0
    if form4_submissions and form4_bound is None:
        raise ValueError("SEC Form 4 maximum filing bound is missing")
    bo_submissions = (
        len(config.watched_beneficial_ownership_filers) if contract.contract_version >= 4 else 0
    )
    bo_current = contract.beneficial_ownership_max_filings_per_window if bo_submissions else 0
    bo_history = contract.beneficial_ownership_max_history_files if bo_submissions else 0
    bo_candidates = (
        contract.beneficial_ownership_max_historical_candidate_documents if bo_submissions else 0
    )
    if bo_submissions and None in (bo_current, bo_history, bo_candidates):
        raise ValueError("SEC beneficial-ownership request bounds are incomplete")

    def bound(value: Any, label: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} is not an integer") from exc

    form4_bound_value = bound(form4_bound, "SEC Form 4 filing bound") if form4_submissions else 0
    bo_current_value = (
        bound(bo_current, "SEC beneficial-ownership current bound") if bo_submissions else 0
    )
    bo_history_value = (
        bound(bo_history, "SEC beneficial-ownership history bound") if bo_submissions else 0
    )
    bo_candidates_value = (
        bound(bo_candidates, "SEC beneficial-ownership candidate bound") if bo_submissions else 0
    )
    return SecSendShape(
        form13f_submissions=form13f_units,
        form13f_documents=form13f_units * 2,
        form4_submissions=form4_submissions,
        form4_documents=form4_submissions * form4_bound_value,
        beneficial_ownership_submissions=bo_submissions,
        beneficial_ownership_current_documents=bo_submissions * bo_current_value,
        beneficial_ownership_history_files=bo_submissions * bo_history_value,
        beneficial_ownership_candidate_documents=bo_submissions * bo_candidates_value,
    )


def validate_sec_deadline(config: Any, contract: Any) -> SecSendShape:
    """Fail closed unless the configured pre-commit budget admits the shape."""
    policy = contract.rate_policy
    if policy is None or policy.unlimited:
        raise ValueError("SEC rate policy must be bounded")
    shape = sec_send_shape(config, contract)
    token_refill_floor = 0
    if shape.total > policy.capacity:
        token_refill_floor = math.ceil(
            (shape.total - policy.capacity) * policy.refill_period_seconds / policy.capacity
        )
    managed_send_floor = max(
        shape.spacing_floor_seconds * policy.minimum_interval_seconds,
        token_refill_floor,
    )
    required = (
        managed_send_floor
        + config.feed.sec_request_network_headroom_seconds
        + config.feed.commit_reserve_seconds
    )
    if config.feed.pre_commit_deadline_seconds < required:
        raise ValueError(
            "SEC pre-commit deadline is below the closed request budget: "
            f"{config.feed.pre_commit_deadline_seconds} < {required}"
        )
    return shape


def load_all_manifests(root: Path | None = None) -> dict[str, Mapping[str, Any]]:
    root = root or MANIFEST_ROOT
    manifests: dict[str, Mapping[str, Any]] = {}
    for path in sorted(root.glob("*/manifest.yaml")):
        pid = path.parent.name
        manifests[pid] = load_manifest(pid, root)
    return manifests
