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
DOMAINS = ("news", "macro_release", "policy", "positioning", "filing")


def test_normal_skill_caller_graph_is_canonical_main_remote_only():
    contract = FEED_REFERENCE.read_text(encoding="utf-8")
    lowered = contract.lower()

    assert "scripts/skill/prepare-feed" in contract
    assert "canonical-main" in lowered
    assert "raw.githubusercontent.com" in lowered
    assert "github rest api" in lowered
    assert "local" in lowered and "fallback" in lowered
    assert "scripts/feed/follow-the-money-feed locally" not in contract


def test_skill_generates_only_the_current_information_digest():
    lowered = SKILL.read_text(encoding="utf-8").lower()
    assert "disable-model-invocation: true" in lowered
    assert (
        "generate the current evidence-based information digest from the published feed" in lowered
    )
    assert (
        "published feed -> validation -> host agent summarization/formatting -> evidence-based information digest"
        in lowered
    )
    assert "scripts/skill/prepare-feed" in lowered
    assert "references/feed-contract.md" in lowered
    assert "references/safety-boundary.md" in lowered
    for term in (
        "without requesting or accepting",
        "company",
        "asset",
        "topic",
        "time range",
        "research question",
        "historical",
        "current feed window",
        "feed data status",
        "evidence cutoff",
        "source provenance",
        "freshness",
        "coverage",
        "limitations",
        "total item count",
        "individually summarized",
        "consolidated",
        "omitted",
        "reconcile",
    ):
        assert term in lowered


def test_normal_skill_output_does_not_require_financial_judgment_sections():
    lowered = SKILL.read_text(encoding="utf-8").lower()
    for forbidden in (
        "financial intelligence briefing",
        "financial research report",
        "significance section",
        "anomaly section",
        "signal section",
        "prediction section",
        "market-impact section",
        "investment-judgment section",
        "trading section",
    ):
        assert forbidden not in lowered


def test_agents_and_readmes_describe_the_feed_only_boundary():
    agents = AGENTS.read_text(encoding="utf-8")
    lowered_agents = agents.lower()
    assert "information digest" in lowered_agents
    assert "host agent summarization/formatting" in lowered_agents
    assert "不读取历史 feed 或 checkpoint" in lowered_agents

    english = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    assert "evidence-based information digest skill" in english.lower()
    assert "证据驱动信息摘要 Skill" in chinese
    for text in (english, chinese):
        lowered = text.lower()
        assert "evidence-preserving" in lowered
        assert "information digest" in lowered
        assert "retained" in lowered
        assert "claimauditor" not in lowered


def test_current_docs_describe_exactly_the_published_domains():
    for path in DOCUMENTATION:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "feed" in lowered, path
        assert all(domain in lowered for domain in DOMAINS), path
        assert "scripts/skill/prepare-feed" in text, path
        assert "local" in lowered or "本地" in lowered, path


def test_current_docs_do_not_claim_removed_capabilities_as_output():
    for path in DOCUMENTATION + (SKILL,):
        lowered = path.read_text(encoding="utf-8").lower()
        assert "produces market_data" not in lowered, path
        assert "produces flow" not in lowered, path
        assert "produces calendar" not in lowered, path
        assert "ranking output" not in lowered, path
        assert "trading instruction" not in lowered, path
