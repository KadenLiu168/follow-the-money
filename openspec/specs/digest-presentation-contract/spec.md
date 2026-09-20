# digest-presentation-contract Specification

## Purpose

Define the static global, compression, and per-domain contracts that constrain Host-Agent presentation of the validated current Evidence Feed while preserving its evidence-only authority and existing runtime boundary.

## Requirements

### Requirement: Every active Feed domain has exactly one presentation contract
The contract set SHALL contain exactly one domain contract per active Feed payload type and none for non-Feed domains. Deterministic Digest preparation SHALL select the contract only from a Feed item's validated `payload.type`, apply its closed current-membership rule, and construct any eligible reader-facing unit before Agent consumption. Selection and membership SHALL NOT depend on title, Provider-name inference, free-form source text, model behavior, importance, relevance, or another evidence category.

#### Scenario: Contract inventory matches the active Feed
- **WHEN** the presentation-contract inventory is compared with the accepted active Feed payload types
- **THEN** `news`, `macro_release`, `policy`, `positioning`, and `filing` each have exactly one contract and no additional domain contract exists

#### Scenario: Host Agent presents a validated item
- **WHEN** Digest preparation evaluates a validated Feed item
- **THEN** the Host Agent receives it as substantive evidence only when the matching contract produces a current `DigestUpdateUnit`

### Requirement: Domain contracts define closed presentation evidence
Each domain contract MUST define its Reader-Facing Unit, Current Membership, Supporting Evidence, Domain Purpose, Evidence Fields, Recommended Representation, and Forbidden Interpretation. Deterministic preparation SHALL enforce the closed unit type, event-time authority, evidence paths, and provenance paths. Unlisted fields, `raw_metadata`, non-current complete items, and a field added by a future Feed contract SHALL remain unavailable until the applicable presentation contract and preparation implementation explicitly add them.

#### Scenario: Listed field is presented
- **WHEN** a current unit contains a whitelisted value
- **THEN** the Host Agent may express it only within its source authority and the domain contract's representation rules

#### Scenario: Unlisted or raw metadata is encountered
- **WHEN** a Feed item is not eligible for a unit or contains an unlisted field
- **THEN** preparation excludes that evidence from Agent-facing substantive content

#### Scenario: Feed schema gains a field
- **WHEN** a later accepted Feed contract adds a field that the matching Digest domain contract has not added to its closed supporting evidence
- **THEN** preparation keeps that field unavailable to the Host Agent

### Requirement: Missing evidence remains missing

Domain presentation contracts and deterministic preparation SHALL preserve null values, explicit unavailability, and absent or legacy-omitted fields as missing evidence. Whitelisted `source_content.text` MAY directly support attributed factual statements, but preparation and presentation MUST NOT use it, titles, `raw_metadata`, another item, a historical Feed or checkpoint, external knowledge, or an unstated calculation to reconstruct an absent structured semantic field or claim that omitted source content is known.

#### Scenario: Legacy semantic context is absent

- **WHEN** a valid legacy `news`, `macro_release`, or `policy` item omits `semantic_context` but may contain other eligible evidence
- **THEN** preparation and presentation use only eligible evidence actually present and do not reconstruct semantic context from source content, title, or another field

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
The presentation-contract hierarchy SHALL define reader-facing compression once for all domains. Every factual claim actually presented SHALL remain traceable through one or more `DigestUpdateUnit` values to their supporting Feed item IDs and eligible original-source provenance. The Host Agent MAY summarize, consolidate source-supported repetition, or omit prepared updates from prose without reporting Feed-domain totals, individual/consolidated/omitted counts, all supporting item IDs to the reader, or a complete audit surface. An omission or the absence of a Feed item from `content.updates` SHALL NOT be characterized as evidence of irrelevance, insignificance, invalidity, low importance, or another financial or editorial judgment.

#### Scenario: Multiple items are consolidated
- **WHEN** the Host Agent consolidates multiple prepared updates into one factual statement
- **THEN** the statement remains supported by every update used for its factual content and internally traceable to their Feed evidence

#### Scenario: Item is omitted for compression
- **WHEN** a Feed item is not eligible for `content.updates` or a prepared update is omitted from prose
- **THEN** the Digest need not account for it visibly and does not describe the omission as an importance or relevance determination

### Requirement: Presentation contracts preserve the Host-Agent and runtime boundary
The Skill SHALL retain validated current-Feed consumption and fail-closed behavior, then deterministically prepare one typed, versioned, non-persisted `DigestContext` v2. Closed evidence selection, current-membership classification, unit construction, reference-state classification, compact status, and material limitations SHALL belong to preparation. Semantic-support assessment, evidence-preserving summarization, source- or explicit-document-type presentation grouping, headings, readability ordering, source-supported consolidation, and final formatting SHALL remain Host-Agent-owned. Neither layer SHALL modify Feed production or add a prose renderer, template engine, prompt pipeline, model invocation, Agent orchestration, standalone Digest service, or another evidence authority.

