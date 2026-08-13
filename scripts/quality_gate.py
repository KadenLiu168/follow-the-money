"""Run the repository's final credential-free quality checks."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, command: list[str]) -> None:
    print(f"[{label}] {' '.join(command)}")
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", "/tmp/follow-the-money-uv-cache")
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def main() -> int:
    python = sys.executable
    if not os.environ.get("FOLLOW_THE_MONEY_QUALITY_TEST"):
        _run("unit/integration/regression/security", [python, "-m", "pytest", "-q"])
    _run("workflow", [python, "scripts/validate_workflows.py"])
    _run("cli", [python, "-m", "follow_the_money.feed.cli", "--help"])
    _run("lint", [python, "-m", "ruff", "check", "src", "tests", "scripts"])
    _run("format", [python, "-m", "ruff", "format", "--check", "src", "tests", "scripts"])
    _run("type-check", [python, "-m", "mypy", "src", "scripts"])
    _run(
        "build",
        ["uv", "build", "--offline", "--wheel", "--out-dir", "/tmp/follow-the-money-dist"],
    )
    print("quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
