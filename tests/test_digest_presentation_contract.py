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
    "## Reader-Facing Unit",
    "## Current Membership",
    "## Supporting Evidence",
    "## Evidence Fields",
    "## Recommended Representation",
    "## Forbidden Interpretation",
)
MEMBERSHIP_AUTHORITIES = {
    "news": "source.published_at",
    "macro_release": "payload.released_at",
    "policy": "payload.announced_at",
    "positioning": "payload.as_of",
    "filing": "payload.accepted_at",
}
AFFIRMATIVE_ANALYTICAL_INSTRUCTIONS = (
    "rank items",
    "score items",
    "classify items as bullish",
    "predict outcomes",
    "recommend trades",
    "add a market-impact section",
)
REMOVED_V1_RECONCILIATION = (
    "domain total = individually summarized + represented through consolidation + omitted",
    "report the domain total and all three category counts",
    "discloses the omission as editorial compression",
    "secondary audit surface",
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


def _hierarchy() -> str:
    return _normalize(
        "\n".join(
            [
                _read(PRESENTATION_CONTRACT),
                _read(COMPRESSION_CONTRACT),
                *(_read(DOMAINS_ROOT / f"{domain}.md") for domain in DOMAIN_NAMES),
            ]
        )
    )


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

        normalized = _normalize(text)
        assert "preparation" in normalized
        assert MEMBERSHIP_AUTHORITIES[domain] in text
        assert "missing" in normalized
        assert "null" in normalized
        assert "unavailable" in normalized
        assert "absent" in normalized or "omitted" in normalized
        assert "reconstruct" in normalized or "infer" in normalized


def test_hierarchy_consumes_only_prepared_updates_and_compact_status():
    hierarchy = _hierarchy()

    for surface in ("content.updates", "status.domains", "status.limitations"):
        assert surface in hierarchy
    assert "digestcontext` version `2`" in hierarchy


def test_hierarchy_removes_v1_reconciliation_and_omission_accounting():
    hierarchy = _hierarchy()

    for removed in REMOVED_V1_RECONCILIATION:
        assert removed not in hierarchy
    assert "not required to display every feed item" in hierarchy
    assert "not required to display every prepared update" in hierarchy


def test_global_compression_contract_owns_claim_support_and_non_exhaustiveness():
    compression = _normalize(_read(COMPRESSION_CONTRACT))

    for term in (
        "content.updates",
        "claim",
        "traceab",
        "omission",
        "unimportant",
        "irrelevant",
        "not required to display every prepared update",
        "authoritative feed",
    ):
        assert term in compression


def test_domain_references_document_the_reader_facing_unit_and_membership_authority():
    for domain in DOMAIN_NAMES:
        text = _read(DOMAINS_ROOT / f"{domain}.md")
        unit = _normalize(_section(text, "## Reader-Facing Unit"))
        membership = _normalize(_section(text, "## Current Membership"))

        assert "unit" in unit
        assert MEMBERSHIP_AUTHORITIES[domain] in membership
        assert "[window.start, window.end)" in membership
        assert "never" in membership
        evidence = _normalize(_section(text, "## Supporting Evidence"))
        assert "unit" in evidence


def test_presentation_hierarchy_preserves_the_host_agent_boundary():
    presentation = _normalize(_read(PRESENTATION_CONTRACT))

    assert "payload.type" in presentation
    assert "host agent owns evidence-preserving summarization and formatting" in presentation
    assert "group related evidence" in presentation
    assert "statement-local provenance or attribution remains sufficiently close" in presentation
    assert "validated" in presentation
    assert "no runtime" in presentation
    for forbidden_runtime in ("renderer", "template engine", "prompt pipeline", "orchestration"):
        assert forbidden_runtime in presentation

    for duplicated_rule in (
        "semantic_context",
        "form13f",
        "form4",
        "beneficial_ownership",
        "current_metrics",
        "delta_metrics",
        "affected_scope",
        "evidence_cutoff_at",
        "group related evidence",
        "derive editorial headings",
    ):
        assert duplicated_rule not in _normalize(_read(SKILL))


def test_hierarchy_does_not_grant_host_agent_membership_or_audit_ownership():
    hierarchy = _hierarchy()

    for revoked in (
        "host agent classifies",
        "host agent must classify",
        "host agent owns current",
        "host agent owns reference-state",
        "host agent owns omission",
        "reconcile every item",
        "assign each item to a representation category",
    ):
        assert revoked not in hierarchy
    assert "do not reclassify a feed item as current" in hierarchy


def test_content_first_hierarchy_preserves_conditional_disclosure():
    hierarchy = _content_first_section()

    assert "semantic priority" in hierarchy
    assert "primary substantive surface" in hierarchy
    assert "content.updates" in hierarchy
    assert "materially affect a reader's understanding" in hierarchy


def test_degraded_and_zero_update_presentation_remain_bounded_and_truthful():
    hierarchy = _content_first_section()

    for term in (
        "concise data-limitation caveat",
        "materially affects interpretation",
        "must not present the feed as healthy",
        "no deterministically eligible current updates",
        "creates no content",
        "fabricated",
        "does not reproduce the reference evidence",
    ):
        assert term in hierarchy


def test_content_first_does_not_alter_the_fail_closed_failure_path():
    hierarchy = _content_first_section()

    for term in (
        "does not alter or bypass the existing fail-closed behavior",
        "retrieval, validation, or preparation failure still produces no normal digest",
    ):
        assert term in hierarchy


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
    hierarchy = _hierarchy()

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
    hierarchy = _hierarchy()

    assert "host agent" in hierarchy
    assert "validated" in hierarchy
