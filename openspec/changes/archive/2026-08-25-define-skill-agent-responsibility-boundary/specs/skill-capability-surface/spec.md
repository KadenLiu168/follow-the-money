## MODIFIED Requirements

### Requirement: Concrete integration contracts remain deferred
The semantic capability surface SHALL NOT define `ResearchContext`, `AgentAnalysis`, `BriefContext`, an equivalent replacement object, any Agent-facing schema, tool or service facade, MCP/RPC/HTTP contract, runtime adapter, invocation protocol, call count or order, orchestration topology, fixed Agent workflow, grounding or unsupported-claim policy, retry or rewrite policy, or Phase-5 runtime implementation. Responsibility allocation, mutation and derivation ownership, and provenance and authority preservation SHALL instead be governed by `skill-agent-responsibility-boundary` without defining a runtime integration mechanism. The semantic capability surface SHALL NOT add an embedded LLM runtime, model SDK or configuration, API-key configuration, a new production caller, Feed-to-retained-library wiring, or placeholder wiring.

#### Scenario: Agent integration surface is audited
- **WHEN** the accepted Change, schemas, runtime entries, imports, and current-facing documentation are inspected
- **THEN** only the semantic capability surface and semantic responsibility boundary have been defined and no concrete Agent object, schema, facade, adapter, protocol, orchestration, or production wiring has been introduced

#### Scenario: Later contract ownership is reviewed
- **WHEN** responsibility, mutation, trust, grounding, validation, unsupported-claim, or output-recovery decisions are sought
- **THEN** responsibility, mutation and derivation ownership, and provenance and authority preservation are governed by `skill-agent-responsibility-boundary`; grounding, final-output validation ownership, unsupported-claim, retry, rewrite, and recovery decisions remain deferred to ECO-35; and runtime implementation remains deferred
