"""Published Feed caller and documentation boundary regressions."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "SKILL.md"
AGENTS = REPO_ROOT / "AGENTS.md"
FEED_REFERENCE = REPO_ROOT / "references" / "feed-contract.md"
PRESENTATION_CONTRACT = REPO_ROOT / "references" / "digest" / "presentation-contract.md"
COMPRESSION_CONTRACT = REPO_ROOT / "references" / "digest" / "compression.md"
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


def test_skill_is_a_thin_current_feed_orchestration_boundary():
    lowered = SKILL.read_text(encoding="utf-8").lower()
    normalized = " ".join(lowered.split())
    assert "disable-model-invocation: true" in lowered
    assert (
        "generate the current evidence-based information digest from the published feed" in lowered
    )
    assert "validated feed -> digestcontext -> host agent -> evidence-preserving digest" in lowered
    assert "scripts/skill/prepare-feed" in lowered
    assert "references/feed-contract.md" in lowered
    assert "references/safety-boundary.md" in lowered
    assert "references/digest/presentation-contract.md" in lowered
    assert "non-persisted" in lowered
    for term in (
        "without requesting or accepting",
        "company",
        "asset",
        "topic",
        "time range",
        "research question",
        "surface the exact stderr and stop",
        "never substitute local, stale, partial, historical, or unvalidated data",
        "do not introduce or infer",
        "financial analysis",
        "investment recommendation",
    ):
        assert term in normalized

    for duplicated_rule in (
        "five-domain",
        "feed data status and evidence cutoff",
        "domain and provider coverage",
        "current updates from the feed",
        "source provenance and freshness",
        "data-quality, unavailable-source, and compression limitations",
        "payload.type",
        "semantic_context",
        "domain total",
        "group related evidence",
        "derive editorial headings",
    ):
        assert duplicated_rule not in normalized


def test_feed_contract_owns_feed_details():
    lowered = FEED_REFERENCE.read_text(encoding="utf-8").lower()

    assert "manifest declares exactly one artifact for each domain" in lowered
    assert all(domain in lowered for domain in DOMAINS)
    for term in (
        "evidence_cutoff_at",
        "run_id",
        "content_digest",
        "source provenance",
        "provider freshness",
        "coverage",
        "degraded",
    ):
        assert term in lowered


def test_presentation_contract_owns_prepared_update_consumption():
    lowered = PRESENTATION_CONTRACT.read_text(encoding="utf-8").lower()

    for term in (
        "content.updates",
        "status.domains",
        "status.limitations",
        "current-membership",
        "claim support",
        "non-exhaustive",
        "source provenance",
        "conditions materially affect a reader's understanding",
        "compact limitation",
    ):
        assert term in lowered
    for removed in (
        "feed data status",
        "evidence_cutoff_at",
        "secondary audit surface",
        "full feed evidence, provider outcomes, freshness records, counts",
    ):
        assert removed not in lowered


def test_presentation_hierarchy_owns_field_and_compression_guidance():
    presentation = PRESENTATION_CONTRACT.read_text(encoding="utf-8").lower()
    compression = COMPRESSION_CONTRACT.read_text(encoding="utf-8").lower()

    assert "validated" in presentation
    assert "payload.type" in presentation
    for term in (
        "not required to display every prepared update",
        "claim",
        "traceab",
        "omission",
        "authoritative feed",
    ):
        assert term in compression
    for removed in (
        "report the domain total",
        "individually summarized",
        "represented through consolidation",
        "must reconcile",
        "counts as omitted",
    ):
        assert removed not in compression


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
