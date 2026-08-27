# agent-grounding-validation-contract Specification

## Purpose

Define the runtime-neutral semantic conditions under which Host-Agent factual assertions may be represented as grounded and Agent-owned research output is admissible.

## Requirements

### Requirement: Grounded factual assertions require semantic support
A Host Agent SHALL represent a factual assertion as grounded only when it can trace the assertion's factual basis to valid Evidence Feed evidence, an unchanged Skill-produced deterministic result, a correctly characterized Skill-produced deterministic result, or a combination of those sources, and the assertion does not claim semantic authority beyond what those sources establish. The existence of an evidence reference SHALL NOT by itself establish that the referenced evidence semantically supports the assertion.

#### Scenario: Evidence reference exists without semantic support
- **WHEN** an Agent factual assertion cites a valid evidence identifier but the cited evidence does not establish the factual proposition being asserted
- **THEN** the assertion is not grounded and the reference presence alone does not make it grounded

#### Scenario: Deterministic result is used within its authority
- **WHEN** an Agent factual assertion accurately states an unchanged or correctly characterized Skill-produced deterministic result within the exact guarantees of its governing living spec
- **THEN** that result may supply the factual basis for representing the assertion as grounded within those guarantees

#### Scenario: Supporting sources have narrower authority
- **WHEN** an Agent factual assertion extends beyond the semantic authority established by its supporting evidence or deterministic results
- **THEN** the extended proposition SHALL NOT be represented as grounded

### Requirement: Host Agent owns semantic support assessment
The Host Agent SHALL own assessment of whether supporting evidence actually establishes its factual proposition, whether an inference exceeds that support, whether a deterministic result is used within its governing semantics, and whether uncertainty or conflicting evidence prevents a proposition from being stated as established fact. This responsibility SHALL NOT be attributed to automatic proof by the current deterministic engine.

#### Scenario: Citation entailment is assessed
- **WHEN** an evidence reference is attached to an Agent-owned factual assertion
- **THEN** the Host Agent determines whether the referenced evidence semantically supports that assertion rather than treating reference presence as deterministic entailment proof

#### Scenario: Uncertainty or conflict prevents establishment
- **WHEN** relevant support is uncertain or conflicting such that the Host Agent cannot establish the factual proposition
- **THEN** the Host Agent SHALL NOT represent that proposition as an established grounded fact

#### Scenario: Deterministic processing succeeds
- **WHEN** Agent-owned information passes all applicable checks of a deterministic capability
- **THEN** the Host Agent still owns semantic support assessment and the deterministic success does not prove complete grounding or factual entailment

### Requirement: Semantic authority is preserved across grounding and narrative
A Skill-produced deterministic result SHALL support only assertions within the exact semantics and invariants guaranteed by its governing living spec. Crossing the Skill-Agent boundary, attaching an evidence identifier, deterministic transformation by itself, inclusion in Agent analysis, or inclusion in final narrative SHALL NOT increase an assertion's provenance, verification status, or semantic authority. Agent-generated interpretation, synthesis, hypotheses, judgments, and conclusions SHALL remain Agent-owned and SHALL NOT be represented as Skill-verified facts solely because their inputs were grounded.

#### Scenario: Grounded inputs support an Agent conclusion
- **WHEN** the Host Agent derives an interpretation, hypothesis, judgment, synthesis, or conclusion from grounded inputs
- **THEN** the derived content remains Agent-owned and does not become a Skill-verified fact solely because the inputs were grounded

#### Scenario: Deterministic transformation processes Agent content
- **WHEN** an accepted deterministic capability processes an Agent-originated assertion
- **THEN** processing alone does not upgrade the assertion's provenance, verification status, or semantic authority

#### Scenario: Narrative includes a deterministic result
- **WHEN** Agent-owned narrative includes or characterizes a Skill-produced deterministic result
- **THEN** the result retains only its governing guarantees and the surrounding narrative remains Agent-owned

### Requirement: Deterministic validation findings retain bounded authority
The Skill SHALL own the correctness and meaning of findings produced by an accepted deterministic capability within that capability's governing living contract. The Host Agent SHALL NOT reinterpret a deterministic failure as a deterministic pass, suppress a known failure while claiming that the candidate passed that validation, or attribute broader semantic meaning to a deterministic finding than its governing capability guarantees. A successful deterministic validation SHALL NOT establish complete semantic grounding, factual entailment, overall answer correctness, or complete final-output validity.

