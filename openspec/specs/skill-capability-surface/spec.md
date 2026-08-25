# skill-capability-surface Specification

## Purpose

Define the closed semantic catalog of deterministic behavior that the Skill owns for future Host-Agent integration while preserving truthful live-versus-retained status and deferring every concrete Agent invocation contract.

## Requirements

### Requirement: Skill capability ownership is semantic and closed
The Skill capability surface SHALL consist of exactly six semantic capability families: Evidence Feed; Evidence and Event Structuring; Market Analytics and State; Confidence and Watchlist; Scoring and Ranking; and Deterministic Audit. Capability ownership SHALL mean that the repository/Skill owns the accepted deterministic behavior and invariants of those families. It SHALL NOT allocate operational responsibility between the Skill and a future Host Agent, and the family names SHALL NOT prescribe API methods, transport operations, invocation granularity, or workflow stages.

#### Scenario: Capability catalog is reviewed
- **WHEN** a future integration identifies deterministic behavior it may conceptually rely on from this repository
- **THEN** that behavior belongs to one of the six named semantic families and remains governed in detail by the accepted living capability from which it derives

#### Scenario: Capability ownership is interpreted
- **WHEN** a capability is identified as Skill-owned
- **THEN** the identification establishes ownership of its deterministic behavior and invariants without deciding which future participant invokes it, supplies its inputs, mutates surrounding state, or validates downstream output

### Requirement: Evidence Feed is the live capability
The Evidence Feed capability SHALL cover evidence acquisition, normalization, provenance, deterministic aggregation, schema and semantic validation, Feed identity and digest, degradation and coverage outcomes, and durable publication as already governed by `feed-evidence-pipeline`. Its execution status SHALL be `live-production`. The Feed SHALL remain evidence-only, and `feed.schema.json` SHALL remain the only current serialized external contract.

#### Scenario: Live capability is traced
- **WHEN** the current production entry and its transitive callers are inspected
- **THEN** the Evidence Feed is the only live capability family and its detailed behavior remains defined by `feed-evidence-pipeline`

#### Scenario: Serialized contracts are inspected
- **WHEN** the capability surface and `schemas/` are reviewed
- **THEN** the new semantic catalog introduces no serialized contract and `feed.schema.json` remains the only current serialized external contract

### Requirement: Evidence and Event Structuring is a retained capability
The Evidence and Event Structuring capability SHALL cover the accepted deterministic behavior for immutable evidence ledgering, closed entity resolution, candidate Components and grouping, canonical Event construction, and story-family and coexistence identity utilities as governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`. It SHALL remain transport-neutral and SHALL NOT define a Resolver transport, Agent request batch, external Event schema, or production wiring.

#### Scenario: Structuring capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its ledger, entity, candidate, Event, family, and coexistence behavior is fully grounded in `deterministic-research-engine` without copying those algorithms into this capability

#### Scenario: Structuring caller status is inspected
- **WHEN** the current production caller graph is reviewed
- **THEN** the structuring family has no production orchestration caller and no transport or serialized Agent boundary has been added

### Requirement: Market Analytics and State is a retained capability
The Market Analytics and State capability SHALL cover the accepted deterministic behavior for market snapshot construction, market formulas, breadth, normalized surprise, and Market State classification as governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`, and the capability SHALL NOT be represented as part of the live Feed production pipeline.

#### Scenario: Market capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its snapshot, formula, breadth, surprise, and state-classification behavior is fully grounded in `deterministic-research-engine`

#### Scenario: Feed wiring is inspected
- **WHEN** the live Feed import and caller graph is reviewed
- **THEN** naming the market family in the Skill surface has not made it a Feed stage or supplied it with a production orchestration caller

### Requirement: Confidence and Watchlist is a retained capability
The Confidence and Watchlist capability SHALL cover the accepted deterministic evidence and Event confidence rules, unresolved outcomes, future-calendar watchlist construction, stable ordering, and bounded results as governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`, and it SHALL NOT be packaged or described as a Brief-preparation stage.

#### Scenario: Confidence and watchlist capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its confidence, unresolved-outcome, calendar-selection, ordering, and bounds behavior is fully grounded in `deterministic-research-engine`

#### Scenario: Presentation workflow is searched
- **WHEN** the capability surface is inspected for a Brief or equivalent presentation-preparation stage
- **THEN** none is defined or implied and the family remains without a production orchestration caller

### Requirement: Scoring and Ranking is a retained capability
The Scoring and Ranking capability SHALL cover the accepted deterministic behavior for Event significance, Event relevance, base priority, component coverage, eligibility, ranking, story-family penalty, and coexistence as governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`. Existing inputs SHALL remain caller-supplied typed Python values, and this capability SHALL NOT define how a future Host Agent serializes, transports, or supplies them.

