## Purpose

Define how normal `/follow-the-money` invocation turns the current validated published evidence Feed into a transparent, evidence-based information digest without adding financial judgment or repository-hosted model execution.

## ADDED Requirements

### Requirement: Normal invocation produces the current information digest
Normal `/follow-the-money` invocation SHALL consume the current validated published Feed and directly produce an evidence-based information digest. It SHALL NOT request or accept a company, asset, topic, time range, research question, or other user-supplied scope, and it SHALL NOT read a historical Feed or checkpoint. “Current” or “new” SHALL mean that evidence belongs to the current Feed window; it SHALL NOT claim comparison with a prior publication unless that comparison is explicitly present in a validated Feed item.

#### Scenario: Skill is invoked without scope
- **WHEN** a user invokes `/follow-the-money`
- **THEN** the Host Agent consumes the current validated published Feed and generates the digest without asking for company, asset, topic, time-range, research-question, or other scope input

#### Scenario: Current evidence is described
- **WHEN** the digest characterizes an item as current or new
- **THEN** the characterization refers only to membership in the current Feed window and does not imply comparison with a historical Feed or checkpoint

### Requirement: Digest exposes status, updates, provenance, freshness, coverage, and limitations
The digest SHALL present Feed data status and evidence cutoff, current evidence updates, source provenance sufficient to trace factual summaries to supporting Feed items, material freshness information, domain and Provider coverage, and data-quality or unavailable-source limitations. It SHALL preserve validated degraded status, warnings, Provider availability, and coverage gaps without presenting degraded evidence as complete.

#### Scenario: Healthy Feed is summarized
- **WHEN** the current validated Feed is healthy
- **THEN** the digest states its status and cutoff and presents traceable current updates together with freshness, coverage, and limitation information

#### Scenario: Degraded Feed is summarized
- **WHEN** the current validated Feed is degraded
- **THEN** the digest preserves and explains the applicable warnings, Provider availability, freshness, and coverage gaps

### Requirement: Editorial transformations remain evidence preserving
The Host Agent MAY group related Feed evidence across domains, derive editorial headings, order content for readability, consolidate repetition, and compress detail. Every factual summary SHALL remain semantically supported by the cited Feed evidence, and editorial grouping, heading, order, consolidation, or compression SHALL NOT be represented as a deterministic Feed result or as evidence of importance.

#### Scenario: Related evidence is consolidated
- **WHEN** multiple Feed items are represented by one consolidated update
- **THEN** the update remains traceable to all supporting items and does not add facts or authority beyond their semantic support

#### Scenario: Content is ordered for readability
- **WHEN** the Host Agent changes presentation order or creates editorial groups
- **THEN** the digest does not characterize that presentation as significance, priority, ranking, or another deterministic finding

### Requirement: Compression coverage is transparent
For every Feed domain, the digest SHALL report the domain’s total item count and account for every item as individually summarized, represented through a consolidated summary, or omitted. Any omission SHALL be disclosed as editorial compression and SHALL NOT be justified by an unsupported importance or relevance judgment. The accounting categories SHALL reconcile to the domain total.

#### Scenario: All items are represented
- **WHEN** every item in a domain is individually summarized or represented through consolidation
- **THEN** the digest reports the domain total, the applicable representation counts, and zero omitted items

#### Scenario: Items are omitted for compression
- **WHEN** one or more Feed items are not represented in the digest body
- **THEN** the digest reports the omitted count, reconciles all categories to the domain total, and discloses the omission without claiming that omitted items are unimportant or irrelevant

### Requirement: Digest excludes financial judgment
The digest SHALL NOT introduce or infer significance, anomaly, signal, causality, market regime, asset impact, price-in status, prediction, investment recommendation, or trading instruction. It MAY accurately summarize such wording only when it is itself part of the validated source evidence, provided the digest attributes the statement to that source and does not adopt or upgrade it as a Host-Agent or Skill conclusion.

#### Scenario: Evidence could invite interpretation
- **WHEN** validated Feed items contain facts from which a financial interpretation could be inferred
- **THEN** the digest summarizes the supported facts without adding significance, anomaly, causality, market-impact, prediction, or investment conclusions

#### Scenario: Source contains analytical language
- **WHEN** a validated Feed item explicitly records a source’s analytical or predictive statement
- **THEN** the digest may summarize it only with clear source attribution and without representing it as a Skill-verified or Host-Agent-derived conclusion

### Requirement: Digest invocation preserves the existing runtime boundary
Normal digest invocation SHALL retain canonical published-Feed retrieval and fail-closed validation under `feed-evidence-pipeline`. Retrieval or validation failure SHALL produce no digest and SHALL NOT trigger Provider collection, local or stale fallback, partial evidence output, Audit, Event Structuring, another retained deterministic capability, or any embedded LLM/model runtime in the repository. The information digest SHALL remain Host-Agent-owned output behavior and SHALL NOT become a seventh family in the deterministic semantic capability catalog.

#### Scenario: Feed consumption fails
- **WHEN** canonical published-Feed retrieval or validation fails
- **THEN** invocation surfaces the precise failure, stops without a digest, and invokes no fallback or independent capability

#### Scenario: Caller topology is inspected
- **WHEN** the information digest contract is compared with the repository capability catalog and runtime paths
- **THEN** Feed production and the six deterministic capability families remain unchanged, no retained capability is wired into the digest path, and the repository contains no model or prompt execution path
