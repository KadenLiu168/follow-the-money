"""Repository boundary: application-build fingerprinting.

Design section 10:

- The mandatory application-build fingerprint works without Git: SHA-256 over
  a closed, sorted path/size/file-SHA-256 manifest of ``src/follow_the_money/``,
  thin runtime scripts, ``pyproject.toml``, and ``uv.lock``, plus the package
  version. Git SHA/dirty flag is supplementary only.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_digest

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
