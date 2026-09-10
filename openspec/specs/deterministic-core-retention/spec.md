# deterministic-core-retention Specification

## Purpose
Define the Feed-only deterministic core, closed configuration, and current-facing architecture invariants.

## Requirements

### Requirement: Deterministic core is Feed-only
The retained deterministic core SHALL consist only of behavior and machinery required to collect, normalize, validate, identify, publish, and consume the five-domain Evidence Feed. The repository SHALL contain no retained no-caller research, Audit, Event, Ledger, candidate, market analytics/state, confidence, watchlist, scoring, or ranking implementation.

#### Scenario: Runtime and import graph are inspected
- **WHEN** production entries and internal imports are traced
- **THEN** every surviving runtime module supports Feed production or current published-Feed consumption and no removed capability module remains

### Requirement: Feed-only configuration is closed and credential-free
Configuration SHALL contain only normative values required by the surviving Feed and its Provider trust boundaries. It SHALL exclude model credentials and all removed Agent invocation, Audit, Event, entity-resolution, market-role/session, Market State, watchlist, scoring/ranking, Brief freshness/run, and analytics-only fields; unknown or removed fields SHALL fail closed.

#### Scenario: Removed configuration is supplied
- **WHEN** configuration contains a removed analytics, Audit, Event, market, scoring, watchlist, role/session, or Brief-only key
- **THEN** startup rejects it instead of ignoring or reviving obsolete behavior

#### Scenario: Feed configuration loads without credentials
- **WHEN** the shipped configuration is loaded with no model, API key, or paid data credential
- **THEN** all eight required Providers can be resolved before collection

### Requirement: Current documentation and instructions describe only Feed behavior
Living OpenSpec, project instructions, Skill documentation, schemas, current docs, and tests SHALL describe only the five-domain Feed and Host-Agent evidence-preserving digest behavior. Archived Changes SHALL remain historical and `openspec/config.yaml` SHALL remain workflow configuration rather than a duplicate product contract.

#### Scenario: Current-facing repository text is audited
- **WHEN** non-archived specs, project `AGENTS.md`, Skill files, schemas, README files, references, and docs are inspected
- **THEN** none claims a private Agent invocation or retained non-Feed capability
