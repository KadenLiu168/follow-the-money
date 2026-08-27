## MODIFIED Requirements

### Requirement: Evidence Feed remains a live capability
The Evidence Feed capability SHALL cover evidence acquisition, normalization, provenance, deterministic aggregation, schema and semantic validation, Feed identity and digest, degradation and coverage outcomes, and durable publication as already governed by `feed-evidence-pipeline`. Its execution status SHALL be `live-production`. The Feed SHALL remain evidence-only, and `feed.schema.json` SHALL remain the unchanged live production Feed contract. The separate accepted `agent-runtime-invocation-contract` SHALL expose Audit independently and SHALL NOT wrap, alter, or require the Feed contract merely for architectural symmetry.

#### Scenario: Live capability is traced
- **WHEN** the current production entries and their transitive callers are inspected after ECO-50
- **THEN** Evidence Feed remains `live-production`, its detailed behavior remains defined by `feed-evidence-pipeline`, and it neither calls nor is required by Deterministic Audit invocation

#### Scenario: Serialized contracts are inspected
- **WHEN** the capability surface and `schemas/` are reviewed after ECO-50
- **THEN** `feed.schema.json` remains the unchanged Feed contract while the separate Agent invocation schema governs the implemented on-demand Audit boundary

### Requirement: Deterministic Audit is a live on-demand capability
The Deterministic Audit capability SHALL cover the accepted workflow-neutral text safety and structured deterministic claim checks governed by `deterministic-research-engine`. After ECO-50, its execution status SHALL be `live-production` because the private `agent-runtime-invocation-contract` boundary is its one approved production caller for `audit.text` and `audit.claims`. Audit SHALL remain on demand and SHALL NOT decide when a Host Agent invokes it, what evidence grounding is sufficient, whether an unsupported Agent claim may be emitted, who owns final-output validation, or whether failed output is retried or rewritten; those semantic rules remain governed by `agent-grounding-validation-contract`.

#### Scenario: Audit capability is traced
- **WHEN** the semantic family is compared with its accepted detailed and invocation contracts
- **THEN** its text safety, structured claim, deterministic finding, and no-silent-rewrite behavior remains grounded in `deterministic-research-engine`, while only its Agent-facing serialization and invocation semantics are governed by `agent-runtime-invocation-contract`

#### Scenario: Audit activation decision is inspected
- **WHEN** runtime entries and the production caller graph are reviewed after ECO-50
- **THEN** Deterministic Audit is `live-production` through exactly the approved private invocation boundary and has no Feed caller, legacy workflow caller, automatic invocation, or unrelated capability caller

#### Scenario: Grounding policy is searched
- **WHEN** the capability surface is inspected for Host-Agent grounding, final-output validation, unsupported-claim, retry, or rewrite policy
- **THEN** the applicable semantic decisions are governed by `agent-grounding-validation-contract` and Audit invocation success does not establish semantic grounding or final-output admissibility

### Requirement: Execution status is descriptive architecture metadata only
The labels `live-production` and `retained-no-production-caller` SHALL describe only the current verified caller state recorded by the architecture contract. They SHALL NOT become runtime state, serialized metadata, configuration fields, a capability enablement registry, or a promise that every named capability is production-wired. A Phase 5 `activate` decision SHALL NOT alter execution status before a dedicated implementation Change establishes a real production caller.

#### Scenario: Status labels are implemented
- **WHEN** repository configuration, schemas, and runtime code are inspected after this Change
- **THEN** neither status label nor the activation matrix exists as a runtime value, serialized field, configuration option, or dynamic registry entry

#### Scenario: Retained capability is named
- **WHEN** ECO-50 establishes and verifies the approved private Audit production caller
- **THEN** Deterministic Audit changes to `live-production` while Evidence/Event Structuring and every other deferred family remain `retained-no-production-caller`

#### Scenario: Event Structuring remains only approved
- **WHEN** Event Structuring is included in the Phase 5 activation plan but ECO-51 has not established its caller
- **THEN** its status remains `retained-no-production-caller`

### Requirement: Concrete integration remains bounded
The semantic capability surface SHALL recognize `agent-runtime-invocation-contract` as the accepted owner of the implemented private local one-shot JSON protocol, Agent-facing Audit representation, compatibility, error, authority-preservation, and Phase 5 activation semantics. The capability surface itself SHALL NOT define `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, a tool or service facade, MCP/RPC/HTTP contract, orchestration topology, fixed Agent workflow, grounding policy, retry or rewrite policy, runtime capability registry, or integration for any capability beyond the approved Audit boundary. Responsibility and authority remain governed by `skill-agent-responsibility-boundary`; grounding and admissibility remain governed by `agent-grounding-validation-contract`. ECO-50 SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, Feed-to-retained-library wiring, Event operation, unrelated retained-capability caller, or placeholder wiring.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** one private executable and adapter implement only `audit.text` and `audit.claims`, while no Event operation, orchestration, registry, remote service, shared state, Feed wiring, or unrelated retained-capability caller has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** invocation, responsibility, grounding, validation, unsupported-claim, or recovery decisions are sought
- **THEN** invocation mechanics are governed by `agent-runtime-invocation-contract`, responsibility and authority by `skill-agent-responsibility-boundary`, grounding and admissibility by `agent-grounding-validation-contract`, and every integration beyond the approved Audit boundary remains deferred to later Changes

## RENAMED Requirements

- FROM: `### Requirement: Evidence Feed is the live capability`
- TO: `### Requirement: Evidence Feed remains a live capability`
- FROM: `### Requirement: Deterministic Audit is a retained capability`
- TO: `### Requirement: Deterministic Audit is a live on-demand capability`
- FROM: `### Requirement: Concrete integration contracts remain deferred`
- TO: `### Requirement: Concrete integration remains bounded`
