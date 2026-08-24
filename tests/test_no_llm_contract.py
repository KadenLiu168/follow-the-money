"""remove-standalone-runtime — retained no-LLM regression contract.

Covers requirement ``deterministic-core-retention``:

- The repository contains no embedded LLM runtime surface.
- Configuration loads credential-free and fails closed on deterministic
  contracts only.
- The minimal internal Feed entry publishes a validating Feed.
- The retained rules (scoring/selection/ClaimAuditor) stay deterministic
  and LLM-free.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from follow_the_money.audit import ClaimAuditor
from follow_the_money.config import load_config
from follow_the_money.feed.cli import (
    FeedExecutionError,
    FeedInputError,
    FeedRunResult,
    run_feed,
)
from follow_the_money.feed.validate import assert_feed_identity, validate_feed
from follow_the_money.schema import validate_against
from tests.test_gate_13_1 import CUTOFF, _fixture_registry

REPO_ROOT = Path(__file__).resolve().parents[1]

# Modules that existed under the embedded LLM runtime / old four-pass contract.
REMOVED_MODULES = (
    "llm",
    "pipeline",
    "brief_cli",
    "cli",
    "__main__",
    "analysis",
    "editor",
    "brief",
    "render",
    "bundle",
    "eval_offline",
    "eval_live",
    "eval_metrics",
    "engine.resolution",
)
REMOVED_SCHEMAS = (
    "resolver-output",
    "analyst-output",
    "editor-output",
    "language-audit-output",
    "event",
    "analysis",
    "verified-event-packet",
    "brief",
    "degraded-report",
    "run-manifest",
)


# ---------------------------------------------------------------------------
# Repository audit: no LLM surface
# ---------------------------------------------------------------------------


def test_repo_has_no_llm_surface():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    assert "openai" not in pyproject
    assert "[project.scripts]" not in pyproject
    lock = (REPO_ROOT / "uv.lock").read_text()
    assert "openai" not in lock
    assert not (REPO_ROOT / "prompts").exists()
    assert not (REPO_ROOT / "evals").exists()
    for mod in REMOVED_MODULES:
        assert not (REPO_ROOT / "src" / "follow_the_money" / f"{mod}.py").exists(), mod
        assert not (REPO_ROOT / "src" / "follow_the_money" / "engine" / f"{mod}.py").exists()
    for name in REMOVED_SCHEMAS:
        assert not (REPO_ROOT / "schemas" / f"{name}.schema.json").exists(), name
    assert (REPO_ROOT / "schemas" / "feed.schema.json").exists()
    config = (REPO_ROOT / "config" / "config.yaml").read_text()
    assert re.search(r"^llm:", config, re.MULTILINE) is None
    assert re.search(r"^audit_severity:", config, re.MULTILINE) is None
    env = (REPO_ROOT / ".env.example").read_text()
    assert "OPENAI_API_KEY" not in env
    assert "OPENAI_MODEL" not in env


def test_package_imports_without_llm_sdk():
    # The retained package must import with no OpenAI SDK installed in the
    # environment and no credential present.
    env = os.environ.copy()
    for key in list(env):
        if "OPENAI" in key or "FOLLOW_THE_MONEY_LLM" in key:
            del env[key]
    env["OPENAI_API_KEY"] = ""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import follow_the_money, follow_the_money.feed.cli, follow_the_money.scoring, "
                "follow_the_money.selection, follow_the_money.audit; print('ok')"
            ),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


# ---------------------------------------------------------------------------
# Credential-free configuration
# ---------------------------------------------------------------------------


def test_shipped_config_loads_credential_free():
    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    assert cfg.schema_version == 1
    assert not hasattr(cfg, "llm")
    assert not hasattr(cfg, "audit_severity")
    assert cfg.safety_lexicon.zh_terms
    assert cfg.rate_registry.version == "1"


# ---------------------------------------------------------------------------
# Minimal internal Feed entry
# ---------------------------------------------------------------------------


def test_minimal_entry_publishes_validating_feed(tmp_path):
    out = tmp_path / "out"
    result = run_feed(output_root=str(out), cutoff=CUTOFF, providers_fn=_fixture_registry)
    assert result.exit_code == 0
    assert result.status == "healthy"
    assert result.feed is not None
    validate_feed(result.feed)
    assert_feed_identity(result.feed)
    validate_against("feed.schema.json", result.feed)
    assert (out / "latest.json").exists()


def test_minimal_entry_status_file_and_exit_contract(tmp_path, monkeypatch, capsys):
    from follow_the_money.feed import cli as feed_cli

    out = tmp_path / "out"
    status = tmp_path / "status.json"

    # The same run_feed the entry calls, producing a validating Feed.
    result = run_feed(output_root=str(out), cutoff=CUTOFF, providers_fn=_fixture_registry)
    assert result.exit_code == 0

    monkeypatch.setattr(feed_cli, "run_feed", lambda **kw: result)
    code = feed_cli.main(
        [
            "--output-root",
            str(out),
            "--cutoff",
            "2026-08-11T00:20:00Z",
            "--status-file",
            str(status),
        ]
    )
    assert code == 0
    payload = __import__("json").loads(status.read_text())
    assert payload["status"] == "healthy"
    assert payload["run_id"] == result.feed["run_id"]
    assert payload["evidence_cutoff_at"] == result.feed["evidence_cutoff_at"]
    assert payload["latest_relative_path"] == "latest.json"
    assert payload["dated_relative_path"].startswith("daily/2026-08-11/")

    # Warnings surface on stderr.
    warned = FeedRunResult(
        status="degraded",
        exit_code=0,
        feed=result.feed,
        warnings=["coverage gap"],
    )
    monkeypatch.setattr(feed_cli, "run_feed", lambda **kw: warned)
    assert feed_cli.main(["--output-root", str(out)]) == 0
    assert "warning: coverage gap" in capsys.readouterr().err

    # Usage/config failures map to exit 2; runtime failures to exit 1.
    def _config_error(**kw):
        raise FeedInputError("publication invalid non_advancing")

    monkeypatch.setattr(feed_cli, "run_feed", _config_error)
    assert feed_cli.main(["--output-root", str(out)]) == 2

    def _runtime_error(**kw):
        raise FeedExecutionError("config invalid provider")

    monkeypatch.setattr(feed_cli, "run_feed", _runtime_error)
    assert feed_cli.main(["--output-root", str(out)]) == 1


# ---------------------------------------------------------------------------
# Retained rules stay deterministic and LLM-free
# ---------------------------------------------------------------------------


def test_retained_rules_deterministic_and_llm_free():
    from decimal import Decimal

    from follow_the_money.scoring import (
        base_priority,
        event_relevance,
        event_significance,
        significance_components,
    )

    cfg = load_config(
        REPO_ROOT / "config" / "config.yaml",
        REPO_ROOT / "config" / "providers.yaml",
        require_verified_enabled=True,
    )
    comps = significance_components(
        scoring=cfg.scoring,
        scope="cross_market",
        fundamental_depth="systemic",
        reversibility="effectively_irreversible",
        structural_horizon="months",
        surprise_values=[Decimal("2.5")],
        affected_groups=3,
        observable_repricing_z=Decimal("2.0"),
    )
    sig1, cov1 = event_significance(comps)
    sig2, cov2 = event_significance(comps)
    assert (sig1, cov1) == (sig2, cov2)
    relevance = event_relevance(
        scoring=cfg.scoring,
        age_hours=Decimal(5),
        cn_hk_exposure="direct",
        us_next_session_exposure="direct",
        catalyst_present=True,
    )
    assert relevance == event_relevance(
        scoring=cfg.scoring,
        age_hours=Decimal(5),
        cn_hk_exposure="direct",
        us_next_session_exposure="direct",
        catalyst_present=True,
    )
    assert base_priority(sig1, relevance, cfg.scoring) == base_priority(
        sig1, relevance, cfg.scoring
    )

    # ClaimAuditor: deterministic, flags prohibited trading instructions.
    auditor = ClaimAuditor(cfg.safety_lexicon)
    result = auditor.audit({"claim_inventory": [{"claim_id": "c1", "text": "今天买入腾讯。"}]})
    assert not result.passed
    assert any(f.category == "trading_instruction" for f in result.findings)
    assert auditor.audit(
        {"claim_inventory": [{"claim_id": "c1", "text": "该政策旨在抑制过热。"}]}
    ).passed  # descriptive exception
