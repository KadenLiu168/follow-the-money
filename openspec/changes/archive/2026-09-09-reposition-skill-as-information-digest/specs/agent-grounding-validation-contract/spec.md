## MODIFIED Requirements

### Requirement: Host Agent owns a constrained output-admissibility decision
The Host Agent SHALL own the operational decision to emit its Agent-owned user-facing output, including an information digest governed by `information-digest-invocation`. It SHALL NOT emit a candidate as grounded user-facing output when it knows that the candidate contains either a factual assertion represented as grounded for which sufficient semantic support has not been established or an unresolved critical deterministic finding from an accepted deterministic validation capability that applies to the candidate. This admissibility rule SHALL remain semantic and SHALL NOT define a runtime pipeline.

#### Scenario: Candidate contains a known unsupported grounded assertion
- **WHEN** the Host Agent knows a candidate represents a factual assertion as grounded without sufficient semantic support
- **THEN** the candidate is inadmissible as grounded user-facing output and SHALL NOT be emitted unchanged

#### Scenario: Candidate contains an unresolved applicable critical finding
- **WHEN** the Host Agent knows an accepted deterministic validation capability has produced an unresolved critical finding that applies to a candidate
- **THEN** the candidate is inadmissible as grounded user-facing output and SHALL NOT be emitted unchanged

#### Scenario: Operational emission ownership is inspected
- **WHEN** the output-admissibility decision is reviewed
- **THEN** the Host Agent owns the operational emission decision subject to this contract without creating a Skill-owned narrative or runtime orchestration duty

### Requirement: Recovery restores admissibility without prescribing control flow
If a candidate is inadmissible under this contract, it SHALL NOT be emitted unchanged as grounded user-facing output. A later candidate MAY be emitted only after the relevant grounding or deterministic-validation violation no longer applies, including through conceptual removal, correction, re-grounding, reformulation, or re-evaluation. This contract SHALL NOT define retry count, automatic retry, rewrite loop, invocation order, call count, recovery topology, or a specific validator invocation.

#### Scenario: Relevant violation is resolved
- **WHEN** removal, correction, re-grounding, reformulation, or re-evaluation produces a later candidate to which the prior grounding or deterministic-validation violation no longer applies
- **THEN** the prior violation no longer makes that later candidate inadmissible under this contract

#### Scenario: Candidate is retried unchanged
- **WHEN** a later candidate preserves the same applicable grounding or deterministic-validation violation
- **THEN** it remains inadmissible as grounded user-facing output regardless of being submitted or considered again

#### Scenario: Recovery mechanism is requested
- **WHEN** retry count, automatic retry, rewrite loops, invocation order, call count, recovery topology, or a specific validator invocation is sought
- **THEN** this contract supplies no such runtime mechanism
