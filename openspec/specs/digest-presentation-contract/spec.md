# digest-presentation-contract Specification

## Purpose

Define the static global, compression, and per-domain contracts that constrain Host-Agent presentation of the validated current Evidence Feed while preserving its evidence-only authority and existing runtime boundary.

## Requirements

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

### Requirement: Domain presentation remains evidence preserving
Every domain contract SHALL define its factual purpose, closed evidence fields, recommended representation, and forbidden interpretation. It MUST NOT direct the Host Agent to add unsupported facts or infer importance, anomaly, ranking, score, causality, sentiment, direction, market impact, signal, prediction, recommendation, or trading instruction. Source-authored analysis MAY be summarized only with attribution and no authority upgrade.

#### Scenario: Facts invite financial interpretation
- **WHEN** a domain item contains facts from which an analytical or financial conclusion could be inferred
- **THEN** the applicable contract permits presentation of supported facts but prohibits adding the inferred conclusion

#### Scenario: Source contains analytical wording
- **WHEN** analytical or predictive wording is itself present in whitelisted validated source evidence
- **THEN** the contract permits only an accurately attributed summary that is not presented as a Feed, Skill, or Host-Agent conclusion

### Requirement: Compression rules are global and transparent
The presentation-contract hierarchy SHALL define compression once for all domains. It SHALL preserve per-domain accounting of total items as individually summarized, represented through consolidation, or omitted; preserve traceability to all items supporting a consolidated summary; disclose omissions as editorial compression; and prohibit importance or relevance claims as an omission rationale.

#### Scenario: Multiple items are consolidated
- **WHEN** multiple Feed items are represented through one consolidated summary
- **THEN** every supporting item remains traceable and the domain accounting assigns all of them to the consolidated category

#### Scenario: Item is omitted for compression
- **WHEN** a Feed item is not represented in the Digest body
- **THEN** the omission is counted and disclosed without characterizing the item as unimportant or irrelevant

### Requirement: Presentation contracts preserve the Host-Agent and runtime boundary
The Skill SHALL retain validated current-Feed consumption and fail-closed behavior, then deterministically prepare one typed, versioned, non-persisted `DigestContext`. Closed field selection and domain dispatch SHALL belong to preparation; recommended representation, semantic-support assessment, summarization, editorial operations, compression decisions and accounting, and final formatting SHALL remain Host-Agent-owned. The presentation hierarchy and preparation layer MUST NOT modify Feed schemas, Providers, collection, validation, identity, publication, or retrieval, and MUST NOT add a prose renderer, template engine, prompt pipeline, model invocation, Agent orchestration, standalone Digest service, or another evidence authority.

#### Scenario: Skill instructions are inspected
- **WHEN** `SKILL.md`, Digest preparation, and the presentation-contract hierarchy are reviewed together
- **THEN** the Skill invokes one deterministic context preparation path and retains global failure and safety requirements without duplicating domain evidence rules

#### Scenario: Runtime surface is inspected
- **WHEN** schemas, runtime entries, imports, and publication behavior are compared before and after this Change
- **THEN** only a bounded current-Feed preparation stage is added, Feed behavior is unchanged, and no narrative, analytical, model, or orchestration runtime exists

### Requirement: Digest presentation is content-first while remaining auditable
The Digest presentation SHALL make presentable current-window Feed updates its primary substantive surface while preserving all required status, evidence cutoff, coverage, Provider and source availability, provenance, freshness, warnings, degraded-state, compression-reconciliation, and limitation information as an auditable secondary surface. Content-first is a semantic priority and MUST NOT prescribe fixed headings, heading levels, section order, visual style, importance, ranking, significance, analysis, or a relevance filter. Provenance or attribution needed to support a factual statement, source-authored analysis, or consolidated summary SHALL remain sufficiently close to the supported content; global Provider, coverage, and reconciliation metadata MAY remain in the secondary audit surface.

#### Scenario: Healthy Feed has presentable current updates
- **WHEN** the Host Agent presents a healthy valid Feed with one or more presentable current-window updates
- **THEN** those updates are the primary substantive reading surface and the complete required audit information remains visible as secondary context rather than preceding the content as an audit report

#### Scenario: Degraded but usable Feed needs a material caveat
- **WHEN** a valid usable Feed has degradation or a source limitation that materially affects interpretation of the current-window content
- **THEN** the Host Agent may place a concise data-limitation caveat before the affected content without presenting the Feed as healthy, and SHALL still preserve the complete status, coverage, freshness, warning, availability, and limitation information in the secondary audit surface

#### Scenario: Valid Feed has no presentable current updates
- **WHEN** the Host Agent presents a valid Feed with zero presentable current-window updates
- **THEN** the primary message accurately states that the current Feed window has no presentable updates, creates no content, and is followed by auditable status, evidence cutoff, coverage, Provider or source availability, and applicable limitations that distinguish an empty window from collection or Provider problems

#### Scenario: Content is compressed
- **WHEN** current-window items are individually summarized, represented through consolidation, or omitted for editorial compression
- **THEN** content-first presentation preserves exact per-domain reconciliation, traceability to every item supporting a consolidation, and omission disclosure without using importance or relevance as the presentation or omission rationale

#### Scenario: Local provenance supports presented content
- **WHEN** provenance or source attribution is necessary to support a factual statement, source-authored analysis, or consolidated summary
- **THEN** that provenance or attribution remains sufficiently close to the supported content and is not moved exclusively into global audit metadata

#### Scenario: Retrieval validation or preparation fails
- **WHEN** current Feed retrieval, validation, or deterministic preparation fails
- **THEN** the existing fail-closed behavior produces no normal Digest and content-first presentation does not alter or bypass the failure path
