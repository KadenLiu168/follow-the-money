# agent-grounding-validation-contract Specification

## Purpose
Define the runtime-neutral semantic conditions for Host-Agent evidence support and evidence-preserving digest emission.

## Requirements

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
