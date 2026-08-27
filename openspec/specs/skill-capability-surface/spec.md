# skill-capability-surface Specification

## Purpose

Define the closed semantic catalog of deterministic behavior that the Skill owns for Host-Agent integration while preserving truthful live-versus-retained status and keeping integration bounded to the implemented Audit and Event invocation contract.

## Requirements

### Requirement: Skill capability ownership is semantic and closed
The Skill capability surface SHALL consist of exactly six semantic capability families: Evidence Feed; Evidence and Event Structuring; Market Analytics and State; Confidence and Watchlist; Scoring and Ranking; and Deterministic Audit. Capability ownership SHALL mean that the repository/Skill owns the accepted deterministic behavior and invariants of those families. It SHALL NOT allocate operational responsibility between the Skill and a future Host Agent, and the family names SHALL NOT prescribe API methods, transport operations, invocation granularity, or workflow stages.

#### Scenario: Capability catalog is reviewed
- **WHEN** a future integration identifies deterministic behavior it may conceptually rely on from this repository
- **THEN** that behavior belongs to one of the six named semantic families and remains governed in detail by the accepted living capability from which it derives

#### Scenario: Capability ownership is interpreted
- **WHEN** a capability is identified as Skill-owned
- **THEN** the identification establishes ownership of its deterministic behavior and invariants without deciding which future participant invokes it, supplies its inputs, mutates surrounding state, or validates downstream output

### Requirement: Evidence Feed remains a live capability
The Evidence Feed capability SHALL cover evidence acquisition, normalization, provenance, deterministic aggregation, schema and semantic validation, Feed identity and digest, degradation and coverage outcomes, and durable publication as already governed by `feed-evidence-pipeline`. Its execution status SHALL be `live-production`. The Feed SHALL remain evidence-only, and `feed.schema.json` SHALL remain the unchanged live production Feed contract. The separate accepted `agent-runtime-invocation-contract` SHALL expose Audit independently and SHALL NOT wrap, alter, or require the Feed contract merely for architectural symmetry.

#### Scenario: Live capability is traced
- **WHEN** the current production entry and its transitive callers are inspected
- **THEN** Evidence Feed remains `live-production`, its detailed behavior remains defined by `feed-evidence-pipeline`, and it neither calls nor is required by Deterministic Audit invocation

#### Scenario: Serialized contracts are inspected
- **WHEN** the capability surface and `schemas/` are reviewed after ECO-50
- **THEN** `feed.schema.json` remains the unchanged Feed contract while the separate Agent invocation schema governs the implemented on-demand Audit boundary

### Requirement: Evidence and Event Structuring is a live on-demand capability
The Evidence and Event Structuring capability SHALL cover the accepted deterministic behavior for immutable evidence ledgering, closed entity resolution, candidate Components and grouping, canonical Event construction, and story-family and coexistence identity utilities as governed by `deterministic-research-engine`. After ECO-51, its execution status SHALL be `live-production` only for the bounded on-demand `event.structure` operation implemented through `agent-runtime-invocation-contract`. All other behavior in this family SHALL remain transport-neutral and SHALL NOT define a Resolver transport, Agent request batch, Ledger API, persistent state, automatic Feed wiring, or another production caller.

#### Scenario: Structuring capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its ledger, entity, candidate, Event, family, and coexistence behavior remains grounded in `deterministic-research-engine` without copying those algorithms into this capability

#### Scenario: Structuring caller status is inspected
- **WHEN** the production caller graph and Agent invocation schema are reviewed after ECO-51
- **THEN** exactly the approved `event.structure` adapter calls canonical Event construction, Evidence/Event Structuring is `live-production` on demand, and no Ledger operation, Feed-to-Event edge, or other family behavior is production-wired

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
The labels `live-production` and `retained-no-production-caller` SHALL describe only the current verified caller state recorded by the architecture contract. They SHALL NOT become runtime state, serialized metadata, configuration fields, a capability enablement registry, or a promise that every behavior in a named family is production-wired. A Phase 5 `activate` decision SHALL NOT alter execution status before a dedicated implementation Change establishes a real production caller.

