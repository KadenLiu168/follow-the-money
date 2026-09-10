"""Typed Feed bundle model, validation, and manifest-first loading."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..canonical import canonical_bytes, canonical_sha256, load_canonical_json
from ..schema import SchemaError, validate_against
from .dedupe import deterministic_item_order, item_total_order_key
from .validate import assert_feed_identity, recompute_feed_identity, validate_feed

DOMAINS = (
    "news",
    "macro_release",
    "policy",
    "positioning",
    "filing",
)
PREVIOUS_DOMAINS = (
    "news",
    "macro_release",
    "policy",
    "market_data",
    "flow",
    "positioning",
    "filing",
    "calendar",
)
SUPPORTED_BUNDLE_MAJOR = 4
SUPPORTED_BUNDLE_MAJORS = (4,)
PREVIOUS_BUNDLE_MAJOR = 3
MIGRATABLE_BUNDLE_MAJORS = (PREVIOUS_BUNDLE_MAJOR,)
SUPPORTED_ARTIFACT_MAJOR = 2
PREVIOUS_ARTIFACT_MAJOR = 1
MANIFEST_FILENAME = "feed-manifest.json"
ARTIFACT_SCHEMA_FILENAME = "feed-artifact.schema.json"
MANIFEST_SCHEMA_FILENAME = "feed-manifest.schema.json"


class BundleError(ValueError):
    """A Feed bundle failed closed validation or publication preparation."""


@dataclass(frozen=True)
class FeedBundle:
    """Canonical in-memory candidate and its exact physical bytes."""

    manifest: dict[str, Any]
    artifacts: dict[str, dict[str, Any]]
    manifest_bytes: bytes
    artifact_bytes: dict[str, bytes]

    @property
    def run_id(self) -> str:
        return self.manifest["run_id"]

    @property
    def content_digest(self) -> str:
        return self.manifest["content_digest"]

    @property
    def cutoff(self) -> str:
        return self.manifest["evidence_cutoff_at"]


def generation_key(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id:
        raise BundleError("run_id must be a non-empty string")
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:32]


def artifact_relative_path(domain: str, run_id: str) -> str:
    if domain not in DOMAINS:
        raise BundleError(f"unsupported Feed domain: {domain!r}")
    return f"feed-{domain}-{generation_key(run_id)}.json"


def _artifact_relative_path_for_version(domain: str, run_id: str, version: int) -> str:
    allowed = DOMAINS if version == SUPPORTED_BUNDLE_MAJOR else PREVIOUS_DOMAINS
    if domain not in allowed:
        raise BundleError(f"unsupported Feed domain: {domain!r}")
    return f"feed-{domain}-{generation_key(run_id)}.json"


# Alias kept deliberately small: tests and deployment code often call this
# operation "artifact_path".
def artifact_path(domain: str, run_id: str) -> str:
    return artifact_relative_path(domain, run_id)


def _schema_descriptor(filename: str) -> dict[str, str]:
    path = Path(__file__).resolve().parents[3] / "schemas" / filename
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BundleError(f"cannot read schema {filename}: {exc}") from exc
    return {"path": f"schemas/{filename}", "sha256": canonical_sha256(data)}


def _manifest_from_feed(feed: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = {key: value for key, value in feed.items() if key != "items"}
    manifest["bundle_schemas"] = {
        "manifest": _schema_descriptor(MANIFEST_SCHEMA_FILENAME),
        "artifact": _schema_descriptor(ARTIFACT_SCHEMA_FILENAME),
    }
    manifest["artifacts"] = artifacts
    return manifest


def split_feed(feed: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Split one validated logical Feed into the fixed typed artifact set."""
    try:
        validate_feed(feed)
        assert_feed_identity(feed)
    except (SchemaError, TypeError, ValueError) as exc:
        raise BundleError(f"cannot split invalid Feed: {exc}") from exc

    grouped: dict[str, list[dict[str, Any]]] = {domain: [] for domain in DOMAINS}
    for item in feed["items"]:
        domain = item.get("payload", {}).get("type")
        if domain not in grouped:
            raise BundleError(f"unsupported Feed payload type: {domain!r}")
        grouped[domain].append(item)

    artifacts: dict[str, dict[str, Any]] = {}
    for domain in DOMAINS:
        items = deterministic_item_order(grouped[domain])
        artifacts[domain] = {
            "schema_version": SUPPORTED_ARTIFACT_MAJOR,
            "run_id": feed["run_id"],
            "domain": domain,
            "items": items,
        }
    return {}, artifacts


