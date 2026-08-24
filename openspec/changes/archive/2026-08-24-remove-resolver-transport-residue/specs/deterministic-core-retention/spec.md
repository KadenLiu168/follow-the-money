## MODIFIED Requirements

### Requirement: Deterministic provenance, validation, and audit capability retained
The deterministic engine SHALL retain canonical digest utilities, Feed identity validation, Feed schema and semantic validation, and the safety audit as working capabilities. The serialized Feed SHALL be reproducible from the same inputs and validated against `feed.schema.json` together with its identity and digest invariants. Internal deterministic structures, including the ledger, candidate Components/grouping, market snapshot/state, watchlist, scoring intermediates, and selection inputs, SHALL be protected by typed Python interfaces, domain invariants and validation, and deterministic tests; they SHALL NOT be required to have standalone JSON Schemas. Candidate Components/grouping SHALL remain transport-neutral and SHALL NOT retain or replace the removed semantic-Resolver request envelope.

#### Scenario: Feed identity and schema validation still gate publication
- **WHEN** a Feed is collected or a fixture Feed is loaded
- **THEN** `feed.schema.json` compliance, Feed semantic invariants, identity fields, and digest integrity are enforced by retained deterministic validation, with no credential and no dependency beyond the configured providers

#### Scenario: Internal structures use internal contracts
- **WHEN** the retained ledger, candidate, market, watchlist, scoring, or selection structures are constructed or exercised
- **THEN** their correctness is enforced through their typed interfaces, applicable domain invariants and validation, and deterministic tests without requiring a standalone JSON Schema for each structure

#### Scenario: Candidate grouping stays transport-neutral
- **WHEN** the retained candidate library is inspected or exercised
- **THEN** it exposes deterministic candidate Components/grouping without a Resolver request Block, request-local alias, transport capacity, replacement batching abstraction, or standalone external candidate schema

#### Scenario: Safety audit applies to any submitted text
- **WHEN** the retained `ClaimAuditor` receives text containing prohibited trading instructions
- **THEN** it flags the violation using the configured safety lexicon and its descriptive exceptions
