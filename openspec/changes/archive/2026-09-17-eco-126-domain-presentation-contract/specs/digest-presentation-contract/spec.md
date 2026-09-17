## Purpose

Define the static global, compression, and per-domain contracts that constrain Host-Agent presentation of the validated current Evidence Feed while preserving its evidence-only authority and existing runtime boundary.

## ADDED Requirements

### Requirement: Every active Feed domain has exactly one presentation contract
The contract set SHALL contain exactly one domain contract per active Feed payload type and none for non-Feed domains. The global contract SHALL select it only by the validated `payload.type`. Selection SHALL remain a Host-Agent instruction and SHALL NOT add a repository resolver, serialized field, or runtime stage.

#### Scenario: Contract inventory matches the active Feed
- **WHEN** the presentation-contract inventory is compared with the accepted active Feed payload types
- **THEN** `news`, `macro_release`, `policy`, `positioning`, and `filing` each have exactly one contract and no additional domain contract exists

#### Scenario: Host Agent presents a validated item
- **WHEN** the Host Agent presents an item from the current validated Feed
- **THEN** it applies the one contract matching that item's validated `payload.type` without invoking a domain resolver or changing the Feed

### Requirement: Domain contracts define closed presentation evidence
Each domain contract MUST list the validated identity, provenance, typed payload, and applicable `semantic_context` field paths the Host Agent may express. The list SHALL be closed: unlisted fields and `raw_metadata` are not presentation evidence, and a new Feed field remains ineligible until its domain contract explicitly adds it.

#### Scenario: Listed field is presented
- **WHEN** a whitelisted field contains validated evidence
- **THEN** the Host Agent may express that evidence within the field's source authority and the domain contract's representation rules

#### Scenario: Unlisted or raw metadata is encountered
- **WHEN** an item contains `raw_metadata` or another field not listed by its domain contract
- **THEN** the Host Agent does not use that field to add, complete, or reinterpret a Digest fact

#### Scenario: Feed schema gains a field
- **WHEN** a new Feed field is valid under a later accepted Feed contract but the domain presentation contract has not been updated
- **THEN** the new field remains ineligible for Digest presentation

### Requirement: Missing evidence remains missing
Domain presentation contracts SHALL preserve null values, explicit unavailability, and absent or legacy-omitted fields as missing evidence. They MUST NOT direct the Host Agent to reconstruct missing facts from titles, free-form text, `raw_metadata`, another item, a historical Feed or checkpoint, external knowledge, or an unstated calculation.

#### Scenario: Legacy semantic context is absent
- **WHEN** a valid legacy `news`, `macro_release`, or `policy` item omits `semantic_context`
- **THEN** presentation uses only the domain contract's whitelisted evidence that is actually present and does not reconstruct semantic context

#### Scenario: Optional evidence is null or unavailable
- **WHEN** a whitelisted field is null or explicitly unavailable
- **THEN** the Digest preserves or accurately discloses that limitation instead of inventing a value or interpretation

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
The Skill SHALL retain validated current-Feed consumption, fail-closed behavior, global Digest output requirements, and safety constraints while delegating field-level presentation guidance to the static contract hierarchy. Presentation contracts SHALL remain Host-Agent-owned instructions and MUST NOT modify Feed schemas, Providers, collection, validation, identity, publication, or retrieval, and MUST NOT add a renderer, template engine, prompt pipeline, model or Agent orchestration, standalone digest service, or other execution path.

#### Scenario: Skill instructions are inspected
- **WHEN** `SKILL.md` and the presentation-contract hierarchy are reviewed together
- **THEN** `SKILL.md` retains the global invocation and evidence boundary, links to the global presentation contract, and does not duplicate domain-specific field or representation rules

#### Scenario: Runtime surface is inspected
- **WHEN** repository schemas, runtime entries, imports, and publication behavior are compared before and after this Change
- **THEN** the Feed and invocation topology are unchanged and the presentation contracts exist only as static Host-Agent guidance