def build_bundle(feed: dict[str, Any]) -> FeedBundle:
    """Build and canonically serialize a complete manifest-led candidate."""
    if feed.get("schema_version") != SUPPORTED_BUNDLE_MAJOR:
        raise BundleError("new production Feed bundles must use schema version 4")
    _unused, artifacts = split_feed(feed)
    artifact_bytes = {domain: canonical_bytes(artifact) for domain, artifact in artifacts.items()}
    inventory = [
        {
            "domain": domain,
            "path": artifact_relative_path(domain, feed["run_id"]),
            "item_count": len(artifacts[domain]["items"]),
            "size_bytes": len(artifact_bytes[domain]),
            "sha256": canonical_sha256(artifact_bytes[domain]),
        }
        for domain in DOMAINS
    ]
    manifest = _manifest_from_feed(feed, inventory)
    try:
        validate_against(MANIFEST_SCHEMA_FILENAME, manifest)
    except SchemaError as exc:
        raise BundleError(f"generated manifest is invalid: {exc}") from exc
    manifest_bytes = canonical_bytes(manifest)
    if load_canonical_json(manifest_bytes, where="Feed manifest") != manifest:
        raise BundleError("generated manifest is not canonical")
    return FeedBundle(manifest, artifacts, manifest_bytes, artifact_bytes)


