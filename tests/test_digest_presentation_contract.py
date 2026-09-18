"""Static presentation-contract hierarchy regressions."""

from __future__ import annotations

import re
from pathlib import Path

from follow_the_money.config.model import SUPPORTED_FEED_PAYLOAD_TYPES

REPO_ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_CONTRACT = REPO_ROOT / "references" / "digest" / "presentation-contract.md"
COMPRESSION_CONTRACT = REPO_ROOT / "references" / "digest" / "compression.md"
DOMAINS_ROOT = REPO_ROOT / "references" / "digest" / "domains"
SKILL = REPO_ROOT / "SKILL.md"
CONTENT_FIRST_PRESENTATION_SECTION = "## Content-First Presentation Hierarchy"

DOMAIN_NAMES = tuple(SUPPORTED_FEED_PAYLOAD_TYPES)
REQUIRED_SECTIONS = (
    "## Domain Purpose",
    "## Evidence Fields",
    "## Recommended Representation",
    "## Forbidden Interpretation",
)
AFFIRMATIVE_ANALYTICAL_INSTRUCTIONS = (
    "rank items",
    "score items",
    "classify items as bullish",
    "predict outcomes",
    "recommend trades",
    "add a market-impact section",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section {heading!r}"
    return match.group("body")


def _content_first_section() -> str:
    contract = _read(PRESENTATION_CONTRACT)
    return _normalize(_section(contract, CONTENT_FIRST_PRESENTATION_SECTION))


def test_domain_contract_inventory_matches_supported_feed_payload_types():
    actual = tuple(sorted(path.stem for path in DOMAINS_ROOT.glob("*.md")))
    assert actual == tuple(sorted(DOMAIN_NAMES))


def test_global_contract_links_compression_and_each_domain_exactly_once():
    contract = _read(PRESENTATION_CONTRACT)

    assert contract.count("](compression.md)") == 1
    for domain in DOMAIN_NAMES:
        assert contract.count(f"](domains/{domain}.md)") == 1


def test_each_domain_contract_has_common_closed_evidence_structure():
    for domain in DOMAIN_NAMES:
        text = _read(DOMAINS_ROOT / f"{domain}.md")
        for heading in REQUIRED_SECTIONS:
            assert heading in text

        fields = _section(text, "## Evidence Fields")
        assert "closed" in fields.lower()
        assert "raw_metadata" not in fields

        lowered = text.lower()
        assert "missing" in lowered
        assert "null" in lowered
        assert "unavailable" in lowered
        assert "absent" in lowered or "omitted" in lowered
        assert "reconstruct" in lowered or "infer" in lowered


def test_global_compression_contract_owns_reconciliation_and_traceability():
    compression = _read(COMPRESSION_CONTRACT)
    lowered = compression.lower()

    assert (
        "domain total = individually summarized + represented through consolidation + omitted"
        in lowered
    )
    assert "every supporting item" in lowered
    assert "traceab" in lowered
    assert "editorial compression" in lowered
    assert "unimportant" in lowered
    assert "irrelevant" in lowered


def test_presentation_hierarchy_owns_field_and_compression_guidance():
    presentation = _read(PRESENTATION_CONTRACT).lower()
    compression = _read(COMPRESSION_CONTRACT).lower()
    skill = _read(SKILL).lower()

    assert "payload.type" in presentation
    assert "host agent owns evidence-preserving summarization and formatting" in presentation
    assert "group related evidence" in presentation
    assert (
        "domain total = individually summarized + represented through consolidation + omitted"
        in compression
    )
    for domain in DOMAIN_NAMES:
        fields = _section(_read(DOMAINS_ROOT / f"{domain}.md"), "## Evidence Fields")
        assert "closed" in fields.lower()

    for duplicated_rule in (
        "payload.type",
        "semantic_context",
        "form13f",
        "form4",
        "beneficial_ownership",
        "current_metrics",
        "delta_metrics",
        "affected_scope",
        "closed evidence-field",
        "feed data status",
        "evidence_cutoff_at",
        "group related evidence",
        "derive editorial headings",
        "domain total",
        "individually summarized",
        "represented through consolidation",
    ):
        assert duplicated_rule not in skill


def test_content_first_hierarchy_preserves_complete_secondary_audit_surface():
    hierarchy = _content_first_section()

    assert "semantic priority" in hierarchy
    assert "primary substantive surface" in hierarchy
    assert "current-window updates" in hierarchy
    assert "secondary audit surface" in hierarchy

    for audit_term in (
        "feed data status",
        "evidence_cutoff_at",
        "coverage",
        "freshness",
        "warnings",
        "degradation",
        "source availability",
        "reconciliation",
        "traceability",
        "omission disclosure",
        "limitations",
    ):
        assert audit_term in hierarchy


def test_degraded_and_zero_update_presentation_remain_bounded_and_truthful():
    hierarchy = _content_first_section()

    for term in (
        "concise data-limitation caveat",
        "materially affects interpretation",
        "does not replace",
        "complete audit",
        "zero presentable current-window updates",
        "creates no content",
        "fabricated",
        "distinguish an empty window from collection or provider problems",
    ):
        assert term in hierarchy


def test_local_provenance_stays_attached_to_the_content_it_supports():
    hierarchy = _content_first_section()

    for term in (
        "statement-local provenance or attribution remains sufficiently close",
        "global provider, coverage, and reconciliation metadata may remain",
    ):
        assert term in hierarchy


def test_content_first_does_not_alter_the_fail_closed_failure_path():
    hierarchy = _content_first_section()

    for term in (
        "does not alter or bypass the existing fail-closed behavior",
        "retrieval, validation, or preparation failure still produces no normal digest",
    ):
        assert term in hierarchy


def test_skill_does_not_own_digest_presentation_ordering():
    skill = _normalize(_read(SKILL))

    # SKILL.md may point at the presentation contract by name; it must not
    # re-encode the contract's surface vocabulary or ordering itself.
    for ordering_rule in (
        "audit-first",
        "primary substantive surface",
        "secondary audit surface",
    ):
        assert ordering_rule not in skill


def test_content_first_is_semantic_not_item_ranking_or_fixed_structure():
    hierarchy = _content_first_section()
    contract = _normalize(_read(PRESENTATION_CONTRACT))

    for term in (
        "importance",
        "ranking",
        "significant",
        "analysis",
        "relevance filter",
        "fixed markdown structure",
        "heading levels",
        "section order",
    ):
        assert term in hierarchy

    for affirmative_instruction in (
        "rank current-window updates",
        "assign importance to updates",
        "filter updates by relevance",
        "use a fixed markdown template",
    ):
        assert affirmative_instruction not in contract


def test_safety_vocabulary_is_present_without_affirmative_analytical_instructions():
    hierarchy = "\n".join(
        [
            _read(PRESENTATION_CONTRACT),
            _read(COMPRESSION_CONTRACT),
            *(_read(DOMAINS_ROOT / f"{domain}.md") for domain in DOMAIN_NAMES),
        ]
    ).lower()

    for term in (
        "importance",
        "ranking",
        "market impact",
        "prediction",
        "recommendation",
        "trading",
    ):
        assert term in hierarchy
    for instruction in AFFIRMATIVE_ANALYTICAL_INSTRUCTIONS:
        assert instruction not in hierarchy


def test_presentation_hierarchy_is_static_host_agent_guidance():
    hierarchy = "\n".join(
        [
            _read(PRESENTATION_CONTRACT),
            _read(COMPRESSION_CONTRACT),
            *(_read(DOMAINS_ROOT / f"{domain}.md") for domain in DOMAIN_NAMES),
        ]
    ).lower()

    assert "host agent" in hierarchy
    assert "validated" in hierarchy
    assert "no runtime" in hierarchy
    for forbidden_runtime in ("renderer", "template engine", "prompt pipeline", "orchestration"):
        assert forbidden_runtime in hierarchy
