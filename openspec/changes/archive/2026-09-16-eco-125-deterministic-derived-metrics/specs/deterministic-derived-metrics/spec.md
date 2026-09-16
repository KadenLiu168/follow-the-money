## Purpose

Define the bounded Producer-internal contract for measured numeric facts and reproducible derived metrics shared by validated evidence Providers without creating a generic semantic layer or changing the published Feed contract.

## ADDED Requirements

### Requirement: Measured numeric facts remain bounded and numeric-only

The Producer semantic core SHALL represent measured numeric facts with a Provider-local name, a bounded canonical decimal value, an explicit unit, and their Provider-supplied source-field support. This representation SHALL NOT claim to model identity, time, text, comparison state, classification, interpretation, or a complete semantic fact system.

#### Scenario: Provider supplies a measured numeric field

- **WHEN** SEC or CFTC supplies a supported bounded numeric source field
- **THEN** the Producer creates the same canonical value and unit required by the existing Provider-v2 payload contract while retaining its Provider-local source-field support internally

#### Scenario: Non-numeric semantics are presented as measured facts

- **WHEN** a caller attempts to use the measured-numeric-fact boundary for entity identity, comparison status, classification, text, time, or interpretation
- **THEN** that concern remains outside the shared primitive and is not admitted as a generic semantic fact

### Requirement: Derived numeric facts retain deterministic internal derivation metadata

Every derived numeric fact produced through the shared derivation boundary SHALL retain immutable metadata containing the concrete arithmetic operation and ordered references to the immutable input fact objects. The references SHALL be sufficient to verify the immediate derivation without a global lookup, external state, JSON path, formula registry, or managed formula identifier lifecycle.

#### Scenario: Difference is derived from two facts

- **WHEN** the Producer derives a difference from compatible measured or derived numeric facts
- **THEN** the result carries the subtraction operation and ordered input references in minuend-then-subtrahend order and is reproducible from those referenced inputs

#### Scenario: Derivation inputs use external lookup

- **WHEN** derivation verification would require resolving a global identifier, string path, registry entry, callback, or external source
- **THEN** the derivation does not satisfy the internal provenance contract

#### Scenario: Derived metadata reaches Feed projection

- **WHEN** a Provider projects a derived result into its existing semantic payload
- **THEN** generic derivation metadata is not serialized and no generic semantic field is added to the Feed wire contract

### Requirement: Numeric derivation owns deterministic decimal arithmetic

Canonical parsing, normalization, and arithmetic used by the shared fact and derivation boundary SHALL use an owned decimal context and SHALL NOT depend on process-global decimal precision, rounding mode, flags, traps, or prior operations. Arithmetic SHALL preserve the existing numeric bounds, reject non-finite, inexact, overflowed, malformed, unit-incompatible, or otherwise unsupported results, and SHALL NOT silently round or truncate.

#### Scenario: Ambient decimal context changes

- **WHEN** identical supported SEC or CFTC numeric evidence is processed under different process-global decimal precision, rounding, flags, or traps
- **THEN** measured facts, derived facts, Provider payloads, and canonical output bytes are identical

#### Scenario: Derived units differ

- **WHEN** subtraction is requested for facts with unequal units
- **THEN** derivation fails closed instead of producing a value or converting units implicitly

#### Scenario: Exact result exceeds the numeric contract

- **WHEN** an exact arithmetic result exceeds the existing canonical numeric bounds
- **THEN** derivation fails closed without rounding, truncating, or publishing the result

### Requirement: Provider semantics and Feed compatibility remain unchanged

SEC SHALL continue to own its security identity, aggregation and full-outer comparison policy, amount-based change classification, unavailable semantics, and payload projection. CFTC SHALL continue to own its market identity, current-side comparison universe, unavailable semantics, existing Provider-specific formula descriptor, and payload projection. For unchanged valid evidence, migration to the shared primitives SHALL preserve the complete SEC/CFTC v2 payloads, canonical item bytes, Feed content digest, cutoff-derived run identity, Provider contract versions, and Host-Agent consumption behavior.

#### Scenario: Existing SEC evidence is migrated

- **WHEN** a valid SEC 13F current/previous input is processed through the shared numeric primitives
- **THEN** its holdings, deltas, change classifications, provenance, ordering, payload bytes, and Feed identity remain identical to the existing SEC v2 contract

#### Scenario: Existing CFTC evidence is migrated

- **WHEN** valid CFTC current/previous report rows are processed through the shared numeric primitives
- **THEN** their metrics, deltas, existing formula descriptor, market selection, payload bytes, and Feed identity remain identical to the existing CFTC v2 contract

#### Scenario: A third domain has not validated an abstraction

- **WHEN** comparison or entity-identity behavior differs between the two existing vertical slices
- **THEN** that behavior remains Provider-specific rather than being parameterized into a shared comparator, identity resolver, rule engine, or generic semantic framework
