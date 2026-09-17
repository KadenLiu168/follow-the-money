## MODIFIED Requirements

### Requirement: Every active Feed domain has exactly one presentation contract
The contract set SHALL contain exactly one domain contract per active Feed payload type and none for non-Feed domains. Deterministic Digest preparation SHALL select it only by the validated `payload.type` and SHALL apply its closed evidence-field rules before Agent consumption. Selection SHALL NOT depend on title, Provider, source text, inferred subtype, model behavior, or another evidence category.

#### Scenario: Contract inventory matches the active Feed
- **WHEN** the presentation-contract inventory is compared with the accepted active Feed payload types
- **THEN** `news`, `macro_release`, `policy`, `positioning`, and `filing` each have exactly one contract and no additional domain contract exists

#### Scenario: Host Agent presents a validated item
- **WHEN** Digest preparation receives an item from the current validated Feed
- **THEN** it applies the one contract matching that item's validated `payload.type` without changing the Feed or invoking an inferred domain resolver

### Requirement: Domain contracts define closed presentation evidence
Each domain contract MUST list the validated identity, provenance, typed payload, and applicable `semantic_context` field paths eligible for `DigestContext` and Host-Agent expression. Deterministic preparation SHALL enforce that closed list: unlisted fields and `raw_metadata` are not presentation evidence, and a new Feed field remains ineligible until its domain contract and preparation implementation explicitly add it.

#### Scenario: Listed field is presented
- **WHEN** a whitelisted field contains validated evidence
- **THEN** preparation exposes it and the Host Agent may express it within the field's source authority and the domain contract's representation rules

#### Scenario: Unlisted or raw metadata is encountered
- **WHEN** an item contains `raw_metadata` or another field not listed by its domain contract
- **THEN** preparation excludes that field from `DigestContext` and the Host Agent cannot use it to add, complete, or reinterpret a Digest fact

#### Scenario: Feed schema gains a field
- **WHEN** a new Feed field is valid under a later accepted Feed contract but the domain presentation contract and preparation implementation have not been updated
- **THEN** the new field remains ineligible for Digest preparation and presentation

### Requirement: Missing evidence remains missing
Domain presentation contracts and deterministic preparation SHALL preserve null values, explicit unavailability, and absent or legacy-omitted fields as missing evidence. They MUST NOT reconstruct missing facts from titles, free-form text, `raw_metadata`, another item, a historical Feed or checkpoint, external knowledge, or an unstated calculation.

#### Scenario: Legacy semantic context is absent
- **WHEN** a valid legacy `news`, `macro_release`, or `policy` item omits `semantic_context`
- **THEN** preparation and presentation use only eligible evidence actually present and do not reconstruct semantic context

#### Scenario: Optional evidence is null or unavailable
- **WHEN** a whitelisted field is null or explicitly unavailable
- **THEN** `DigestContext` preserves that state and the Digest preserves or accurately discloses the limitation instead of inventing a value or interpretation

### Requirement: Presentation contracts preserve the Host-Agent and runtime boundary
The Skill SHALL retain validated current-Feed consumption and fail-closed behavior, then deterministically prepare one typed, versioned, non-persisted `DigestContext`. Closed field selection and domain dispatch SHALL belong to preparation; recommended representation, semantic-support assessment, summarization, editorial operations, compression decisions and accounting, and final formatting SHALL remain Host-Agent-owned. The presentation hierarchy and preparation layer MUST NOT modify Feed schemas, Providers, collection, validation, identity, publication, or retrieval, and MUST NOT add a prose renderer, template engine, prompt pipeline, model invocation, Agent orchestration, standalone Digest service, or another evidence authority.

#### Scenario: Skill instructions are inspected
- **WHEN** `SKILL.md`, Digest preparation, and the presentation-contract hierarchy are reviewed together
- **THEN** the Skill invokes one deterministic context preparation path and retains global failure and safety requirements without duplicating domain evidence rules

#### Scenario: Runtime surface is inspected
- **WHEN** schemas, runtime entries, imports, and publication behavior are compared before and after this Change
- **THEN** only a bounded current-Feed preparation stage is added, Feed behavior is unchanged, and no narrative, analytical, model, or orchestration runtime exists
