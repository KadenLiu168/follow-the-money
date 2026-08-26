## MODIFIED Requirements

### Requirement: Responsibility boundary remains separate from grounding and runtime policy
This capability SHALL define responsibility, semantic ownership after mutation or derivation, and provenance and authority preservation only. It SHALL NOT itself define evidence-grounding sufficiency for Agent claims, final Agent-output validation ownership, unsupported-claim emission or handling, final-answer acceptance or rejection, retry, rewrite, or recovery policy; those semantic decisions SHALL be governed by `agent-grounding-validation-contract`. It SHALL NOT define Agent-facing DTOs or schemas, serialized Agent request or response contracts, facades, adapters, protocols, orchestration, invocation order or count, runtime implementation, shared mutable state, production wiring, or LLM/model capability.

#### Scenario: ECO-35 policy is requested
- **WHEN** a decision is sought about grounding sufficiency, final-output validation, unsupported claims, acceptance or rejection, retry, rewrite, or recovery
- **THEN** this responsibility boundary supplies no such policy and the applicable semantic decision is governed by `agent-grounding-validation-contract`

#### Scenario: Runtime integration is requested
- **WHEN** a callable Skill-Agent integration, Agent data contract, orchestration topology, shared state contract, or runtime mechanism is sought
- **THEN** this capability supplies no such contract and leaves it to a later explicitly approved Change

#### Scenario: Serialized contracts are inspected
- **WHEN** the accepted responsibility boundary and `schemas/` are reviewed
- **THEN** no Agent-facing serialized contract has been added and `feed.schema.json` remains the only current serialized external contract
