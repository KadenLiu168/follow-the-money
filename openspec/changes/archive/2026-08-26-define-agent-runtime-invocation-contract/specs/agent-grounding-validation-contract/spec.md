## MODIFIED Requirements

### Requirement: Grounding contract remains runtime-neutral
This capability SHALL define semantic grounding, validation-authority, admissibility, unsupported-assertion, and recovery rules only. The existence or use of the separate `agent-runtime-invocation-contract` SHALL NOT make this capability an invocation protocol or allow an Audit result to prove semantic support, factuality, entailment, overall answer correctness, or final-output admissibility. This capability SHALL NOT introduce or require `ResearchContext`, `AgentAnalysis`, `BriefContext`, equivalent workflow DTOs, final-output JSON Schema, MCP/RPC/HTTP interfaces, a validator service or facade, an Agent runtime adapter, mandatory Audit invocation, automatic semantic or citation-entailment validation, Feed-to-retained-library wiring, retained-capability production wiring, Agent orchestration, a fixed Agent or Brief pipeline, invocation order or counts, retry counts, rewrite loops, shared runtime state, prompt architecture, model SDK or configuration, API-key configuration, or an embedded LLM runtime. Existing internal Audit structures SHALL remain internal rather than becoming the Agent-facing representation.

#### Scenario: Serialized contracts are inspected
- **WHEN** this capability and the repository's serialized schemas are reviewed after ECO-49
- **THEN** the Agent invocation schema defines only bounded invocation and Audit representation semantics, while no Agent-facing grounding-proof, Claim-grounding, or final-output schema exists

#### Scenario: Production caller graph is inspected
- **WHEN** the Feed entry paths and retained deterministic capabilities are traced
- **THEN** the Feed remains evidence-only, Deterministic Audit remains `retained-no-production-caller`, and no Feed-to-retained-library or Agent-validation production wiring has been introduced

#### Scenario: Internal audit structures are inspected
- **WHEN** existing `AuditClaim`, `AuditFlow`, `AuditResult`, or related internal Python structures are reviewed against the Agent invocation schema
- **THEN** they remain internal capability inputs or results and are mapped to, rather than promoted as, the separate Agent-facing representation

#### Scenario: Semantic automation is requested
- **WHEN** automatic proof of semantic grounding, factual entailment, citation entailment, or complete answer validity is sought
- **THEN** neither this capability nor successful deterministic invocation defines such proof
