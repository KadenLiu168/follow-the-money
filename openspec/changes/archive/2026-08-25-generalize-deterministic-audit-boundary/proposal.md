## Why

`ClaimAuditor` remains a valuable deterministic safety library, but its current `brief: Mapping` entry point and dashboard/section vocabulary preserve a removed Editor/Brief workflow as an accidental contract. ECO-30 is the remaining Phase 2 audit-boundary decontamination step before ECO-31 can assess the complete Pre-Agent living baseline without carrying that obsolete shape forward.

## What Changes

- **BREAKING**: replace the legacy Brief-shaped Mapping as the normal audit input with a small, typed, audit-owned Python boundary; tests are migrated rather than preserving the obsolete shape as a compatibility shim.
- Support deterministic text safety auditing without requiring claim inventory, presentation sections, or future Agent structures, while retaining optional claim identity on findings.
- Support structured claim auditing over only claim identity, claim text, direct-evidence obligation, evidence references, independently supplied submitted/rendered claim identities, and confirmed-flow ownership information.
- Replace the `class != "dashboard"` evidence exemption with an explicit workflow-neutral evidence obligation while preserving the accepted missing-evidence behavior.
- Fail closed through `AuditResult` semantics for missing or invalid required claim identity, and make `outside_inventory` independently observable.
- Preserve `AuditFinding`, `AuditResult`, critical-finding failure behavior, `SafetyLexicon`, trading-instruction matching, descriptive exceptions, and confirmed-flow policy.
- Correct only stale comments and docstrings local to `audit.py`; do not define future Agent contracts, add orchestration or production wiring, create serialized schemas, or perform ECO-31 baseline cleanup.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-research-engine`: generalize the retained deterministic safety audit into workflow-neutral text and structured-claim boundaries, with explicit evidence obligations, independently observable submitted membership, and fail-closed identity validation.

## Impact

- Primary implementation surface: `src/follow_the_money/audit.py`.
- Focused verification surface: audit-focused tests and the retained-library assertions in `tests/test_no_llm_contract.py`.
- Contract surface: a delta to `openspec/specs/deterministic-research-engine/spec.md` only; `deterministic-core-retention` already describes safety audit over submitted text and retained no-caller status without requiring a Brief shape.
- No expected changes to Feed/provider/scoring behavior, configuration, `SafetyLexicon`, serialized schemas, `SKILL.md`, or repository-wide architecture documentation.
- No production caller is added. Future Agent work must adapt its separately accepted structures to this internal deterministic boundary rather than treating ECO-30 inputs as an Agent contract.
