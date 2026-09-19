## MODIFIED Requirements

### Requirement: Normal invocation produces the current information digest
Normal `/follow-the-money` invocation SHALL consume the current validated published Feed through deterministic preparation and provide its one Feed-bound `DigestContext` version `2` to the Host Agent for direct production of a reader-first evidence-based information digest. The Host Agent SHALL use `content.updates` as its default substantive input and `status.domains` plus `status.limitations` only for applicable conditional disclosure. Invocation SHALL NOT request or accept a company, asset, topic, time range, research question, or other user-supplied scope and SHALL NOT read a historical Feed or checkpoint. “Current” or “new” SHALL mean membership proven by the applicable preparation contract, not mere presence in the current Feed or comparison with a prior publication.

#### Scenario: Skill is invoked without scope
- **WHEN** a user invokes `/follow-the-money`
- **THEN** the Skill prepares one v2 context from the current validated published Feed and the Host Agent generates the Digest without requesting another scope

#### Scenario: Current evidence is described
- **WHEN** the Digest characterizes evidence as current or new
- **THEN** that evidence is represented by a prepared update whose closed membership authority falls within the Feed window

### Requirement: Digest exposes status, updates, provenance, freshness, coverage, and limitations
The preparation layer SHALL expose the exact Feed binding, deterministic current update units, source provenance sufficient for claim-level traceability, compact reader-relevant domain status, and closed material limitations. The Host Agent SHALL accurately disclose limitations that affect understanding, including Provider unavailability, coverage gaps, carried or stale reference state, and unproven current membership when applicable. It SHALL NOT be required to present pipeline warning strings, full Provider outcomes, complete freshness tables, domain totals, reference-item counts, or Feed-wide audit accounting.

#### Scenario: Healthy Feed is summarized
- **WHEN** a v2 context has current updates and no material limitation
- **THEN** the Digest presents traceable reader-facing updates without a mandatory audit appendix

#### Scenario: Degraded Feed is summarized
- **WHEN** a v2 context contains a Provider-unavailable or coverage limitation
- **THEN** the Digest explains that compact material limitation without presenting degraded coverage as complete

### Requirement: Editorial transformations remain evidence preserving
The Host Agent MAY summarize prepared updates, group them by source or explicit document or event type, derive editorial headings, order content for readability, consolidate source-supported repetition, and compress detail. Every factual claim SHALL remain semantically supported by one or more prepared updates and traceable Feed evidence. The Host Agent SHALL NOT reclassify Feed items as current, expose reference items as substantive updates, perform Feed-wide omission accounting, or represent editorial grouping, order, consolidation, or compression as importance, ranking, relevance, or another deterministic Feed result.

#### Scenario: Related evidence is consolidated
- **WHEN** multiple prepared updates are represented by one consolidated statement
- **THEN** the statement remains traceable to all updates supporting its factual content and adds no unsupported fact or authority

#### Scenario: Content is ordered for readability
- **WHEN** the Host Agent changes presentation order or creates headings
- **THEN** the Digest does not characterize that presentation choice as significance, priority, ranking, or membership evidence

### Requirement: Digest invocation preserves the existing runtime boundary
Normal Digest invocation SHALL retrieve and fail-closed validate only the canonical current published Feed, deterministically prepare one non-persisted Feed-bound `DigestContext` version `2`, and pass it to the Host Agent. Retrieval, validation, or preparation failure SHALL produce no context or Digest and SHALL NOT trigger Provider collection, local or stale fallback, partial evidence output, historical input, another evidence capability, or any embedded model runtime. Version `1` complete projection SHALL NOT remain a parallel normal Host-Agent input. Evidence Feed SHALL remain the repository's sole evidence authority, and the Digest SHALL remain Host-Agent-owned output behavior rather than a Feed field or repository-generated narrative.

#### Scenario: Feed consumption fails
- **WHEN** canonical published-Feed retrieval, validation, or v2 preparation fails
- **THEN** invocation surfaces the precise failure and stops without a partial context, v1 fallback, or Digest

#### Scenario: Caller topology is inspected
- **WHEN** the invocation contract is compared with repository schemas, runtime entries, and imports
- **THEN** only Feed production, current published-Feed consumption, deterministic v2 structuring, and Host-Agent presentation remain

## ADDED Requirements

### Requirement: Digest selection is non-exhaustive and claim-traceable
The default Digest SHALL NOT be required to display every Feed item or domain, reconcile every item into representation categories, expose all supporting item IDs, disclose every omission, or print complete Provider and freshness audit tables. Every factual claim that the Digest does present SHALL remain traceable through a prepared update to supporting Feed evidence and eligible original-source provenance.

#### Scenario: Feed contains extensive reference state
- **WHEN** a validated Feed contains many old, carried, stale, or unproven-current items and only a small number of eligible current updates
- **THEN** the Digest uses the eligible updates as substantive content and uses only applicable compact statuses and limitations for the remaining conditions

## REMOVED Requirements

### Requirement: Compression coverage is transparent
**Reason**: Feed-wide individual/consolidated/omitted accounting makes a complete Feed require a complete visible textual audit and conflicts with selective reader-facing v2 preparation.

**Migration**: Replace per-domain totals and representation counts with claim-level traceability from each presented statement through `DigestUpdateUnit` to supporting Feed evidence. Full evidence accounting remains in the authoritative Feed.
