"""Strict loading and composition of checked-in Provider contracts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import yaml

from ..config.model import FetchRule, ProviderEntry, RatePolicy, SourceLinkRule
from .urls import UrlValidationError, canonicalize_url

MANIFEST_ROOT = Path(__file__).resolve().parents[3] / "providers"
SUPPORTED_CONTRACT_VERSION = 1
MAPPING_PROVENANCE_KINDS = frozenset({"repository_fixture", "authoritative_https"})
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
        "limits",
        "time",
        "identity",
        "units",
        "freshness",
        "role_mappings",
        "adjustment_policy",
        "empty_valid_for_window",
        "pagination",
        "default_enabled",
        "fixture_provenance",
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
    if int(raw["capacity"]) <= 0 or int(raw["refill_period_seconds"]) <= 0:
        raise ManifestError(f"{where}: capacity and refill_period_seconds must be positive")
    if int(raw["minimum_interval_seconds"]) < 0:
        raise ManifestError(f"{where}.minimum_interval_seconds must be non-negative")


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
    if data["contract_version"] != SUPPORTED_CONTRACT_VERSION:
        raise ManifestError(f"manifest {path}: unsupported contract_version")
    if data["protocol"] != "https":
        raise ManifestError(f"manifest {path}: protocol must be https")
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
    if int(data["response_limit_bytes"]) <= 0 or int(data["attempt_timeout_seconds"]) <= 0:
        raise ManifestError(f"manifest {path}: response and timeout limits must be positive")

    for section, required in (
        ("time", {"knowledge_time", "payload_types"}),
        ("identity", {"stable_record_id"}),
        ("freshness", {"policy"}),
        ("fixture_provenance", {"source", "files"}),
    ):
        value = data[section]
        if not isinstance(value, dict):
            raise ManifestError(f"manifest {path}.{section} must be a mapping")
        _require(value, required, f"manifest {path}.{section}")
    _unknown(
        data["time"],
        frozenset(
            {"knowledge_time", "payload_types", "calendar_capability", "availability_lag_seconds"}
        ),
        f"manifest {path}.time",
    )
    _unknown(data["identity"], frozenset({"stable_record_id"}), f"manifest {path}.identity")
    _unknown(data["freshness"], frozenset({"policy"}), f"manifest {path}.freshness")
    _unknown(
        data["fixture_provenance"],
        frozenset({"source", "files"}),
        f"manifest {path}.fixture_provenance",
    )
    if "limits" in data:
        if not isinstance(data["limits"], dict):
            raise ManifestError(f"manifest {path}.limits must be a mapping")
        _unknown(data["limits"], frozenset({"max_observations"}), f"manifest {path}.limits")
    if "adjustment_policy" in data:
        if not isinstance(data["adjustment_policy"], dict):
            raise ManifestError(f"manifest {path}.adjustment_policy must be a mapping")
        _unknown(
            data["adjustment_policy"],
            frozenset({"splits_dividends_adjusted", "notes"}),
            f"manifest {path}.adjustment_policy",
        )
    if not isinstance(data["time"]["payload_types"], list) or not data["time"]["payload_types"]:
        raise ManifestError(f"manifest {path}.time.payload_types must be non-empty")
    if (
        "availability_lag_seconds" in data["time"]
        and int(data["time"]["availability_lag_seconds"]) < 0
    ):
        raise ManifestError(f"manifest {path}.time.availability_lag_seconds must be non-negative")
    if not isinstance(data["fixture_provenance"]["files"], list):
        raise ManifestError(f"manifest {path}.fixture_provenance.files must be a list")
    if not isinstance(data["units"], dict):
        raise ManifestError(f"manifest {path}.units must be a mapping")
    if not isinstance(data["empty_valid_for_window"], bool) or not isinstance(
        data["default_enabled"], bool
    ):
        raise ManifestError(f"manifest {path}: boolean contract fields are invalid")
    if data["pagination"] not in {"none", "cursor", "page_number"}:
        raise ManifestError(f"manifest {path}: unsupported pagination")
    if "role_mappings" in data and not isinstance(data["role_mappings"], list):
        raise ManifestError(f"manifest {path}.role_mappings must be a list")
    for index, mapping in enumerate(data.get("role_mappings", [])):
        if not isinstance(mapping, dict):
            raise ManifestError(f"manifest {path}.role_mappings[{index}] must be a mapping")
        _validate_role_mapping_shape(mapping, f"manifest {path}.role_mappings[{index}]")


def _validate_role_mapping_shape(mapping: Mapping[str, Any], where: str) -> None:
    _require(mapping, {"role_id", "instrument", "unit", "mapping_verified"}, where)
    _unknown(
        mapping,
        frozenset(
            {
                "role_id",
                "instrument",
                "unit",
                "mapping_verified",
                "reason",
                "verification_provenance",
            }
        ),
        where,
    )
    for field_name in ("role_id", "instrument", "unit"):
        if not isinstance(mapping[field_name], str) or not mapping[field_name].strip():
            raise ManifestError(f"{where}.{field_name} must be non-empty")
    if not isinstance(mapping["mapping_verified"], bool):
        raise ManifestError(f"{where}.mapping_verified must be boolean")

    if mapping["mapping_verified"]:
        if "reason" in mapping:
            raise ManifestError(f"{where}: verification branches are exclusive")
        provenance = mapping.get("verification_provenance")
        if not isinstance(provenance, dict):
            raise ManifestError(f"{where}.verification_provenance is required for verified mapping")
        _require(provenance, {"kind", "reference"}, f"{where}.verification_provenance")
        _unknown(
            provenance,
            frozenset({"kind", "reference"}),
            f"{where}.verification_provenance",
        )
        if provenance["kind"] not in MAPPING_PROVENANCE_KINDS:
            raise ManifestError(
                f"{where}.verification_provenance.kind is unsupported: {provenance['kind']!r}"
            )
        if not isinstance(provenance["reference"], str) or not provenance["reference"].strip():
            raise ManifestError(f"{where}.verification_provenance.reference must be non-empty")
    else:
        if "verification_provenance" in mapping:
            raise ManifestError(f"{where}: verification branches are exclusive")
        reason = mapping.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ManifestError(f"{where}.reason must be non-empty for unverified mapping")


def _source_link_rules(manifest: Mapping[str, Any]) -> tuple[SourceLinkRule, ...]:
    return tuple(
        SourceLinkRule(
            host=str(rule["host"]).lower().rstrip("."),
            allow_subdomains=bool(rule.get("allow_subdomains", False)),
            allowed_ports=tuple(int(port) for port in rule.get("allowed_ports", [443])),
            allowed_query_params=tuple(rule.get("allowed_query_params", [])),
            query_value_grammar=str(rule.get("query_value_grammar", "any")),
            drop_query_params=tuple(rule.get("drop_query_params", [])),
        )
        for rule in manifest["source_link_hosts"]
    )


def _rule_allows_authoritative_url(reference: str, manifest: Mapping[str, Any]) -> bool:
    parts = urlsplit(reference)
    try:
        port = parts.port or 443
    except ValueError:
        return False
    host = parts.hostname
    if host is None:
        return False
    host = host.lower().rstrip(".")

    authorities: list[tuple[str, bool, list[int]]] = []
    for raw in (*manifest["fetch_hosts"], *manifest["redirect_hosts"]):
        authorities.append(
            (
                str(raw["host"]).lower().rstrip("."),
                bool(raw.get("allow_subdomains", False)),
                list(raw.get("allowed_ports", [443])),
            )
        )
    for raw in manifest["source_link_hosts"]:
        authorities.append(
            (
                str(raw["host"]).lower().rstrip("."),
                bool(raw.get("allow_subdomains", False)),
                list(raw.get("allowed_ports", [443])),
            )
        )
    contract = manifest["verification"].get("contract_url")
    if isinstance(contract, str) and contract:
        contract_parts = urlsplit(contract)
        if contract_parts.hostname:
            try:
                contract_port = contract_parts.port or 443
            except ValueError:
                return False
            authorities.append(
                (contract_parts.hostname.lower().rstrip("."), False, [contract_port])
            )

    if not any(
        (host == allowed_host or (allow_subdomains and host.endswith(f".{allowed_host}")))
        and port in allowed_ports
        for allowed_host, allow_subdomains, allowed_ports in authorities
    ):
        return False

    if not parts.query:
        return True
    if isinstance(contract, str) and reference == contract:
        return True

    try:
        return (
            canonicalize_url(
                reference,
                rules=_source_link_rules(manifest),
                where="authoritative HTTPS verification reference",
            )
            == reference
        )
    except UrlValidationError:
        return False


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


def validate_mapping_provenance(
    manifest: Mapping[str, Any],
    mapping: Mapping[str, Any],
    *,
    manifest_root: Path,
    provider_id: str,
) -> None:
    """Validate mapping evidence locally during strict Provider resolution."""
    if not mapping["mapping_verified"]:
        return
    provenance = mapping["verification_provenance"]
    kind = provenance["kind"]
    reference = provenance["reference"]
    if reference != reference.strip():
        raise ManifestError(f"mapping verification reference must be canonical: {reference!r}")
    if kind == "authoritative_https":
        parts = urlsplit(reference)
        if parts.scheme != "https" or parts.username is not None or parts.password is not None:
            raise ManifestError(
                f"authoritative HTTPS verification reference has invalid HTTPS URL: {reference!r}"
            )
        if parts.fragment:
            raise ManifestError(
                f"authoritative HTTPS verification reference must not contain a fragment: {reference!r}"
            )
        if _canonical_authoritative_url(reference) != reference:
            raise ManifestError(
                f"authoritative HTTPS verification reference must be canonical: {reference!r}"
            )
        if not _rule_allows_authoritative_url(reference, manifest):
            raise ManifestError(
                f"authoritative HTTPS verification reference violates Provider URL policy: {reference!r}"
            )
        if provider_id == "yahoo_market":
            expected_path = f"/v8/finance/chart/{quote(str(mapping['instrument']), safe='')}"
            if parts.path != expected_path:
                raise ManifestError(
                    "Yahoo authoritative HTTPS provenance must use the chart URL for "
                    f"mapping instrument {mapping['instrument']!r}"
                )
        return

    reference_path = Path(reference)
    if reference_path.is_absolute() or ".." in reference_path.parts:
        raise ManifestError(
            f"repository fixture reference must be repository-relative and non-escaping: {reference!r}"
        )
    repository_root = manifest_root.resolve().parent
    provider_root = (manifest_root / provider_id).resolve()
    resolved = (repository_root / reference_path).resolve()
    if not resolved.is_relative_to(repository_root):
        raise ManifestError(f"repository fixture reference escapes repository root: {reference!r}")
    if not resolved.is_relative_to(provider_root):
        raise ManifestError(
            f"repository fixture reference is outside owning Provider: {reference!r}"
        )
    if not resolved.exists():
        raise ManifestError(f"repository fixture reference does not exist: {reference!r}")
    if not resolved.is_file():
        raise ManifestError(f"repository fixture reference is not a file: {reference!r}")

    if provider_id != "yahoo_market":
        return
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        results = payload["chart"]["result"]
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise KeyError("chart.result")
        symbol = results[0]["meta"]["symbol"]
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        raise ManifestError(
            f"Yahoo chart fixture does not expose one usable chart.result meta.symbol: {reference!r}"
        ) from exc
    if symbol != mapping["instrument"]:
        raise ManifestError(
            f"Yahoo chart fixture meta.symbol {symbol!r} does not match mapping instrument {mapping['instrument']!r}"
        )


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
        capacity=int(rate["capacity"]),
        refill_period_seconds=int(rate["refill_period_seconds"]),
        minimum_interval_seconds=int(rate["minimum_interval_seconds"]),
        shared_host=rate.get("shared_host"),
    )


def _freeze_contract_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_contract_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_contract_value(item) for item in value)
    return value


def _freeze_contract_mapping(mapping: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(
        {str(key): _freeze_contract_value(value) for key, value in mapping.items()}
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
    limits = manifest.get("limits", {})
    return ProviderEntry(
        id=str(manifest["provider_id"]),
        name=str(manifest["name"]),
        enabled=bool(enabled),
        verified=bool(verification["verified"]),
        default_enabled=bool(manifest["default_enabled"]),
        group="",
        source_family_id=str(manifest["source_family_id"]),
        tier=str(manifest["tier"]),
        user_agent=str(manifest["user_agent"]),
        fetch_hosts=tuple(
            FetchRule(
                str(f["host"]).lower().rstrip("."),
                bool(f.get("allow_subdomains", False)),
                tuple(int(p) for p in f.get("allowed_ports", [443])),
            )
            for f in manifest["fetch_hosts"]
        ),
        redirect_hosts=tuple(
            FetchRule(
                str(f["host"]).lower().rstrip("."),
                bool(f.get("allow_subdomains", False)),
                tuple(int(p) for p in f.get("allowed_ports", [443])),
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
        response_limit_bytes=int(manifest["response_limit_bytes"]),
        credentials_required=str(manifest["authentication"]).lower() not in {"none", "anonymous"},
        verification_date=verification["verification_date"],
        contract_url=verification["contract_url"],
        notes=verification["usage_note"],
        contract_version=int(manifest["contract_version"]),
        authentication=str(manifest["authentication"]),
        protocol=str(manifest["protocol"]),
        attempt_timeout_seconds=int(manifest["attempt_timeout_seconds"]),
        request_limit_bytes=int(manifest["response_limit_bytes"]),
        max_observations=int(limits["max_observations"]) if "max_observations" in limits else None,
        time_knowledge_time=str(time["knowledge_time"]),
        payload_types=tuple(str(p) for p in time["payload_types"]),
        calendar_capability=time.get("calendar_capability"),
        availability_lag_seconds=int(time["availability_lag_seconds"])
        if "availability_lag_seconds" in time
        else None,
        identity_stable_record_id=str(manifest["identity"]["stable_record_id"]),
        units={str(k): str(v) for k, v in manifest["units"].items()},
        freshness_policy=str(manifest["freshness"]["policy"]),
        role_mappings=tuple(_freeze_contract_mapping(m) for m in manifest.get("role_mappings", [])),
        adjustment_policy=dict(manifest.get("adjustment_policy", {})),
        fixture_provenance_source=str(manifest["fixture_provenance"]["source"]),
        fixture_files=tuple(str(f) for f in manifest["fixture_provenance"]["files"]),
        coverage_groups=tuple(coverage_groups),
    )


def load_all_manifests(root: Path | None = None) -> dict[str, Mapping[str, Any]]:
    root = root or MANIFEST_ROOT
    manifests: dict[str, Mapping[str, Any]] = {}
    for path in sorted(root.glob("*/manifest.yaml")):
        pid = path.parent.name
        manifests[pid] = load_manifest(pid, root)
    return manifests
