"""Private repository-native deployment boundary for the scheduled Feed."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config.model import AppConfig, RatePolicy
from ..providers.rate import (
    PERSISTENCE_MARKER,
    REGISTRY_FILENAME,
    RateRegistry,
    RateStateError,
    _atomic_write,
)

LEASE_FILENAME = "feed-run-lease.json"
LEASE_VERSION = "1"
LEASE_STATES = frozenset({"bootstrap", "in_progress", "success", "failure"})
LEASE_FIELDS = frozenset(
    {
        "version",
        "deployment_run_id",
        "state",
        "armed_at",
        "finished_at",
        "feed_start_not_after",
        "recovery_not_before",
    }
)


class DeploymentError(ValueError):
    """Hosted deployment state failed closed."""


@dataclass(frozen=True)
class DeploymentLease:
    version: str
    deployment_run_id: str
    state: str
    armed_at: datetime
    finished_at: datetime | None
    feed_start_not_after: datetime | None
    recovery_not_before: datetime


@dataclass(frozen=True)
class DeploymentPreparation:
    mode: str
    lease: DeploymentLease
    paths: tuple[Path, ...]


GitRunner = Callable[[list[str]], str]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DeploymentError("deployment clock must be timezone-aware")
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    return (
        None
        if value is None
        else _utc(value).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _parse_time(value: object, field: str, *, required: bool) -> datetime | None:
    if value is None:
        if required:
            raise DeploymentError(f"lease {field} is required")
        return None
    if not isinstance(value, str):
        raise DeploymentError(f"lease {field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DeploymentError(f"lease {field} must be an ISO-8601 UTC timestamp") from exc
    return _utc(parsed)


def read_lease(path: Path, *, expected_run_id: str | None = None) -> DeploymentLease:
    try:
        raw = json.loads(Path(path).read_bytes())
    except (OSError, ValueError) as exc:
        raise DeploymentError(f"cannot read lease: {path}") from exc
    if not isinstance(raw, dict):
        raise DeploymentError("lease must be a JSON object")
    unknown = set(raw) - LEASE_FIELDS
    missing = LEASE_FIELDS - set(raw)
    if unknown:
        raise DeploymentError(f"unknown lease fields: {sorted(unknown)}")
    if missing:
        raise DeploymentError(f"missing lease fields: {sorted(missing)}")
    if raw["version"] != LEASE_VERSION:
        raise DeploymentError(f"unknown lease version: {raw['version']!r}")
    run_id = raw["deployment_run_id"]
    state = raw["state"]
    if not isinstance(run_id, str) or not run_id.strip():
        raise DeploymentError("lease deployment_run_id must be non-empty")
    if not isinstance(state, str) or state not in LEASE_STATES:
        raise DeploymentError(f"unknown lease state: {state!r}")
    if expected_run_id is not None and run_id != expected_run_id:
        raise DeploymentError("lease deployment_run_id does not match this run")

    armed_at = _parse_time(raw["armed_at"], "armed_at", required=True)
    finished_at = _parse_time(
        raw["finished_at"], "finished_at", required=state in {"success", "failure"}
    )
    feed_start = _parse_time(
        raw["feed_start_not_after"],
        "feed_start_not_after",
        required=state in {"in_progress", "success", "failure"},
    )
    recovery = _parse_time(raw["recovery_not_before"], "recovery_not_before", required=True)
    assert armed_at is not None and recovery is not None
    if state == "bootstrap" and (finished_at is not None or feed_start is not None):
        raise DeploymentError("bootstrap lease has terminal or armed fields")
    if state == "in_progress" and finished_at is not None:
        raise DeploymentError("in_progress lease has finished_at")
    if feed_start is not None and feed_start < armed_at:
        raise DeploymentError("lease feed_start_not_after precedes armed_at")
    if recovery < armed_at or (feed_start is not None and recovery < feed_start):
        raise DeploymentError("lease recovery_not_before is inconsistent")
    if finished_at is not None and finished_at < armed_at:
        raise DeploymentError("lease finished_at precedes armed_at")
    return DeploymentLease(
        version=LEASE_VERSION,
        deployment_run_id=run_id,
        state=state,
        armed_at=armed_at,
        finished_at=finished_at,
        feed_start_not_after=feed_start,
        recovery_not_before=recovery,
    )


def write_lease(path: Path, lease: DeploymentLease) -> None:
    read_lease_bytes = {
        "version": lease.version,
        "deployment_run_id": lease.deployment_run_id,
        "state": lease.state,
        "armed_at": _iso(lease.armed_at),
        "finished_at": _iso(lease.finished_at),
        "feed_start_not_after": _iso(lease.feed_start_not_after),
        "recovery_not_before": _iso(lease.recovery_not_before),
    }
    if lease.version != LEASE_VERSION or lease.state not in LEASE_STATES:
        raise DeploymentError("cannot write unsupported lease")
    _atomic_write(
        Path(path),
        json.dumps(read_lease_bytes, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )


def _scope_policies(config: AppConfig) -> dict[str, RatePolicy]:
    policies: dict[str, RatePolicy] = {}
    for provider in config.providers:
        policy = provider.rate_policy
        if not provider.enabled or policy is None or policy.unlimited:
            continue
        previous = policies.get(policy.scope_id)
        if previous is not None and previous != policy:
            raise DeploymentError(f"rate scope {policy.scope_id!r} has inconsistent policies")
        policies[policy.scope_id] = policy
    return policies


def _validate_deployment_compatibility(config: AppConfig) -> None:
    if config.rate_registry.version != LEASE_VERSION:
        raise DeploymentError("unsupported RateRegistry version for hosted deployment")
    if config.rate_registry.schema_file != REGISTRY_FILENAME:
        raise DeploymentError("hosted deployment requires the authoritative RateRegistry file")
    if config.feed.pre_commit_deadline_seconds <= 0:
        raise DeploymentError("pre_commit_deadline_seconds must be positive")


def _cooldown_seconds(config: AppConfig) -> int:
    hours = config.rate_registry.crash_cooldown_hours
    if not isinstance(hours, int) or hours <= 0:
        raise DeploymentError("crash_cooldown_hours must be positive")
    return hours * 3600


def _validate_recovery_envelope(config: AppConfig, policies: Iterable[RatePolicy]) -> int:
    cooldown = _cooldown_seconds(config)
    for policy in policies:
        if policy.refill_period_seconds > cooldown or policy.minimum_interval_seconds > cooldown:
            raise DeploymentError(f"rate scope {policy.scope_id!r} exceeds recovery envelope")
    return cooldown


def _validate_existing_state(
    root: Path, config: AppConfig, policies: dict[str, RatePolicy]
) -> RateRegistry:
    marker = root / PERSISTENCE_MARKER
    registry = RateRegistry(root)
    if not marker.is_file() or not registry.registry_path.is_file():
        raise DeploymentError("established deployment state is missing marker or registry")
    try:
        scope_ids = registry.registered_scope_ids()
        for scope_id in scope_ids:
            state = registry.read_active_scope(scope_id)
            policy = policies.get(scope_id)
            if policy is not None and (
                state.capacity != str(policy.capacity)
                or state.refill_period_seconds != policy.refill_period_seconds
                or state.minimum_interval_seconds != policy.minimum_interval_seconds
            ):
                raise DeploymentError(f"rate scope {scope_id!r} policy is incompatible")
    except RateStateError as exc:
        raise DeploymentError(str(exc)) from exc
    return registry


def _durable_paths(root: Path, registry: RateRegistry) -> tuple[Path, ...]:
    marker = root / PERSISTENCE_MARKER
    if not marker.is_file():
        raise RateStateError("deployment persistence marker is missing")
    scope_ids = registry.registered_scope_ids()
    for scope_id in scope_ids:
        registry.read_active_scope(scope_id)
    return (
        marker,
        root / REGISTRY_FILENAME,
        *(registry.scope_path(scope_id) for scope_id in scope_ids),
        root / LEASE_FILENAME,
    )


def allowlisted_paths(root: Path) -> tuple[Path, ...]:
    """Return only repository-backed state named by the registry and lease."""
    root = Path(root)
    registry = RateRegistry(root)
    try:
        return _durable_paths(root, registry)
    except RateStateError as exc:
        raise DeploymentError(str(exc)) from exc


def prepare_deployment(
    root: Path,
    config: AppConfig,
    *,
    deployment_run_id: str,
    now: Callable[[], datetime],
) -> DeploymentPreparation:
    root = Path(root)
    current = _utc(now())
    _validate_deployment_compatibility(config)
    policies = _scope_policies(config)
    cooldown = _validate_recovery_envelope(config, policies.values())
    lease_path = root / LEASE_FILENAME
    registry_path = root / REGISTRY_FILENAME
    marker_path = root / PERSISTENCE_MARKER
    present = (lease_path.exists(), registry_path.exists(), marker_path.exists())

    if not any(present):
        if any(path.is_file() for path in root.glob("scope-*.json")):
            raise DeploymentError("partial deployment state is not accepted")
        root.mkdir(parents=True, exist_ok=True)
        registry = RateRegistry(root)
        try:
            registry.ensure_registry(now=now)
            for policy in policies.values():
                registry.initialize_scope(
                    policy.scope_id,
                    policy.capacity,
                    policy.refill_period_seconds,
                    policy.minimum_interval_seconds,
                    now=now,
                )
        except (OSError, RateStateError) as exc:
            raise DeploymentError(str(exc)) from exc
        lease = DeploymentLease(
            version=LEASE_VERSION,
            deployment_run_id=deployment_run_id,
            state="bootstrap",
            armed_at=current,
            finished_at=None,
            feed_start_not_after=None,
            recovery_not_before=current + timedelta(seconds=cooldown),
        )
        write_lease(lease_path, lease)
        return DeploymentPreparation("bootstrap", lease, _durable_paths(root, registry))

    if not all(present):
        raise DeploymentError("partial deployment state is not accepted")
    lease = read_lease(lease_path)
    if lease.deployment_run_id == deployment_run_id:
        raise DeploymentError("deployment_run_id has already been used")
    registry = _validate_existing_state(root, config, policies)
    if lease.state in {"bootstrap", "in_progress"} and current < lease.recovery_not_before:
        raise DeploymentError("recovery_not_before has not elapsed")

    registered = set(registry.registered_scope_ids())
    try:
        for scope_id, policy in policies.items():
            if scope_id not in registered:
                registry.initialize_scope(
                    scope_id,
                    policy.capacity,
                    policy.refill_period_seconds,
                    policy.minimum_interval_seconds,
                    now=now,
                )
    except (OSError, RateStateError) as exc:
        raise DeploymentError(str(exc)) from exc

    feed_start = current + timedelta(seconds=config.feed.pre_commit_deadline_seconds)
    armed = DeploymentLease(
        version=LEASE_VERSION,
        deployment_run_id=deployment_run_id,
        state="in_progress",
        armed_at=current,
        finished_at=None,
        feed_start_not_after=feed_start,
        recovery_not_before=feed_start
        + timedelta(seconds=config.feed.pre_commit_deadline_seconds + cooldown),
    )
    write_lease(lease_path, armed)
    return DeploymentPreparation("armed", armed, _durable_paths(root, registry))


def assert_feed_admitted(
    root: Path, *, deployment_run_id: str, now: datetime | Callable[[], datetime]
) -> DeploymentLease:
    lease = read_lease(Path(root) / LEASE_FILENAME, expected_run_id=deployment_run_id)
    if lease.state != "in_progress" or lease.feed_start_not_after is None:
        raise DeploymentError("deployment is not armed for Feed execution")
    current = _utc(now() if callable(now) else now)
    if current > lease.feed_start_not_after:
        raise DeploymentError("feed_start_not_after has elapsed")
    return lease


def _feed_paths(root: Path, status_path: Path) -> tuple[Path, ...]:
    try:
        raw = json.loads(Path(status_path).read_bytes())
    except (OSError, ValueError) as exc:
        raise DeploymentError("successful Feed status is missing or corrupt") from exc
    if (
        not isinstance(raw, dict)
        or raw.get("status") not in {"healthy", "degraded"}
        or not isinstance(raw.get("run_id"), str)
        or not raw["run_id"]
        or not isinstance(raw.get("evidence_cutoff_at"), str)
    ):
        raise DeploymentError("successful Feed status is invalid")
    try:
        cutoff = _utc(datetime.fromisoformat(raw["evidence_cutoff_at"]))
    except (DeploymentError, ValueError) as exc:
        raise DeploymentError("successful Feed evidence_cutoff_at is invalid") from exc
    expected = {
        "dated_relative_path": (
            f"daily/{cutoff.astimezone(ZoneInfo('Asia/Shanghai')):%Y-%m-%d}/{raw['run_id']}.json"
        ),
        "latest_relative_path": "latest.json",
    }
    paths: list[Path] = []
    root_resolved = root.resolve()
    for field in ("dated_relative_path", "latest_relative_path"):
        relative = raw.get(field)
        if relative != expected[field]:
            raise DeploymentError(f"Feed status {field} is invalid")
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root_resolved) or not candidate.is_file():
            raise DeploymentError(f"Feed status {field} is outside or missing")
        if candidate.stat().st_size == 0:
            raise DeploymentError(f"Feed status {field} is empty")
        paths.append(candidate)
    if paths[0] == paths[1]:
        raise DeploymentError("Feed status paths must be distinct")
    return tuple(paths)


def finalize_deployment(
    root: Path,
    *,
    deployment_run_id: str,
    feed_succeeded: bool,
    status_path: Path,
    now: Callable[[], datetime],
) -> tuple[Path, ...]:
    root = Path(root)
    lease_path = root / LEASE_FILENAME
    lease = read_lease(lease_path, expected_run_id=deployment_run_id)
    if lease.state != "in_progress":
        raise DeploymentError("only an in_progress lease can be finalized")
    feed_paths = _feed_paths(root, status_path) if feed_succeeded else ()
    finished_at = _utc(now())
    if finished_at < lease.armed_at:
        raise DeploymentError("finalization clock precedes lease arming")
    registry = RateRegistry(root)
    try:
        durable = _durable_paths(root, registry)
    except RateStateError as exc:
        raise DeploymentError(str(exc)) from exc
    terminal = DeploymentLease(
        version=LEASE_VERSION,
        deployment_run_id=lease.deployment_run_id,
        state="success" if feed_succeeded else "failure",
        armed_at=lease.armed_at,
        finished_at=finished_at,
        feed_start_not_after=lease.feed_start_not_after,
        recovery_not_before=lease.recovery_not_before,
    )
    write_lease(lease_path, terminal)
    return durable + feed_paths


def _default_git(repo_root: Path) -> GitRunner:
    def run(args: list[str]) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise DeploymentError(f"git {' '.join(args)} failed") from exc
        return completed.stdout

    return run


def refresh_repository(repo_root: Path, *, git: GitRunner | None = None) -> None:
    runner = git or _default_git(Path(repo_root))
    runner(["fetch", "origin", "main"])
    runner(["merge", "--ff-only", "origin/main"])


def _relative_allowed(repo_root: Path, paths: Iterable[Path]) -> list[str]:
    root = Path(repo_root).resolve()
    relative: list[str] = []
    for path in paths:
        candidate = Path(path).resolve()
        if not candidate.is_relative_to(root):
            raise DeploymentError(f"generated path is outside repository: {path}")
        relative.append(str(candidate.relative_to(root)))
    return sorted(set(relative))


def publish_generated_state(
    repo_root: Path,
    paths: Iterable[Path],
    *,
    message: str,
    git: GitRunner | None = None,
) -> None:
    runner = git or _default_git(Path(repo_root))
    allowed = _relative_allowed(repo_root, paths)
    if not allowed:
        raise DeploymentError("generated publication allowlist is empty")
    staged_before = set(runner(["diff", "--cached", "--name-only"]).splitlines())
    if not staged_before.issubset(allowed):
        raise DeploymentError("unrelated paths are already staged")
    runner(["add", "--", *allowed])
    staged_after = set(runner(["diff", "--cached", "--name-only"]).splitlines())
    if not staged_after.issubset(allowed) or not staged_after:
        raise DeploymentError("generated publication staged an unexpected or empty set")
    runner(["diff", "--cached", "--check"])
    runner(["config", "user.name", "follow-the-money[bot]"])
    runner(["config", "user.email", "follow-the-money[bot]@users.noreply.github.com"])
    runner(["commit", "-m", message])
    runner(["push", "origin", "HEAD:main"])


def _write_output(path: str | None, mode: str) -> None:
    if path:
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(f"mode={mode}\n")


def _write_feed_status(path: Path, result: Any) -> None:
    status: dict[str, Any] = {"status": result.status, "warnings": result.warnings}
    if result.feed is not None and result.status in {"healthy", "degraded"}:
        cutoff = datetime.fromisoformat(result.feed["evidence_cutoff_at"])
        day = cutoff.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        status.update(
            {
                "run_id": result.feed["run_id"],
                "evidence_cutoff_at": result.feed["evidence_cutoff_at"],
                "dated_relative_path": f"daily/{day}/{result.feed['run_id']}.json",
                "latest_relative_path": "latest.json",
            }
        )
    Path(path).write_text(json.dumps(status), encoding="utf-8")


def _command_prepare(args: argparse.Namespace) -> int:
    from .cli import _load_app_config

    refresh_repository(Path(args.repo))
    config = _load_app_config(args.config)
    result = prepare_deployment(
        Path(args.root),
        config,
        deployment_run_id=args.run_id,
        now=lambda: datetime.now(UTC),
    )
    _write_output(args.output, result.mode)
    return 0


def _command_publish(args: argparse.Namespace) -> int:
    lease = read_lease(Path(args.root) / LEASE_FILENAME, expected_run_id=args.run_id)
    if lease.state not in {"bootstrap", "in_progress"}:
        raise DeploymentError("pre-network publication requires bootstrap or in_progress lease")
    publish_generated_state(
        Path(args.repo),
        allowlisted_paths(Path(args.root)),
        message=f"feeds: {lease.state}",
    )
    return 0


def _command_collect(args: argparse.Namespace) -> int:
    from .cli import FeedExecutionError, FeedInputError, run_feed

    status_path = Path(args.status_file)
    exit_path = Path(args.exit_file) if args.exit_file else None
    try:
        assert_feed_admitted(
            Path(args.root),
            deployment_run_id=args.run_id,
            now=lambda: datetime.now(UTC),
        )
        result = run_feed(config_path=args.config, output_root=str(args.root))
        _write_feed_status(status_path, result)
        code = result.exit_code
    except FeedInputError as exc:
        status_path.write_text(
            json.dumps({"status": "failure", "message": str(exc)}), encoding="utf-8"
        )
        code = 2
    except FeedExecutionError as exc:
        status_path.write_text(
            json.dumps({"status": "failure", "message": str(exc)}), encoding="utf-8"
        )
        code = 1
    if exit_path:
        exit_path.write_text(str(code), encoding="utf-8")
    return code


def _command_finalize(args: argparse.Namespace) -> int:
    paths = finalize_deployment(
        Path(args.root),
        deployment_run_id=args.run_id,
        feed_succeeded=args.feed_succeeded == "true",
        status_path=Path(args.status_file),
        now=lambda: datetime.now(UTC),
    )
    publish_generated_state(
        Path(args.repo),
        paths,
        message=f"feeds: {'success' if args.feed_succeeded == 'true' else 'failure'}",
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="follow-the-money-feed-deployment")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--repo", default=".")
    prepare.add_argument("--root", default="feeds")
    prepare.add_argument("--config", default=None)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--output", default=None)
    subparsers.add_parser("publish").add_argument("--phase", choices=("pre",), required=True)
    publish = subparsers.choices["publish"]
    publish.add_argument("--repo", default=".")
    publish.add_argument("--root", default="feeds")
    publish.add_argument("--run-id", required=True)
    collect = subparsers.add_parser("collect")
    collect.add_argument("--root", default="feeds")
    collect.add_argument("--config", default=None)
    collect.add_argument("--run-id", required=True)
    collect.add_argument("--status-file", default="feed-status.json")
    collect.add_argument("--exit-file", default=None)
    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--repo", default=".")
    finalize.add_argument("--root", default="feeds")
    finalize.add_argument("--run-id", required=True)
    finalize.add_argument("--status-file", default="feed-status.json")
    finalize.add_argument("--feed-succeeded", choices=("true", "false"), required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        if args.command == "prepare":
            return _command_prepare(args)
        if args.command == "publish":
            return _command_publish(args)
        if args.command == "collect":
            return _command_collect(args)
        return _command_finalize(args)
    except DeploymentError as exc:
        print(f"follow-the-money-feed-deployment: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
