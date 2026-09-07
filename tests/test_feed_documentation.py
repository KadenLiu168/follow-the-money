"""Published Feed caller and documentation boundary regressions."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "SKILL.md"
AGENTS = REPO_ROOT / "AGENTS.md"
FEED_REFERENCE = REPO_ROOT / "references" / "feed-contract.md"
DOCUMENTATION = (
    FEED_REFERENCE,
    REPO_ROOT / "README.md",
    REPO_ROOT / "README.zh-CN.md",
    REPO_ROOT / "docs" / "architecture.md",
    REPO_ROOT / "docs" / "feed-contract.md",
)


def test_normal_skill_caller_graph_is_canonical_main_remote_only():
    contract = FEED_REFERENCE.read_text(encoding="utf-8")

    assert "scripts/skill/prepare-feed" in contract
    assert "canonical" in contract
    assert "raw.githubusercontent.com" in contract
    assert "zero github rest api requests" in contract.lower()
    assert "local producer" in contract
    assert "fallback" in contract
    assert "scripts/feed/follow-the-money-feed locally" not in contract


def test_skill_generates_only_the_current_feed_briefing():
    skill = SKILL.read_text(encoding="utf-8")
    lowered = skill.lower()

    assert "disable-model-invocation: true" in lowered
    assert "generate the current evidence-based financial intelligence briefing" in lowered
    assert "scripts/skill/prepare-feed" in skill
    assert "references/feed-contract.md" in skill
    assert "references/safety-boundary.md" in skill
    assert "without requesting or accepting" in lowered
    assert "historical" in lowered
    assert "prior publication or checkpoint" in lowered
    assert "requested research report" not in lowered
    assert "latest capital-flow changes" in lowered
    assert "new significant events" in lowered
    assert "anomalous signals" in lowered


def test_agents_keeps_private_capabilities_outside_the_current_briefing_skill():
    agents = AGENTS.read_text(encoding="utf-8")

    assert "不是通用金融研究助手" in agents
    assert "不读取历史 Feed 或 checkpoint" in agents
    assert "不是 Skill 行为" in agents
    assert "Current financial intelligence briefing" in agents


def test_all_changed_docs_name_remote_entry_and_retain_explicit_local_boundary():
    for path in DOCUMENTATION:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "scripts/skill/prepare-feed" in text, path
        assert "canonical-main" in lowered, path
        assert "github rest api" in lowered, path
        assert "hosted" in lowered, path
        assert "development" in lowered, path
        assert "diagnostic" in lowered, path
        assert "operator" in lowered, path


def test_current_runtime_docs_reject_stale_commit_discovery_claims():
    for path in DOCUMENTATION:
        lowered = path.read_text(encoding="utf-8").lower()
        assert "commit-pinned" not in lowered, path
        assert "git reference api" not in lowered, path
        assert "api.github.com" not in lowered, path


def test_normal_documentation_rejects_provider_or_local_fallback_claims():
    for path in DOCUMENTATION:
        lowered = path.read_text(encoding="utf-8").lower()
        assert "remote failure" in lowered, path
        assert "local fallback" in lowered, path
