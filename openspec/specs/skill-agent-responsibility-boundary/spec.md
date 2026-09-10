# skill-agent-responsibility-boundary Specification

## Purpose
Define the evidence-preserving responsibility and authority boundary between the Feed Skill and the Host Agent.

## Requirements

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
