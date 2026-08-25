# skill-agent-responsibility-boundary Specification

## Purpose

Define the semantic responsibility, ownership, mutation, provenance, and authority boundary between the Skill and a Host Agent without selecting or implying a runtime integration mechanism.

## Requirements

### Requirement: Host Agent owns the non-deterministic research layer
The Host Agent SHALL own understanding user research intent, financial interpretation, reasoning and judgment, Agent-generated hypotheses and conclusions, Agent working analysis, and user-facing synthesis and narrative. These responsibilities SHALL NOT imply an invocation order, call count, control flow, Agent data structure, transport mechanism, or obligation to invoke a retained capability that has no production orchestration caller.

#### Scenario: Host Agent produces research interpretation
- **WHEN** financial evidence or a Skill-produced deterministic result is interpreted, combined with judgment, or expressed as a user-facing conclusion
- **THEN** the interpretation, judgment, conclusion, and narrative are Host-Agent-owned rather than Skill-produced deterministic results

#### Scenario: Responsibility is reviewed for runtime implications
- **WHEN** the Host Agent responsibility allocation is inspected
- **THEN** it defines no Agent object, transport, invocation sequence, call count, control flow, or requirement to invoke a retained capability

### Requirement: Skill owns accepted deterministic capability semantics
The Skill SHALL own the accepted semantics, deterministic behavior and invariants, and existing capability-local fail-closed validation of the six families governed by `skill-capability-surface`, with detailed domain guarantees remaining governed by their referenced living specs. The Skill SHALL correctly represent the Evidence Feed as `live-production` and each of the five post-Feed families as `retained-no-production-caller`. It SHALL NOT claim responsibility for financial interpretation, Agent reasoning, Agent narrative, Agent-generated assertions, or Agent runtime orchestration.

#### Scenario: Skill responsibility is traced
- **WHEN** responsibility for a deterministic family is reviewed
- **THEN** the Skill owns only the accepted deterministic semantics, invariants, and capability-local validation guaranteed by that family's governing living specs

#### Scenario: Capability status is reviewed
- **WHEN** the responsibility boundary is compared with the current production caller graph
- **THEN** the Evidence Feed remains the only `live-production` family and no retained family is represented as Agent-callable or as having a production orchestration caller

### Requirement: Deterministic engine is an internal Skill responsibility layer
Within the Skill boundary, the deterministic engine SHALL be responsible only for executing and enforcing accepted typed and domain invariants, deterministic transformations, canonicalization, deterministic calculations, stable ordering, and existing capability-local validation. It SHALL NOT be represented as a third external participant, service, tool endpoint, facade, transport boundary, Agent runtime, or direct Host-Agent contract.

#### Scenario: Deterministic responsibility is allocated
- **WHEN** an accepted deterministic capability is exercised
- **THEN** its deterministic execution and enforcement are internal Skill responsibilities governed by the applicable living spec

#### Scenario: External participants are identified
- **WHEN** the Skill-Agent boundary is inspected for external actors or callable boundaries
- **THEN** the deterministic engine is not a third external actor and no `Host Agent ↔ deterministic engine` service, endpoint, facade, or transport contract exists

### Requirement: Skill-produced results have bounded semantic authority
A value represented as a Skill-produced deterministic result SHALL be authoritative only for the exact semantics and invariants guaranteed by its governing living spec. Information crossing the Skill-Agent boundary SHALL NOT acquire guarantees beyond that governing contract solely because the Skill produced, exposed, or received it.

#### Scenario: Deterministic result is consumed unchanged
- **WHEN** a consumer relies on an unchanged Skill-produced deterministic result
- **THEN** the result carries only the authority and guarantees established by its governing living spec

#### Scenario: Boundary crossing is interpreted
- **WHEN** information passes between the Skill and Host Agent
- **THEN** the crossing alone does not increase that information's provenance, verification status, or authority

