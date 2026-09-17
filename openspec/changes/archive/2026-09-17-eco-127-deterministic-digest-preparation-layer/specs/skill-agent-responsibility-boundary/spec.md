## MODIFIED Requirements

### Requirement: Skill owns only the validated Evidence Feed
The Skill SHALL own the accepted deterministic semantics and trust guarantees of Feed production and current published-Feed consumption, including the typed, versioned, deterministic preparation of a non-persisted Agent-facing `DigestContext` wholly derived from one validated Feed. Preparation SHALL remain Feed consumption machinery and SHALL NOT become a second semantic or evidence capability. The Skill SHALL NOT own or expose Audit, Event Structuring, post-Feed entity/candidate processing, market analytics/state, confidence, watchlist, scoring, ranking, financial interpretation, Agent reasoning, narrative generation, or Agent orchestration.

#### Scenario: Skill responsibility is traced
- **WHEN** repository behavior and Host-Agent integration are inspected
- **THEN** the Skill owns only Feed evidence, its contracted trust guarantees, and deterministic preparation of that evidence for bounded Agent consumption

### Requirement: Host Agent owns evidence-preserving digest presentation
The Host Agent SHALL receive one validated-Feed-bound `DigestContext` and SHALL own semantic-support assessment, summarization, editorial grouping, headings, readability ordering, transparent consolidation or omission, compression accounting, formatting, and user-facing Digest presentation. Those responsibilities SHALL NOT introduce significance, anomaly, causality, market impact, prediction, investment recommendation, trading judgment, or another authority not established by the prepared Feed evidence.

#### Scenario: Host Agent produces the digest
- **WHEN** one `DigestContext` is summarized for a user
- **THEN** presentation remains Host-Agent-owned, evidence-preserving, transparently accounted, and free of repository-produced or Agent-inferred financial judgment

### Requirement: Feed authority remains bounded after consumption
Deterministic projection into `DigestContext` SHALL preserve Feed identity, provenance, verification, freshness, coverage, and limitation semantics without upgrading any source statement. Every context evidence value SHALL remain traceable to its supporting Feed item. Any Host-Agent modification, synthesis, or derivation SHALL remain Host-Agent-owned and SHALL NOT be represented as unchanged Feed or `DigestContext` output.

#### Scenario: Feed evidence is transformed
- **WHEN** validated Feed evidence is projected into a context and the Host Agent summarizes or combines it
- **THEN** the context adds no evidence authority and the resulting language carries no authority beyond its semantically supporting Feed evidence
