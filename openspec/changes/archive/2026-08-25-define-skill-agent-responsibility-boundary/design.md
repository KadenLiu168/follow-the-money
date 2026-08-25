## Context

See `proposal.md` for motivation. ECO-33 established exactly six semantic Skill capability families, with Evidence Feed as the only `live-production` family and five post-Feed families as `retained-no-production-caller`. Detailed deterministic behavior remains governed by `feed-evidence-pipeline`, `deterministic-research-engine`, and `deterministic-core-retention`; `feed.schema.json` remains the only current serialized external contract.

ECO-34 must add responsibility, mutation/derivation ownership, and provenance/authority semantics without creating a call graph. The repository has no Agent runtime, embedded LLM runtime, Agent-facing schema, facade, adapter, invocation protocol, or post-Feed production caller, and the design must preserve those negative facts.

## Goals / Non-Goals

**Goals:**

- Establish one cross-cutting semantic contract that future integration work can reference without depending on Python layout or a runtime mechanism.
- Allocate Host Agent and Skill responsibilities while keeping the deterministic engine internal to the Skill.
- Make ownership after consumer mutation or derivation explicit without prescribing mutability or storage mechanisms.
- Preserve the provenance and authority of inputs and results across the boundary.
- Keep ECO-35 grounding and final-output policy visibly separate.

**Non-Goals:**

- Define a service boundary, tool surface, Agent data model, serialization format, shared state, persistence mechanism, call sequence, fixed workflow, or runtime topology.
- Add a production caller or imply that any retained capability is currently Agent-callable.
- Restate domain formulas, validation algorithms, Feed semantics, or capability-local failure rules.
- Change production code, tests, schemas, configuration, Providers, dependencies, financial formulas, or caller wiring.

## Decisions

### 1. Use one semantic responsibility capability

Add `skill-agent-responsibility-boundary` as a cross-cutting living capability. It defines who owns categories of responsibility and information, not how any participant invokes another.

Alternative considered: place responsibility clauses in each of the six capability families. Rejected because it would duplicate the same cross-boundary rules, invite drift, and make a semantic architecture concern appear capability-local.

Alternative considered: model the boundary as a facade or protocol. Rejected because there is no current Agent integration runtime or callable post-Feed surface, and ECO-34 is explicitly architecture-only.

### 2. Treat the deterministic engine as internal Skill responsibility

The external semantic participants are the Skill and Host Agent. “Deterministic engine” names the internal Skill layer responsible for executing accepted deterministic behavior; it is not a third actor or a direct Host-Agent endpoint.

Alternative considered: assign the engine an independent interface contract. Rejected because that would select a service boundary, expose internal structure, and imply a caller that does not exist.

### 3. Bind authority to governing living specs

A Skill-produced result is authoritative only for guarantees made by its governing living spec. ECO-34 references existing Feed and deterministic-domain contracts rather than copying their provenance, identity, digest, validation, formula, ordering, or failure rules.

Alternative considered: create a generic trust level, confidence enum, or authority schema. Rejected because a coarse new label would duplicate or obscure capability-specific guarantees and would introduce executable metadata with no accepted consumer.

### 4. Make mutation ownership semantic

When a consumer changes, supplements, interprets, or transforms a Skill result outside its governing deterministic capability, the derived value becomes consumer/Agent-owned and cannot be represented as the unchanged original Skill result. This rule constrains claims of origin and authority, not object mutability.

Alternative considered: require immutable Python values or storage. Rejected because implementation-level immutability is neither necessary nor sufficient to establish semantic ownership and would over-constrain later integration design.

### 5. Preserve source authority through deterministic transformation

The Skill owns an accepted deterministic transformation and its output invariants, but deterministic processing does not upgrade the provenance or authority of an Agent-supplied assertion. Originating information and derived deterministic results therefore retain distinct ownership and guarantee scopes.

Alternative considered: treat every valid deterministic input as verified evidence. Rejected because input validity is capability-local and does not establish source truth or evidence authority unless the governing living contract explicitly does so.

### 6. Modify only the ECO-33 deferred-integration requirement

The `skill-capability-surface` delta copies the complete `Concrete integration contracts remain deferred` requirement and preserves both inherited scenario names. It replaces only the ECO-34 deferral with a reference to the new accepted responsibility capability; the six-family taxonomy, execution statuses, infrastructure exclusions, runtime deferrals, and ECO-35 policy ownership remain unchanged.

Alternative considered: modify `deterministic-core-retention` or the detailed Feed/domain specs. Rejected because their behavior and architecture boundaries do not change merely because cross-boundary ownership is now named.

### 7. Apply as contract and current-facing documentation alignment only

Apply will align stale ECO-34 deferral language in `SKILL.md`, `docs/architecture.md`, `README.md`, and `README.zh-CN.md`. It will add no runtime wording that implies invocation, and it will not edit `src/follow_the_money/boundary.py`, production code, tests, schemas, configuration, Providers, or dependencies.

Verification will use strict OpenSpec validation, semantic requirement review, static architecture diff/caller/schema inspection, and the canonical repository quality gate. No test will be added solely to assert Markdown wording or an invented runtime structure.

## Risks / Trade-offs

- [“Skill-owned result” is read as unlimited factual authority] → Bind every result to the exact guarantees of its governing living spec and forbid authority escalation by boundary crossing.
- [The internal deterministic engine is mistaken for a third participant or future endpoint] → State its internal status normatively and reject direct Host-Agent engine contracts in scenarios.
- [Mutation ownership is mistaken for a Python immutability mandate] → Specify ownership as semantic attribution and explicitly exclude data-structure, storage, mutation-API, and persistence requirements.
- [Deterministic processing launders an Agent assertion into verified evidence] → Preserve originating provenance and authority separately from transformation correctness.
- [ECO-34 drifts into ECO-35 output policy] → Enumerate grounding, final-output validation, unsupported-claim, retry, rewrite, and recovery decisions as deferred.
- [Documentation implies retained libraries are now callable] → Preserve exact execution-status labels and perform a fresh caller/import review during Apply.
- [The narrow MODIFIED delta loses inherited scenarios during archive] → Preserve the full requirement and exact scenario names, then validate strictly before Apply and archive.

## Migration Plan

1. Review the two deltas against accepted living specs and the current caller/schema facts.
2. During an explicitly authorized Apply, align only current-facing documentation whose ECO-34 deferral language becomes stale.
3. Run semantic and static architecture reviews, the canonical repository quality gate, and required OpenSpec checks.
4. If any runtime, schema, configuration, Provider, or caller change appears, remove that out-of-scope edit rather than adapting this contract to it.

No data migration, deployment, compatibility shim, production rollback, archive, commit, or push is part of this Change's Apply plan. Archival and delivery remain separate authorization boundaries.