### Requirement: Consumer mutation or derivation transfers semantic ownership
If a consumer changes, supplements, interprets, or transforms a Skill-produced deterministic result outside the governing deterministic capability, the derived value SHALL become consumer-owned or Host-Agent-owned and SHALL NOT be represented as the unchanged original Skill-produced result. This ownership rule SHALL be semantic and SHALL NOT require Python-level immutability, immutable storage, a mutation API, a shared state model, or a particular data structure.

#### Scenario: Consumer modifies a deterministic result
- **WHEN** a consumer changes or supplements a Skill-produced deterministic result outside its governing capability
- **THEN** the changed value is consumer-owned or Host-Agent-owned and is not represented as the unchanged original Skill-produced result

#### Scenario: Ownership rule is implemented conceptually
- **WHEN** the mutation and derivation rule is reviewed for implementation requirements
- **THEN** it introduces no immutable-storage requirement, mutation API, shared workspace contract, session store, state store, or persistence protocol

### Requirement: Agent-owned information remains Agent-owned
Host-Agent reasoning state, hypotheses, interpretations, conclusions, narratives, and other Agent-originated assertions SHALL remain Agent-owned. Supplying such information to an accepted deterministic capability SHALL NOT by itself convert the originating assertion into Skill-owned evidence, verified fact, or a Skill-produced assertion.

#### Scenario: Agent assertion enters deterministic processing
- **WHEN** an Agent-owned hypothesis, interpretation, or assertion is supplied as valid input to an accepted deterministic capability
- **THEN** the originating assertion remains Agent-owned and does not become verified evidence or verified fact merely because deterministic processing occurred

#### Scenario: Agent narrative incorporates a Skill result
- **WHEN** a Host Agent incorporates a Skill-produced deterministic result into its analysis or narrative
- **THEN** the resulting analysis or narrative remains Agent-owned while the unchanged deterministic result retains only its governing Skill guarantees

### Requirement: Deterministic transformation preserves input provenance and authority
When an accepted deterministic capability consumes valid inputs and produces a result, the Skill SHALL own the deterministic transformation and the invariants guaranteed for its result. The transformation SHALL preserve the provenance and authority distinctions established for the originating inputs and SHALL NOT silently upgrade an unsupported or Agent-derived source assertion beyond what the governing living contracts establish.

#### Scenario: Deterministic capability processes mixed-authority inputs
- **WHEN** an accepted deterministic capability processes valid inputs whose provenance or authority differs
- **THEN** its result satisfies the capability's deterministic guarantees without silently upgrading any originating input's provenance or authority

#### Scenario: Existing Feed guarantees cross the boundary
- **WHEN** Feed information is consumed across the Skill-Agent boundary
- **THEN** the provenance, identity, digest, verification, validation, and fail-closed guarantees governed by `feed-evidence-pipeline` remain authoritative and unchanged

### Requirement: Responsibility boundary remains separate from grounding and runtime policy
This capability SHALL define responsibility, semantic ownership after mutation or derivation, and provenance and authority preservation only. It SHALL NOT define evidence-grounding sufficiency for Agent claims, final Agent-output validation ownership, unsupported-claim emission or handling, final-answer acceptance or rejection, retry, rewrite, or recovery policy; those decisions SHALL remain deferred to ECO-35. It SHALL NOT define Agent-facing DTOs or schemas, serialized Agent request or response contracts, facades, adapters, protocols, orchestration, invocation order or count, runtime implementation, shared mutable state, production wiring, or LLM/model capability.

#### Scenario: ECO-35 policy is requested
- **WHEN** a decision is sought about grounding sufficiency, final-output validation, unsupported claims, acceptance or rejection, retry, rewrite, or recovery
- **THEN** this responsibility boundary supplies no such policy and the decision remains deferred to ECO-35

#### Scenario: Runtime integration is requested
- **WHEN** a callable Skill-Agent integration, Agent data contract, orchestration topology, shared state contract, or runtime mechanism is sought
- **THEN** this capability supplies no such contract and leaves it to a later explicitly approved Change

#### Scenario: Serialized contracts are inspected
- **WHEN** the accepted responsibility boundary and `schemas/` are reviewed
- **THEN** no Agent-facing serialized contract has been added and `feed.schema.json` remains the only current serialized external contract
