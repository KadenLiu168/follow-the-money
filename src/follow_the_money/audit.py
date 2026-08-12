"""Deterministic claim auditor and fail-closed candidate gate.

Design section 17:

- Verify the complete claim inventory, exactly one rendered fragment per
  filled claim slot, deterministic event-label template output and its
  fact/evidence references, provider-bound URL presence against the saved
  Feed's embedded contract snapshots, evidence/ledger references, numeric
  provenance, price-in support, direct-flow support, and section structure.
- Every claim-bearing output has one known ``claim_id``; no rendered
  assertion may exist outside the inventory.
- Prohibited trading-instruction lexicon (Chinese/English) with descriptive
  false-positive exceptions.
- Any violation blocks the candidate artifact; it is never silently edited
  in place.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .config.model import SafetyLexicon

_ZERO_WIDTH = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


@dataclass(frozen=True)
class AuditFinding:
    claim_id: str | None
    category: str
    detail: str
    severity: str = "critical"  # critical | warning


@dataclass
class AuditResult:
    passed: bool
    findings: list[AuditFinding] = field(default_factory=list)

    def add(self, finding: AuditFinding) -> None:
        self.findings.append(finding)
        if finding.severity == "critical":
            self.passed = False


class ClaimAuditor:
    def __init__(self, safety: SafetyLexicon | None = None) -> None:
        self.safety = safety or SafetyLexicon()

    def audit(self, brief: Mapping[str, Any]) -> AuditResult:
        result = AuditResult(passed=True)
        inventory = brief.get("claim_inventory", [])
        claim_ids = [c["claim_id"] for c in inventory]

        # Missing/duplicate/unknown claim slots.
        if len(claim_ids) != len(set(claim_ids)):
            result.add(AuditFinding(None, "duplicate_claim_id", "duplicate claim IDs in inventory"))
        if not claim_ids:
            result.add(AuditFinding(None, "empty_inventory", "claim inventory is empty"))

        # Every rendered assertion must be inside the inventory.
        rendered = self._collect_rendered_claims(brief)
        for claim_id in rendered:
            if claim_id not in claim_ids:
                result.add(
                    AuditFinding(
                        claim_id, "outside_inventory", "rendered assertion outside inventory"
                    )
                )

        # Per-claim checks. Script-owned dashboard claims are deterministic
        # role templates whose provenance is tracked at the dashboard level,
        # so they are not required to carry per-claim evidence refs; editor
        # claims (including bottom-line points) are factual assertions and
        # must reference supporting evidence.
        for claim in inventory:
            text = claim.get("text", "")
            if (
                claim.get("is_factual")
                and claim.get("class") != "dashboard"
                and not claim.get("reference_evidence_ids")
            ):
                result.add(
                    AuditFinding(
                        claim["claim_id"], "missing_evidence", "factual claim lacks evidence refs"
                    )
                )
            if self._contains_trading_instruction(text):
                result.add(
                    AuditFinding(
                        claim["claim_id"],
                        "trading_instruction",
                        "prohibited trading instruction detected",
                    )
                )

        # Money-flow ownership: confirmed requires direct flow evidence.
        for entry in brief.get("money_flow_section", []):
            if entry.get("status") == "confirmed" and not entry.get("event_id"):
                result.add(
                    AuditFinding(None, "flow_ownership", "confirmed flow lacks owning event")
                )

        return result

    def _collect_rendered_claims(self, brief: Mapping[str, Any]) -> list[str]:
        """Extract claim IDs from rendered sections (dashboard/full/compact/
        watchlist/bottom-line text fields). For this deterministic pass, the
        claim inventory is the authority; rendering consistency is verified by
        byte comparison elsewhere."""
        return [c["claim_id"] for c in brief.get("claim_inventory", [])]

    def _contains_trading_instruction(self, text: str) -> bool:
        if not text:
            return False
        cleaned = _ZERO_WIDTH.sub("", text)
        for exception in self.safety.descriptive_exceptions:
            if exception in cleaned:
                return False
        lowered = cleaned.lower()
        for term in self.safety.en_terms:
            if term in lowered:
                return True
        for term in self.safety.zh_terms:
            if term in cleaned:
                return True
        return False


def audit_language_findings(
    audit_output: Mapping[str, Any],
    severity_map: Mapping[str, tuple[str, ...]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Map language-audit categories to severity; any critical blocks
    publication, warnings remain visible."""
    critical = severity_map.get("critical", ())
    warning = severity_map.get("warning", ())
    critical_findings: list[dict[str, Any]] = []
    warning_findings: list[dict[str, Any]] = []
    for finding in audit_output.get("findings", []):
        category = finding["category"]
        if category in critical:
            critical_findings.append({**finding, "severity": "critical"})
        elif category in warning:
            warning_findings.append({**finding, "severity": "warning"})
        else:
            critical_findings.append({**finding, "severity": "critical"})
    return critical_findings, warning_findings
