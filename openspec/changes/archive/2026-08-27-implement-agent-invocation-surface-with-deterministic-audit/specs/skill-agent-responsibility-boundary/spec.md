## MODIFIED Requirements

### Requirement: Skill owns accepted deterministic capability semantics
The Skill SHALL own the accepted semantics, deterministic behavior and invariants, and existing capability-local fail-closed validation of the six families governed by `skill-capability-surface`, with detailed domain guarantees remaining governed by their referenced living specs. The Skill SHALL correctly represent Evidence Feed and, after ECO-50, Deterministic Audit as `live-production`; Evidence/Event Structuring, Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking SHALL remain `retained-no-production-caller`. The Skill SHALL NOT claim responsibility for financial interpretation, Agent reasoning, Agent narrative, Agent-generated assertions, or Agent runtime orchestration beyond executing the explicitly addressed deterministic Audit operation.

#### Scenario: Skill responsibility is traced
- **WHEN** responsibility for a deterministic family is reviewed
- **THEN** the Skill owns only the accepted deterministic semantics, invariants, and capability-local validation guaranteed by that family's governing living specs

#### Scenario: Capability status is reviewed
- **WHEN** the responsibility boundary is compared with the post-ECO-50 production caller graph
- **THEN** Evidence Feed and on-demand Deterministic Audit are `live-production`, while the other four families remain unwired and no mandatory sequence exists between the two live capabilities

### Requirement: Responsibility boundary remains separate from grounding and runtime policy
This capability SHALL define responsibility, semantic ownership after mutation or derivation, and provenance and authority preservation only. It SHALL NOT itself define evidence-grounding sufficiency for Agent claims, final Agent-output validation ownership, unsupported-claim emission or handling, final-answer acceptance or rejection, retry, rewrite, or recovery policy; those semantic decisions SHALL be governed by `agent-grounding-validation-contract`. It SHALL NOT itself define Agent-facing DTOs or schemas, serialized Agent request or response contracts, facades, adapters, protocols, orchestration, invocation order or count, runtime implementation, shared mutable state, production wiring, or LLM/model capability. The separate `agent-runtime-invocation-contract` SHALL govern and ECO-50 SHALL implement the accepted private Audit invocation mechanics and serialized representation without changing the ownership and authority rules in this capability.

#### Scenario: ECO-35 policy is requested
- **WHEN** a decision is sought about grounding sufficiency, final-output validation, unsupported claims, acceptance or rejection, retry, rewrite, or recovery
- **THEN** this responsibility boundary supplies no such policy and the applicable semantic decision is governed by `agent-grounding-validation-contract`

#### Scenario: Runtime integration is requested
- **WHEN** invocation mechanics, an Agent-facing Audit data contract, orchestration topology, shared state contract, or runtime implementation is sought
- **THEN** only the accepted Audit invocation mechanics, serialization, and runtime are governed by `agent-runtime-invocation-contract`, while orchestration, shared state, other capability integrations, and runtime policy remain undefined by this responsibility capability

#### Scenario: Serialized contracts are inspected
- **WHEN** the accepted responsibility boundary, `schemas/`, and caller graph are reviewed after ECO-50
- **THEN** the separate Agent invocation boundary preserves this capability's ownership and authority rules, explicitly maps internal Audit structures, and adds no authority upgrade or caller beyond the approved Audit adapter
