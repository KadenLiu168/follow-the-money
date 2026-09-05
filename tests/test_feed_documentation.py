"""Published Feed caller and documentation boundary regressions."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTATION = (
    REPO_ROOT / "SKILL.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "README.zh-CN.md",
    REPO_ROOT / "docs" / "architecture.md",
    REPO_ROOT / "docs" / "feed-contract.md",
)


def test_normal_skill_caller_graph_is_commit_pinned_remote_only():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    normal = skill[skill.index("## Daily flow") :]

    assert "scripts/skill/prepare-feed" in normal
    assert "commit-pinned" in normal
    assert "local producer" in normal
    assert "fallback" in normal
    assert "scripts/feed/follow-the-money-feed locally" not in normal


def test_skill_describes_normal_invocation_as_credential_free_feed_consumption():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    lowered = skill.lower()

    assert "collect the evidence feed" not in lowered
    assert "retrieve" in lowered
    assert "consume" in lowered
    assert "scripts/skill/prepare-feed" in skill
    assert "no github token" in lowered
    assert "no provider credentials" in lowered


def test_all_changed_docs_name_remote_entry_and_retain_explicit_local_boundary():
    for path in DOCUMENTATION:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "scripts/skill/prepare-feed" in text, path
        assert "commit-pinned" in lowered, path
        assert "hosted" in lowered, path
        assert "development" in lowered, path
        assert "diagnostic" in lowered, path
        assert "operator" in lowered, path


def test_normal_documentation_rejects_provider_or_local_fallback_claims():
    for path in DOCUMENTATION:
        lowered = path.read_text(encoding="utf-8").lower()
        assert "remote failure" in lowered, path
        assert "local fallback" in lowered, path
