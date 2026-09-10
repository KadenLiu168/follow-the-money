"""Feed-only architecture and credential-free startup regressions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from follow_the_money.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
RETAINED_MODULES = (
    "agent_invocation.py",
    "analysis.py",
    "audit.py",
    "events.py",
    "ledger.py",
    "scoring.py",
    "selection.py",
    "state.py",
    "watchlist.py",
)


def test_removed_runtime_and_schema_surfaces_are_absent():
    source_root = REPO_ROOT / "src" / "follow_the_money"
    for name in RETAINED_MODULES:
        assert not (source_root / name).exists(), name
    assert not (source_root / "engine").exists()
    assert not (source_root / "market").exists()
    assert not (REPO_ROOT / "schemas" / "agent-invocation.schema.json").exists()
    assert not (REPO_ROOT / "providers" / "yahoo_market").exists()
    assert not (REPO_ROOT / "prompts").exists()
    assert "exchange-calendars" not in (REPO_ROOT / "pyproject.toml").read_text()


def test_package_imports_without_model_or_credential_runtime():
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("OPENAI_MODEL", None)
    proc = subprocess.run(
        [sys.executable, "-c", "import follow_the_money, follow_the_money.feed.cli; print('ok')"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


def test_shipped_configuration_loads_without_credentials():
    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        manifest_root=REPO_ROOT / "providers",
        require_verified_enabled=True,
    )
    assert len(cfg.providers) == 8
    assert all(provider.authentication == "none" for provider in cfg.providers)


def test_feed_entry_help_is_the_only_producer_surface():
    proc = subprocess.run(
        [sys.executable, "-m", "follow_the_money.feed.cli", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "usage:" in proc.stdout
    assert "--dry-run" in proc.stdout
