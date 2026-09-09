## MODIFIED Requirements

### Requirement: Host Agent owns the non-deterministic presentation layer
For normal `/follow-the-money` invocation, the Host Agent SHALL own evidence-preserving summarization, editorial grouping, heading derivation, readability ordering, transparent consolidation or omission, formatting, and user-facing information-digest narrative under `information-digest-invocation`. It SHALL NOT turn those presentation responsibilities into financial interpretation, significance, anomaly, causality, market-impact, prediction, investment recommendation, or trading judgment. Outside the normal digest path, Host-Agent reasoning state, interpretations, hypotheses, judgments, conclusions, and inputs supplied to independently invoked deterministic capabilities SHALL remain Host-Agent-owned under the existing ownership and authority rules. These responsibilities SHALL NOT imply an invocation order, call count, control flow, Agent data structure, transport mechanism, repository LLM runtime, or obligation to invoke a retained capability that has no production orchestration caller.

#### Scenario: Host Agent produces the current information digest
- **WHEN** the Host Agent summarizes and formats the current validated published Feed for `/follow-the-money`
- **THEN** the digest presentation is Host-Agent-owned, remains within the evidence and editorial boundaries of `information-digest-invocation`, and is not a Skill-produced deterministic result or financial judgment

#### Scenario: Host Agent uses an independent repository capability
- **WHEN** the Host Agent explicitly supplies inputs to on-demand Audit or Event Structuring independently of the digest path
- **THEN** the Agent-originated selections, interpretations, and assertions remain Host-Agent-owned while the deterministic result retains only its governing Skill guarantees

#### Scenario: Host Agent produces research interpretation
- **WHEN** financial evidence or a Skill-produced deterministic result is interpreted, combined with judgment, or expressed as a user-facing conclusion outside the normal information-digest behavior
- **THEN** the interpretation, judgment, conclusion, and narrative remain Host-Agent-owned and are not represented as output required or produced by the normal `/follow-the-money` digest invocation

#### Scenario: Responsibility is reviewed for runtime implications
- **WHEN** the Host Agent responsibility allocation is inspected
- **THEN** it defines no Agent object, transport, invocation sequence, call count, control flow, embedded model execution, or requirement to invoke a retained capability

## RENAMED Requirements

- FROM: `### Requirement: Host Agent owns the non-deterministic research layer`
- TO: `### Requirement: Host Agent owns the non-deterministic presentation layer`
