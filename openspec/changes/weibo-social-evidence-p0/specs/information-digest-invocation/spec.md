## MODIFIED Requirements

### Requirement: Normal invocation produces the current information digest
Normal `/follow-the-money` invocation SHALL consume the current validated published Feed through deterministic preparation and provide its one Feed-bound `DigestContext` version `3` to the Host Agent for direct production of a reader-first evidence-based information digest. The Host Agent SHALL use `content.updates` as its default substantive input and `status.domains` plus `status.limitations` only for applicable conditional disclosure. Invocation SHALL NOT request or accept a company, asset, topic, time range, research question, or other user-supplied scope and SHALL NOT read a historical Feed or checkpoint. “Current” or “new” SHALL mean membership proven by the applicable preparation contract, not mere presence in the current Feed or comparison with a prior publication.

#### Scenario: Skill is invoked without scope
- **WHEN** a user invokes `/follow-the-money`
- **THEN** the Skill prepares one v3 context from the current validated published Feed and the Host Agent generates the Digest without requesting another scope

#### Scenario: Current evidence is described
- **WHEN** the Digest characterizes evidence as current or new
- **THEN** that evidence is represented by a prepared update whose closed membership authority falls within the Feed window

### Requirement: Digest exposes status, updates, provenance, freshness, coverage, and limitations
The preparation layer SHALL expose the exact Feed binding, deterministic current update units, source provenance sufficient for claim-level traceability, compact reader-relevant domain status, and closed material limitations. The Host Agent SHALL accurately disclose limitations that affect understanding, including Provider unavailability, coverage gaps, carried or stale reference state, and unproven current membership when applicable. Current Social acquisition failure SHALL be disclosed even with zero updates, including configured affected accounts, the missing Feed window, a sanitized reason and no automatic backfill. This current-digest disclosure SHALL be the only added notification path; no push, email, GitHub issue, historical lookup or later gap reminder SHALL be introduced. It SHALL NOT be required to present pipeline warning strings, full Provider outcomes, complete freshness tables, domain totals, reference-item counts, or Feed-wide audit accounting.

#### Scenario: Healthy Feed is summarized
- **WHEN** a v3 context has current updates and no material limitation
- **THEN** the Digest presents traceable reader-facing updates without a mandatory audit appendix

#### Scenario: Degraded Feed is summarized
- **WHEN** a v3 context contains a Provider-unavailable or coverage limitation
- **THEN** the Digest explains that compact material limitation without presenting degraded coverage as complete

#### Scenario: Social fails while other current updates are absent
- **WHEN** a valid current Feed contains Social acquisition unavailability but no current update units
- **THEN** the digest still explains the affected selection, missing window, sanitized cause and no automatic backfill rather than saying only that no updates exist

### Requirement: Digest invocation preserves the existing runtime boundary
Normal Digest invocation SHALL retrieve and fail-closed validate only the canonical current published Feed, deterministically prepare one non-persisted Feed-bound `DigestContext` version `3`, and pass it to the Host Agent. Retrieval, validation, or preparation failure SHALL produce no context or Digest and SHALL NOT trigger Provider collection, local or stale fallback, partial evidence output, historical input, another evidence capability, or any embedded model runtime. Versions `1` and `2` SHALL NOT remain a parallel normal Host-Agent input. Evidence Feed SHALL remain the repository's sole evidence authority, and the Digest SHALL remain Host-Agent-owned output behavior rather than a Feed field or repository-generated narrative.

#### Scenario: Feed consumption fails
- **WHEN** canonical published-Feed retrieval, validation, or v3 preparation fails
- **THEN** invocation surfaces the precise failure and stops without a partial context, legacy context fallback, or Digest

#### Scenario: Caller topology is inspected
- **WHEN** the invocation contract is compared with repository schemas, runtime entries, and imports
- **THEN** only Feed production, current published-Feed consumption, deterministic v3 structuring, and Host-Agent presentation remain
