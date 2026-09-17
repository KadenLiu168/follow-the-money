## Purpose

Define the typed, versioned, deterministic preparation of one non-persisted Agent-facing `DigestContext` from the canonical validated current Evidence Feed without creating another evidence authority or schema.

## ADDED Requirements

### Requirement: Digest preparation consumes exactly one validated current Feed
Normal Digest preparation SHALL begin only after the existing canonical published-Feed retrieval, bundle reconstruction, Feed schema and semantic validation, provenance validation, and identity validation have succeeded. It SHALL reuse that path without duplicating its validation rules and SHALL NOT accept a local, historical, stale, partial, caller-supplied, or independently reconstructed Feed.

#### Scenario: Current Feed validation succeeds
- **WHEN** canonical current published-Feed consumption returns one fully validated Feed
- **THEN** preparation derives one `DigestContext` from exactly that Feed

#### Scenario: Retrieval or validation fails
- **WHEN** any existing published-Feed retrieval or validation step fails
- **THEN** preparation exposes the existing typed failure and produces no partial `DigestContext`

### Requirement: DigestContext is typed, versioned, and deterministic
`DigestContext` SHALL have an explicit code-level type and `context_version`. Its Agent-facing representation SHALL be canonical JSON produced by the repository's canonical serializer. For the same validated Feed and supported context version, preparation SHALL produce byte-identical output independent of wall-clock time, environment, filesystem state, iteration order, or network state after Feed consumption.

#### Scenario: Preparation is repeated
- **WHEN** the same validated Feed is prepared repeatedly under the same supported context version
- **THEN** the resulting typed values and canonical JSON bytes are identical

#### Scenario: Context version is unsupported
- **WHEN** an unsupported `context_version` is requested or encountered
- **THEN** preparation fails closed without silently interpreting it as another version

### Requirement: DigestContext remains wholly Feed-derived and Feed-bound
Every evidence, status, coverage, warning, freshness, availability, limitation, and provenance value in `DigestContext` SHALL be copied from or deterministically computed from the single validated input Feed. The context SHALL carry the source Feed's schema version, `run_id`, `content_digest`, window, and evidence cutoff so its derivation remains unambiguous. Fixed context-version and structural discriminator values SHALL describe only the preparation contract and SHALL NOT assert evidence. Preparation MUST NOT enrich values from external knowledge, another Feed, a checkpoint, current configuration, Provider access, free-form interpretation, or an unstated calculation.

#### Scenario: Feed identity is retained
- **WHEN** a context is prepared successfully
- **THEN** its Feed binding exactly matches the validated Feed's schema version, `run_id`, `content_digest`, window, and evidence cutoff

#### Scenario: Evidence is unavailable
- **WHEN** an eligible Feed value is null, absent, legacy-omitted, or explicitly unavailable
- **THEN** preparation preserves that limitation and does not reconstruct or replace the value

### Requirement: DigestContext exposes deterministic status and coverage context
`DigestContext` SHALL include the validated pipeline status, warnings, structured coverage gap when present, all planned Provider outcomes needed to express availability and freshness, and one deterministic total for each active Feed domain. Provider ordering SHALL preserve the validated Feed order, domain ordering SHALL be `news`, `macro_release`, `policy`, `positioning`, and `filing`, and all five domains SHALL be represented even when empty.

#### Scenario: Healthy Feed is prepared
- **WHEN** a healthy validated Feed is prepared
- **THEN** the context exposes healthy status, the exact warnings and coverage state, all Provider availability and freshness outcomes, and five reconciled domain totals

#### Scenario: Degraded Feed is prepared
- **WHEN** a consumable degraded Feed contains warnings, unavailable-source information, or a coverage gap
- **THEN** those limitations remain explicit in the context without being weakened or described as complete coverage

### Requirement: ECO-126 domain evidence rules are enforced before Agent consumption
Preparation SHALL select a domain solely from each item's validated `payload.type` and SHALL expose only the identity, provenance, typed payload, and applicable `semantic_context` paths permitted by that domain's accepted presentation contract. `raw_metadata`, every unlisted field, and a field added by a future Feed contract SHALL remain unavailable until the applicable Digest presentation contract and preparation implementation are deliberately updated. Preparation SHALL retain deterministic traceability from every projected item to its Feed item ID and eligible source provenance.

#### Scenario: Eligible field is present
- **WHEN** a validated item contains a value permitted by its matching ECO-126 domain contract
- **THEN** the prepared domain item exposes that value with its Feed item and provenance references intact

#### Scenario: Unlisted field is present
- **WHEN** a valid Feed item contains `raw_metadata` or another field not permitted by its matching domain presentation contract
- **THEN** that field is absent from `DigestContext` and cannot become Agent presentation evidence

#### Scenario: Every item is accounted for
- **WHEN** a validated Feed is prepared
- **THEN** each Feed item appears exactly once under its validated domain and the five domain totals equal the projected item counts

### Requirement: DigestContext is not an independent evidence schema or persisted artifact
`DigestContext` SHALL be a non-persisted Agent-facing consumption interface, not a published artifact, checkpoint, cache, Feed replacement, or independent evidence authority. It SHALL have no standalone JSON Schema and SHALL NOT change Feed schemas, canonical Feed bytes, Feed identity, collection, validation, publication, or retrieval. Context validity and authority SHALL derive from successful construction by the typed preparation layer and its retained binding to the validated Feed.

#### Scenario: Repository artifacts are inspected
- **WHEN** schemas, published Feed products, checkpoints, caches, and runtime state are inspected after preparation
- **THEN** no `DigestContext` artifact or schema exists and no persistent state was mutated

#### Scenario: Context and Feed authority are compared
- **WHEN** a projected context value is used by the Host Agent
- **THEN** its authority remains limited to its supporting validated Feed evidence and the context adds no independent fact or verification claim

### Requirement: Preparation performs no Host-Agent presentation work
Preparation SHALL NOT summarize prose, create editorial headings, group items by inferred subject, choose readability order, consolidate evidence, omit evidence for compression, assess semantic support for a proposed assertion, generate final-output accounting, or format a user-facing Digest. It SHALL NOT add importance, priority, ranking, significance, anomaly, causality, sentiment, direction, market impact, signal, prediction, recommendation, investment judgment, or trading instruction, and SHALL add no model/LLM runtime, prompt pipeline, renderer, template engine, retry/rewrite loop, or Agent orchestration.

#### Scenario: Context is prepared
- **WHEN** preparation succeeds
- **THEN** the output contains only deterministic Feed-derived context and leaves evidence-preserving summarization and formatting to the Host Agent
