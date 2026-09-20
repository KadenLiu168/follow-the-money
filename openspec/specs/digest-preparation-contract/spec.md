# digest-preparation-contract Specification

## Purpose

Define the typed, versioned, deterministic preparation of one non-persisted Agent-facing `DigestContext` from the canonical validated current Evidence Feed without creating another evidence authority or schema.

## Requirements

### Requirement: Digest preparation consumes exactly one validated current Feed
Normal Digest preparation SHALL begin only after the existing canonical published-Feed retrieval, bundle reconstruction, Feed schema and semantic validation, provenance validation, and identity validation have succeeded. It SHALL reuse that path without duplicating its validation rules and SHALL NOT accept a local, historical, stale, partial, caller-supplied, or independently reconstructed Feed.

#### Scenario: Current Feed validation succeeds
- **WHEN** canonical current published-Feed consumption returns one fully validated Feed
- **THEN** preparation derives one `DigestContext` from exactly that Feed

#### Scenario: Retrieval or validation fails
- **WHEN** any existing published-Feed retrieval or validation step fails
- **THEN** preparation exposes the existing typed failure and produces no partial `DigestContext`

### Requirement: DigestContext is typed, versioned, and deterministic
Normal Digest preparation SHALL produce the explicit code-level `DigestContext` version `2`. Its Agent-facing representation SHALL be canonical JSON produced by the repository's canonical serializer. For the same validated Feed and supported context version, preparation SHALL produce byte-identical typed values and bytes independent of wall-clock time, environment, filesystem state, iteration order, current configuration, network state after Feed consumption, historical Feed state, checkpoint state, or model behavior. Version `1` SHALL NOT remain a normal Agent-facing output, and any unsupported version SHALL fail closed.

#### Scenario: Preparation is repeated
- **WHEN** the same validated Feed is prepared repeatedly as context version `2`
- **THEN** the resulting typed values, unit identities, ordering, status descriptors, limitation descriptors, and canonical JSON bytes are identical

#### Scenario: Context version is unsupported
- **WHEN** preparation is requested with a context version other than `2`
- **THEN** preparation fails closed without emitting version `1`, silently interpreting the request as version `2`, or producing a partial context

### Requirement: DigestContext remains wholly Feed-derived and Feed-bound
Every evidence, status, coverage, warning, freshness, availability, limitation, and provenance value in `DigestContext` SHALL be copied from or deterministically computed from the single validated input Feed. The context SHALL carry the source Feed's schema version, `run_id`, `content_digest`, window, and evidence cutoff so its derivation remains unambiguous. Fixed context-version and structural discriminator values SHALL describe only the preparation contract and SHALL NOT assert evidence. Preparation MUST NOT enrich values from external knowledge, another Feed, a checkpoint, current configuration, Provider access, free-form interpretation, or an unstated calculation.

#### Scenario: Feed identity is retained
- **WHEN** a context is prepared successfully
- **THEN** its Feed binding exactly matches the validated Feed's schema version, `run_id`, `content_digest`, window, and evidence cutoff

#### Scenario: Evidence is unavailable
- **WHEN** an eligible Feed value is null, absent, legacy-omitted, or explicitly unavailable
- **THEN** preparation preserves that limitation and does not reconstruct or replace the value

### Requirement: DigestContext exposes deterministic status and coverage context
`DigestContext` version `2` SHALL expose `status.domains` and `status.limitations` as closed, typed, Feed-derived descriptors rather than copying complete Feed item, Provider-outcome, warning, freshness, coverage, or reconciliation audit surfaces. Domain descriptors SHALL use only the closed states `current_updates_available`, `no_current_update`, `carried_reference_state`, `stale_reference_state`, `current_membership_unproven`, `provider_unavailable`, and `domain_empty`; implementation MAY represent unavailable Providers exclusively as limitation descriptors rather than duplicating them in domain status. Material Provider unavailability and a structured Feed coverage gap SHALL remain accurately represented by closed limitation codes with the supporting Provider identity, affected coverage groups, or gap bounds needed for reader-facing disclosure. Attempted, fetched, accepted, rejected, upstream HTTP status, raw warning strings, complete Provider rows, Feed-domain totals, reference-item counts, and representation-accounting counts SHALL NOT be exposed by default.

