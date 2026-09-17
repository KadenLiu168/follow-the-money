## MODIFIED Requirements

### Requirement: Host Agent owns Feed support assessment and emission
The Host Agent SHALL assess whether prepared validated Feed evidence supports each factual summary and SHALL own the operational decision to emit the evidence-preserving Digest. Deterministic `DigestContext` preparation SHALL enforce domain evidence eligibility and traceability but SHALL NOT assess natural-language entailment or approve a proposed assertion. The repository SHALL provide no Audit, Event, grounding-proof, entailment, retry, rewrite, or final-output validation runtime.

#### Scenario: Current Feed is summarized
- **WHEN** the Host Agent prepares a digest from one validated-Feed-bound `DigestContext`
- **THEN** it assesses semantic support and emits only an admissible evidence-preserving presentation without invoking another repository capability

### Requirement: Feed grounding remains runtime-neutral
This capability SHALL permit the typed, versioned Agent-facing `DigestContext` only as deterministic, non-persisted current-Feed consumption machinery. The context SHALL have no independent evidence schema or authority, and the repository SHALL NOT introduce a grounding schema, grounding validator, private Agent process, capability registry, orchestration, embedded model runtime, prompt pipeline, retry/rewrite loop, or shared state.

#### Scenario: Runtime implementation is inspected
- **WHEN** schemas and production entries are reviewed
- **THEN** only Feed production, current Feed consumption, deterministic context preparation, and Host-Agent-owned presentation exist, with no grounding or Audit runtime and no second evidence schema
