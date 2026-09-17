## MODIFIED Requirements

### Requirement: Normal invocation produces the current information digest
Normal `/follow-the-money` invocation SHALL consume the current validated published Feed through the deterministic preparation layer and provide its one Feed-bound `DigestContext` to the Host Agent for direct production of an evidence-based information digest. It SHALL NOT request or accept a company, asset, topic, time range, research question, or other user-supplied scope, and it SHALL NOT read a historical Feed or checkpoint. “Current” or “new” SHALL mean that evidence belongs to the current Feed window; it SHALL NOT claim comparison with a prior publication unless that comparison is explicitly present in prepared validated Feed evidence.

#### Scenario: Skill is invoked without scope
- **WHEN** a user invokes `/follow-the-money`
- **THEN** the Skill prepares one context from the current validated published Feed and the Host Agent generates the digest without asking for company, asset, topic, time-range, research-question, or other scope input

#### Scenario: Current evidence is described
- **WHEN** the digest characterizes an item as current or new
- **THEN** the characterization refers only to membership in the prepared current Feed window and does not imply comparison with a historical Feed or checkpoint

### Requirement: Digest exposes status, updates, provenance, freshness, coverage, and limitations
The Digest preparation layer SHALL expose in `DigestContext` the validated Feed data status and evidence cutoff, eligible current evidence, source provenance sufficient to trace factual summaries to supporting Feed items, material freshness information, deterministic domain totals, Provider coverage, and data-quality or unavailable-source limitations. The Host Agent SHALL present those facts and SHALL preserve validated degraded status, warnings, Provider availability, and coverage gaps without presenting degraded evidence as complete.

#### Scenario: Healthy Feed is summarized
- **WHEN** a context derived from the healthy current validated Feed is summarized
- **THEN** the digest states its status and cutoff and presents traceable current updates together with freshness, coverage, and limitation information

#### Scenario: Degraded Feed is summarized
- **WHEN** a context derived from a consumable degraded Feed is summarized
- **THEN** the digest preserves and explains the applicable warnings, Provider availability, freshness, and coverage gaps

### Requirement: Digest invocation preserves the existing runtime boundary
Normal Digest invocation SHALL retrieve and fail-closed validate only the canonical current published Feed under `feed-evidence-pipeline`, deterministically prepare one non-persisted Feed-bound `DigestContext`, and pass it to the Host Agent. Retrieval, validation, or preparation failure SHALL produce no context or digest and SHALL NOT trigger Provider collection, local or stale fallback, partial evidence output, historical input, another evidence capability, or any embedded LLM/model runtime. Evidence Feed SHALL remain the repository's sole semantic and evidence capability; Digest preparation SHALL remain bounded consumption machinery, and the information digest SHALL remain Host-Agent-owned output behavior rather than a Feed field or repository-generated narrative.

#### Scenario: Feed consumption fails
- **WHEN** canonical published-Feed retrieval, validation, or deterministic preparation fails
- **THEN** invocation surfaces the precise failure, stops without a partial context or digest, and invokes no fallback or independent capability

#### Scenario: Caller topology is inspected
- **WHEN** the information-digest contract is compared with repository schemas, runtime entries, and imports
- **THEN** only Feed production, current published-Feed consumption, typed context preparation, and Host-Agent presentation remain, with no Audit, Event, market, confidence, watchlist, scoring, ranking, model, prompt, renderer, or orchestration execution path