#### Scenario: Applicable critical finding is reported
- **WHEN** an accepted deterministic capability reports a critical finding that applies to a candidate
- **THEN** the Host Agent SHALL preserve that failure as the deterministic result defined by the governing capability and SHALL NOT represent the candidate as having passed that validation

#### Scenario: Deterministic validation passes
- **WHEN** a candidate passes all rules exercised by an accepted deterministic capability
- **THEN** the pass establishes only those bounded deterministic results and does not establish complete grounding, factual entailment, overall correctness, or complete final-output validity

#### Scenario: Finding is interpreted beyond its contract
- **WHEN** a deterministic finding is used in Agent reasoning or narrative
- **THEN** the finding SHALL NOT be attributed semantic authority beyond the exact guarantees of its governing living spec

### Requirement: Host Agent owns a constrained output-admissibility decision
The Host Agent SHALL own the operational decision to emit its Agent-owned narrative. It SHALL NOT emit a candidate as grounded research output when it knows that the candidate contains either a factual assertion represented as grounded for which sufficient semantic support has not been established or an unresolved critical deterministic finding from an accepted deterministic validation capability that applies to the candidate. This admissibility rule SHALL remain semantic and SHALL NOT define a runtime pipeline.

#### Scenario: Candidate contains a known unsupported grounded assertion
- **WHEN** the Host Agent knows a candidate represents a factual assertion as grounded without sufficient semantic support
- **THEN** the candidate is inadmissible as grounded research output and SHALL NOT be emitted unchanged

#### Scenario: Candidate contains an unresolved applicable critical finding
- **WHEN** the Host Agent knows an accepted deterministic validation capability has produced an unresolved critical finding that applies to a candidate
- **THEN** the candidate is inadmissible as grounded research output and SHALL NOT be emitted unchanged

#### Scenario: Operational emission ownership is inspected
- **WHEN** the output-admissibility decision is reviewed
- **THEN** the Host Agent owns the operational emission decision subject to this contract without creating a Skill-owned narrative or runtime orchestration duty

### Requirement: Unsupported assertions require substantive handling
An unsupported factual assertion SHALL NOT be presented as a grounded fact. The Host Agent MAY omit the assertion, change the factual proposition to match the available support, obtain or use additional valid support, or accurately characterize genuinely uncertain reasoning as interpretation, hypothesis, or uncertainty. Merely relabeling an unsupported factual assertion without materially changing its epistemic status SHALL NOT establish grounding.

#### Scenario: Unsupported assertion is omitted
- **WHEN** the Host Agent removes an unsupported factual assertion from a candidate
- **THEN** that assertion no longer creates a grounding violation for the later candidate

#### Scenario: Assertion is narrowed to its support
- **WHEN** the Host Agent materially changes a factual proposition so that it matches sufficient valid support and does not exceed the support's authority
- **THEN** the changed proposition may be assessed as grounded under this contract

#### Scenario: Unsupported assertion is merely relabeled
- **WHEN** the Host Agent changes only the label or presentation of an unsupported factual assertion while preserving its unsupported epistemic claim
- **THEN** the assertion remains unsupported and SHALL NOT be represented as grounded

#### Scenario: Uncertain reasoning is characterized accurately
- **WHEN** genuinely uncertain reasoning is presented as Agent-owned interpretation, hypothesis, or uncertainty without representing it as an established grounded fact
- **THEN** the characterization does not falsely upgrade the reasoning to grounded factual authority

### Requirement: Recovery restores admissibility without prescribing control flow
If a candidate is inadmissible under this contract, it SHALL NOT be emitted unchanged as grounded research output. A later candidate MAY be emitted only after the relevant grounding or deterministic-validation violation no longer applies, including through conceptual removal, correction, re-grounding, reformulation, or re-evaluation. This contract SHALL NOT define retry count, automatic retry, rewrite loop, invocation order, call count, recovery topology, or a specific validator invocation.

#### Scenario: Relevant violation is resolved
- **WHEN** removal, correction, re-grounding, reformulation, or re-evaluation produces a later candidate to which the prior grounding or deterministic-validation violation no longer applies
- **THEN** the prior violation no longer makes that later candidate inadmissible under this contract

#### Scenario: Candidate is retried unchanged
- **WHEN** a later candidate preserves the same applicable grounding or deterministic-validation violation
- **THEN** it remains inadmissible as grounded research output regardless of being submitted or considered again

#### Scenario: Recovery mechanism is requested
- **WHEN** retry count, automatic retry, rewrite loops, invocation order, call count, recovery topology, or a specific validator invocation is sought
- **THEN** this contract supplies no such runtime mechanism

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
