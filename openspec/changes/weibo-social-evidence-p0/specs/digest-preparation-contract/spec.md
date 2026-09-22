## MODIFIED Requirements

### Requirement: DigestContext is typed, versioned, and deterministic
Normal Digest preparation SHALL produce the explicit code-level `DigestContext` version `3`. Its Agent-facing representation SHALL be canonical JSON produced by the repository's canonical serializer. For the same validated Feed and supported context version, preparation SHALL produce byte-identical typed values and bytes independent of wall-clock time, environment, filesystem state, iteration order, current configuration, network state after Feed consumption, historical Feed state, checkpoint state, or model behavior. Versions `1` and `2` SHALL NOT remain a normal Agent-facing output, and any unsupported version SHALL fail closed.

#### Scenario: Preparation is repeated
- **WHEN** the same validated Feed is prepared repeatedly as context version `3`
- **THEN** the resulting typed values, unit identities, ordering, status descriptors, limitation descriptors, and canonical JSON bytes are identical

#### Scenario: Context version is unsupported
- **WHEN** preparation is requested with a context version other than `3`
- **THEN** preparation fails closed without emitting a legacy context version, silently interpreting the request as version `3`, or producing a partial context

### Requirement: DigestContext exposes deterministic status and coverage context
`DigestContext` version `3` SHALL expose `status.domains` and `status.limitations` as closed, typed, Feed-derived descriptors rather than copying complete Feed item, Provider-outcome, warning, freshness, coverage, or reconciliation audit surfaces. Domain descriptors SHALL use only the closed states `current_updates_available`, `no_current_update`, `carried_reference_state`, `stale_reference_state`, `current_membership_unproven`, `provider_unavailable`, `domain_empty`, and `not_configured`; for core scopes implementation MAY represent unavailable Providers exclusively as limitation descriptors rather than duplicating them in domain status. Material Provider unavailability and a structured Feed coverage gap SHALL remain accurately represented by closed limitation codes with the supporting Provider identity, affected coverage groups, or gap bounds needed for reader-facing disclosure. Attempted, fetched, accepted, rejected, upstream HTTP status, raw warning strings, complete Provider rows, Feed-domain totals, reference-item counts, and representation-accounting counts SHALL NOT be exposed by default.

#### Scenario: Healthy Feed is prepared
- **WHEN** every reader-facing scope is either represented by a current update or contains no current evidence condition requiring disclosure
- **THEN** preparation emits the current units and only the compact deterministic domain status required by the closed contract

#### Scenario: Degraded Feed is prepared
- **WHEN** a validated consumable Feed records a core Provider as unavailable and identifies its affected coverage groups
- **THEN** preparation emits a `provider_unavailable` limitation containing the Provider ID and affected coverage groups without copying the Provider audit row or raw warning text

#### Scenario: Feed contains a coverage gap
- **WHEN** the validated Feed contains a structured coverage gap
- **THEN** preparation emits one closed coverage-gap limitation retaining its exact Feed-supported bounds

#### Scenario: Social failure has no evidence items
- **WHEN** enabled Social acquisition is unavailable and its artifact is empty
- **THEN** preparation derives its mandatory structured failure limitation from the embedded outcome, account selection and Feed window, not from nonexistent items or current local configuration

### Requirement: DigestContext v2 contains only current update units as substantive content
`DigestContext` version `3` SHALL retain the exact source Feed schema version, `run_id`, `content_digest`, window, and evidence cutoff under `feed`; SHALL expose substantive evidence only as `content.updates`; and SHALL expose non-substantive conditions only as compact `status.domains` and `status.limitations`. It SHALL NOT expose `domains[].items[]`, `reference_state`, `unresolved_items`, complete Provider outcomes, or another collection of non-current evidence. Each `DigestUpdateUnit` SHALL contain a deterministic `unit_id`, a domain from the accepted six-domain whitelist, a unit type from `news_publication`, `macro_release`, `policy_document`, `positioning_report`, `sec_filing`, or `social_post`, an explicit event-time `kind` and `value`, Provider identity, closed source provenance, closed supporting evidence, and `trace.feed_item_ids`.

#### Scenario: Current item becomes an update
- **WHEN** one validated Feed item satisfies its closed current-membership rule
- **THEN** preparation emits one unit whose trace identifies that supporting Feed item and whose evidence does not exceed the domain whitelist

#### Scenario: Feed contains reference evidence
- **WHEN** a valid Feed contains evidence that is old, carried, stale, or not provably current
- **THEN** preparation emits no complete representation of that evidence outside `content.updates` and represents only an applicable compact status