#### Scenario: Skill instructions are inspected
- **WHEN** `SKILL.md`, Digest preparation, and the presentation hierarchy are reviewed together
- **THEN** the Skill invokes one v2 preparation path and the Host Agent consumes `content.updates` as its default substantive input

#### Scenario: Runtime surface is inspected
- **WHEN** schemas, runtime entries, imports, publication behavior, and persistent state are compared before and after the Change
- **THEN** Feed behavior is unchanged and no narrative, analytical, model, renderer, orchestration, or persisted Digest runtime exists

### Requirement: Digest presentation is content-first while remaining auditable
The default Digest SHALL be a selective reader-facing editorial view of the current validated Feed, not a complete textual projection. `content.updates` SHALL be its default substantive input; `status.domains` and `status.limitations` SHALL be conditionally disclosed when their compact conditions affect a reader's understanding. Material limitations SHALL remain visible and accurate, while full Feed evidence, Provider outcomes, freshness records, counts, and audit detail remain available through the authoritative Feed rather than being required in the Digest. Statement-local provenance or attribution SHALL remain sufficiently close to every factual claim it supports. Reader-first presentation SHALL NOT prescribe fixed headings, section order, visual style, importance, ranking, significance, analysis, or relevance filtering.

#### Scenario: Healthy Feed has presentable current updates
- **WHEN** one or more prepared current updates are available
- **THEN** the Host Agent presents an accurate concise view of those updates with claim-level provenance and only applicable compact status or limitations

#### Scenario: Valid Feed has no presentable current updates
- **WHEN** `content.updates` is empty
- **THEN** the Host Agent accurately reports that no deterministically eligible current updates are available and uses compact status or limitations to distinguish empty, old, carried, stale, unproven-current, and unavailable conditions without exposing reference items

#### Scenario: Degraded but usable Feed needs a material caveat
- **WHEN** a compact limitation records Provider unavailability or affected coverage
- **THEN** the Host Agent discloses that material limitation without printing the complete Provider audit table or presenting coverage as complete

#### Scenario: Content is compressed
- **WHEN** the Host Agent summarizes, consolidates, or omits prepared updates for reader-facing compression
- **THEN** every presented factual claim remains supported and traceable without mandatory per-domain reconciliation or omission counts

#### Scenario: Local provenance supports presented content
- **WHEN** provenance or attribution is needed to support a factual statement or consolidated summary
- **THEN** it remains sufficiently close to that content while internal Feed item IDs need not be printed

#### Scenario: Retrieval validation or preparation fails
- **WHEN** current Feed retrieval, validation, or deterministic preparation fails
- **THEN** the existing fail-closed behavior produces no normal Digest

### Requirement: Non-current Feed evidence remains authoritative but non-substantive
Evidence excluded from `content.updates` SHALL remain unchanged and authoritative in the validated Feed. Its absence from substantive Digest content SHALL mean only that the v2 membership contract did not expose it as a current reader update; it SHALL NOT imply that the evidence is irrelevant, insignificant, invalid, false, or unimportant.

#### Scenario: Old Form 13F remains in the Feed
- **WHEN** a validated Feed retains watched-company Form 13F current state accepted before the current window
- **THEN** the Digest may disclose compact `no_current_update` status but does not reproduce the filing or holdings as current substantive content

### Requirement: Bounded official source content supports evidence-preserving summaries

The news, macro-release, and policy domain contracts SHALL list `payload.source_content.text`, `payload.source_content.format`, and `payload.source_content.truncated` as closed supporting evidence for current units. The Host Agent MAY summarize factual statements and source-authored analysis explicitly present in that text, subject to the existing attribution, authority, claim support, compression, and forbidden-interpretation rules. It SHALL NOT claim that bounded source content is a complete document when `truncated = true`, expose extraction method or document hash, access the source URL, or treat source wording as a Feed, Skill, or Host-Agent conclusion.

#### Scenario: Official text supports a concise summary

- **WHEN** a current unit contains bounded official source text supporting factual statements
- **THEN** the Host Agent may produce a concise attributed summary whose claims remain supported and traceable to that unit and its Feed item

#### Scenario: Official source text contains analysis

- **WHEN** whitelisted official source content itself contains analytical, causal, predictive, or policy-purpose wording
- **THEN** the Host Agent may summarize it only with clear source attribution and without adopting or upgrading that wording as its own conclusion

#### Scenario: Source content is truncated

- **WHEN** a current unit carries `source_content.truncated = true`
- **THEN** the Host Agent does not characterize the bounded text as the complete official document or infer facts from omitted content

#### Scenario: Extraction provenance exists only in the Feed

- **WHEN** the validated Feed contains an extraction method and document digest but DigestContext excludes them
- **THEN** presentation neither reconstructs nor prints those Feed-only provenance values
