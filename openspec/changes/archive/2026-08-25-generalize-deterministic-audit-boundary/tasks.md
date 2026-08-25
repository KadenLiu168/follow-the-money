## 1. Reconfirm the Audit Boundary and Add RED Coverage

- [x] 1.1 Re-run repository caller, schema, active-Change, and documentation searches before implementation; confirm there is still no production `ClaimAuditor` caller or external audit schema, and stop to document any real dependency or contract conflict discovered.
- [x] 1.2 Add focused failing tests for standalone text safety auditing: Chinese and English prohibited instructions, configured descriptive exceptions, optional finding identity, use without a Brief-shaped Mapping, identical repeated results, and unchanged no-LLM/model/credential behavior.
- [x] 1.3 Add focused failing structured-audit tests for empty inventory, duplicate identities, missing/non-string/empty/whitespace identities returning deterministic failed results, independently supplied outside-inventory identities, both explicit evidence-obligation values, confirmed-flow ownership, non-confirmed flow behavior, and reuse of text safety semantics.
- [x] 1.4 Add architecture regression assertions that the normal tests no longer construct the legacy Brief dictionary, no removed Editor/Brief sections or future Agent objects are introduced, no serialized audit schema exists, and Feed/Agent entry paths do not call the retained auditor.

## 2. Implement the Workflow-Neutral Deterministic Boundary

- [x] 2.1 Introduce the smallest immutable/typed audit-owned structured inputs needed for claim records, independently submitted identities, and confirmed-flow ownership; do not add serialization, adapters, an all-purpose context, or future workflow state.
- [x] 2.2 Implement the standalone text safety operation over the existing `SafetyLexicon`, preserving zero-width cleanup, Chinese/English matching, descriptive exceptions, optional claim attribution, `AuditFinding`, `AuditResult`, and critical-finding semantics.
- [x] 2.3 Implement structured identity validation before any identity use so missing, non-string, empty, or whitespace-only required identities fail through deterministic audit results without incidental Mapping/type exceptions or synthesized normalization.
- [x] 2.4 Implement structured inventory, duplicate, independently supplied membership, explicit direct-evidence obligation, and confirmed-flow ownership checks, and reuse the standalone text safety rule for each valid structured claim.
- [x] 2.5 Remove the legacy Brief-shaped Mapping entry point and dashboard/section policy inference, migrating current tests without a compatibility shim unless task 1.1 found a concrete current dependency requiring the minimum documented exception.
- [x] 2.6 Replace `audit.py` module-level and local comments/docstrings with a truthful description limited to the retained deterministic identity, membership, evidence, ownership, and text-safety responsibilities.

## 3. Align Retained-Library Tests and Scope

- [x] 3.1 Update `tests/test_no_llm_contract.py` to exercise the neutral text boundary while retaining its deterministic and no-LLM assertions; keep `SafetyLexicon` terms and matching behavior unchanged.
- [x] 3.2 Run the focused audit and no-LLM tests, resolve only ECO-30 regressions, and verify malformed/reordered/repeated inputs produce stable fail-closed results.
- [x] 3.3 Review the Apply diff against scope: implementation remains centered on `audit.py` and focused tests, the `deterministic-research-engine` delta agrees with behavior, and there are no Feed/provider/scoring/config/schema, production wiring, future Agent contract, broad SKILL/docs, or archived-Change edits.

## 4. Canonical Verification

- [x] 4.1 Prepare the locked development environment with `uv sync --frozen --all-groups`.
- [x] 4.2 Run the canonical repository gate with `.venv/bin/python scripts/quality_gate.py` and record the complete result.
- [x] 4.3 Run `openspec doctor`, `openspec validate generalize-deterministic-audit-boundary --strict`, and `openspec validate --all --strict`; fix only ECO-30 planning/contract inconsistencies and record the actual results.
- [x] 4.4 Complete the AGENTS.md final review, explicitly report any unresolved conflict/risk or follow-up for ECO-31, and leave archive, Linear mutation, commit, and push for separately authorized workflows.
