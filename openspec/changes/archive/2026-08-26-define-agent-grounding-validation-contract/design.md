## Context

See `proposal.md` for motivation. The accepted Phase-4 baseline already separates the closed six-family Skill capability surface from Skill-Agent responsibility and authority ownership. It deliberately leaves grounding sufficiency, final-output admissibility, unsupported-assertion handling, and recovery semantics to ECO-35.

The Evidence Feed is the only `live-production` family and `feed.schema.json` is the only current serialized external contract. The other five families, including Deterministic Audit, are `retained-no-production-caller`. Existing audit types and checks are internal typed library contracts; they neither prove semantic entailment nor constitute a complete final-answer validator.

## Goals / Non-Goals

**Goals:**

- Add one independent semantic layer after capability classification and responsibility allocation that defines grounded factual assertions and constrained output admissibility.
- Preserve source authority across evidence references, deterministic results, Agent reasoning, and narrative.
- Make the split between Host-Agent semantic judgment and Skill-owned deterministic findings explicit.
- Close current ECO-35 deferrals with minimal, traceable spec and documentation alignment.
- Make architecture regressions directly inspectable without inventing runtime artifacts.

**Non-Goals:**

- Select an Agent DTO, Claim model, schema, protocol, adapter, facade, validator, prompt, state model, or orchestration topology.
- Add automatic entailment or complete-answer validation.
- Require `ClaimAuditor` or any other retained capability to gain a production caller.
- Change Feed behavior, provider behavior, configuration, dependencies, production code, or serialized schemas.
- Perform OpenSpec sync/archive, Linear updates, commit, or push as part of proposal or Apply work; those remain separately authorized lifecycle steps.

## Decisions

### 1. Create an independent grounding and admissibility capability

Add `agent-grounding-validation-contract` rather than merging the policy into `skill-agent-responsibility-boundary`. The three Phase-4 layers then remain independently reviewable:

```text
skill-capability-surface
        ↓ deterministic semantics and caller status
skill-agent-responsibility-boundary
        ↓ ownership and authority preservation
agent-grounding-validation-contract
        ↓ grounded representation and output admissibility
```

This preserves ECO-34's narrower ownership role and lets later runtime design consume the semantic contracts without rewriting them.

Alternative considered: extend `skill-agent-responsibility-boundary`. Rejected because it would collapse ownership allocation and output policy into one capability, obscuring which contract answers which question.

### 2. Define grounding by traceability, semantic support, and bounded authority

A grounded factual assertion requires a traceable factual basis in valid Feed evidence and/or an unchanged or correctly characterized Skill-produced deterministic result. Grounding also requires that the proposition stay within the semantic authority those sources establish. Evidence-reference presence is treated only as a potentially observable relation, never as proof that the evidence entails the proposition.

Alternative considered: define grounding as possession of one or more evidence IDs. Rejected because it would turn citation presence into a false verification upgrade and conflict with the accepted authority-preservation boundary.

### 3. Split semantic support judgment from deterministic validation authority

The Host Agent owns semantic support assessment for its assertions and the operational decision to emit its narrative. The Skill owns the correctness and meaning of findings that an accepted deterministic capability produces within its governing spec. Therefore an applicable critical finding cannot be represented as a pass, while a deterministic pass proves only the bounded rules actually evaluated.

This is an authority split, not an execution sequence. The contract does not state that a validator is invoked, when it is invoked, or how information is transported.

Alternative considered: describe Deterministic Audit as the final-output validator. Rejected because its retained rules are bounded, it has no production caller, and success does not establish semantic grounding or overall answer correctness.

### 4. Express admissibility and recovery as semantic state constraints

A candidate is inadmissible as grounded research output when the Host Agent knows it contains an unsupported grounded factual assertion or an unresolved applicable critical deterministic finding. A later candidate becomes eligible for a new admissibility decision only when the relevant violation no longer applies. Removal, correction, re-grounding, reformulation, and re-evaluation are conceptual examples rather than prescribed control-flow steps.

Alternative considered: specify a retry or rewrite loop. Rejected because counts, ordering, invocations, and recovery topology belong to a later explicitly approved runtime architecture.

### 5. Use OpenSpec deltas and prose alignment only

The Change adds the new capability delta and full `MODIFIED` blocks for only the existing requirements whose ECO-35 deferrals change. Apply work minimally aligns `docs/architecture.md`, `SKILL.md`, `README.md`, and `README.zh-CN.md`. The delta remains the planned contract until a separately authorized OpenSpec sync/archive updates the living baseline.

No production artifact is needed to demonstrate a semantic contract. Architecture verification will inspect the schema set, caller/import boundaries, current status language, and absence of prohibited Agent/runtime constructs; focused audit tests and the canonical quality gate provide behavioral regression evidence.

Alternative considered: add a conceptual Claim schema or validator facade to make the contract concrete. Rejected because it would prematurely choose Phase-5 implementation types and create a false external or callable boundary.

## Risks / Trade-offs

- [Semantic support is necessarily judgment-based] → State Host-Agent ownership explicitly and avoid claims that the deterministic engine proves entailment.
- [“Grounded” could be stretched to cover Agent conclusions] → Require bounded source authority and preserve Agent ownership of interpretations, hypotheses, judgments, synthesis, and conclusions.
- [A deterministic finding could be overread] → Bind every finding and pass to the exact authority of its governing living spec.
- [Admissibility language could imply a hidden pipeline] → Express only conditions on candidates and explicitly exclude invocation, retry, rewrite, and recovery control flow.
- [Cross-reference edits could accidentally broaden existing capabilities] → Modify only complete affected requirement blocks, retain inherited scenario names, and verify exact capability status and serialized-boundary invariants.
- [Documentation may imply implementation that does not exist] → Describe the contract as semantic and runtime-neutral, and continue to state that concrete Agent integration is deferred.

## Migration Plan

1. Apply the new and modified delta requirements without changing production implementation or schemas.
2. Minimally replace current-facing ECO-35 deferral language with references to `agent-grounding-validation-contract` while retaining the runtime-integration deferral.
3. Run focused retained-audit regressions, direct architecture inspections, OpenSpec strict validation, and the canonical repository quality gate.
4. After separate authorization, sync/archive the accepted deltas into the living specs; rollback before archive consists of reverting only the attributable Change and documentation edits.
