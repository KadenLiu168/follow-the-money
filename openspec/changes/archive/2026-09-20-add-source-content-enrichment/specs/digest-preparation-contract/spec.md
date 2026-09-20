## ADDED Requirements

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

