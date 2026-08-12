"""Gate 13.7 — complete repository quality gate is executable."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts import quality_gate

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_quality_gate_runs_all_required_checks():
    env = os.environ.copy()
    env["FOLLOW_THE_MONEY_QUALITY_TEST"] = "1"
    completed = subprocess.run(
        [".venv/bin/python", "scripts/quality_gate.py"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    output = completed.stdout.lower()
    for label in ("lint", "format", "type-check", "build", "workflow", "cli"):
        assert label in output


def test_quality_gate_uses_a_static_type_checker(monkeypatch):
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setenv("FOLLOW_THE_MONEY_QUALITY_TEST", "1")
    monkeypatch.setattr(quality_gate, "_run", lambda label, command: calls.append((label, command)))

    assert quality_gate.main() == 0

    type_commands = [command for label, command in calls if label == "type-check"]
    assert len(type_commands) == 1
    assert type_commands[0][1:3] == ["-m", "mypy"]
