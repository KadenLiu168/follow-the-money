"""Deterministic identity, evidence, ownership, and text-safety auditing."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from .config.model import SafetyLexicon

_ZERO_WIDTH = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


@dataclass(frozen=True)
class AuditClaim:
    """The claim fields consumed by the structured audit rules."""

    claim_id: str
    text: str
    requires_direct_evidence: bool
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", tuple(self.evidence_ids))


@dataclass(frozen=True)
class AuditFlow:
    """Confirmed-flow state and its optional owning Event identity."""

    confirmed: bool
    owning_event_id: str | None = None


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

    def audit_text(self, text: str, *, claim_id: str | None = None) -> AuditResult:
        result = AuditResult(passed=True)
        if self._contains_trading_instruction(text):
            result.add(
                AuditFinding(
                    claim_id,
                    "trading_instruction",
                    "prohibited trading instruction detected",
                )
            )
        return result

    def audit_claims(
        self,
        claims: Sequence[AuditClaim],
        submitted_claim_ids: Sequence[str],
        flows: Sequence[AuditFlow] = (),
    ) -> AuditResult:
        result = AuditResult(passed=True)
        inventory = tuple(claims)
        submitted = tuple(submitted_claim_ids)

        if not inventory:
            result.add(AuditFinding(None, "empty_inventory", "claim inventory is empty"))

        valid_claims: list[AuditClaim] = []
        for claim in inventory:
            if not self._is_valid_identity(claim.claim_id):
                result.add(
                    AuditFinding(
                        None,
                        "invalid_claim_id",
                        "claim identity must be a non-empty string",
                    )
                )
                continue
            valid_claims.append(claim)

        claim_ids = [claim.claim_id for claim in valid_claims]
        if len(claim_ids) != len(set(claim_ids)):
            result.add(AuditFinding(None, "duplicate_claim_id", "duplicate claim IDs in inventory"))

        valid_submitted: list[str] = []
        for claim_id in submitted:
            if not self._is_valid_identity(claim_id):
                result.add(
                    AuditFinding(
                        None,
                        "invalid_claim_id",
                        "claim identity must be a non-empty string",
                    )
                )
                continue
            valid_submitted.append(claim_id)

        inventory_ids = set(claim_ids)
        for claim_id in sorted(valid_submitted):
            if claim_id not in inventory_ids:
                result.add(
                    AuditFinding(
                        claim_id,
                        "outside_inventory",
                        "rendered assertion outside inventory",
                    )
                )

        for claim in sorted(valid_claims, key=self._claim_sort_key):
            if claim.requires_direct_evidence and not claim.evidence_ids:
                result.add(
                    AuditFinding(
                        claim.claim_id,
                        "missing_evidence",
                        "factual claim lacks evidence refs",
                    )
                )
            result.findings.extend(self.audit_text(claim.text, claim_id=claim.claim_id).findings)
            if any(finding.severity == "critical" for finding in result.findings):
                result.passed = False

        for flow in flows:
            if flow.confirmed and not flow.owning_event_id:
                result.add(
                    AuditFinding(None, "flow_ownership", "confirmed flow lacks owning event")
                )

        return result

    @staticmethod
    def _is_valid_identity(identity: object) -> bool:
        return isinstance(identity, str) and bool(identity.strip())

    @staticmethod
    def _claim_sort_key(claim: AuditClaim) -> tuple[str, str, str, str]:
        return (
            claim.claim_id,
            repr(claim.text),
            repr(claim.requires_direct_evidence),
            repr(claim.evidence_ids),
        )

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
