## Context

See `proposal.md` for motivation. Today `ClaimAuditor` receives an open-ended Mapping whose keys encode the removed Brief pipeline. Its submitted-membership check cannot detect an assertion outside the inventory because both sets are derived from the same inventory, and direct `claim["claim_id"]` access lets malformed inputs escape the intended `AuditResult` failure path. The module also contains broader historical rendering/provenance claims that its implementation does not perform.

There is no production caller to migrate: repository tracing finds only focused retained-library tests. `SafetyLexicon`, `AuditFinding`, and `AuditResult` already represent the accepted configuration and result semantics. The design therefore stays local to `audit.py`, its focused tests, and the `deterministic-research-engine` delta.

## Goals / Non-Goals

**Goals:**

- Separate standalone text safety checks from optional structured claim invariants.
- Make every datum at the audit trust boundary explicit, typed, immutable where practical, and limited to a retained rule that consumes it.
- Return deterministic fail-closed findings for invalid structured identity instead of leaking incidental Mapping exceptions.
- Preserve existing lexicon matching, finding categories where already meaningful, and critical-finding failure behavior.

**Non-Goals:**

- Define or infer any future Host Agent request, analysis, report, or delivery shape.
- Add serialization, a generic validation/policy framework, adapters, compatibility wiring, or production callers.
- Recreate rendering, URL, numeric provenance, price-in, section, or broader Brief validation.
- Change which claims semantically require evidence, confirmed-flow policy, or any Feed/provider/scoring/configuration behavior.

## Decisions

### 1. Use two narrow audit-owned levels over one all-purpose context

The implementation will expose a standalone text safety operation and a structured claim operation. The structured operation will reuse the same text rule for each claim rather than duplicate matching logic. Structured inputs will contain only:

- an inventory of claim records with identity, text, explicit direct-evidence obligation, and evidence references;
- a separately supplied collection of submitted/rendered claim identities;
- flow ownership records containing only confirmed state and optional owning Event identity.

Small frozen dataclasses or equivalently closed typed parameters are preferred. Exact public names are left to Apply-time fit with repository style; their semantic fields are fixed by the delta spec.

Alternative considered: one large `AuditContext` carrying optional workflow state. Rejected because it would invite speculative Agent/Brief fields and make text-only use construct irrelevant state.

### 2. Validate identity at the boundary without a generic schema layer

A required claim identity is valid only when it is a non-empty, non-whitespace Python string. Inventory and independently submitted/rendered identities will be validated before duplicate, membership, evidence, or text checks consume them. Invalid identity will add a critical finding and keep evaluation deterministic; Apply may reuse an existing category or introduce the smallest identity-specific category if the retained result model cannot otherwise express the failure cleanly.

The auditor will not normalize, synthesize, or repair identities. Evidence references and Event identities remain subject only to the existing presence checks; ECO-30 does not create a broader identifier-validation framework.

Alternative considered: rely on dataclass type annotations or direct indexing. Rejected because runtime callers can forge values and the accepted boundary must fail closed through `AuditResult` rather than incidental exceptions.

### 3. Make evidence obligation an explicit boolean

Each structured claim will state whether direct evidence references are required. The missing-evidence rule becomes the direct predicate: obligation is true and the reference collection is empty. The old `is_factual` plus `class != "dashboard"` inference is removed.

Alternative considered: rename `dashboard` to another claim class. Rejected because presentation classification does not belong to the reusable audit boundary and would preserve the same coupling under a neutral-sounding label.

The caller remains responsible for deciding the obligation under its own accepted contract. ECO-30 changes representation, not evidence policy.

### 4. Treat submitted membership as independent caller input

The structured operation will compare the independently supplied submitted/rendered identity collection against the validated inventory identity set. It will not reconstruct submitted membership from inventory text or removed rendering sections. This makes `outside_inventory` observable without restoring a renderer.

Input ordering will not affect pass/fail or finding content. Apply should retain the repository's existing deterministic ordering style when multiple findings are emitted.

Alternative considered: parse claim markers from rendered prose. Rejected because it would establish a new text format and reintroduce rendering responsibilities.

### 5. Represent flow ownership directly and neutrally

The structured boundary will carry only whether a flow is confirmed and its optional owning Event identity. The existing rule applies only when confirmed is true. No `money_flow_section`, presentation section, or additional flow semantics are retained.

Alternative considered: pass the historical flow-section dictionaries through a compatibility layer. Rejected because no real caller requires compatibility and the shim would preserve the obsolete contract.

### 6. Preserve result and safety configuration models

`AuditFinding`, `AuditResult`, the critical severity gate, `SafetyLexicon`, zero-width cleanup, term matching, and configured descriptive exceptions remain authoritative. Standalone text findings may carry an optional caller-supplied claim identity. Neither audit level rewrites input.

The module docstring and local comments will be narrowed to these real responsibilities. `SKILL.md` and `docs/architecture.md` already truthfully describe a retained deterministic safety audit with no caller, so they remain untouched unless Apply-time inspection reveals a direct contradiction.

## Risks / Trade-offs

- [Internal Python callers outside the repository may still use the Mapping API] → The repository has no current production caller; document the breaking library change and add only minimum compatibility if Apply discovers a concrete in-repository dependency, surfacing that conflict rather than silently retaining Brief semantics.
- [Explicit evidence obligation moves policy selection to callers] → Keep the boolean narrowly named and test both values; do not add classification heuristics or defaults that conceal caller intent.
- [Malformed identities could create cascaded or unstable findings] → Validate identities first, avoid using invalid values for membership/evidence/text attribution, and assert deterministic results for repeated malformed inputs.
- [A new typed boundary could be mistaken for the future Agent Contract] → Keep it internal, minimal, unserialized, and free of Agent/report/orchestration vocabulary; preserve no-caller architecture tests.

## Migration Plan

1. Add focused RED tests for standalone text auditing and the complete structured trust-boundary matrix, including malformed identity and independently observable outside-inventory input.
2. Introduce the smallest audit-owned typed inputs and text primitive, then adapt structured auditing to reuse it.
3. Remove the legacy Brief Mapping entry point and migrate retained-library tests; do not add a compatibility shim unless a real current repository caller is discovered.
4. Correct `audit.py` module-local documentation and run focused tests, no-LLM/architecture regression checks, the canonical repository quality gate, and required OpenSpec validation.

Rollback is a normal source revert because the boundary has no production caller, persistence, configuration, or serialized data migration.
