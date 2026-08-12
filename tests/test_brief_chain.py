"""Task 10.3-10.13 — renderer, claim audit, run bundle, and Brief CLI fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from follow_the_money.audit import ClaimAuditor, audit_language_findings
from follow_the_money.boundary import application_build_fingerprint, build_fingerprint_to_dict
from follow_the_money.brief_cli import _generate_brief_run_id, run_brief
from follow_the_money.bundle import (
    BundleError,
    BundleWriter,
    _atomic_no_replace_directory_rename,
    replay_bundle,
    verify_bundle_integrity,
)
from follow_the_money.canonical import canonical_digest
from follow_the_money.render import (
    RenderError,
    escape_text_node,
    render_brief,
    render_dashboard,
    render_link,
)
from follow_the_money.schema import validate_against
from follow_the_money.unicode import UnicodeError_

REPO_ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 8, 11, 0, 20, 0, tzinfo=UTC)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------
# Renderer escaping
# ---------------------------------------------------------------------------


def test_escape_html_entities():
    # & < > become HTML entities first (no extra backslash).
    assert escape_text_node("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_escape_fences_and_links():
    # Backslash-escape ASCII punctuation: ```~~~===[]():/
    out = escape_text_node("``` ~~~ === [link](https://x)")
    assert "\\`\\`\\`" in out
    assert "\\[link\\]" in out
    assert "\\(" in out and "\\)" in out
    assert "\\/" in out


def test_escape_leading_four_spaces():
    # Whitespace is collapsed and stripped (leading 4-space blocks neutralized
    # by removal); indented-code injection cannot survive.
    assert escape_text_node("    indented") == "indented"


def test_reject_controls():
    with pytest.raises(UnicodeError_):
        escape_text_node("bad\u0000control")
    with pytest.raises(UnicodeError_):
        escape_text_node("bidi\u202eoverride")
    with pytest.raises(UnicodeError_):
        escape_text_node("zero\u200bwidth")
    with pytest.raises(UnicodeError_):
        escape_text_node("para\u2028sep")


def test_lone_surrogate_rejected():
    with pytest.raises(Exception, match="surrogate"):
        escape_text_node("bad\ud800")


def test_link_requires_https():
    with pytest.raises(RenderError, match="https"):
        render_link("来源", "http://example.com/x")
    with pytest.raises(RenderError, match="https"):
        render_link("来源", "javascript:alert(1)")


def test_render_dashboard_heading_order():
    md = render_dashboard(
        [
            {"role_id": "sp500", "available": True, "display": "标普500", "return_pct": "0.5"},
            {"role_id": "vix", "available": False, "display": "VIX"},
        ]
    )
    assert md.startswith("## 市场仪表盘")
    assert "标普500：0.5%" in md
    assert "VIX：不可用" in md


def test_render_brief_full_structure():
    brief = {
        "schema_version": 1,
        "brief_id": "b1",
        "brief_generated_at": _ts(T0 + timedelta(minutes=5)),
        "brief_completed_at": _ts(T0 + timedelta(minutes=6)),
        "evidence_cutoff_at": _ts(T0),
        "feed_run_id": "r1",
        "mode": "normal",
        "headings": [],
        "dashboard": [
            {"role_id": "sp500", "available": True, "display": "标普500", "return_pct": "0.5"}
        ],
        "market_state": {
            "regime": "neutral",
            "vector": {},
            "missing_roles": [],
            "explanation": "说明",
        },
        "full_events": [],
        "compact_events": [],
        "money_flow_section": [],
        "watchlist": [],
        "bottom_line": [],
        "claim_inventory": [],
        "warnings": [],
        "audit_status": {"script_audit": "passed", "language_audit": "passed", "findings": []},
        "provenance": {"feed_digest": "a" * 64, "config_hash": "b" * 64, "prompt_fingerprints": {}},
    }
    md = render_brief(brief)
    assert "市场仪表盘" in md
    assert "市场状态" in md
    assert "重点事件" in md
    assert "结论" in md
    assert "证据截止" in md
    # No 资金流 section when empty.
    assert "资金流与持仓" not in md


# ---------------------------------------------------------------------------
# Claim audit
# ---------------------------------------------------------------------------


def _brief_with_claims(claims: list[dict]) -> dict:
    return {
        "claim_inventory": claims,
        "money_flow_section": [],
    }


def test_audit_passes_clean_claims():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "美联储维持利率不变",
                    "is_factual": True,
                    "is_causal": False,
                    "reference_evidence_ids": ["ev_1"],
                },
            ]
        )
    )
    assert result.passed


def test_audit_factual_missing_evidence():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "某事实",
                    "is_factual": True,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
            ]
        )
    )
    assert not result.passed
    assert any(f.category == "missing_evidence" for f in result.findings)


def test_audit_duplicate_claim_ids():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "a",
                    "is_factual": False,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
                {
                    "claim_id": "c_0",
                    "text": "b",
                    "is_factual": False,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
            ]
        )
    )
    assert not result.passed
    assert any(f.category == "duplicate_claim_id" for f in result.findings)


def test_audit_trading_instruction_zh():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "建议立即买入该ETF",
                    "is_factual": False,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
            ]
        )
    )
    assert not result.passed
    assert any(f.category == "trading_instruction" for f in result.findings)


def test_audit_trading_instruction_en():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "You should buy this asset now",
                    "is_factual": False,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
            ]
        )
    )
    assert not result.passed


def test_audit_descriptive_false_positive_allowed():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "基金净买入额达到新高",
                    "is_factual": False,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
            ]
        )
    )
    assert result.passed  # descriptive exception


def test_audit_zero_width_stripped_for_instruction():
    auditor = ClaimAuditor()
    result = auditor.audit(
        _brief_with_claims(
            [
                {
                    "claim_id": "c_0",
                    "text": "建\u200b仓",
                    "is_factual": False,
                    "is_causal": False,
                    "reference_evidence_ids": [],
                },
            ]
        )
    )
    assert not result.passed


def test_language_audit_severity_mapping():
    audit_output = {
        "covered_claim_ids": ["c_0"],
        "findings": [
            {
                "claim_id": "c_0",
                "category": "causal_overclaim",
                "rationale": "因果过度",
                "reference_aliases": [],
            },
            {
                "claim_id": "c_0",
                "category": "excessive_certainty",
                "rationale": "过于确定",
                "reference_aliases": [],
            },
        ],
    }
    severity_map = {
        "critical": (
            "causal_overclaim",
            "inference_as_fact",
            "unsupported_conclusion",
            "fact_modification",
            "trading_instruction",
            "wrong_language",
        ),
        "warning": ("excessive_certainty", "missing_uncertainty"),
    }
    critical, warning = audit_language_findings(audit_output, severity_map)
    assert len(critical) == 1
    assert critical[0]["category"] == "causal_overclaim"
    assert len(warning) == 1
    assert warning[0]["category"] == "excessive_certainty"


# ---------------------------------------------------------------------------
# Run bundle
# ---------------------------------------------------------------------------


def _bundle_writer(tmp_path: Path, run_id: str = "run_1") -> BundleWriter:
    build = build_fingerprint_to_dict(application_build_fingerprint(REPO_ROOT, "0.1.0"))
    return BundleWriter(
        root=tmp_path / "runs",
        brief_run_id=run_id,
        attempt_id=f"attempt_{run_id}",
        feed_run_id="feed_run_1",
        mode="normal",
        brief_generated_at=_ts(T0 + timedelta(minutes=5)),
        brief_completed_at=_ts(T0 + timedelta(minutes=6)),
        build=build,
        schema_fingerprints={"feed": "a" * 64},
        config_fingerprint="b" * 64,
        prompt_fingerprints={"resolver": "c" * 64},
        model_fingerprint="gpt-test",
    )


def test_bundle_write_and_verify(tmp_path):
    writer = _bundle_writer(tmp_path)
    final = writer.write(
        {
            "input/feed.json": b"{}",
            "output/brief.json": b"{}",
        }
    )
    assert final.exists()
    manifest = verify_bundle_integrity(final)
    assert manifest["generation_status"] == "ready_for_commit"
    assert manifest["bundle_digest"]
    # No indexed member contains brief_run_id/bundle_digest.
    for member in manifest["members"]:
        assert "brief_run_id" not in member
        assert "bundle_digest" not in member


def test_bundle_no_overwrite(tmp_path):
    writer = _bundle_writer(tmp_path, run_id="dup")
    writer.write({"input/feed.json": b"{}"})
    with pytest.raises(BundleError, match="already exists"):
        writer.write({"input/feed.json": b"{}"})


@pytest.mark.skipif(__import__("sys").platform != "darwin", reason="Darwin renamex_np contract")
def test_bundle_directory_publication_is_atomic_no_replace(tmp_path):
    source = tmp_path / "staging"
    destination = tmp_path / "published"
    source.mkdir()
    destination.mkdir()
    (destination / "keep").write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        _atomic_no_replace_directory_rename(source, destination)

    assert source.is_dir()
    assert (destination / "keep").read_bytes() == b"existing"


def test_bundle_tamper_detected(tmp_path):
    writer = _bundle_writer(tmp_path)
    final = writer.write({"input/feed.json": b"{}", "output/brief.json": b"{}"})
    (final / "output" / "brief.json").write_bytes(b"tampered!")
    with pytest.raises(BundleError, match="tamper"):
        verify_bundle_integrity(final)


def test_bundle_manifest_member_is_reserved_during_verification(tmp_path):
    writer = _bundle_writer(tmp_path)
    final = writer.write({"input/feed.json": b"{}"})
    manifest = json.loads((final / "manifest.json").read_bytes())
    manifest["members"].append({"path": "manifest.json", "size": 0, "sha256": "0" * 64})
    manifest["directory_id"] = writer.directory_id(manifest["members"])
    manifest["bundle_digest"] = canonical_digest(
        {key: value for key, value in manifest.items() if key != "bundle_digest"}
    )
    (final / "manifest.json").write_bytes(json.dumps(manifest).encode("utf-8"))
    with pytest.raises(BundleError, match="manifest.json is reserved"):
        verify_bundle_integrity(final)


def test_bundle_member_added_detected(tmp_path):
    writer = _bundle_writer(tmp_path)
    final = writer.write({"input/feed.json": b"{}"})
    # Add an unlisted member.
    (final / "extra.json").write_bytes(b"x")
    with pytest.raises(BundleError, match="missing|tamper"):
        verify_bundle_integrity(final)


def test_bundle_replay_build_mismatch(tmp_path):
    writer = _bundle_writer(tmp_path)
    final = writer.write({"input/feed.json": b"{}"})
    # Replay against a different repo root => build fingerprint mismatch.
    result = replay_bundle(final, repo_root=tmp_path)
    assert not result.ok
    assert any("build" in e for e in result.errors)


def test_bundle_manifest_schema(tmp_path):
    writer = _bundle_writer(tmp_path)
    final = writer.write({"input/feed.json": b"{}"})
    manifest = json.loads((final / "manifest.json").read_bytes())
    validate_against("run-manifest.schema.json", manifest)


# ---------------------------------------------------------------------------
# Brief CLI (mocked deterministic path)
# ---------------------------------------------------------------------------


def _write_valid_feed(tmp_path: Path) -> Path:
    from follow_the_money.feed.validate import recompute_feed_identity

    feed = {
        "schema_version": 1,
        "run_id": "feed_run_1",
        "window": {"start": _ts(T0 - timedelta(hours=72)), "end": _ts(T0)},
        "collection_started_at": _ts(T0 - timedelta(seconds=30)),
        "evidence_cutoff_at": _ts(T0),
        "collection_completed_at": _ts(T0 + timedelta(minutes=4)),
        "generated_at": _ts(T0 + timedelta(minutes=5)),
        "provider_outcomes": [],
        "producer": {"package_version": "0.1.0", "files": [], "fingerprint": "a" * 64},
        "feed_config": {"snapshot": {}, "hash": "b" * 64},
        "feed_schema": {"path": "x", "sha256": "c" * 64},
        "provider_contracts": [],
        "git": None,
        "content_digest": "d" * 64,
        "items": [],
        "pipeline": {"status": "healthy", "warnings": []},
        "calendar_horizon_end": _ts(T0 + timedelta(hours=26)),
    }
    digest, run_id = recompute_feed_identity(feed)
    feed["content_digest"] = digest
    feed["run_id"] = run_id
    path = tmp_path / "latest.json"
    path.write_bytes(json.dumps(feed, ensure_ascii=False).encode("utf-8"))
    return path


def test_brief_degraded_report_success(tmp_path):
    feed = _write_valid_feed(tmp_path)
    out_root = tmp_path / "feeds"
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(out_root),
        feed_path=str(feed),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        runs_root=str(tmp_path / "runs"),
        degraded_report=True,
    )
    assert result.exit_code == 0
    assert result.brief_path
    assert Path(result.brief_path).exists()
    manifest = json.loads((Path(result.brief_path) / "manifest.json").read_bytes())
    assert manifest["mode"] == "degraded"
    assert manifest["feed_run_id"].startswith("2026-08-11")


def test_same_feed_and_clock_allocate_distinct_attempt_bundles(tmp_path):
    feed = _write_valid_feed(tmp_path)
    kwargs = {
        "config_path": str(REPO_ROOT / "config" / "config.yaml"),
        "output_root": str(tmp_path / "feeds"),
        "feed_path": str(feed),
        "generated_at": _ts(T0 + timedelta(minutes=10)),
        "runs_root": str(tmp_path / "runs"),
        "degraded_report": True,
    }
    first = run_brief(**kwargs)
    second = run_brief(**kwargs)
    assert first.exit_code == second.exit_code == 0
    assert first.brief_path != second.brief_path
    assert Path(first.brief_path).exists()
    assert Path(second.brief_path).exists()


def test_brief_run_id_binds_execution_provenance():
    common = {
        "feed_run_id": "feed_run_1",
        "generated_at": _ts(T0 + timedelta(minutes=10)),
        "attempt_id": "attempt_1",
        "mode": "normal",
        "build_fingerprint": "a" * 64,
        "config_fingerprint": "b" * 64,
        "prompt_fingerprints": {"resolver": "c" * 64},
        "model_fingerprint": "model-a",
    }
    baseline = _generate_brief_run_id(**common)
    for field, value in (
        ("mode", "degraded"),
        ("build_fingerprint", "d" * 64),
        ("config_fingerprint", "e" * 64),
        ("prompt_fingerprints", {"resolver": "f" * 64}),
        ("model_fingerprint", "model-b"),
    ):
        changed = {**common, field: value}
        assert _generate_brief_run_id(**changed) != baseline


def test_brief_missing_llm_normal_mode_exit_2(tmp_path):
    feed = _write_valid_feed(tmp_path)
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(feed),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        runs_root=str(tmp_path / "runs"),
    )
    assert result.exit_code == 2
    assert result.status == "startup_rejection"


def test_brief_missing_feed_exit_1(tmp_path):
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(tmp_path / "nope.json"),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        runs_root=str(tmp_path / "runs"),
    )
    assert result.exit_code == 1
    assert result.status == "pre_attempt_domain_failure"


def test_brief_clock_before_feed(tmp_path):
    feed = _write_valid_feed(tmp_path)
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(feed),
        generated_at=_ts(T0 - timedelta(minutes=1)),
        runs_root=str(tmp_path / "runs"),
    )
    assert result.exit_code == 1


def test_brief_skip_llm_normal_path(tmp_path):
    feed = _write_valid_feed(tmp_path)
    result = run_brief(
        config_path=str(REPO_ROOT / "config" / "config.yaml"),
        output_root=str(tmp_path / "feeds"),
        feed_path=str(feed),
        generated_at=_ts(T0 + timedelta(minutes=10)),
        skip_llm=True,
        runs_root=str(tmp_path / "runs"),
        output_path=str(tmp_path / "out.md"),
    )
    assert result.exit_code == 0
    assert (tmp_path / "out.md").exists()
