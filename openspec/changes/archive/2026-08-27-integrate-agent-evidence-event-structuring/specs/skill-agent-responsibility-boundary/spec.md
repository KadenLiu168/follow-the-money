## MODIFIED Requirements

### Requirement: Skill owns accepted deterministic capability semantics
The Skill SHALL own the accepted semantics, deterministic behavior and invariants, and existing capability-local fail-closed validation of the six families governed by `skill-capability-surface`, with detailed domain guarantees remaining governed by their referenced living specs. The Skill SHALL correctly represent Evidence Feed, Deterministic Audit, and after ECO-51 Evidence/Event Structuring as independently `live-production`; Market Analytics and State, Confidence and Watchlist, and Scoring and Ranking SHALL remain `retained-no-production-caller`. The Skill SHALL NOT claim responsibility for financial interpretation, Agent reasoning, Agent narrative, Agent-originated Event classifications, evidence/fact/entity selections, family/coexistence hypotheses, or Agent runtime orchestration beyond executing the explicitly addressed deterministic Audit or Event Structuring operation.

#### Scenario: Skill responsibility is traced
- **WHEN** responsibility for a deterministic family is reviewed
- **THEN** the Skill owns only the accepted deterministic semantics, invariants, and capability-local validation guaranteed by that family's governing living specs

#### Scenario: Capability status is reviewed
- **WHEN** the responsibility boundary is compared with the post-ECO-51 production caller graph
- **THEN** Evidence Feed, on-demand Deterministic Audit, and on-demand Event Structuring are `live-production`, the other three families remain unwired, and no mandatory sequence exists among live capabilities

### Requirement: Agent-owned information remains Agent-owned
Host-Agent reasoning state, hypotheses, interpretations, conclusions, narratives, Event classifications, evidence/fact/entity selections, family/coexistence hypotheses, display inputs, and other Agent-originated assertions SHALL remain Agent-owned. Supplying such information to an accepted deterministic capability SHALL NOT by itself convert the originating assertion or classification into Skill-owned evidence, verified fact, semantic grounding, or a Skill-produced assertion.

#### Scenario: Agent assertion enters deterministic processing
- **WHEN** an Agent-owned hypothesis, interpretation, assertion, classification, or research selection is supplied as valid input to an accepted deterministic capability
- **THEN** the originating value remains Agent-owned and does not become verified evidence or verified fact merely because deterministic processing occurred

#### Scenario: Agent-selected Event inputs are structured
- **WHEN** the Host Agent supplies Event type, evidence, entities, defining facts, family/coexistence peers, or display inputs to `event.structure`
- **THEN** those selections and classifications remain Agent-owned while the Skill owns only the contracted canonical identities, ordering, time projections, family/pair transformations, and deterministic label formatting

#### Scenario: Agent narrative incorporates a Skill result
- **WHEN** a Host Agent incorporates a Skill-produced deterministic result into its analysis or narrative
- **THEN** the resulting analysis or narrative remains Agent-owned while the unchanged deterministic result retains only its governing Skill guarantees

### Requirement: Deterministic transformation preserves input provenance and authority
When an accepted deterministic capability consumes valid inputs and produces a result, the Skill SHALL own the deterministic transformation and the invariants guaranteed for its result. The transformation SHALL preserve the provenance and authority distinctions established for the originating inputs and SHALL NOT silently upgrade an unsupported, evidence-referenced, or Agent-derived source assertion beyond what the governing living contracts establish.

#### Scenario: Deterministic capability processes mixed-authority inputs
- **WHEN** an accepted deterministic capability processes valid inputs whose provenance or authority differs
- **THEN** its result satisfies the capability's deterministic guarantees without silently upgrading any originating input's provenance or authority

#### Scenario: Existing Feed guarantees cross the boundary
- **WHEN** Feed information is consumed across the Skill-Agent boundary
- **THEN** the provenance, identity, digest, verification, validation, and fail-closed guarantees governed by `feed-evidence-pipeline` remain authoritative and unchanged

#### Scenario: Event evidence references cross the boundary
- **WHEN** Agent-supplied evidence identities are preserved through Event Structuring and associated with generated canonical fact identities
- **THEN** the association proves only deterministic identity and traceability and does not establish evidence verification, semantic support, factuality, entailment, answer correctness, or admissibility

### Requirement: Responsibility boundary remains separate from grounding and runtime policy
This capability SHALL define responsibility, semantic ownership after mutation or derivation, and provenance and authority preservation only. It SHALL NOT itself define evidence-grounding sufficiency for Agent claims, final Agent-output validation ownership, unsupported-claim emission or handling, final-answer acceptance or rejection, retry, rewrite, or recovery policy; those semantic decisions SHALL be governed by `agent-grounding-validation-contract`. It SHALL NOT itself define Agent-facing DTOs or schemas, serialized Agent request or response contracts, facades, adapters, protocols, orchestration, invocation order or count, runtime implementation, shared mutable state, production wiring, or LLM/model capability. The separate `agent-runtime-invocation-contract` SHALL govern the accepted private Audit and Event Structuring invocation mechanics and serialized representations without changing the ownership and authority rules in this capability.

#### Scenario: Grounding policy is requested
- **WHEN** a decision is sought about grounding sufficiency, final-output validation, unsupported claims, acceptance or rejection, retry, rewrite, or recovery
- **THEN** this responsibility boundary supplies no such policy and the applicable semantic decision is governed by `agent-grounding-validation-contract`

#### Scenario: ECO-35 policy is requested
- **WHEN** a decision is sought about grounding sufficiency, final-output validation, unsupported claims, acceptance or rejection, retry, rewrite, or recovery
- **THEN** this responsibility boundary supplies no such policy and the applicable semantic decision remains governed by `agent-grounding-validation-contract`

#### Scenario: Runtime integration is requested
- **WHEN** invocation mechanics, an Agent-facing Audit or Event data contract, orchestration topology, shared state contract, or runtime implementation is sought
- **THEN** only the accepted Audit and Event Structuring invocation mechanics, serialization, and runtime are governed by `agent-runtime-invocation-contract`, while orchestration, shared state, other capability integrations, and runtime policy remain undefined by this responsibility capability

#### Scenario: Serialized contracts are inspected
- **WHEN** the accepted responsibility boundary, `schemas/`, and caller graph are reviewed after ECO-51
- **THEN** the separate Agent invocation boundary preserves this capability's ownership and authority rules, explicitly maps internal Audit and Event structures, and adds no authority upgrade or caller beyond the approved Audit and Event adapters
