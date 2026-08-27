## MODIFIED Requirements

### Requirement: Grounding contract remains runtime-neutral
This capability SHALL define semantic grounding, validation-authority, admissibility, unsupported-assertion, and recovery rules only. The existence or use of the implemented `agent-runtime-invocation-contract` Audit boundary SHALL NOT make this capability an invocation protocol or allow an Audit result to prove semantic support, factuality, entailment, overall answer correctness, or final-output admissibility. This capability SHALL NOT introduce or require `ResearchContext`, `AgentAnalysis`, `BriefContext`, equivalent workflow DTOs, final-output JSON Schema, MCP/RPC/HTTP interfaces, a validator service or facade, mandatory Audit invocation, automatic semantic or citation-entailment validation, Feed-to-Audit wiring, production wiring for another retained capability, Agent orchestration, a fixed Agent or Brief pipeline, invocation order or counts, retry counts, rewrite loops, shared runtime state, prompt architecture, model SDK or configuration, API-key configuration, or an embedded LLM runtime. Existing internal Audit structures SHALL remain internal rather than becoming the Agent-facing representation.

#### Scenario: Serialized contracts are inspected
- **WHEN** this capability and the repository's serialized schemas are reviewed after ECO-50
- **THEN** the Agent invocation schema defines only bounded invocation and Audit representation semantics, while no Agent-facing grounding-proof, Claim-grounding, or final-output schema exists

#### Scenario: Production caller graph is inspected
- **WHEN** the Feed entry paths, Audit invocation boundary, and retained deterministic capabilities are traced
- **THEN** the Feed remains evidence-only, Deterministic Audit has exactly the approved on-demand Host-Agent production caller, and no Feed-to-Audit or other retained-capability production wiring has been introduced

#### Scenario: Internal audit structures are inspected
- **WHEN** existing internal Audit inputs or results are reviewed against the Agent invocation schema
- **THEN** they remain internal capability structures and are explicitly mapped to and from, rather than promoted as, the separate Agent-facing representation

#### Scenario: Audit pass is interpreted
- **WHEN** Agent-owned assertions pass an invoked deterministic Audit operation or carry evidence references through that operation
- **THEN** they remain Agent-owned and the result proves only the exercised Audit semantics, not semantic support, factuality, entailment, overall answer correctness, or final-output admissibility

#### Scenario: Semantic automation is requested
- **WHEN** automatic proof of semantic grounding, factual entailment, citation entailment, or complete answer validity is sought
- **THEN** neither this capability nor successful deterministic invocation defines such proof
