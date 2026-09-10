## ADDED Requirements

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

## REMOVED Requirements

### Requirement: No embedded LLM runtime
**Reason**: Replaced by the narrower Feed-only core and configuration requirements while preserving the no-LLM invariant.
**Migration**: Continue to prohibit model/runtime/credential code through the replacement requirements and Feed contracts.

### Requirement: Functional evidence-only Feed with one minimal internal invocation
**Reason**: Superseded by the Feed-only core contract and canonical producer/consumer contracts.
**Migration**: Retain only the existing Feed producer and current published-Feed consumer entries.

### Requirement: Deterministic domain rules retain explicit caller boundaries
**Reason**: The no-caller deterministic domain rules are removed rather than retained.
**Migration**: No synthetic or replacement caller is introduced.

### Requirement: Deterministic provenance, validation, and audit capability retained
**Reason**: Feed provenance and validation remain, but Audit and non-Feed structures are removed.
**Migration**: Rely only on Feed provenance, validation, identity, and evidence-only guarantees.

### Requirement: OpenSpec living baseline matches the active architecture
**Reason**: Superseded by the Feed-only documentation and instruction alignment requirement.
**Migration**: Reconcile living specs to the Feed-only architecture.

### Requirement: Baseline acceptance uses semantic trace evidence
**Reason**: The historical pre-Agent baseline process and retained-capability trace are no longer the active completion contract.
**Migration**: Verify this breaking removal through focused Feed regressions, canonical quality gate, and strict OpenSpec validation.
