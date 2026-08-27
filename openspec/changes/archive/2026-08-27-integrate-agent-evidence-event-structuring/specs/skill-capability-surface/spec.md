## MODIFIED Requirements

### Requirement: Evidence and Event Structuring is a live on-demand capability
The Evidence and Event Structuring capability SHALL cover the accepted deterministic behavior for immutable evidence ledgering, closed entity resolution, candidate Components and grouping, canonical Event construction, and story-family and coexistence identity utilities as governed by `deterministic-research-engine`. After ECO-51, its execution status SHALL be `live-production` only for the bounded on-demand `event.structure` operation implemented through `agent-runtime-invocation-contract`. All other behavior in this family SHALL remain transport-neutral and SHALL NOT define a Resolver transport, Agent request batch, Ledger API, persistent state, automatic Feed wiring, or another production caller.

#### Scenario: Structuring capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its ledger, entity, candidate, Event, family, and coexistence behavior remains grounded in `deterministic-research-engine` without copying those algorithms into this capability

#### Scenario: Structuring caller status is inspected
- **WHEN** the production caller graph and Agent invocation schema are reviewed after ECO-51
- **THEN** exactly the approved `event.structure` adapter calls canonical Event construction, Evidence/Event Structuring is `live-production` on demand, and no Ledger operation, Feed-to-Event edge, or other family behavior is production-wired

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

### Requirement: Concrete integration remains bounded
The semantic capability surface SHALL recognize `agent-runtime-invocation-contract` as the accepted owner of the implemented private local one-shot JSON protocol, the Agent-facing Audit and Event Structuring representations, compatibility, error, authority-preservation, and Phase 5 activation semantics. The capability surface itself SHALL NOT define `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, a tool or service facade, MCP/RPC/HTTP contract, orchestration topology, fixed Agent workflow, grounding policy, retry or rewrite policy, runtime capability registry, or integration beyond the approved Audit and Event Structuring operations. Responsibility and authority remain governed by `skill-agent-responsibility-boundary`; grounding and admissibility remain governed by `agent-grounding-validation-contract`. ECO-51 SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, Feed-to-Event wiring, Ledger API, automatic Audit, or a caller for Market, Confidence/Watchlist, Scoring/Ranking, or any other retained behavior.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** one private executable and adapter implement only `audit.text`, `audit.claims`, and `event.structure`, while no Ledger operation, orchestration, registry, remote service, shared state, Feed wiring, or unrelated retained-capability caller has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** invocation, responsibility, grounding, validation, unsupported-claim, or recovery decisions are sought
- **THEN** invocation mechanics are governed by `agent-runtime-invocation-contract`, responsibility and authority by `skill-agent-responsibility-boundary`, grounding and admissibility by `agent-grounding-validation-contract`, and every integration beyond the approved Audit and Event Structuring operations remains deferred to later Changes
