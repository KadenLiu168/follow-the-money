## ADDED Requirements

### Requirement: Digest factual assertions require Feed semantic support
A Host Agent SHALL present a digest factual assertion as grounded only when valid current Feed evidence semantically supports the proposition and the assertion does not exceed the evidence's provenance or authority. An evidence identifier by itself SHALL NOT establish semantic support.

#### Scenario: Citation lacks semantic support
- **WHEN** a digest assertion cites a valid Feed item that does not establish the asserted proposition
- **THEN** the assertion is not grounded and SHALL NOT be emitted unchanged as a grounded fact

### Requirement: Host Agent owns Feed support assessment and emission
The Host Agent SHALL assess whether Feed evidence supports each factual summary and SHALL own the operational decision to emit the evidence-preserving digest. The repository SHALL provide no Audit, Event, grounding-proof, entailment, retry, rewrite, or final-output validation runtime.

#### Scenario: Current Feed is summarized
- **WHEN** the Host Agent prepares a digest from a validated Feed
- **THEN** it assesses semantic support and emits only an admissible evidence-preserving presentation without invoking a removed repository capability

### Requirement: Unsupported digest assertions require substantive handling
An unsupported factual assertion SHALL NOT be presented as grounded. The Host Agent MAY omit it, narrow it to available Feed support, or accurately characterize source-stated uncertainty, but relabeling alone SHALL NOT establish grounding.

#### Scenario: Assertion is narrowed
- **WHEN** an unsupported assertion is materially changed to match sufficient Feed evidence
- **THEN** the changed proposition may be reassessed as grounded

### Requirement: Feed grounding remains runtime-neutral
This capability SHALL define Host-Agent semantic behavior only and SHALL NOT introduce an Agent-facing schema, repository validator, private invocation process, capability registry, orchestration, embedded model runtime, prompt pipeline, retry/rewrite loop, or shared state.

#### Scenario: Runtime implementation is inspected
- **WHEN** schemas and production entries are reviewed
- **THEN** only Feed production and current Feed consumption exist and no grounding or Audit runtime is present

## REMOVED Requirements

### Requirement: Grounded factual assertions require semantic support
**Reason**: Superseded by the Feed-specific grounding requirement after non-Feed deterministic results are removed.
**Migration**: Ground assertions only in current validated Feed evidence.

### Requirement: Host Agent owns semantic support assessment
**Reason**: Superseded by the combined Feed support and emission requirement.
**Migration**: Assess only Feed evidence support for the normal digest.

### Requirement: Semantic authority is preserved across grounding and narrative
**Reason**: Non-Feed deterministic-result authority is removed; Feed authority is covered by the replacement requirements.
**Migration**: Do not exceed the supporting Feed evidence's authority.

### Requirement: Deterministic validation findings retain bounded authority
**Reason**: No Agent-output deterministic validation capability remains.
**Migration**: Feed validation findings still govern Feed admissibility under the Feed contract, not final narrative validation.

### Requirement: Host Agent owns a constrained output-admissibility decision
**Reason**: Superseded by the Feed-specific support and emission requirement.
**Migration**: Do not emit known unsupported digest assertions unchanged.

### Requirement: Unsupported assertions require substantive handling
**Reason**: Superseded by the narrower digest-specific requirement.
**Migration**: Apply substantive handling only against current Feed support.

### Requirement: Recovery restores admissibility without prescribing control flow
**Reason**: Retry/recovery semantics are unnecessary for the simplified digest contract.
**Migration**: A later digest candidate is admissible only when it independently satisfies current requirements; no runtime recovery mechanism is specified.

### Requirement: Grounding contract remains runtime-neutral
**Reason**: Superseded by the Feed-only runtime-neutral requirement.
**Migration**: Remove all Audit/invocation references and retain no grounding runtime.
