# skill-capability-surface Specification

## Purpose
Define the single deterministic Evidence Feed capability exposed by the repository and its bounded Host-Agent consumption boundary.

## Requirements

### Requirement: Evidence Feed is the sole Skill capability
The repository and Skill SHALL own exactly one semantic capability: Evidence Feed. That capability SHALL cover credential-free evidence acquisition, normalization, provenance, deterministic aggregation, schema and semantic validation, Feed identity and digest, freshness, coverage and degradation outcomes, durable publication, and canonical current-Feed consumption. No Audit, Event Structuring, Ledger, candidate Event, market analytics/state, confidence, watchlist, scoring, or ranking capability SHALL remain live or retained.

#### Scenario: Capability surface is inspected
- **WHEN** current specs, runtime entries, schemas, configuration, tests, and documentation are reviewed
- **THEN** every positive repository capability belongs to Evidence Feed and no non-Feed capability or retained capability catalog remains

#### Scenario: Absence of a caller is reviewed
- **WHEN** a removed capability is sought because it formerly had no production caller
- **THEN** neither its implementation nor placeholder wiring is retained solely for possible future use

### Requirement: Feed-only status is not runtime metadata
The Feed-only capability definition SHALL remain architecture contract information and SHALL NOT create a capability registry, discovery operation, activation matrix, or serialized execution-status field.

#### Scenario: Runtime metadata is inspected
- **WHEN** Feed schemas and configuration are reviewed
- **THEN** they contain no capability catalog, activation status, or discovery metadata

### Requirement: Internal Feed machinery remains implementation detail
Provider adapters and manifests, HTTP clients, collection locks, rate-state machinery, configuration loaders, canonical serialization and digest helpers, publication mechanics, and deduplication helpers SHALL remain internal Feed machinery rather than separate Host-Agent capabilities.

#### Scenario: Feed implementation changes
- **WHEN** an internal mechanism changes while preserving accepted Feed behavior
- **THEN** no new semantic capability is created