#### Scenario: Healthy Feed is prepared
- **WHEN** every reader-facing scope is either represented by a current update or contains no current evidence condition requiring disclosure
- **THEN** preparation emits the current units and only the compact deterministic domain status required by the closed contract

#### Scenario: Degraded Feed is prepared
- **WHEN** a validated consumable Feed records a Provider as unavailable and identifies its affected coverage groups
- **THEN** preparation emits a `provider_unavailable` limitation containing the Provider ID and affected coverage groups without copying the Provider audit row or raw warning text

#### Scenario: Feed contains a coverage gap
- **WHEN** the validated Feed contains a structured coverage gap
- **THEN** preparation emits one closed coverage-gap limitation retaining its exact Feed-supported bounds

### Requirement: ECO-126 domain evidence rules are enforced before Agent consumption
Preparation SHALL select a domain solely from each Feed item's validated `payload.type` and SHALL expose only current `DigestUpdateUnit` evidence paths permitted by that domain's accepted presentation contract. A unit SHALL separate its closed structural fields, event-time semantic, source provenance, supporting evidence, and Feed-item trace. `raw_metadata`, complete non-current Feed items, every unlisted field, and a field added by a future Feed contract SHALL remain unavailable until the applicable Digest presentation contract and preparation implementation are deliberately updated. Every exposed unit SHALL retain deterministic traceability to at least one supporting Feed item ID and sufficient eligible source provenance to reach the original source when present.

#### Scenario: Eligible field is present
- **WHEN** a Feed item has contract-proven current membership and contains values permitted by its matching domain contract
- **THEN** preparation exposes one closed update unit carrying only those eligible values, source provenance, event-time semantic, and Feed-item trace

#### Scenario: Unlisted field is present
- **WHEN** a Feed item is not a contract-proven current update or contains `raw_metadata` or another unlisted field
- **THEN** preparation excludes the complete item or unlisted field from `content.updates` and does not copy it into another Agent-facing evidence collection

#### Scenario: Every item is accounted for
- **WHEN** a validated Feed is prepared
- **THEN** every Feed item is deterministically classified as a current unit candidate, an explicit non-current condition, or an unproven-current condition without requiring every item to appear in Agent-facing content

### Requirement: DigestContext is not an independent evidence schema or persisted artifact
`DigestContext` SHALL be a non-persisted Agent-facing consumption interface, not a published artifact, checkpoint, cache, Feed replacement, or independent evidence authority. It SHALL have no standalone JSON Schema and SHALL NOT change Feed schemas, canonical Feed bytes, Feed identity, collection, validation, publication, or retrieval. Context validity and authority SHALL derive from successful construction by the typed preparation layer and its retained binding to the validated Feed.

#### Scenario: Repository artifacts are inspected
- **WHEN** schemas, published Feed products, checkpoints, caches, and runtime state are inspected after preparation
- **THEN** no `DigestContext` artifact or schema exists and no persistent state was mutated

#### Scenario: Context and Feed authority are compared
- **WHEN** a projected context value is used by the Host Agent
- **THEN** its authority remains limited to its supporting validated Feed evidence and the context adds no independent fact or verification claim

### Requirement: Preparation performs no Host-Agent presentation work
Preparation MAY perform only contract-defined deterministic current-membership classification, reader-facing unit construction, compact domain-status derivation, material-limitation derivation, and canonical ordering wholly supported by explicit validated Feed evidence. It SHALL NOT perform semantic inference, open-ended topic or event grouping, title/provider/date/keyword/embedding similarity grouping, importance selection, top-N selection, ranking, readability ordering, summarization, prose generation, financial interpretation, semantic-support assessment for proposed prose, or final-output accounting. It SHALL add no model/LLM runtime, prompt pipeline, renderer, template engine, retry/rewrite loop, or Agent orchestration.

#### Scenario: Context is prepared
- **WHEN** preparation succeeds
- **THEN** it emits only deterministic Feed-derived units, status, limitations, and traceability while leaving evidence-preserving summarization and presentation to the Host Agent

#### Scenario: Several documents appear related
- **WHEN** multiple Feed items share a Provider, date, title prefix, keyword, or apparent subject but no accepted shared identity
- **THEN** preparation does not merge them into one update unit

