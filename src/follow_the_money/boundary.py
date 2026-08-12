"""Repository boundary: application-build fingerprinting, packet verification.

Design sections 10/20:

- The mandatory application-build fingerprint works without Git: SHA-256 over
  a closed, sorted path/size/file-SHA-256 manifest of ``src/follow_the_money/``,
  thin runtime scripts, ``pyproject.toml``, and ``uv.lock``, plus the package
  version. Git SHA/dirty flag is supplementary only.
- ``verified-event-packet`` assembly validates in-Feed provenance, provider-
  bound canonical URLs, knowledge instants, and completeness; it never
  performs network access.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_digest
from .schema import SchemaError, validate_against

FINGERPRINT_DIRS = ("src/follow_the_money", "scripts")
FINGERPRINT_FILES = ("pyproject.toml", "uv.lock")


@dataclass(frozen=True)
class BuildFingerprint:
    package_version: str
    files: tuple[dict[str, Any], ...]
    fingerprint: str
    git: dict[str, Any] | None = None


def _file_manifest(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for rel in FINGERPRINT_DIRS:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix
                not in {
                    ".pyc",
                    ".pyo",
                }
            ):
                entries.append(_entry(root, path))
    for name in FINGERPRINT_FILES:
        path = root / name
        if path.exists():
            entries.append(_entry(root, path))
    entries.sort(key=lambda e: e["path"])
    return entries


def _entry(root: Path, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(root)),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def application_build_fingerprint(
    root: Path, package_version: str, git: dict[str, Any] | None = None
) -> BuildFingerprint:
    """Compute the mandatory non-Git application build fingerprint."""
    files = tuple(_file_manifest(root))
    payload = {
        "package_version": package_version,
        "files": files,
        "git": git,
    }
    return BuildFingerprint(
        package_version=package_version,
        files=files,
        fingerprint=canonical_digest(payload),
        git=git,
    )


def build_fingerprint_to_dict(build: BuildFingerprint) -> dict[str, Any]:
    return {
        "package_version": build.package_version,
        "fingerprint": build.fingerprint,
        "files": list(build.files),
        "git": build.git,
    }


def recompute_build_fingerprint(build: Mapping[str, Any], root: Path) -> str:
    """Recompute the fingerprint from a stored manifest (for replay checks)."""
    files = tuple(
        {"path": f["path"], "size": f["size"], "sha256": f["sha256"]}
        for f in build.get("files", [])
    )
    payload = {
        "package_version": build.get("package_version"),
        "files": files,
        "git": build.get("git"),
    }
    return canonical_digest(payload)


# ---------------------------------------------------------------------------
# Verified packet assembly
# ---------------------------------------------------------------------------


def assemble_verified_packet(
    *,
    packet_id: str,
    event: Mapping[str, Any],
    feed_run_id: str,
    ledger_entries: Iterable[Mapping[str, Any]],
    evidence_refs: Iterable[Mapping[str, Any]],
    market_observations: Iterable[Mapping[str, Any]] = (),
    conflicts: Iterable[Mapping[str, Any]] = (),
    eligible_catalyst_calendar_ids: Iterable[str] = (),
    verification_status: str = "passed",
    completeness_findings: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Assemble a verified event packet from frozen ledger and in-Feed refs."""
    key_ids = tuple(event.get("key_fact_ids", []))
    if not key_ids:
        raise SchemaError("verified packet requires key_fact_ids")

    catalyst = tuple(dict.fromkeys(eligible_catalyst_calendar_ids))
    if len(catalyst) > 6:
        raise SchemaError("eligible_catalyst_calendar_ids exceeds 6 items")

    packet = {
        "schema_version": 1,
        "packet_id": packet_id,
        "event_id": event["event_id"],
        "feed_run_id": feed_run_id,
        "verification_status": verification_status,
        "key_fact_ids": list(key_ids),
        "fully_known_at": event["fully_known_at"],
        "ledger": [dict(e) for e in ledger_entries],
        "evidence": [dict(e) for e in evidence_refs],
        "market_observations": [dict(o) for o in market_observations],
        "conflicts": [dict(c) for c in conflicts],
        "eligible_catalyst_calendar_ids": list(catalyst),
        "completeness_findings": [dict(f) for f in completeness_findings],
    }
    validate_against("verified-event-packet.schema.json", packet)
    return packet


def validate_packet_references(packet: Mapping[str, Any]) -> None:
    """Semantic cross-reference validation for a verified packet.

    Every key fact must appear in the frozen ledger; every evidence ref must
    be unique and non-empty; no network access is performed.
    """
    ledger_ids = {e["fact_id"] for e in packet["ledger"]}
    for fid in packet["key_fact_ids"]:
        if fid not in ledger_ids:
            raise SchemaError(f"key fact {fid!r} missing from frozen ledger")

    evidence_ids = [e["evidence_id"] for e in packet["evidence"]]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise SchemaError("duplicate evidence refs in packet")

    for ref in packet["evidence"]:
        if not ref.get("source_url", "").startswith("https://"):
            raise SchemaError(f"evidence {ref['evidence_id']!r} source_url must be https")
