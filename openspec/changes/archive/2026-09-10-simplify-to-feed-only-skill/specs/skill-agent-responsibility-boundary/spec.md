## ADDED Requirements

### Requirement: Skill owns only the validated Evidence Feed
The Skill SHALL own the accepted deterministic semantics and trust guarantees of Feed production and current published-Feed consumption. It SHALL NOT own or expose Audit, Event Structuring, post-Feed entity/candidate processing, market analytics/state, confidence, watchlist, scoring, ranking, financial interpretation, Agent reasoning, narrative generation, or Agent orchestration.

#### Scenario: Skill responsibility is traced
- **WHEN** repository behavior and Host-Agent integration are inspected
- **THEN** the Skill owns only Feed evidence and its contracted provenance, freshness, coverage, degradation, validation, identity, publication, and consumption guarantees

### Requirement: Host Agent owns evidence-preserving digest presentation
The Host Agent SHALL own summarization, editorial grouping, headings, readability ordering, transparent consolidation or omission, formatting, semantic-support assessment, and user-facing digest presentation over the current validated Feed. Those responsibilities SHALL NOT introduce significance, anomaly, causality, market impact, prediction, investment recommendation, trading judgment, or another authority not established by the Feed evidence.

#### Scenario: Host Agent produces the digest
- **WHEN** the current validated Feed is summarized for a user
- **THEN** presentation remains Host-Agent-owned, evidence-preserving, transparently accounted, and free of repository-produced or Agent-inferred financial judgment

### Requirement: Feed authority remains bounded after consumption
Crossing the Skill-Agent boundary SHALL preserve Feed provenance, verification, identity, freshness, coverage, and limitation semantics without upgrading any source statement. Any Host-Agent modification, synthesis, or derivation SHALL remain Host-Agent-owned and SHALL NOT be represented as an unchanged Feed result.

#### Scenario: Feed evidence is transformed
- **WHEN** the Host Agent summarizes or combines Feed items
- **THEN** the resulting language remains Host-Agent-owned and carries no authority beyond its semantically supporting Feed evidence

## REMOVED Requirements

### Requirement: Host Agent owns the non-deterministic presentation layer
**Reason**: Superseded by the Feed-only Host-Agent presentation requirement.
**Migration**: Apply the replacement requirement without independent capability inputs.

### Requirement: Skill owns accepted deterministic capability semantics
**Reason**: The six-family ownership model is removed.
**Migration**: Skill ownership is limited to Evidence Feed.

### Requirement: Deterministic engine is an internal Skill responsibility layer
**Reason**: Superseded by a Feed-only internal responsibility boundary.
**Migration**: Surviving deterministic machinery serves only Feed behavior.

### Requirement: Skill-produced results have bounded semantic authority
**Reason**: Superseded by the Feed-specific bounded-authority requirement.
**Migration**: Treat only validated Feed evidence as Skill-produced output.

### Requirement: Consumer mutation or derivation transfers semantic ownership
**Reason**: Incorporated into the Feed-specific bounded-authority requirement.
**Migration**: Host-Agent transformations remain Host-Agent-owned.

### Requirement: Agent-owned information remains Agent-owned
**Reason**: Non-Feed Agent inputs no longer enter repository deterministic capabilities.
**Migration**: Agent-owned digest presentation remains governed by the replacement presentation requirement.

### Requirement: Deterministic transformation preserves input provenance and authority
**Reason**: Non-Feed transformations are removed and Feed authority is covered by the replacement requirement.
**Migration**: Preserve authority through Feed validation and evidence-preserving summarization.

### Requirement: Responsibility boundary remains separate from grounding and runtime policy
**Reason**: The private invocation and retained-capability policy branches are removed.
**Migration**: Keep the normal Feed-to-Host-Agent path free of repository runtime orchestration.
