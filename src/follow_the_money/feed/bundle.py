"""Typed Feed bundle model, validation, and manifest-first loading."""

from __future__ import annotations

import hashlib
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
    "market_data",
    "flow",
    "positioning",
    "filing",
    "calendar",
)
SUPPORTED_BUNDLE_MAJOR = 2
SUPPORTED_BUNDLE_MAJORS = (1, 2)
SUPPORTED_ARTIFACT_MAJOR = 1
MANIFEST_FILENAME = "feed-manifest.json"
LEGACY_FILENAME = "latest.json"
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


def _safe_artifact_path(root: Path, relative: object, expected: str) -> Path:
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
    candidate = (root / candidate_rel).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise BundleError("artifact path escapes Feed product root")
    if not candidate.is_file():
        raise BundleError(f"missing Feed artifact: {relative}")
    return candidate


def _validate_inventory(
    manifest: dict[str, Any], root: Path
) -> list[tuple[str, Path, dict[str, Any]]]:
    inventory = manifest.get("artifacts")
    if not isinstance(inventory, list) or len(inventory) != len(DOMAINS):
        raise BundleError("Feed manifest inventory must contain the exact fixed domain order")
    if any(not isinstance(entry, dict) for entry in inventory):
        raise BundleError("Feed manifest artifact inventory entry is invalid")
    if [entry.get("domain") for entry in inventory] != list(DOMAINS):
        raise BundleError("Feed manifest inventory must contain the exact fixed domain order")
    result: list[tuple[str, Path, dict[str, Any]]] = []
    seen: set[str] = set()
    for entry in inventory:
        domain = entry.get("domain")
        if domain in seen:
            raise BundleError(f"duplicate Feed artifact domain: {domain}")
        seen.add(domain)
        expected = artifact_relative_path(domain, manifest["run_id"])
        path = _safe_artifact_path(root, entry.get("path"), expected)
        result.append((domain, path, entry))
    if seen != set(DOMAINS):
        raise BundleError("Feed manifest inventory is incomplete")
    return result


def validate_bundle(
    product_root: Path,
    *,
    manifest: dict[str, Any] | None = None,
    manifest_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Validate a complete bundle and return its reconstructed logical Feed."""
    root = Path(product_root)
    path = root / MANIFEST_FILENAME
    if manifest_bytes is None:
        try:
            manifest_bytes = path.read_bytes()
        except OSError as exc:
            raise BundleError(f"cannot read Feed manifest: {path}") from exc
    decoded = _canonical_object(manifest_bytes, where="Feed manifest")
    if manifest is not None and decoded != manifest:
        raise BundleError("provided manifest differs from manifest bytes")
    manifest = decoded
    try:
        validate_against(MANIFEST_SCHEMA_FILENAME, manifest)
    except SchemaError as exc:
        raise BundleError(str(exc)) from exc
    if manifest.get("schema_version") not in SUPPORTED_BUNDLE_MAJORS:
        raise BundleError("unsupported Feed manifest schema version")
    if manifest["window"]["end"] != manifest["evidence_cutoff_at"]:
        raise BundleError("manifest window.end must equal evidence_cutoff_at")

    entries = _validate_inventory(manifest, root)
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
        if (
            artifact.get("schema_version") != SUPPORTED_ARTIFACT_MAJOR
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
        validate_feed(feed)
        assert_feed_identity(feed)
    except (SchemaError, TypeError, ValueError) as exc:
        raise BundleError(f"reconstructed Feed is invalid: {exc}") from exc
    return feed


def load_feed(product_root: Path, *, domain: str | None = None) -> dict[str, Any]:
    """Load manifest-first, with legacy fallback only when no manifest exists."""
    root = Path(product_root)
    manifest_path = root / MANIFEST_FILENAME
    if manifest_path.exists():
        feed = validate_bundle(root)
    else:
        legacy_path = root / LEGACY_FILENAME
        try:
            feed = _canonical_object(legacy_path.read_bytes(), where="legacy latest.json")
            validate_feed(feed)
            assert_feed_identity(feed)
        except Exception as exc:
            raise BundleError(f"invalid legacy Feed: {exc}") from exc
    if feed.get("pipeline", {}).get("status") == "failure":
        raise BundleError("pipeline.status=failure: Feed is not consumable")
    if domain is not None:
        if domain not in DOMAINS:
            raise BundleError(f"unsupported Feed domain: {domain!r}")
        feed = dict(feed)
        feed["items"] = [item for item in feed["items"] if item["payload"]["type"] == domain]
    return feed


# Compatibility spellings for callers that treat this as a parser operation.
validate_feed_bundle = validate_bundle
load_latest_or_bundle = load_feed


def bundle_inventory(bundle: FeedBundle) -> tuple[Path, ...]:
    """Return manifest plus its exact active artifact paths."""
    root = Path(".")
    return (root / MANIFEST_FILENAME,) + tuple(
        root / artifact_relative_path(domain, bundle.run_id) for domain in DOMAINS
    )


def recompute_bundle_identity(feed: dict[str, Any]) -> tuple[str, str]:
    """Explicit alias documenting that layout does not alter logical identity."""
    return recompute_feed_identity(feed)
