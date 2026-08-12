"""Command-line entry point for Follow the Money.

Exposes ``feed``, ``brief``, ``eval``, and ``replay`` subcommands. Importing
this module or running ``follow-the-money --help`` never requires credentials
or network access.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="follow-the-money",
        description="Deterministic daily financial intelligence pipeline.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    feed = sub.add_parser("feed", help="Collect and publish the evidence-only Feed.")
    feed.add_argument(
        "--config", default=None, help="Explicit config file path (default: repo default)."
    )
    feed.add_argument(
        "--output-root", default=None, help="Explicit output root for feeds/ and rate state."
    )
    feed.add_argument(
        "--dry-run", action="store_true", help="Validate and report without publishing."
    )
    feed.add_argument("--cutoff", default=None, help="Fixture: explicit ISO-8601 evidence cutoff.")
    feed.add_argument(
        "--window-start", default=None, help="Fixture: explicit ISO-8601 window start."
    )
    feed.add_argument(
        "--status-file", default=None, help="Write machine-readable status JSON here."
    )
    feed.set_defaults(handler=_cmd_feed)

    brief = sub.add_parser("brief", help="Generate the Morning Money Brief (requires Feed + LLM).")
    brief.add_argument("--config", default=None)
    brief.add_argument("--output-root", default=None)
    brief.add_argument(
        "--feed", default=None, help="Explicit input Feed path (default: <root>/feeds/latest.json)."
    )
    brief.add_argument(
        "--output", default=None, help="Convenience delivery path for rendered Markdown."
    )
    brief.add_argument(
        "--degraded-report",
        action="store_true",
        help="Emit the separate deterministic degraded report.",
    )
    brief.add_argument("--status-file", default=None)
    brief.set_defaults(handler=_cmd_brief)

    eval_ = sub.add_parser("eval", help="Run offline or credentialed live regression evaluation.")
    eval_.add_argument("--config", default=None)
    eval_.add_argument("--mode", choices=["offline", "live"], default="offline")
    eval_.add_argument(
        "--day", default=None, help="Restrict evaluation to one golden day (YYYY-MM-DD)."
    )
    eval_.add_argument("--output", default=None)
    eval_.add_argument("--repetitions", type=int, default=1, help="Live mode repetitions per day.")
    eval_.add_argument(
        "--max-cost-usd", type=str, default=None, help="Live mode total cost budget (Decimal)."
    )
    eval_.set_defaults(handler=_cmd_eval)

    replay = sub.add_parser(
        "replay", help="Replay a validated run audit bundle without network/LLM."
    )
    replay.add_argument("bundle", help="Path to a runs/<brief_run_id>/ bundle directory.")
    replay.add_argument("--status-file", default=None)
    replay.set_defaults(handler=_cmd_replay)

    return parser


def _cmd_feed(args: argparse.Namespace) -> int:
    from .feed.cli import FeedCliError, run_feed
    from .feed.plan import FeedPlanError

    cutoff = None
    if args.cutoff:
        from datetime import datetime

        cutoff = datetime.fromisoformat(args.cutoff)
    try:
        result = run_feed(
            config_path=args.config,
            output_root=args.output_root,
            dry_run=args.dry_run,
            cutoff=cutoff,
        )
    except (FeedCliError, FeedPlanError) as exc:
        print(f"follow-the-money feed: {exc}", file=sys.stderr)
        return 2 if "non_advancing" in str(exc) or "config" in str(exc).lower() else 1
    if args.status_file:
        status = {"status": result.status, "warnings": result.warnings}
        if result.feed is not None:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            cutoff = datetime.fromisoformat(result.feed["evidence_cutoff_at"])
            asia_date = cutoff.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
            status.update(
                {
                    "run_id": result.feed["run_id"],
                    "evidence_cutoff_at": result.feed["evidence_cutoff_at"],
                    "dated_relative_path": f"daily/{asia_date}/{result.feed['run_id']}.json",
                    "latest_relative_path": "latest.json",
                }
            )
        Path(args.status_file).write_text(json.dumps(status), encoding="utf-8")
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if result.feed is not None and args.dry_run:
        print(json.dumps(result.feed, ensure_ascii=False, indent=2)[:2000])
    return result.exit_code


def _cmd_brief(args: argparse.Namespace) -> int:
    from .brief_cli import run_brief

    try:
        result = run_brief(
            config_path=args.config,
            output_root=args.output_root,
            feed_path=args.feed,
            output_path=args.output,
            degraded_report=args.degraded_report,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"follow-the-money brief: {exc}", file=sys.stderr)
        return 1
    if args.status_file and result.brief_path:
        Path(args.status_file).write_text(
            json.dumps({"status": result.status, "bundle": result.brief_path}),
            encoding="utf-8",
        )
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if result.exit_code != 0:
        print(f"follow-the-money brief: {result.message}", file=sys.stderr)
    elif result.brief_path:
        print(f"committed bundle: {result.brief_path}", file=sys.stderr)
    return result.exit_code


def _cmd_eval(args: argparse.Namespace) -> int:
    from .eval_offline import GoldenDatasetError, load_golden_dataset, run_offline_evaluation

    dataset = Path(__file__).resolve().parents[2] / "evals" / "dataset"
    try:
        days = load_golden_dataset(dataset)
        if args.day:
            days = tuple(d for d in days if d.date == args.day)
            if not days:
                print(f"follow-the-money eval: no golden day {args.day!r}", file=sys.stderr)
                return 1
        aggregate, violations = run_offline_evaluation(
            dataset, dates=[args.day] if args.day else None
        )
    except GoldenDatasetError as exc:
        print(f"follow-the-money eval: {exc}", file=sys.stderr)
        return 1
    report = {
        "schema_version": 1,
        "days": len(days),
        "categories": sorted({d.category for d in days}),
        "metrics": {name: metric.as_report() for name, metric in aggregate.metrics.items()},
        "applicable_days": aggregate.applicable_days,
        "non_applicable_days": aggregate.non_applicable_days,
        "violations": violations,
        "evidence": {
            "dataset": str(dataset),
            "fixture_references_validated": True,
            "recorded_outputs_replayed": True,
            "live_provider_calls": 0,
            "llm_calls": 0,
        },
    }
    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(
        f"evidence-backed offline evaluation: {len(days)} golden days; "
        f"categories: {sorted({d.category for d in days})}"
    )
    if violations:
        for violation in violations:
            print(f"violation: {violation}", file=sys.stderr)
        return 1
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    from .bundle import BundleError, replay_bundle, verify_bundle_integrity

    bundle = Path(args.bundle)
    try:
        verify_bundle_integrity(bundle)

        result = replay_bundle(bundle, repo_root=Path(__file__).resolve().parents[2])
    except (BundleError, OSError) as exc:
        print(f"follow-the-money replay: {exc}", file=sys.stderr)
        return 1
    if not result.ok:
        for error in result.errors:
            print(f"replay: {error}", file=sys.stderr)
        return 1
    if args.status_file:
        Path(args.status_file).write_text(json.dumps({"ok": True}), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> NoReturn:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.handler(args)
    except NotImplementedError as exc:
        print(f"follow-the-money: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