#### Scenario: Scoring and ranking capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its scoring, coverage, eligibility, ordering, family-penalty, and coexistence behavior is fully grounded in `deterministic-research-engine`

#### Scenario: Future input transport is searched
- **WHEN** the capability surface is inspected for an Agent-facing scoring, ranking, or Event input contract
- **THEN** no serialized schema or transport rule exists and the retained typed Python inputs have not gained a production orchestration caller

### Requirement: Deterministic Audit is a retained capability
The Deterministic Audit capability SHALL cover the accepted workflow-neutral text safety and structured deterministic claim checks governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`. The capability SHALL NOT decide when a Host Agent invokes auditing, what evidence grounding is sufficient, whether an unsupported Agent claim may be emitted, who owns final-output validation, or whether failed output is retried or rewritten.

#### Scenario: Audit capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its text safety, structured claim, deterministic finding, and no-silent-rewrite behavior is fully grounded in `deterministic-research-engine`

#### Scenario: Grounding policy is searched
- **WHEN** the capability surface is inspected for Host-Agent grounding, final-output validation, unsupported-claim, retry, or rewrite policy
- **THEN** those decisions remain undefined for ECO-35 and the audit family remains without a production orchestration caller

### Requirement: Execution status is descriptive architecture metadata only
The labels `live-production` and `retained-no-production-caller` SHALL describe only the current caller state recorded by the architecture contract. They SHALL NOT become runtime state, serialized metadata, configuration fields, a capability enablement registry, or a promise that every named capability is production-wired. Adding a retained family to the semantic surface SHALL NOT itself add or require a production caller.

#### Scenario: Status labels are implemented
- **WHEN** repository configuration, schemas, and runtime code are inspected after this Change
- **THEN** neither status label exists as a runtime value, serialized field, configuration option, or dynamic registry entry

#### Scenario: Retained capability is named
- **WHEN** a retained deterministic family is included in the semantic catalog
- **THEN** its status remains `retained-no-production-caller` until a later implementation Change explicitly establishes real production wiring

### Requirement: Internal infrastructure remains outside the capability surface
Provider adapters and manifests, HTTP clients, collection locks, rate-state machinery, configuration loaders, canonical serialization and digest helpers, publication filesystem mechanics, title-similarity primitives, internal helper functions, and individual Python structure layouts SHALL remain implementation machinery rather than stable Host-Agent capabilities. Such machinery MAY change without changing the semantic capability surface when the accepted behavior and invariants of the owning capability remain unchanged.

#### Scenario: Internal mechanism is reviewed
- **WHEN** a repository mechanism implements part of a semantic capability but does not itself define the capability's accepted behavior
- **THEN** it remains internal implementation machinery and is not promoted into the Host-Agent capability catalog

#### Scenario: Internal implementation is refactored
- **WHEN** a later Change replaces an internal mechanism while preserving the owning capability's accepted deterministic behavior and invariants
- **THEN** the semantic Skill capability surface does not require a contract change solely because that mechanism changed

### Requirement: Concrete integration contracts remain deferred
The semantic capability surface SHALL NOT define `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, any Agent-facing schema, tool or service facade, MCP/RPC/HTTP contract, runtime adapter, invocation protocol, call count or order, orchestration topology, fixed Agent workflow, grounding or unsupported-claim policy, retry or rewrite policy, or Phase-5 runtime implementation. Responsibility allocation, mutation and derivation ownership, and provenance and authority preservation SHALL instead be governed by `skill-agent-responsibility-boundary` without defining a runtime integration mechanism. The semantic capability surface SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, a new production caller, Feed-to-retained-library wiring, or placeholder wiring.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** only the semantic capability surface and semantic responsibility boundary have been defined and no concrete Agent object, schema, facade, adapter, protocol, orchestration, or production wiring has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** responsibility, mutation, trust, grounding, validation, unsupported-claim, or output-recovery decisions are sought
- **THEN** responsibility, mutation and derivation ownership, and provenance and authority preservation are governed by `skill-agent-responsibility-boundary`; grounding, final-output validation ownership, unsupported-claim, retry, rewrite, and recovery decisions remain deferred to ECO-35; and runtime implementation remains deferred