### Requirement: Unit and descriptor ordering is deterministic
Preparation SHALL preserve validated Feed item order among emitted update units. Unit identity SHALL be a closed deterministic function of unit type and supporting Feed item IDs and SHALL not depend on the Feed run ID, wall clock, presentation choice, or mutable external state. Domain status SHALL use the accepted domain order `news`, `macro_release`, `policy`, `positioning`, `filing`, `social` and a fixed closed scope order within each domain; limitations SHALL use a fixed code order and Provider ID or other closed deterministic tie-breakers. Counts of non-current evidence SHALL not participate in reader-facing descriptors.

#### Scenario: Input iteration is perturbed before validated order is restored
- **WHEN** semantically identical validated Feed input is prepared repeatedly
- **THEN** units, domain statuses, limitations, and canonical bytes have identical identity and order

### Requirement: Current reader units expose only reader-relevant source content

For a contract-proven current `news`, `macro_release`, or `policy` item, DigestContext v3 preparation SHALL include `payload.source_content.text`, `payload.source_content.format`, and `payload.source_content.truncated` in the matching unit's closed supporting evidence exactly when they are present in the validated Feed. Preparation SHALL NOT expose `payload.source_content.extraction_method` or `payload.source_content.document_sha256`; copy `raw_metadata`; dereference the source URL; parse a source document; fetch another resource; or reconstruct omitted source content. Source-content presence SHALL NOT change current-membership authority, unit identity, event time, ordering, status, limitations, or Feed-item traceability.

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

- **WHEN** a valid core item preserved through bounded major-5 migration has no source content
- **THEN** preparation preserves the omission and does not fetch, infer, or synthesize text

#### Scenario: Preparation is repeated

- **WHEN** the same validated major-6 Feed is prepared repeatedly
- **THEN** the resulting DigestContext v3 values and canonical bytes, including reader-relevant source content, are identical

## ADDED Requirements

### Requirement: Social reader units use publication membership and closed attributed evidence

DigestContext v3 SHALL assign Social the domain `social`, scope `weibo_social`, unit type `social_post`, and membership/event-time authority `source.published_at`. Each top-level Social item in `[window.start, window.end)` SHALL produce exactly one current unit in validated Feed order with stable unit identity and Feed item trace. Preparation SHALL expose only platform, account identity, source post identity, content kind, authored text, bounded reference evidence, and existing eligible source provenance. It SHALL NOT expose raw HTML, Cookie, backend configuration, paths, statistics, arbitrary metadata, separately extracted links or attachments. It SHALL NOT cluster posts, infer topics or independently promote reference snapshots to units.

#### Scenario: Current reshare contains historical referenced text
- **WHEN** a current Social post refers to an earlier original post
- **THEN** exactly one Social reader unit contains the attributed nested reference and trace to the top-level Feed item

#### Scenario: Social post is outside the window
- **WHEN** its publication is earlier than start or at or after the cutoff
- **THEN** preparation emits no current Social unit and does not use retrieval or reference-post time as a substitute

### Requirement: Social status distinguishes success empty unavailable and disabled

Social status SHALL derive solely from the validated embedded activation, enabled account selection and Provider outcome. Enabled complete acquisition with items SHALL yield `current_updates_available`; complete empty SHALL yield `no_current_update`; acquisition failure SHALL yield `provider_unavailable`; disabled Social SHALL yield `not_configured`. Missing or contradictory required outcomes SHALL fail validation, not become disabled or empty.

For an unavailable Social Provider, preparation SHALL emit exactly one typed `social_acquisition_unavailable` limitation with Provider identity, the entire enabled account selection's IDs and display labels, exact Feed window start/end, a closed sanitized reason code, and `automatic_backfill = false`. It SHALL not claim each account individually failed: all accounts are affected because the Provider slice is atomic. The limitation SHALL be emitted even with no current units and SHALL not duplicate an additional generic limitation for the same Social failure. Its evidence SHALL come from the current Feed alone. A later successful Feed SHALL NOT reconstruct earlier gaps or claim backfill.

#### Scenario: Missing Cookie prevents acquisition
- **WHEN** the current valid Feed reports `credential_unavailable` for enabled Social
- **THEN** preparation exposes Social unavailability, its configured affected selection, exact window and no-automatic-backfill fact without a fabricated Social post

#### Scenario: All Social accounts are outside the disabled plan
- **WHEN** embedded activation disables `weibo_social`
- **THEN** preparation reports `not_configured` without a failure limitation or synthetic Provider outcome

#### Scenario: Next window succeeds
- **WHEN** a later validated Feed has complete Social acquisition
- **THEN** only that window's status is exposed and no historical Feed or checkpoint is read to infer gap recovery