### Requirement: DigestContext v2 contains only current update units as substantive content
`DigestContext` version `2` SHALL retain the exact source Feed schema version, `run_id`, `content_digest`, window, and evidence cutoff under `feed`; SHALL expose substantive evidence only as `content.updates`; and SHALL expose non-substantive conditions only as compact `status.domains` and `status.limitations`. It SHALL NOT expose `domains[].items[]`, `reference_state`, `unresolved_items`, complete Provider outcomes, or another collection of non-current evidence. Each `DigestUpdateUnit` SHALL contain a deterministic `unit_id`, a domain from the accepted five-domain whitelist, a unit type from `news_publication`, `macro_release`, `policy_document`, `positioning_report`, or `sec_filing`, an explicit event-time `kind` and `value`, Provider identity, closed source provenance, closed supporting evidence, and `trace.feed_item_ids`.

#### Scenario: Current item becomes an update
- **WHEN** one validated Feed item satisfies its closed current-membership rule
- **THEN** preparation emits one unit whose trace identifies that supporting Feed item and whose evidence does not exceed the domain whitelist

#### Scenario: Feed contains reference evidence
- **WHEN** a valid Feed contains evidence that is old, carried, stale, or not provably current
- **THEN** preparation emits no complete representation of that evidence outside `content.updates` and represents only an applicable compact status

### Requirement: News, macro, and policy membership uses closed source-time authorities
Preparation SHALL evaluate membership in the half-open interval `[feed.window.start, feed.window.end)`. A news item SHALL become one `news_publication` unit only when `source.published_at` proves membership; an explicitly earlier publication SHALL not become a unit, and a missing, invalid, at-or-after-end, or otherwise unusable publication authority SHALL produce `current_membership_unproven`. A macro-release item SHALL become one `macro_release` unit only when `payload.released_at` proves membership, and a policy item SHALL become one `policy_document` unit only when `payload.announced_at` proves membership. Preparation SHALL NOT substitute news `occurred_at`, `source.updated_at`, `source.knowledge_available_at`, policy `effective_at`, retrieval time, or another timestamp for the named authority. Numeric facts, observation period, revisions, effective time, affected scope, policy type, and source-supported action SHALL remain supporting evidence inside the one applicable unit rather than becoming additional updates.

#### Scenario: News publication is inside the window
- **WHEN** `source.published_at` for a news item falls in `[window.start, window.end)`
- **THEN** preparation emits exactly one `news_publication` unit with event-time kind `published_at`

#### Scenario: Policy takes effect later
- **WHEN** a policy item's `payload.announced_at` is inside the window and `payload.effective_at` is later than the window
- **THEN** preparation emits one current `policy_document` unit using `announced_at` and retains `effective_at` only as supporting evidence

#### Scenario: Membership authority is missing
- **WHEN** the named domain membership authority is absent or unusable
- **THEN** preparation emits no update for that item and derives `current_membership_unproven` without using a fallback timestamp

### Requirement: SEC filings are accession-level reader updates
Preparation SHALL use `payload.accepted_at` as the SEC current-membership authority and SHALL NOT silently fall back to `filed_at`. A current Form 13F, Form 4, or beneficial-ownership top-level accession SHALL produce exactly one `sec_filing` unit regardless of its number of holdings, owners, transactions, reporting positions, footnotes, remarks, or comparison facts. A Form 13F accepted before the window SHALL not enter `content.updates` and SHALL yield `filing/form13f/no_current_update`. A beneficial-ownership `previous_snapshot` and other historical comparison evidence SHALL remain nested supporting evidence for the current accession and SHALL not become another update.

#### Scenario: Old watched Form 13F remains Feed state
- **WHEN** a Form 13F item's `accepted_at` is earlier than `window.start`
- **THEN** preparation emits no filing unit for it and emits compact `filing/form13f/no_current_update` status without exposing its holdings

#### Scenario: Current Form 4 has many entries
- **WHEN** one Form 4 accession is accepted inside the window and contains multiple non-derivative or derivative entries
- **THEN** preparation emits exactly one `sec_filing` unit and retains the entries only as supporting evidence

#### Scenario: Current beneficial-ownership filing has previous evidence
- **WHEN** one current 13D/G accession contains a previous snapshot or comparison reference
- **THEN** preparation emits exactly one unit for the current accession and no unit for the nested historical evidence