def reconstruct_feed(manifest: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Recreate the logical Feed identity projection from a manifest."""
    feed = {
        key: value for key, value in manifest.items() if key not in {"bundle_schemas", "artifacts"}
    }
    feed["items"] = items
    return feed


def _canonical_object(data: bytes, *, where: str) -> dict[str, Any]:
    try:
        value = load_canonical_json(data, where=where)
    except Exception as exc:
        raise BundleError(f"{where}: invalid canonical JSON: {exc}") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != data:
        raise BundleError(f"{where}: bytes are not canonical")
    return value


def _validated_artifact_relative_path(relative: object, expected: str) -> str:
    if not isinstance(relative, str) or relative != expected:
        raise BundleError("artifact path is not the canonical generation-qualified path")
    candidate_rel = Path(relative)
    if (
        candidate_rel.is_absolute()
        or candidate_rel.name != relative
        or "/" in relative
        or "\\" in relative
        or ".." in candidate_rel.parts
    ):
        raise BundleError("artifact path is unsafe")
    return relative


def _safe_artifact_path(root: Path, relative: object, expected: str) -> Path:
    relative = _validated_artifact_relative_path(relative, expected)
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise BundleError("artifact path escapes Feed product root")
    if not candidate.is_file():
        raise BundleError(f"missing Feed artifact: {relative}")
    return candidate


def _validated_inventory_paths(
    manifest: dict[str, Any], *, allow_previous: bool = False
) -> tuple[str, ...]:
    version = manifest.get("schema_version")
    if version == PREVIOUS_BUNDLE_MAJOR:
        if not allow_previous:
            raise BundleError("previous eight-domain Feed bundle requires bounded migration")
        domains: tuple[str, ...] = PREVIOUS_DOMAINS
    elif version == SUPPORTED_BUNDLE_MAJOR:
        domains = DOMAINS
    else:
        raise BundleError("unsupported Feed manifest schema version")
    inventory = manifest.get("artifacts")
    if not isinstance(inventory, list) or len(inventory) != len(domains):
        raise BundleError("Feed manifest inventory must contain the exact fixed domain order")
    if any(not isinstance(entry, dict) for entry in inventory):
        raise BundleError("Feed manifest artifact inventory entry is invalid")
    if [entry.get("domain") for entry in inventory] != list(domains):
        raise BundleError("Feed manifest inventory must contain the exact fixed domain order")
    paths: list[str] = []
    seen: set[str] = set()
    for entry in inventory:
        domain = entry["domain"]
        if domain in seen:
            raise BundleError(f"duplicate Feed artifact domain: {domain}")
        seen.add(domain)
        expected = _artifact_relative_path_for_version(domain, manifest["run_id"], int(version))
        paths.append(_validated_artifact_relative_path(entry["path"], expected))
    if seen != set(domains):
        raise BundleError("Feed manifest inventory is incomplete")
    return tuple(paths)


def validate_manifest_and_inventory(
    manifest_bytes: bytes,
    *,
    manifest: dict[str, Any] | None = None,
    allow_previous: bool = False,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Validate manifest bytes before any manifest-declared artifact is opened."""
    decoded = _canonical_object(manifest_bytes, where="Feed manifest")
    if manifest is not None and decoded != manifest:
        raise BundleError("provided manifest differs from manifest bytes")
    manifest = decoded
    try:
        validate_against(MANIFEST_SCHEMA_FILENAME, manifest)
    except SchemaError as exc:
        raise BundleError(str(exc)) from exc
    if manifest.get("schema_version") not in (*SUPPORTED_BUNDLE_MAJORS, *MIGRATABLE_BUNDLE_MAJORS):
        raise BundleError("unsupported Feed manifest schema version")
    if manifest.get("schema_version") == PREVIOUS_BUNDLE_MAJOR and not allow_previous:
        raise BundleError("previous eight-domain Feed bundle requires bounded migration")
    if manifest["window"]["end"] != manifest["evidence_cutoff_at"]:
        raise BundleError("manifest window.end must equal evidence_cutoff_at")
    return manifest, _validated_inventory_paths(manifest, allow_previous=allow_previous)


def _validate_inventory(
    manifest: dict[str, Any], root: Path, paths: tuple[str, ...]
) -> list[tuple[str, Path, dict[str, Any]]]:
    result: list[tuple[str, Path, dict[str, Any]]] = []
    for entry, relative in zip(manifest["artifacts"], paths, strict=True):
        domain = entry["domain"]
        expected = _artifact_relative_path_for_version(
            domain, manifest["run_id"], int(manifest["schema_version"])
        )
        path = _safe_artifact_path(root, relative, expected)
        result.append((domain, path, entry))
    return result


def validate_bundle(
    product_root: Path,
    *,
    manifest: dict[str, Any] | None = None,
    manifest_bytes: bytes | None = None,
    allow_previous: bool = False,
) -> dict[str, Any]:
    """Validate a complete bundle and return its reconstructed logical Feed."""
    root = Path(product_root)
    path = root / MANIFEST_FILENAME
    if manifest_bytes is None:
        try:
            manifest_bytes = path.read_bytes()
        except OSError as exc:
            raise BundleError(f"cannot read Feed manifest: {path}") from exc
    manifest, paths = validate_manifest_and_inventory(
        manifest_bytes, manifest=manifest, allow_previous=allow_previous
    )
    entries = _validate_inventory(manifest, root, paths)
    all_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for domain, artifact_path_value, inventory_entry in entries:
        try:
            data = artifact_path_value.read_bytes()
        except OSError as exc:
            raise BundleError(f"cannot read Feed artifact {artifact_path_value.name}") from exc
        if len(data) != inventory_entry["size_bytes"]:
            raise BundleError(f"Feed artifact {domain} byte size does not match manifest")
        if canonical_sha256(data) != inventory_entry["sha256"]:
            raise BundleError(f"Feed artifact {domain} SHA-256 does not match manifest")
        artifact = _canonical_object(data, where=f"Feed artifact {domain}")
        try:
            validate_against(ARTIFACT_SCHEMA_FILENAME, artifact)
        except SchemaError as exc:
            raise BundleError(str(exc)) from exc
        expected_artifact_major = (
            PREVIOUS_ARTIFACT_MAJOR
            if manifest["schema_version"] == PREVIOUS_BUNDLE_MAJOR
            else SUPPORTED_ARTIFACT_MAJOR
        )
        if (
            artifact.get("schema_version") != expected_artifact_major
            or artifact.get("run_id") != manifest["run_id"]
            or artifact.get("domain") != domain
        ):
            raise BundleError(f"Feed artifact {domain} binding does not match manifest")
        items = artifact.get("items")
        if not isinstance(items, list) or len(items) != inventory_entry["item_count"]:
            raise BundleError(f"Feed artifact {domain} item count does not match manifest")
        if items != deterministic_item_order(items):
            raise BundleError(f"Feed artifact {domain} items are not deterministically ordered")
        for item in items:
            item_id = item.get("id")
            if item_id in seen_ids:
                raise BundleError(f"Feed item occurs more than once: {item_id}")
            seen_ids.add(item_id)
        all_items.extend(items)

    all_items = sorted(all_items, key=item_total_order_key)
    feed = reconstruct_feed(manifest, all_items)
    try:
        validate_feed(feed, allow_previous=allow_previous)
        assert_feed_identity(feed)
    except (SchemaError, TypeError, ValueError) as exc:
        raise BundleError(f"reconstructed Feed is invalid: {exc}") from exc
    return feed


def load_feed(product_root: Path, *, domain: str | None = None) -> dict[str, Any]:
    """Load the manifest-led current five-domain Feed."""
    root = Path(product_root)
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise BundleError("current Feed manifest is missing")
    feed = validate_bundle(root)
    if feed.get("pipeline", {}).get("status") == "failure":
        raise BundleError("pipeline.status=failure: Feed is not consumable")
    if domain is not None:
        if domain not in DOMAINS:
            raise BundleError(f"unsupported Feed domain: {domain!r}")
        feed = dict(feed)
        feed["items"] = [item for item in feed["items"] if item["payload"]["type"] == domain]
    return feed


def migrate_feed(
    feed: Mapping[str, Any],
    *,
    target_feed_config: Mapping[str, Any],
    target_provider_contracts: Sequence[Mapping[str, Any]],
    target_feed_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert one fully validated v3 eight-domain Feed into a v4 candidate.

    Migration is deliberately bounded: the caller supplies the current
    Feed-owned configuration, Provider contracts, and schema descriptor. The
    old candidate is validated before any projection, removed-domain items
    and providers are discarded, and the new identity is recomputed by the
    caller/build path rather than copied from the old generation.
    """
    if feed.get("schema_version") != PREVIOUS_BUNDLE_MAJOR:
        raise BundleError("only the previous eight-domain Feed major is migratable")
    try:
        validate_feed(feed, allow_previous=True)
        assert_feed_identity(feed)
    except (SchemaError, TypeError, ValueError) as exc:
        raise BundleError(f"previous Feed is invalid: {exc}") from exc

    required_provider_ids = {
        "federal_reserve",
        "bls",
        "pboc",
        "nbs",
        "sse",
        "szse",
        "sec_edgar",
        "cftc",
    }
    contracts = [deepcopy(dict(entry)) for entry in target_provider_contracts]
    provider_ids = [entry.get("provider_id") for entry in contracts]
    if any(not isinstance(provider_id, str) for provider_id in provider_ids):
        raise BundleError("target Provider contract identity is invalid")
    typed_provider_ids = [
        provider_id for provider_id in provider_ids if isinstance(provider_id, str)
    ]
    if typed_provider_ids != sorted(typed_provider_ids):
        raise BundleError("target Provider contracts must be ordered by provider_id")
    if set(typed_provider_ids) != required_provider_ids:
        raise BundleError(
            "target Provider contracts must contain exactly the eight required Providers"
        )
    for entry in contracts:
        provider_id = entry.get("provider_id")
        snapshot = entry.get("snapshot")
        if not isinstance(provider_id, str) or not isinstance(snapshot, Mapping):
            raise BundleError("target Provider contract is invalid")
        if snapshot.get("provider_id") != provider_id:
            raise BundleError("target Provider contract identity is invalid")
        payload_types = snapshot.get("payload_types")
        if (
            not isinstance(payload_types, list)
            or not payload_types
            or any(payload not in DOMAINS for payload in payload_types)
        ):
            raise BundleError("target Provider contract payload types are invalid")
        if entry.get("hash") != canonical_sha256(canonical_bytes(snapshot)):
            raise BundleError("target Provider contract hash is invalid")

    config = deepcopy(dict(target_feed_config))
    snapshot = config.get("snapshot")
    if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("coverage"), list):
        raise BundleError("target Feed configuration must contain a coverage snapshot")
    coverage_groups: dict[str, tuple[str, ...]] = {}
    for row in snapshot["coverage"]:
        if not isinstance(row, Mapping) or not isinstance(row.get("group"), str):
            raise BundleError("target Feed coverage snapshot is invalid")
        members = row.get("members")
        if not isinstance(members, list) or any(not isinstance(member, str) for member in members):
            raise BundleError("target Feed coverage members are invalid")
        for provider_id in members:
            coverage_groups.setdefault(provider_id, ())
            coverage_groups[provider_id] = tuple(
                sorted((*coverage_groups[provider_id], row["group"]))
            )
    if set(coverage_groups) != required_provider_ids:
        raise BundleError("target Feed coverage must include exactly the eight required Providers")

    target_hashes = {entry["provider_id"]: entry["hash"] for entry in contracts}
    target_contracts = {entry["provider_id"]: entry["snapshot"] for entry in contracts}
    retained_items: list[Mapping[str, Any]] = []
    for raw_item in feed.get("items", []):
        item = deepcopy(dict(raw_item))
        payload = item.get("payload")
        provider_id = item.get("provider_id")
        if not isinstance(payload, Mapping) or payload.get("type") not in DOMAINS:
            continue
        if provider_id not in required_provider_ids:
            raise BundleError("retained Feed evidence belongs to a removed Provider")
        if payload.get("type") not in target_contracts[provider_id].get("payload_types", ()):
            raise BundleError("retained Feed evidence is outside its target Provider contract")
        lineage = item.get("source_lineage")
        if isinstance(lineage, list):
            item["source_lineage"] = [
                record
                for record in lineage
                if isinstance(record, Mapping)
                and record.get("provider_id") in required_provider_ids
            ]
            if not item["source_lineage"]:
                item.pop("source_lineage", None)
        retained_items.append(item)
    retained_items = deterministic_item_order(retained_items)

    old_outcomes = {
        outcome.get("provider_id"): deepcopy(dict(outcome))
        for outcome in feed.get("provider_outcomes", [])
        if isinstance(outcome, Mapping)
    }
    old_provider_ids = set(old_outcomes)
    if not required_provider_ids.issubset(old_provider_ids) or not old_provider_ids.issubset(
        required_provider_ids | {"yahoo_market"}
    ):
        raise BundleError("previous Feed outcomes contain an unsupported Provider generation")
    outcomes: list[dict[str, Any]] = []
    complete_ids: set[str] = set()
    blocked_ids: set[str] = set()
    incomplete_ids: set[str] = set()
    for provider_id in sorted(required_provider_ids):
        outcome = old_outcomes[provider_id]
        outcome["affected_coverage_groups"] = list(coverage_groups.get(provider_id, ()))
        freshness = outcome.get("freshness")
        if isinstance(freshness, Mapping):
            freshness = dict(freshness)
            if freshness.get("status") in {"fresh", "valid_unchanged", "stale"}:
                freshness["origin_contract_hash"] = target_hashes[provider_id]
            outcome["freshness"] = freshness
        if (
            outcome.get("availability") == "blocked"
            and outcome.get("upstream_http_status") in {401, 403}
            and outcome.get("state") == "failed"
            and outcome.get("accepted") == 0
            and outcome.get("rejected") == 0
        ):
            blocked_ids.add(provider_id)
        elif outcome.get("state") == "healthy" or (
            outcome.get("state") == "empty"
            and target_contracts[provider_id].get("empty_valid_for_window") is True
        ):
            complete_ids.add(provider_id)
        else:
            incomplete_ids.add(provider_id)
        outcomes.append(outcome)

    coverage_rows = snapshot["coverage"]
    deficient_groups: set[str] = set()
    for row in coverage_rows:
        if not isinstance(row, Mapping):
            raise BundleError("target Feed coverage snapshot is invalid")
        members = row.get("members")
        minimum = row.get("minimum")
        optional = row.get("optional")
        if (
            not isinstance(members, list)
            or any(not isinstance(member, str) for member in members)
            or isinstance(minimum, bool)
            or not isinstance(minimum, int)
            or not isinstance(optional, bool)
        ):
            raise BundleError("target Feed coverage snapshot is invalid")
        effective_minimum = max(0, minimum - sum(member in blocked_ids for member in members))
        complete_count = sum(member in complete_ids for member in members)
        if not optional and complete_count < effective_minimum:
            deficient_groups.add(str(row.get("group")))

    migrated = deepcopy(dict(feed))
    migrated["schema_version"] = SUPPORTED_BUNDLE_MAJOR
    migrated["feed_config"] = config
    migrated["feed_schema"] = deepcopy(
        dict(target_feed_schema)
        if target_feed_schema is not None
        else _schema_descriptor("feed.schema.json")
    )
    migrated["provider_contracts"] = contracts
    migrated["provider_outcomes"] = outcomes
    migrated["items"] = retained_items
    migrated.pop("calendar_horizon_end", None)
    # Warnings are execution reporting, not evidence. Do not carry messages
    # that describe discarded providers or domains into the new product.
    migrated["pipeline"] = {
        "status": (
            "failure"
            if incomplete_ids or deficient_groups
            else "degraded"
            if blocked_ids
            else "healthy"
        ),
        "warnings": [],
        "coverage_gap": feed["pipeline"].get("coverage_gap"),
    }
    migrated["content_digest"] = "0" * 64
    migrated["run_id"] = ""
    digest, run_id = recompute_feed_identity(migrated)
    migrated["content_digest"] = digest
    migrated["run_id"] = run_id
    try:
        validate_feed(migrated)
        assert_feed_identity(migrated)
    except (SchemaError, TypeError, ValueError) as exc:
        raise BundleError(f"migrated five-domain Feed is invalid: {exc}") from exc
    return migrated


def migrate_previous_bundle(
    product_root: Path,
    *,
    target_feed_config: Mapping[str, Any],
    target_provider_contracts: Sequence[Mapping[str, Any]],
    target_feed_schema: Mapping[str, Any] | None = None,
) -> FeedBundle:
    """Read one previous bundle and return a validated five-domain candidate."""
    root = Path(product_root)
    previous = validate_bundle(root, allow_previous=True)
    migrated = migrate_feed(
        previous,
        target_feed_config=target_feed_config,
        target_provider_contracts=target_provider_contracts,
        target_feed_schema=target_feed_schema,
    )
    return build_bundle(migrated)


# Compatibility spelling for callers that treat this as a parser operation.
validate_feed_bundle = validate_bundle


def bundle_inventory(bundle: FeedBundle) -> tuple[Path, ...]:
    """Return manifest plus its exact active artifact paths."""
    root = Path(".")
    return (root / MANIFEST_FILENAME,) + tuple(
        root / artifact_relative_path(domain, bundle.run_id) for domain in DOMAINS
    )


def recompute_bundle_identity(feed: dict[str, Any]) -> tuple[str, str]:
    """Explicit alias documenting that layout does not alter logical identity."""
    return recompute_feed_identity(feed)