#### Scenario: Status labels are implemented
- **WHEN** repository configuration, schemas, and runtime code are inspected after ECO-51
- **THEN** neither status label nor the activation matrix exists as a runtime value, serialized field, configuration option, or dynamic registry entry

#### Scenario: Event caller is verified
- **WHEN** ECO-51 establishes and verifies the approved `event.structure` production caller
- **THEN** Evidence/Event Structuring changes to `live-production` while Market, Confidence/Watchlist, and Scoring/Ranking remain `retained-no-production-caller`

#### Scenario: Event family scope is interpreted
- **WHEN** the Evidence/Event Structuring family is marked `live-production`
- **THEN** the label describes the verified Event operation caller and does not imply that entity resolution, candidate grouping, Ledger state, or Feed-to-Event orchestration has become externally callable

#### Scenario: Retained capability is named
- **WHEN** a family without a verified production caller is named in the accepted semantic catalog after ECO-51
- **THEN** it remains `retained-no-production-caller` and gains no runtime value, operation, or wiring from its catalog membership

#### Scenario: Event Structuring remains only approved
- **WHEN** the Phase 5 activation decision is reviewed before ECO-51 Apply is verified
- **THEN** Evidence/Event Structuring remains `retained-no-production-caller`; its status changes only with the implemented and tested `event.structure` caller

### Requirement: Internal infrastructure remains outside the capability surface
Provider adapters and manifests, HTTP clients, collection locks, rate-state machinery, configuration loaders, canonical serialization and digest helpers, publication filesystem mechanics, title-similarity primitives, internal helper functions, and individual Python structure layouts SHALL remain implementation machinery rather than stable Host-Agent capabilities. Such machinery MAY change without changing the semantic capability surface when the accepted behavior and invariants of the owning capability remain unchanged.

#### Scenario: Internal mechanism is reviewed
- **WHEN** a repository mechanism implements part of a semantic capability but does not itself define the capability's accepted behavior
- **THEN** it remains internal implementation machinery and is not promoted into the Host-Agent capability catalog

#### Scenario: Internal implementation is refactored
- **WHEN** a later Change replaces an internal mechanism while preserving the owning capability's accepted deterministic behavior and invariants
- **THEN** the semantic Skill capability surface does not require a contract change solely because that mechanism changed

### Requirement: Concrete integration remains bounded
The semantic capability surface SHALL recognize `agent-runtime-invocation-contract` as the accepted owner of the implemented private local one-shot JSON protocol, the Agent-facing Audit and Event Structuring representations, compatibility, error, authority-preservation, and Phase 5 activation semantics. The capability surface itself SHALL NOT define `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, a tool or service facade, MCP/RPC/HTTP contract, orchestration topology, fixed Agent workflow, grounding policy, retry or rewrite policy, runtime capability registry, or integration beyond the approved Audit and Event Structuring operations. Responsibility and authority remain governed by `skill-agent-responsibility-boundary`; grounding and admissibility remain governed by `agent-grounding-validation-contract`. ECO-51 SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, Feed-to-Event wiring, Ledger API, automatic Audit, or a caller for Market, Confidence/Watchlist, Scoring/Ranking, or any other retained behavior.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** one private executable and adapter implement only `audit.text`, `audit.claims`, and `event.structure`, while no Ledger operation, orchestration, registry, remote service, shared state, Feed wiring, or unrelated retained-capability caller has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** invocation, responsibility, grounding, validation, unsupported-claim, or recovery decisions are sought
- **THEN** invocation mechanics are governed by `agent-runtime-invocation-contract`, responsibility and authority by `skill-agent-responsibility-boundary`, grounding and admissibility by `agent-grounding-validation-contract`, and every integration beyond the approved Audit and Event Structuring operations remains deferred to later Changes
