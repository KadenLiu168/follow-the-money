## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Skill capability ownership is semantic and closed
**Reason**: Replaced by the Feed-only catalog rather than the former six-family catalog.
**Migration**: Treat Evidence Feed as the sole Skill capability.

### Requirement: Evidence Feed remains a live capability
**Reason**: Superseded by the stronger Feed-only capability requirement.
**Migration**: Evidence Feed remains live under the new requirement.

### Requirement: Evidence and Event Structuring is a live on-demand capability
**Reason**: Event Structuring is removed.
**Migration**: No Event operation remains.

### Requirement: Market Analytics and State is a retained capability
**Reason**: Retained analytics are removed.
**Migration**: No replacement capability is provided.

### Requirement: Confidence and Watchlist is a retained capability
**Reason**: Confidence and Watchlist are removed.
**Migration**: Use Feed provenance/freshness and transparent digest accounting without confidence/watchlist derivation.

### Requirement: Scoring and Ranking is a retained capability
**Reason**: Scoring and Ranking are removed.
**Migration**: Digest order remains presentation-only and unranked.

### Requirement: Deterministic Audit is a live on-demand capability
**Reason**: Deterministic Audit is removed.
**Migration**: Host-Agent digest prohibitions remain normative without repository Audit runtime.

### Requirement: Execution status is descriptive architecture metadata only
**Reason**: The multi-capability status and activation matrix no longer exist.
**Migration**: Evidence Feed is the sole capability and requires no status catalog.

### Requirement: Internal infrastructure remains outside the capability surface
**Reason**: Superseded by the narrower Feed-machinery requirement.
**Migration**: Apply the replacement requirement only to surviving Feed internals.

### Requirement: Concrete integration remains bounded
**Reason**: The private Agent integration is removed in full.
**Migration**: Normal Skill consumption uses only the canonical published Feed.
