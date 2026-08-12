"""Brief orchestration and CLI wiring (task 10.11/10.12, gate 13.3).

Pipeline: validate Feed -> build ledger/events (deterministic) -> resolve
blocks (LLM) -> verify packets -> analyst (LLM) -> score/select (deterministic)
-> market state/watchlist (deterministic) -> editor (LLM) -> assemble Brief ->
render -> script audit -> language audit (LLM) -> commit run bundle -> deliver.

The normal path is the complete pipeline from :mod:`follow_the_money.pipeline`;
there are no ``_mock_*`` shortcuts. ``--degraded-report`` is the separate
explicit deterministic path and never satisfies the normal gate.

Exit contract: 0 success; 1 runtime/domain/integrity/deadline/publication
failure; 2 usage/config/credential/startup-capability failure (startup
rejection before any bundle).
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .boundary import application_build_fingerprint, build_fingerprint_to_dict
from .bundle import BundleWriter
from .canonical import canonical_digest
from .config import load_config
from .engine.entities import EntityResolver
from .engine.feed_health import FeedLoadError, assess_health, load_latest_feed
from .llm import ResponsesAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIEF_RUN_ID_PREFIX = "brief"


class BriefCliError(ValueError):
    """Typed Brief CLI failure."""


@dataclass
class BriefRunResult:
    exit_code: int
    status: str = ""
    brief_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    message: str = ""


def _generate_brief_run_id(
    feed_run_id: str,
    generated_at: str,
    attempt_id: str,
    *,
    mode: str,
    build_fingerprint: str,
    config_fingerprint: str,
    prompt_fingerprints: Mapping[str, str],
    model_fingerprint: str,
) -> str:
    digest = canonical_digest(
        {
            "feed": feed_run_id,
            "generated": generated_at,
            "attempt": attempt_id,
            "mode": mode,
            "build_fingerprint": build_fingerprint,
            "config_fingerprint": config_fingerprint,
            "prompt_fingerprints": prompt_fingerprints,
            "model_fingerprint": model_fingerprint,
        }
    )[:16]
    return f"{BRIEF_RUN_ID_PREFIX}_{generated_at[:16].replace(':', '').replace('-', '')}_{digest}"


def _load_prompts() -> dict[str, str]:
    prompts_root = REPO_ROOT / "prompts"
    return {
        "resolver": (prompts_root / "resolve-events.md").read_text(encoding="utf-8"),
        "analyst": (prompts_root / "analyze-event.md").read_text(encoding="utf-8"),
        "editor": (prompts_root / "render-digest.md").read_text(encoding="utf-8"),
        "audit": (prompts_root / "audit-claims.md").read_text(encoding="utf-8"),
    }


def run_brief(
    *,
    config_path: str | None = None,
    output_root: str | None = None,
    feed_path: str | None = None,
    output_path: str | None = None,
    degraded_report: bool = False,
    generated_at: str | None = None,
    runs_root: str | None = None,
    llm_client: Any | None = None,
    model: str | None = None,
    skip_llm: bool = False,
    attempt_id: str | None = None,
) -> BriefRunResult:
    """Execute one Brief attempt with injected clocks/clients.

    Production requires the LLM client; ``skip_llm`` is retained only for
    the degraded deterministic path and never produces a normal Brief.
    """
    cfg = load_config(
        config_path or str(REPO_ROOT / "config" / "config.yaml"),
        str(REPO_ROOT / "config" / "providers.yaml"),
        require_verified_enabled=True,
    )
    root = Path(output_root or cfg.output_root)
    feed_file = Path(feed_path or (root / "latest.json"))
    generated = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    # Feed validation (pre-attempt domain check).
    try:
        feed = load_latest_feed(feed_file)
    except FeedLoadError as exc:
        return BriefRunResult(exit_code=1, status="pre_attempt_domain_failure", message=str(exc))

    try:
        health = assess_health(
            feed,
            brief_generated_at=generated,
            freshness_limit_minutes=cfg.freshness_limit_minutes,
            normal_lag_hours=cfg.normal_lag_hours,
        )
    except FeedLoadError as exc:
        return BriefRunResult(exit_code=1, status="clock_or_lag_failure", message=str(exc))

    attempt_id = attempt_id or f"attempt_{secrets.token_hex(16)}"
    build = build_fingerprint_to_dict(application_build_fingerprint(REPO_ROOT, "0.1.0"))
    mode = "degraded" if degraded_report or skip_llm else "normal"
    config_fingerprint = _config_fingerprint(cfg)
    prompt_fingerprints = _prompt_fingerprints()
    effective_model = model or cfg.llm.model
    run_id = _generate_brief_run_id(
        feed["run_id"],
        generated,
        attempt_id,
        mode=mode,
        build_fingerprint=build["fingerprint"],
        config_fingerprint=config_fingerprint,
        prompt_fingerprints=prompt_fingerprints,
        model_fingerprint=effective_model,
    )

    if degraded_report or skip_llm:
        # Deterministic degraded path: no LLM passes.
        from .brief import build_degraded_report

        report = build_degraded_report(
            report_id=run_id,
            brief_generated_at=generated,
            evidence_cutoff_at=feed["evidence_cutoff_at"],
            feed_run_id=feed["run_id"],
            feed_health={"status": health.status, "warnings": health.warnings},
            dashboard=_dashboard(feed),
            analytics={},
            unresolved_counts={
                "candidate_blocks": 0,
                "unresolved_groups": 0,
                "unresolved_events": 0,
            },
            warnings=health.warnings,
        )
        return _commit_and_deliver(
            cfg=cfg,
            run_id=run_id,
            generated=generated,
            feed=feed,
            output_object=report,
            mode="degraded",
            output_path=output_path,
            build=build,
            warnings=health.warnings,
            runs_root=runs_root,
            attempt_id=attempt_id,
            model_fingerprint=effective_model,
        )

    # Normal path requires an LLM client.
    if llm_client is None:
        return BriefRunResult(
            exit_code=2, status="startup_rejection", message="missing LLM credential/client"
        )
    adapter = ResponsesAdapter(model=effective_model, client=llm_client)

    from .pipeline import PipelineError, run_pipeline

    resolver = EntityResolver(cfg.entities)
    try:
        result = run_pipeline(
            cfg=cfg,
            feed=feed,
            brief_generated_at=generated,
            adapter=adapter,
            resolver=resolver,
            prompts=_load_prompts(),
        )
    except PipelineError as exc:
        return BriefRunResult(exit_code=1, status="pipeline_failure", message=str(exc))

    brief = result.brief
    from .render import render_brief

    rendered = render_brief(brief).encode("utf-8")
    return _commit_and_deliver(
        cfg=cfg,
        run_id=run_id,
        generated=generated,
        feed=feed,
        output_object=brief,
        mode="normal",
        output_path=output_path,
        build=build,
        warnings=health.warnings + result.warnings,
        runs_root=runs_root,
        pipeline=result,
        rendered=rendered,
        attempt_id=attempt_id,
        model_fingerprint=effective_model,
    )


def _dashboard(feed: Mapping[str, Any]) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for item in feed.get("items", []):
        payload = item.get("payload", {})
        if payload.get("type") == "market_data":
            obs = payload.get("observations", [])
            roles.append(
                {
                    "role_id": payload.get("instrument_id", item["id"]),
                    "available": bool(obs),
                    "display": payload.get("instrument_id", item["id"]),
                    "return_pct": str(obs[-1].get("value")) if obs else None,
                }
            )
    return roles


def _commit_and_deliver(
    *,
    cfg,
    run_id,
    generated,
    feed,
    output_object,
    mode,
    output_path,
    build,
    warnings,
    runs_root=None,
    pipeline=None,
    rendered=None,
    attempt_id=None,
    model_fingerprint=None,
) -> BriefRunResult:
    from .ledger import ledger_to_records

    runs_root_path = Path(runs_root or cfg.runs_root)
    output_bytes = json.dumps(output_object, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    bundle_writer = BundleWriter(
        root=runs_root_path,
        brief_run_id=run_id,
        attempt_id=attempt_id or f"attempt_{secrets.token_hex(16)}",
        feed_run_id=feed["run_id"],
        mode=mode,
        brief_generated_at=generated,
        brief_completed_at=generated,
        build=build,
        schema_fingerprints=_schema_fingerprints(),
        config_fingerprint=_config_fingerprint(cfg),
        prompt_fingerprints=_prompt_fingerprints(),
        model_fingerprint=model_fingerprint or _model_fingerprint(cfg),
    )
    members = {
        "input/feed.json": json.dumps(feed, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        ),
        "output/brief.json": output_bytes,
        "config-effective.json": _config_snapshot_bytes(cfg),
    }
    if pipeline is not None:
        # Complete self-contained normal-path bundle: canonical pipeline
        # artifacts + saved structured LLM outcomes + rendered bytes + audit.
        members.update(
            {
                "pipeline/events.json": json.dumps(
                    pipeline.events, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
                "pipeline/ledger.json": json.dumps(
                    ledger_to_records(pipeline.ledger), ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
                "pipeline/packets.json": json.dumps(
                    pipeline.packets, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
                "pipeline/analyses.json": json.dumps(
                    pipeline.analyses, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
                "pipeline/selection.json": json.dumps(
                    [
                        {
                            "event_id": s.event_id,
                            "format": s.format,
                            "final_priority": str(s.final_priority),
                        }
                        for s in pipeline.selected
                    ],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
                "pipeline/llm.json": json.dumps(
                    pipeline.llm_data, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8"),
                "output/brief.md": rendered or b"",
                "output/claim_inventory.json": json.dumps(
                    output_object.get("claim_inventory", []),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
                "audit/results.json": json.dumps(
                    output_object.get("audit_status", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
            }
        )
    try:
        final = bundle_writer.write(members)
    except Exception as exc:  # noqa: BLE001
        return BriefRunResult(exit_code=1, status="bundle_failure", message=str(exc))

    # Convenience delivery after commit.
    if output_path:
        Path(output_path).write_bytes(output_bytes)
    return BriefRunResult(
        exit_code=0, status=f"{mode}_committed", brief_path=str(final), warnings=warnings
    )


def _schema_fingerprints() -> dict[str, str]:
    import hashlib

    return {
        p.name: hashlib.sha256((REPO_ROOT / "schemas" / p.name).read_bytes()).hexdigest()
        for p in (REPO_ROOT / "schemas").glob("*.schema.json")
    }


def _config_fingerprint(cfg) -> str:
    return canonical_digest(asdict(cfg))


def _prompt_fingerprints() -> dict[str, str]:
    from .canonical import canonical_sha256

    return {
        name: canonical_sha256((REPO_ROOT / "prompts" / file).read_bytes())
        for name, file in (
            ("resolver", "resolve-events.md"),
            ("analyst", "analyze-event.md"),
            ("editor", "render-digest.md"),
            ("audit", "audit-claims.md"),
        )
    }


def _model_fingerprint(cfg) -> str:
    return cfg.llm.model or "unconfigured"


def _config_snapshot_bytes(cfg) -> bytes:
    """Canonical resolved redacted non-secret effective-config snapshot."""
    snapshot = asdict(cfg)
    payload = canonical_digest(snapshot)
    return json.dumps(
        {"snapshot": snapshot, "fingerprint": payload},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
