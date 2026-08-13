"""Task 2.11 — application build fingerprint boundary fixture.

The verified-event-packet and run-manifest contracts were removed with the
old four-pass pipeline (see remove-standalone-runtime); only the build
fingerprint, consumed by the Feed's ``producer`` field, remains.
"""

from __future__ import annotations

from pathlib import Path

from follow_the_money.boundary import (
    application_build_fingerprint,
    build_fingerprint_to_dict,
    recompute_build_fingerprint,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Application build fingerprint (mandatory non-Git)
# ---------------------------------------------------------------------------


def test_build_fingerprint_deterministic():
    a = application_build_fingerprint(REPO_ROOT, "0.1.0")
    b = application_build_fingerprint(REPO_ROOT, "0.1.0")
    assert a.fingerprint == b.fingerprint
    assert a.files  # src/ + pyproject.toml + uv.lock must exist


def test_build_fingerprint_changes_with_version():
    a = application_build_fingerprint(REPO_ROOT, "0.1.0")
    b = application_build_fingerprint(REPO_ROOT, "0.1.1")
    assert a.fingerprint != b.fingerprint


def test_build_fingerprint_covers_uv_lock():
    a = application_build_fingerprint(REPO_ROOT, "0.1.0")
    paths = {f["path"] for f in a.files}
    assert "uv.lock" in paths
    assert "pyproject.toml" in paths
    assert not any("__pycache__" in path or path.endswith((".pyc", ".pyo")) for path in paths)


def test_build_fingerprint_recompute_matches():
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    payload = build_fingerprint_to_dict(build)
    assert recompute_build_fingerprint(payload, REPO_ROOT) == payload["fingerprint"]


def test_build_fingerprint_reject_mismatch():
    build = application_build_fingerprint(REPO_ROOT, "0.1.0")
    payload = build_fingerprint_to_dict(build)
    payload["files"] = list(payload["files"]) + [
        {"path": "injected.py", "size": 1, "sha256": "0" * 64}
    ]
    assert recompute_build_fingerprint(payload, REPO_ROOT) != payload["fingerprint"]


def test_build_fingerprint_git_metadata_optional():
    build = application_build_fingerprint(REPO_ROOT, "0.1.0", git={"sha": "x" * 40, "dirty": False})
    assert build.git == {"sha": "x" * 40, "dirty": False}
