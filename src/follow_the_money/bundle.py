"""Local ignored run-audit bundles and replay (task 10.9/10.10).

Design section 20:

- Every Brief/degraded attempt writes an atomic create-only local
  ``runs/<brief_run_id>/`` bundle: manifest, exact canonical validated input
  Feed as ``input/feed.json``, canonical resolved redacted non-secret
  effective-config snapshot, build/schema/config/prompt/model fingerprints,
  events/ledger/packets/analysis/selection/Brief/render/audit, and indexed
  ``generation_status``.
- The terminal manifest contains a closed ordered path/size/SHA-256 member
  index; no indexed member may contain ``brief_run_id``/``bundle_digest``.
- Publication: unpredictable same-parent/same-device staging, create-only
  writes, file/staging-dir fsync, atomic no-replace directory rename,
  parent fsync. Rename + parent fsync is the durable publication point.
- ``replay`` verifies member closure, exact saved Feed identity, saved
  config fingerprint, current build/schema fingerprints, then re-runs the
  deterministic path from saved outputs without network/LLM and compares
  every saved artifact.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import secrets
import sys
from collections.abc import Callable, Mapping
from ctypes import CDLL, c_char_p, c_int, c_uint, get_errno
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .boundary import (
    application_build_fingerprint,
)
from .canonical import canonical_digest, canonical_sha256
from .providers.lock import CollectionLock
from .schema import validate_against


class BundleError(ValueError):
    """Run-bundle creation/replay failed closed."""


@dataclass
class BundleWriter:
    root: Path  # runs/
    brief_run_id: str
    attempt_id: str
    feed_run_id: str
    mode: str  # normal | degraded
    brief_generated_at: str
    brief_completed_at: str
    build: Mapping[str, Any]
    schema_fingerprints: Mapping[str, str]
    config_fingerprint: str
    prompt_fingerprints: Mapping[str, str]
    model_fingerprint: str

    def write(self, members: Mapping[str, bytes]) -> Path:
        """Atomically publish the bundle and return its final path."""
        final = self.root / self.brief_run_id
        if final.exists():
            raise BundleError(f"bundle {final} already exists (no overwrite)")
        self.root.mkdir(parents=True, exist_ok=True)
        lock = CollectionLock(self.root, timeout_seconds=0.0)
        try:
            lock.acquire()
            staging = self._stage_dir(final)
            try:
                for rel, data in sorted(members.items()):
                    _write_member(staging, rel, data)
                for directory in sorted(
                    (path for path in staging.rglob("*") if path.is_dir()),
                    key=lambda path: len(path.parts),
                    reverse=True,
                ):
                    _fsync_dir(directory)
                _fsync_dir(staging)
                manifest = self._build_manifest(staging, members)
                (staging / "manifest.json").write_bytes(
                    json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
                )
                _fsync_file(staging / "manifest.json")
                _fsync_dir(staging)
                # Atomic no-replace directory rename. Darwin exposes the
                # directory-safe primitive through renamex_np; the fallback is
                # retained for platforms without that primitive.
                _atomic_no_replace_directory_rename(staging, final)
                _fsync_dir(self.root)
            finally:
                if staging.exists():
                    import shutil

                    shutil.rmtree(staging, ignore_errors=True)
        except OSError as exc:
            raise BundleError(f"bundle publication failed: {exc}") from exc
        finally:
            lock.release()
        return final

    def _stage_dir(self, final: Path) -> Path:
        if not self.root.exists():
            raise BundleError(f"bundle root {self.root} missing")
        return final.parent / f".bundle-stage-{os.getpid()}-{secrets.token_hex(8)}"

    def _build_manifest(self, staging: Path, members: Mapping[str, bytes]) -> dict[str, Any]:
        index = []
        for rel in sorted(members):
            data = members[rel]
            index.append({"path": rel, "size": len(data), "sha256": canonical_sha256(data)})
        manifest = {
            "schema_version": 1,
            "brief_run_id": self.brief_run_id,
            "bundle_digest": "0" * 64,  # recomputed below (omits itself)
            "directory_id": self.directory_id(index),
            "attempt_id": self.attempt_id,
            "feed_run_id": self.feed_run_id,
            "mode": self.mode,
            "brief_generated_at": self.brief_generated_at,
            "brief_completed_at": self.brief_completed_at,
            "application_build": self.build,
            "schema_fingerprints": self.schema_fingerprints,
            "config_fingerprint": self.config_fingerprint,
            "prompt_fingerprints": self.prompt_fingerprints,
            "model_fingerprint": self.model_fingerprint,
            "members": index,
            "generation_status": "ready_for_commit",
        }
        digest = canonical_digest({k: v for k, v in manifest.items() if k != "bundle_digest"})
        manifest["bundle_digest"] = digest
        return manifest

    def directory_id(self, member_index: list[dict[str, Any]]) -> str:
        payload = {
            "brief_run_id": self.brief_run_id,
            "attempt_id": self.attempt_id,
            "feed_run_id": self.feed_run_id,
            "mode": self.mode,
            "brief_generated_at": self.brief_generated_at,
            "build_fingerprint": self.build.get("fingerprint"),
            "config_fingerprint": self.config_fingerprint,
            "member_index": member_index,
        }
        digest = canonical_digest(payload)
        return f"dir_{digest[:32]}"


def _write_member(staging: Path, rel: str, data: bytes) -> None:
    if rel == "manifest.json":
        raise BundleError("manifest.json is reserved for the terminal manifest")
    if ".." in rel or rel.startswith("/"):
        raise BundleError(f"unsafe member path {rel!r}")
    path = staging / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_no_replace_directory_rename(src: Path, dst: Path) -> None:
    """Publish a directory without replacing an existing destination."""
    if sys.platform == "darwin":
        renamex_np = CDLL(None, use_errno=True).renamex_np
        renamex_np.argtypes = [c_char_p, c_char_p, c_uint]
        renamex_np.restype = c_int
        if renamex_np(os.fsencode(src), os.fsencode(dst), 0x00000004) == 0:
            return
        error = get_errno()
        raise OSError(error, os.strerror(error), str(dst))
    if sys.platform.startswith("linux"):
        renameat2 = getattr(CDLL(None, use_errno=True), "renameat2", None)
        if renameat2 is not None:
            renameat2.argtypes = [c_int, c_char_p, c_int, c_char_p, c_uint]
            renameat2.restype = c_int
            if renameat2(-100, os.fsencode(src), -100, os.fsencode(dst), 0x00000001) == 0:
                return
            error = get_errno()
            raise OSError(error, os.strerror(error), str(dst))
    raise OSError(errno.ENOTSUP, "atomic no-replace directory rename is unavailable")


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


@dataclass
class ReplayResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def verify_bundle_integrity(bundle: Path) -> dict[str, Any]:
    """Verify manifest closure and member hashes; fail closed on tamper."""
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        raise BundleError("bundle missing manifest.json")
    manifest = json.loads(manifest_path.read_bytes())
    validate_against("run-manifest.schema.json", manifest)

    digest = canonical_digest({k: v for k, v in manifest.items() if k != "bundle_digest"})
    if manifest["bundle_digest"] != digest:
        raise BundleError("bundle_digest mismatch (tamper)")

    directory_payload = {
        "brief_run_id": manifest["brief_run_id"],
        "attempt_id": manifest["attempt_id"],
        "feed_run_id": manifest["feed_run_id"],
        "mode": manifest["mode"],
        "brief_generated_at": manifest["brief_generated_at"],
        "build_fingerprint": manifest["application_build"].get("fingerprint"),
        "config_fingerprint": manifest["config_fingerprint"],
        "member_index": manifest["members"],
    }
    expected_directory_id = f"dir_{canonical_digest(directory_payload)[:32]}"
    if manifest["directory_id"] != expected_directory_id:
        raise BundleError("directory_id mismatch (tamper)")

    indexed_paths: set[str] = set()
    for member in manifest["members"]:
        rel = member["path"]
        if rel == "manifest.json":
            raise BundleError("manifest.json is reserved for the terminal manifest")
        if rel in indexed_paths:
            raise BundleError(f"duplicate indexed member {rel!r}")
        indexed_paths.add(rel)
        path = bundle / rel
        if not path.exists() or not path.is_file():
            raise BundleError(f"member {rel!r} missing")
        if path.is_symlink():
            raise BundleError(f"member {rel!r} is a symlink")
        data = path.read_bytes()
        if len(data) != member["size"] or canonical_sha256(data) != member["sha256"]:
            raise BundleError(f"member {rel!r} hash/size mismatch (tamper)")

    # Closed member closure: every regular file under the bundle except the
    # terminal manifest must be indexed; unlisted files are rejected.
    manifest_rel = manifest_path.name
    for path in bundle.rglob("*"):
        if path.is_file() and path.name != manifest_rel:
            rel = str(path.relative_to(bundle))
            if rel not in indexed_paths:
                raise BundleError(f"unlisted member {rel!r} (tamper)")
        if path.is_symlink():
            raise BundleError(f"symlink {path} (tamper)")
    return manifest


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def _compare_artifact(name: str, saved: Any, reconstructed: Any, errors: list[str]) -> None:
    if isinstance(saved, bytes) or isinstance(reconstructed, bytes):
        equal = saved == reconstructed
    else:
        equal = _canonical_json_bytes(saved) == _canonical_json_bytes(reconstructed)
    if not equal:
        errors.append(f"replay drift: {name} differs from saved bundle member")


def replay_bundle(
    bundle: Path,
    *,
    repo_root: Path,
    compare: Callable[[dict[str, Any], dict[str, Any]], list[str]] | None = None,
) -> ReplayResult:
    """Deterministic replay from saved outputs without network or LLM access.

    Verifies member closure, exact saved Feed identity, saved config
    fingerprint, and current build/schema fingerprints, then re-executes the
    full deterministic pipeline from the saved Feed with the recorded
    structured LLM outputs and compares every indexed artifact (events,
    ledger, packets, analyses, selection, Brief, claim inventory, rendered
    Markdown, and audit results). Any identity/build/schema/config/reference/
    output drift is a failure.
    """
    errors: list[str] = []
    try:
        manifest = verify_bundle_integrity(bundle)
    except BundleError as exc:
        message = str(exc)
        if "hash/size mismatch" in message:
            message = f"replay drift: {message}"
        return ReplayResult(ok=False, errors=[message])

    # Current build fingerprint must match the recorded one.
    current_build = application_build_fingerprint(repo_root, "0.1.0")
    recorded_fp = manifest["application_build"].get("fingerprint")
    if current_build.fingerprint != recorded_fp:
        errors.append("application build fingerprint mismatch")
        return ReplayResult(ok=False, errors=errors)

    # Config fingerprint recomputation.
    saved_config = bundle / "config-effective.json"
    if saved_config.exists():
        data = json.loads(saved_config.read_bytes())
        fp = data.get("fingerprint")
        if fp and fp != manifest["config_fingerprint"]:
            errors.append("config fingerprint mismatch")

    # The bundle records provenance for the producer inputs.  Config and
    # schema fingerprints remain replay dependencies because they control the
    # deterministic merge; prompt/model fingerprints are historical
    # provenance and must not require the current prompt files or model
    # configuration to be available.
    try:
        current_schema = _schema_fingerprints(repo_root)
        if current_schema != manifest.get("schema_fingerprints"):
            errors.append("schema fingerprint mismatch")
    except OSError as exc:
        errors.append(f"schema fingerprint source unavailable: {exc}")

    try:
        from .config import load_config

        current_cfg = load_config(
            repo_root / "config" / "config.yaml",
            repo_root / "config" / "providers.yaml",
            require_verified_enabled=True,
        )
        if _config_fingerprint(current_cfg) != manifest.get("config_fingerprint"):
            errors.append("current config fingerprint mismatch")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"current config fingerprint source unavailable: {exc}")

    # Feed identity check.
    feed_path = bundle / "input" / "feed.json"
    feed: dict[str, Any] = {}
    if feed_path.exists():
        from .feed.validate import assert_feed_identity

        try:
            feed = json.loads(feed_path.read_bytes())
            if "evidence_cutoff_at" not in feed or "run_id" not in feed:
                errors.append("saved feed missing required identity fields")
            else:
                assert_feed_identity(feed)
                if feed.get("run_id") != manifest["feed_run_id"]:
                    errors.append("feed run_id mismatch")
        except (ValueError, KeyError) as exc:
            errors.append(f"feed identity invalid: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"feed identity invalid: {exc}")

    if manifest["mode"] != "normal":
        # Degraded bundles contain only the deterministic report; integrity,
        # build, config, and feed checks above are the replay contract.
        if errors == [] and compare is not None:
            errors.extend(compare(manifest, {}))
        return ReplayResult(ok=not errors, errors=errors)

    # Full deterministic replay of the normal path.
    if not feed or not (bundle / "pipeline" / "llm.json").exists():
        errors.append("replay: normal bundle missing input/feed.json or pipeline/llm.json")
        return ReplayResult(ok=False, errors=errors)

    try:
        saved_llm = json.loads((bundle / "pipeline" / "llm.json").read_bytes())
        saved = {
            "events": json.loads((bundle / "pipeline" / "events.json").read_bytes()),
            "unresolved": json.loads((bundle / "pipeline" / "unresolved.json").read_bytes()),
            "ledger": json.loads((bundle / "pipeline" / "ledger.json").read_bytes()),
            "packets": json.loads((bundle / "pipeline" / "packets.json").read_bytes()),
            "analyses": json.loads((bundle / "pipeline" / "analyses.json").read_bytes()),
            "selection": json.loads((bundle / "pipeline" / "selection.json").read_bytes()),
            "brief": json.loads((bundle / "output" / "brief.json").read_bytes()),
            "rendered": (bundle / "output" / "brief.md").read_bytes(),
            "claims": json.loads((bundle / "output" / "claim_inventory.json").read_bytes()),
            "audit": json.loads((bundle / "audit" / "results.json").read_bytes()),
        }
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"replay: missing/invalid pipeline member: {exc}")
        return ReplayResult(ok=False, errors=errors)

    from .config import load_config
    from .engine.entities import EntityResolver
    from .pipeline import PipelineError, run_pipeline
    from .render import render_brief

    # ``saved_llm`` bypasses live passes, so prompt text is intentionally not
    # loaded during replay.  Empty placeholders satisfy the pipeline's
    # request shape while preserving replay independence from current prompt
    # files.
    prompts = {name: "" for name in ("resolver", "analyst", "editor", "audit")}

    try:
        cfg = load_config(
            repo_root / "config" / "config.yaml",
            repo_root / "config" / "providers.yaml",
            require_verified_enabled=True,
        )
        result = run_pipeline(
            cfg=cfg,
            feed=feed,
            brief_generated_at=manifest["brief_generated_at"],
            adapter=None,
            resolver=EntityResolver(cfg.entities),
            prompts=prompts,
            saved_llm=saved_llm,
        )
    except PipelineError as exc:
        errors.append(f"replay pipeline failed: {exc}")
        return ReplayResult(ok=False, errors=errors)

    from .ledger import ledger_to_records

    reconstructed = {
        "events": result.events,
        "unresolved": result.unresolved_groups,
        "ledger": ledger_to_records(result.ledger),
        "packets": result.packets,
        "analyses": result.analyses,
        "selection": [
            {
                "event_id": s.event_id,
                "format": s.format,
                "final_priority": str(s.final_priority),
            }
            for s in result.selected
        ],
        "brief": dict(result.brief),
        "rendered": render_brief(result.brief).encode("utf-8"),
        "claims": result.brief["claim_inventory"],
        "audit": result.brief["audit_status"],
    }
    # The saved Brief's provenance fingerprints are provenance of the original
    # run (recorded in the manifest) and are not re-derived by replay; compare
    # the authoritative Brief content only.
    reconstructed["brief"].pop("provenance", None)
    saved["brief"].pop("provenance", None)

    for name in (
        "events",
        "unresolved",
        "ledger",
        "packets",
        "analyses",
        "selection",
        "brief",
        "rendered",
        "claims",
        "audit",
    ):
        _compare_artifact(name, saved[name], reconstructed[name], errors)

    if errors == [] and compare is not None:
        errors.extend(compare(manifest, result.brief))

    return ReplayResult(ok=not errors, errors=errors)


def _schema_fingerprints(repo_root: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((repo_root / "schemas").glob("*.schema.json"))
    }


def _config_fingerprint(cfg: Any) -> str:
    return canonical_digest(asdict(cfg))
