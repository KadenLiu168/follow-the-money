## MODIFIED Requirements

### Requirement: Digest invocation preserves the existing runtime boundary
Normal digest invocation SHALL retrieve and fail-closed validate only the canonical current published Feed under `feed-evidence-pipeline`. Retrieval or validation failure SHALL produce no digest and SHALL NOT trigger Provider collection, local or stale fallback, partial evidence output, another repository capability, or any embedded LLM/model runtime. Evidence Feed SHALL be the repository's sole semantic capability, while the information digest SHALL remain Host-Agent-owned output behavior rather than a deterministic Feed field or capability.

#### Scenario: Feed consumption fails
- **WHEN** canonical published-Feed retrieval or validation fails
- **THEN** invocation surfaces the precise failure, stops without a digest, and invokes no fallback or independent capability

#### Scenario: Caller topology is inspected
- **WHEN** the information-digest contract is compared with repository schemas, runtime entries, and imports
- **THEN** only Feed production and current published-Feed consumption remain, and no Agent invocation, Audit, Event, market, confidence, watchlist, scoring, ranking, model, or prompt execution path exists
