## MODIFIED Requirements

### Requirement: Evidence Feed is the sole Skill capability
The repository and Skill SHALL own exactly one semantic and evidence capability: Evidence Feed. That capability SHALL cover credential-free evidence acquisition, normalization, provenance, deterministic aggregation, schema and semantic validation, Feed identity and digest, freshness, coverage and degradation outcomes, durable publication, canonical current-Feed consumption, and deterministic preparation of one non-persisted Feed-bound `DigestContext` for the Host Agent. Context preparation SHALL NOT constitute a second semantic capability or evidence authority. No Audit, Event Structuring, Ledger, candidate Event, market analytics/state, confidence, watchlist, scoring, or ranking capability SHALL remain live or retained.

#### Scenario: Capability surface is inspected
- **WHEN** current specs, runtime entries, schemas, configuration, tests, and documentation are reviewed
- **THEN** every positive repository capability belongs to Evidence Feed or its bounded consumption preparation and no independent Digest evidence, analytical, or removed capability remains

#### Scenario: Absence of a caller is reviewed
- **WHEN** a removed capability is sought because it formerly had no production caller
- **THEN** neither its implementation nor placeholder wiring is retained solely for possible future use

### Requirement: Internal Feed machinery remains implementation detail
Provider adapters and manifests, HTTP clients, collection locks, rate-state machinery, configuration loaders, canonical serialization and digest helpers, publication mechanics, deduplication helpers, and typed Digest preparation SHALL remain internal Feed machinery rather than separate Host-Agent semantic capabilities. The Agent-facing `DigestContext` SHALL expose only its accepted deterministic consumption contract and no implementation registry or alternate runtime entry.

#### Scenario: Feed implementation changes
- **WHEN** an internal mechanism changes while preserving accepted Feed and `DigestContext` behavior
- **THEN** no new semantic or evidence capability is created
