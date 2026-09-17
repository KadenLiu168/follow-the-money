# semantic-context Specification

## Purpose

Define one closed, deterministic, evidence-only semantic context that lets a Host Agent express supported News, Macro, and Policy evidence without interpreting titles, parsing raw metadata, or inventing analysis.

## Requirements

### Requirement: Semantic context is one closed evidence-only primitive

`semantic_context` SHALL be one item-level structure shared by `news`, `macro_release`, and `policy`. It SHALL contain a context version, a bounded ordered entity set, one typed event fact with source-semantic time, a bounded ordered numeric-fact set, and exactly one domain-discriminated extension matching the item's payload type. Every nested object SHALL be closed to unknown members, every vocabulary SHALL be closed and documented, and all retained text SHALL be bounded, NFC-normalized source evidence.

The context SHALL express only who, what, when, source-supported facts, and exact numeric observations. It SHALL NOT express or accept cause, importance, confidence, ranking, sentiment, bullish/bearish direction, market impact, signal, prediction, recommendation, or trading semantics. Missing source facts SHALL remain null, empty, or explicitly unavailable as allowed by the closed field contract; they SHALL NOT be inferred from unrelated evidence.

#### Scenario: Context matches its domain

- **WHEN** a supported item is assigned a semantic context
- **THEN** its context version, event, entities, numeric facts, and exactly one domain extension validate under the closed contract for the item's payload discriminator

#### Scenario: Unknown or analytical meaning is supplied

- **WHEN** a context contains an unknown member or an impact, ranking, sentiment, signal, prediction, recommendation, or other analytical field
- **THEN** validation rejects the item rather than retaining the field as extensible metadata

#### Scenario: Source does not establish an optional fact

- **WHEN** the normalized source evidence does not establish a referenced entity, effective date, affected scope, revision, or optional numeric observation
- **THEN** the context uses only the domain contract's null, empty, or explicit-unavailable representation and does not derive the missing fact

### Requirement: News context identifies the bounded event and document

A `news` context SHALL identify one source-supported subject entity, a deterministic event category, the source-semantic occurrence time or explicit null, and a document containing the retained title and a closed document type. Referenced entities SHALL be retained only when an exact Provider-local rule can identify their source text and type; their order SHALL be deterministic and duplicates SHALL be removed without entity resolution.

News mapping SHALL use only the normalized payload, validated source/provider identity, and closed Provider-local constants or exact rules. A Provider organization MAY be the subject only when the source evidence establishes that organization as the actor or issuing subject; otherwise the mapping SHALL use the closed non-inferential fallback allowed for that Provider or fail context construction. It SHALL NOT infer people, organizations, assets, importance, intent, or event consequences from open-ended language.

#### Scenario: BLS statistical release is mapped as news

- **WHEN** a normalized BLS release is emitted as `news` under the current Provider contract
- **THEN** the context identifies the source-supported subject, the closed official-statistical-release category, the retained document title/type, and only explicitly supported referenced entities

#### Scenario: Generic official notice has no supported references

- **WHEN** a supported official-news item has a valid subject and document but no exact referenced-entity match
- **THEN** the context retains the bounded subject/event/document facts and emits an empty referenced-entity set

#### Scenario: Mapping cannot establish a required news fact

- **WHEN** no closed mapping can establish the required subject, event category, or document type from normalized evidence
- **THEN** semantic construction fails closed instead of emitting an invented or free-form category

### Requirement: Macro context preserves indicator, period, observations, and real revisions

A `macro_release` context SHALL identify the indicator by a stable Provider-local identifier and source-supported display name, retain the normalized reporting period, and publish observations as deterministically ordered metric, value, unit, and availability facts. When `payload.observation_period` is null, the context SHALL retain `period = null` rather than invent a period or failing construction. Present numeric values SHALL use the shared bounded canonical-decimal rules; unavailable observations SHALL retain their explicit reason and unit without fabricating a value.

A revision SHALL be present only when the same source evidence explicitly identifies the prior and revised values for the same indicator and reporting period. A previous-period observation, consensus, comparison value, or earlier Feed SHALL NOT be relabeled as a revision. Context construction SHALL use no historical Feed lookup or arithmetic not explicitly required by the closed mapping.

#### Scenario: NBS observation is enriched

- **WHEN** a supported NBS macro release contains a known series, reporting period, actual value, unit, and previous-period value
- **THEN** the context exposes the indicator name, period, canonical actual and previous observations in deterministic order and does not claim a revision

#### Scenario: Observation is unavailable

- **WHEN** a supported observation has a null value and an allowed unavailable reason
- **THEN** the semantic numeric fact retains the metric, unit, and reason with no invented numeric value

#### Scenario: Reporting period is unavailable

- **WHEN** a supported macro-release payload has `observation_period = null`
- **THEN** semantic context construction succeeds with `period = null` and does not infer a period from release time, title, or another observation

#### Scenario: Explicit revision is supplied

- **WHEN** normalized source evidence explicitly supplies previous and revised values for the same indicator and period
- **THEN** the context retains both canonical values as a revision with their common unit and source-supported period

#### Scenario: Unknown indicator mapping is encountered

- **WHEN** a macro item uses an indicator identifier outside the closed Provider-local mapping
- **THEN** semantic construction fails closed rather than converting the identifier into an unverified display name

### Requirement: Policy context states issuer and policy facts without interpretation

A `policy` context SHALL identify the source-supported issuing organization, a closed policy type, a closed factual action, the source-semantic announcement time, an effective date or null, and a deterministically ordered bounded affected-scope set. The effective date and affected scope SHALL be retained only when normalized source evidence explicitly supplies them. A generic official-policy-announcement action MAY be used only as a documented Provider-local fallback that describes the document act itself and makes no claim about policy effect.

#### Scenario: Monetary-policy announcement is mapped

- **WHEN** a supported PBOC or Federal Reserve item exactly matches a closed monetary-policy announcement mapping
- **THEN** the context identifies the issuing organization, monetary-policy type, factual announcement action, and only source-supported effective date and affected scope

#### Scenario: Policy date is not stated

- **WHEN** the source establishes the announcement time but not an effective date
- **THEN** the context retains the announcement time and a null effective date without copying retrieval time or guessing from the title

#### Scenario: Generic policy fallback is used

- **WHEN** a supported policy document does not match a more specific closed action but its issuing Provider and document act are established
- **THEN** the context uses the Provider's generic official-policy-announcement action and adds no inferred purpose, impact, or affected market

### Requirement: Context construction is deterministic and numerically bounded

For the same validated Provider identity, normalized payload, source evidence, and fixed mapping version, context construction SHALL return byte-identical semantic context independent of process-global decimal state, input-map insertion order, or repeated execution. Entity, numeric-fact, referenced-entity, and affected-scope ordering and duplicate handling SHALL be explicit total orders.

Numeric context SHALL reuse the accepted bounded canonical numeric construction from the Producer semantic core. This reuse SHALL NOT add text, identity, time, comparison, classification, serialization, or domain-mapping responsibility to the numeric primitive, and SHALL NOT expose its internal derivation objects in the Feed.

#### Scenario: Identical fixture is repeated

- **WHEN** the same Provider fixture is normalized and enriched repeatedly under different ambient decimal contexts and map insertion orders
- **THEN** every emitted semantic context has identical canonical bytes

#### Scenario: Numeric bound is violated

- **WHEN** a context mapping receives a malformed, non-finite, inexact, over-precision, over-exponent, over-magnitude, or unit-incompatible numeric fact
- **THEN** construction fails through the existing bounded numeric authority without rounding or truncation