### Requirement: Positioning remains status-only without explicit report identity
Preparation SHALL NOT use `payload.as_of` alone as positioning publication-time or current-membership authority. A CFTC Provider freshness record with non-null `carried_forward_from_run_id` SHALL produce `carried_reference_state`; a contract-proven stale selected slice SHALL produce `stale_reference_state`; and a non-carried slice without explicit accepted shared report identity and publication-time evidence SHALL produce `current_membership_unproven`. In all three cases, market rows SHALL remain outside `content.updates`, while a source-supported `data_as_of` MAY be retained in compact status. A future `positioning_report` unit SHALL be permitted only after the accepted Feed contract exposes enough explicit shared identity and publication evidence to construct it without grouping by Provider, date, title, similarity, or row coincidence.

#### Scenario: CFTC slice is carried forward
- **WHEN** CFTC freshness has a non-null `carried_forward_from_run_id`
- **THEN** preparation emits no positioning units or market rows and emits `positioning/cftc/carried_reference_state` with supported `data_as_of` when available

#### Scenario: CFTC slice is stale
- **WHEN** the accepted freshness contract proves the selected CFTC slice is stale
- **THEN** preparation emits no positioning units or market rows and emits `positioning/cftc/stale_reference_state`

#### Scenario: CFTC rows lack report-level membership authority
- **WHEN** a non-carried CFTC slice contains row observation times but lacks explicit accepted shared report identity and publication-time evidence
- **THEN** preparation emits no positioning unit and emits `positioning/cftc/current_membership_unproven`

### Requirement: Unit and descriptor ordering is deterministic
Preparation SHALL preserve validated Feed item order among emitted update units. Unit identity SHALL be a closed deterministic function of unit type and supporting Feed item IDs and SHALL not depend on the Feed run ID, wall clock, presentation choice, or mutable external state. Domain status SHALL use the accepted domain order `news`, `macro_release`, `policy`, `positioning`, `filing` and a fixed closed scope order within each domain; limitations SHALL use a fixed code order and Provider ID or other closed deterministic tie-breakers. Counts of non-current evidence SHALL not participate in reader-facing descriptors.

#### Scenario: Input iteration is perturbed before validated order is restored
- **WHEN** semantically identical validated Feed input is prepared repeatedly
- **THEN** units, domain statuses, limitations, and canonical bytes have identical identity and order

### Requirement: Current reader units expose only reader-relevant source content

For a contract-proven current `news`, `macro_release`, or `policy` item, DigestContext v2 preparation SHALL include `payload.source_content.text`, `payload.source_content.format`, and `payload.source_content.truncated` in the matching unit's closed supporting evidence exactly when they are present in the validated Feed. Preparation SHALL NOT expose `payload.source_content.extraction_method` or `payload.source_content.document_sha256`; copy `raw_metadata`; dereference the source URL; parse a source document; fetch another resource; or reconstruct omitted source content. Source-content presence SHALL NOT change current-membership authority, unit identity, event time, ordering, status, limitations, or Feed-item traceability.

#### Scenario: Current enriched news or policy becomes a unit

- **WHEN** a validated current news or policy item contains source content
- **THEN** its existing reader unit carries the exact `text`, `format`, and `truncated` values as supporting evidence without exposing extraction method or document hash

#### Scenario: Current enriched macro release becomes a unit

- **WHEN** a validated current macro-release item contains source content
- **THEN** its existing macro-release unit carries the exact reader-relevant source-content values without changing numeric, period, revision, or membership semantics

#### Scenario: Enriched evidence is old or reference state

- **WHEN** source content belongs to an item that is old, carried, stale, or not provably current under the existing closed membership rules
- **THEN** preparation emits no substantive source content for it and preserves only the applicable existing compact status

#### Scenario: Source content is absent in a valid legacy item

- **WHEN** a valid migrated version-4 item has no source content
- **THEN** preparation preserves the omission and does not fetch, infer, or synthesize text

#### Scenario: Preparation is repeated

- **WHEN** the same validated major-5 Feed is prepared repeatedly
- **THEN** the resulting DigestContext v2 values and canonical bytes, including reader-relevant source content, are identical
