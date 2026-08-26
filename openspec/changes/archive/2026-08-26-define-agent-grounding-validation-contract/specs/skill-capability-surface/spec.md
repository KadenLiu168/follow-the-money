## MODIFIED Requirements

### Requirement: Deterministic Audit is a retained capability
The Deterministic Audit capability SHALL cover the accepted workflow-neutral text safety and structured deterministic claim checks governed by `deterministic-research-engine`. Its execution status SHALL be `retained-no-production-caller`. The capability SHALL NOT decide when a Host Agent invokes auditing, what evidence grounding is sufficient, whether an unsupported Agent claim may be emitted, who owns final-output validation, or whether failed output is retried or rewritten; the applicable semantic grounding, validation-authority, admissibility, unsupported-assertion, and recovery rules SHALL instead be governed by `agent-grounding-validation-contract` without creating a production orchestration caller.

#### Scenario: Audit capability is traced
- **WHEN** the semantic family is compared with its accepted detailed contract
- **THEN** its text safety, structured claim, deterministic finding, and no-silent-rewrite behavior is fully grounded in `deterministic-research-engine`

#### Scenario: Grounding policy is searched
- **WHEN** the capability surface is inspected for Host-Agent grounding, final-output validation, unsupported-claim, retry, or rewrite policy
- **THEN** the applicable semantic decisions are governed by `agent-grounding-validation-contract` and the audit family remains without a production orchestration caller

### Requirement: Concrete integration contracts remain deferred
The semantic capability surface SHALL NOT define `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, any Agent-facing schema, tool or service facade, MCP/RPC/HTTP contract, runtime adapter, invocation protocol, call count or order, orchestration topology, fixed Agent workflow, grounding or unsupported-claim policy, retry or rewrite policy, or Phase-5 runtime implementation. Responsibility allocation, mutation and derivation ownership, and provenance and authority preservation SHALL instead be governed by `skill-agent-responsibility-boundary`; semantic grounding, validation-authority, admissibility, unsupported-assertion, and recovery rules SHALL be governed by `agent-grounding-validation-contract`; neither capability defines a runtime integration mechanism. The semantic capability surface SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, a new production caller, Feed-to-retained-library wiring, or placeholder wiring.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** only semantic capability, responsibility, grounding, validation-authority, admissibility, unsupported-assertion, and recovery contracts have been defined and no concrete Agent object, schema, facade, adapter, protocol, orchestration, or production wiring has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** responsibility, mutation, trust, grounding, validation, unsupported-claim, or output-recovery decisions are sought
- **THEN** responsibility, mutation and derivation ownership, and provenance and authority preservation are governed by `skill-agent-responsibility-boundary`; semantic grounding, validation-authority, admissibility, unsupported-assertion, and recovery decisions are governed by `agent-grounding-validation-contract`; and runtime implementation remains deferred
