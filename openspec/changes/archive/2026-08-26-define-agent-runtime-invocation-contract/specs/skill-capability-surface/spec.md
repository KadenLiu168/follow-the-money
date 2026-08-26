## MODIFIED Requirements

### Requirement: Evidence Feed is the live capability
The Evidence Feed capability SHALL cover evidence acquisition, normalization, provenance, deterministic aggregation, schema and semantic validation, Feed identity and digest, degradation and coverage outcomes, and durable publication as already governed by `feed-evidence-pipeline`. Its execution status SHALL be `live-production`. The Feed SHALL remain evidence-only, and `feed.schema.json` SHALL remain the only live production Feed contract. The separate accepted `agent-runtime-invocation-contract` SHALL NOT wrap or alter the Feed contract merely for architectural symmetry.

#### Scenario: Live capability is traced
- **WHEN** the current production entry and its transitive callers are inspected
- **THEN** the Evidence Feed is the only live capability family and its detailed behavior remains defined by `feed-evidence-pipeline`

#### Scenario: Serialized contracts are inspected
- **WHEN** the capability surface and `schemas/` are reviewed after ECO-49
- **THEN** `feed.schema.json` remains the unchanged live production Feed contract and the separate Agent invocation schema is contract-only until a later implementation Change creates a real caller

### Requirement: Evidence and Event Structuring is a retained capability
The Evidence and Event Structuring capability SHALL cover the accepted deterministic behavior for immutable evidence ledgering, closed entity resolution, candidate Components and grouping, canonical Event construction, and story-family and coexistence identity utilities as governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`. It SHALL remain transport-neutral and SHALL NOT define a Resolver transport, Agent request batch, external Event schema, Event-specific Agent operation, or production wiring. The Phase 5 activation plan SHALL approve a later ECO-51 Change to add only its justified Event operation contract and caller after ECO-50 proves the common invocation boundary.

#### Scenario: Structuring capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its ledger, entity, candidate, Event, family, and coexistence behavior is fully grounded in `deterministic-research-engine` without copying those algorithms into this capability

#### Scenario: Structuring caller status is inspected
- **WHEN** the current production caller graph and Agent invocation schema are reviewed after ECO-49
- **THEN** the structuring family has no production orchestration caller and no Event-specific transport or serialized Agent payload has been added

### Requirement: Deterministic Audit is a retained capability
The Deterministic Audit capability SHALL cover the accepted workflow-neutral text safety and structured deterministic claim checks governed by `deterministic-research-engine`. Its execution status SHALL remain `retained-no-production-caller` after ECO-49. The accepted `agent-runtime-invocation-contract` SHALL define the separate Agent-facing `audit.text` and `audit.claims` representation and approve ECO-50 to implement its first production caller, but ECO-49 SHALL NOT create that caller. This capability SHALL NOT decide when a Host Agent invokes auditing, what evidence grounding is sufficient, whether an unsupported Agent claim may be emitted, who owns final-output validation, or whether failed output is retried or rewritten; those semantic rules remain governed by `agent-grounding-validation-contract`.

#### Scenario: Audit capability is traced
- **WHEN** the semantic family is compared with its accepted detailed and invocation contracts
- **THEN** its text safety, structured claim, deterministic finding, and no-silent-rewrite behavior remains grounded in `deterministic-research-engine`, while only its Agent-facing serialization and invocation semantics are governed by `agent-runtime-invocation-contract`

#### Scenario: Audit activation decision is inspected
- **WHEN** ECO-49 artifacts, runtime entries, and the production caller graph are reviewed
- **THEN** Audit is approved for ECO-50 but remains `retained-no-production-caller` with no automatic invocation or production wiring

#### Scenario: Grounding policy is searched
- **WHEN** the capability surface is inspected for Host-Agent grounding, final-output validation, unsupported-claim, retry, or rewrite policy
- **THEN** the applicable semantic decisions are governed by `agent-grounding-validation-contract` and Audit invocation success does not establish semantic grounding or final-output admissibility

### Requirement: Execution status is descriptive architecture metadata only
The labels `live-production` and `retained-no-production-caller` SHALL describe only the current caller state recorded by the architecture contract. They SHALL NOT become runtime state, serialized metadata, configuration fields, a capability enablement registry, or a promise that every named capability is production-wired. A Phase 5 `activate` decision SHALL mean only approval for a later dedicated implementation Change and SHALL NOT alter execution status before real production wiring exists.

#### Scenario: Status labels are implemented
- **WHEN** repository configuration, schemas, and runtime code are inspected after this Change
- **THEN** neither status label nor the activation matrix exists as a runtime value, serialized field, configuration option, or dynamic registry entry

#### Scenario: Retained capability is named
- **WHEN** Audit or Event Structuring is included in the Phase 5 activation plan
- **THEN** its status remains `retained-no-production-caller` until ECO-50 or ECO-51 explicitly establishes its real production caller

### Requirement: Concrete integration contracts remain deferred
The semantic capability surface SHALL recognize `agent-runtime-invocation-contract` as the accepted owner of the private local one-shot JSON protocol, Agent-facing Audit representation, compatibility, error, authority-preservation, and Phase 5 activation semantics. The capability surface itself SHALL NOT define or implement `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, a tool or service facade, MCP/RPC/HTTP contract, runtime adapter, orchestration topology, fixed Agent workflow, grounding policy, retry or rewrite policy, runtime capability registry, or Phase 5 production wiring. Responsibility and authority remain governed by `skill-agent-responsibility-boundary`; grounding and admissibility remain governed by `agent-grounding-validation-contract`. ECO-49 SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, a production caller, Feed-to-retained-library wiring, or placeholder wiring.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** the common contract and Audit serialization exist as planning/contract artifacts, while no executable, adapter, production caller, Event operation, orchestration, registry, remote service, or shared state has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** invocation, responsibility, grounding, validation, unsupported-claim, or recovery decisions are sought
- **THEN** invocation mechanics are governed by `agent-runtime-invocation-contract`, responsibility and authority by `skill-agent-responsibility-boundary`, grounding and admissibility by `agent-grounding-validation-contract`, and runtime implementation remains deferred to later Changes
