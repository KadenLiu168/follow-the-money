"""Classify a push as an exact, manifest-validated generated-state update."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from follow_the_money.feed.bundle import MANIFEST_FILENAME, BundleError, validate_bundle

RUNTIME_FILES = {
    ".feed-state/.follow-the-money-persistent",
    ".feed-state/feed-checkpoint.json",
    ".feed-state/rate-registry.json",
    ".feed-state/feed-run-lease.json",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _manifest_paths(raw: bytes | None) -> set[str]:
    if raw is None:
        return set()
    try:
        manifest = json.loads(raw)
        return {entry["path"] for entry in manifest["artifacts"]} | {MANIFEST_FILENAME}
    except (KeyError, TypeError, ValueError):
        return set()


def _scope_paths(raw: bytes | None) -> set[str]:
    if raw is None:
        return set()
    try:
        scopes = json.loads(raw).get("scopes", {})
        return {
            ".feed-state/scope-"
            + hashlib.sha256(scope_id.encode("utf-8")).hexdigest()[:16]
            + ".json"
            for scope_id in scopes
            if isinstance(scope_id, str)
        }
    except (AttributeError, TypeError, ValueError):
        return set()


def generated_state_only(repo: Path, *, head: str = "HEAD", base: str | None = None) -> bool:
    repo = Path(repo)
    if base is None:
        try:
            base = f"{head}^"
            _git(repo, "rev-parse", base)
        except (subprocess.CalledProcessError, OSError):
            return False
    changed = {line for line in _git(repo, "diff", "--name-only", base, head).splitlines() if line}
    if not changed:
        return False

    current_manifest = repo / "feeds" / MANIFEST_FILENAME
    current_paths: set[str] = set()
    if current_manifest.is_file():
        try:
            validate_bundle(repo / "feeds")
        except (BundleError, OSError, TypeError, ValueError):
            return False
        try:
            json.loads(current_manifest.read_text(encoding="utf-8"))
            current_paths = {
                "feeds/" + name for name in _manifest_paths(current_manifest.read_bytes())
            }
        except (OSError, ValueError):
            return False

    previous_paths = set()
    try:
        previous_manifest = _git(repo, "show", f"{base}:feeds/{MANIFEST_FILENAME}").encode()
        previous_paths = {"feeds/" + name for name in _manifest_paths(previous_manifest)}
    except subprocess.CalledProcessError:
        pass
    try:
        previous_registry = _git(repo, "show", f"{base}:.feed-state/rate-registry.json").encode()
    except subprocess.CalledProcessError:
        previous_registry = None
    current_registry = None
    registry_path = repo / ".feed-state" / "rate-registry.json"
    if registry_path.is_file():
        try:
            current_registry = registry_path.read_bytes()
        except OSError:
            return False
    allowed = set(RUNTIME_FILES) | _scope_paths(current_registry) | _scope_paths(previous_registry)
    allowed |= {
        path
        for path in current_paths | previous_paths
        if path == "feeds/feed-manifest.json" or path.startswith("feeds/feed-")
    }
    # Migration is the only accepted legacy deletion, and only alongside a
    # now-valid active manifest.
    if (
        current_paths
        and "feeds/latest.json" in changed
        and not (repo / "feeds" / "latest.json").exists()
    ):
        try:
            _git(repo, "cat-file", "-e", f"{base}:feeds/latest.json")
        except subprocess.CalledProcessError:
            pass
        else:
            allowed.add("feeds/latest.json")
    return changed.issubset(allowed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--base", default=None)
    args = parser.parse_args()
    try:
        result = generated_state_only(Path(args.repo), head=args.head, base=args.base)
    except (OSError, subprocess.CalledProcessError):
        result = False
    print("true" if result else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
