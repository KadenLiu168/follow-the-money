## MODIFIED Requirements

### Requirement: Responsibility boundary remains separate from grounding and runtime policy
This capability SHALL define responsibility, semantic ownership after mutation or derivation, and provenance and authority preservation only. It SHALL NOT itself define evidence-grounding sufficiency for Agent claims, final Agent-output validation ownership, unsupported-claim emission or handling, final-answer acceptance or rejection, retry, rewrite, or recovery policy; those semantic decisions SHALL be governed by `agent-grounding-validation-contract`. It SHALL NOT itself define Agent-facing DTOs or schemas, serialized Agent request or response contracts, facades, adapters, protocols, orchestration, invocation order or count, runtime implementation, shared mutable state, production wiring, or LLM/model capability. The separate `agent-runtime-invocation-contract` SHALL govern the accepted private invocation mechanics and serialized Audit representation without changing the ownership and authority rules in this capability.

#### Scenario: ECO-35 policy is requested
- **WHEN** a decision is sought about grounding sufficiency, final-output validation, unsupported claims, acceptance or rejection, retry, rewrite, or recovery
- **THEN** this responsibility boundary supplies no such policy and the applicable semantic decision is governed by `agent-grounding-validation-contract`

#### Scenario: Runtime integration is requested
- **WHEN** invocation mechanics, an Agent-facing Audit data contract, orchestration topology, shared state contract, or runtime implementation is sought
- **THEN** only invocation mechanics and serialization are governed by `agent-runtime-invocation-contract`, while orchestration, shared state, and production implementation remain undefined by this responsibility capability

#### Scenario: Serialized contracts are inspected
- **WHEN** the accepted responsibility boundary and `schemas/` are reviewed after ECO-49
- **THEN** the separate Agent invocation schema preserves this capability's ownership and authority rules without promoting internal Python structures or changing the current production caller graph
