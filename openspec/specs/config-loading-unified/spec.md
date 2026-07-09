# config-loading-unified Specification

## Purpose
TBD - created by archiving change low-priority-cleanup. Update Purpose after archive.
## Requirements
### Requirement: single shared default-sources loader
The system SHALL expose `loadDefaultSources()` from `lib/config/load-default-sources.js` that reads and parses `config/default-sources.json`.

#### Scenario: aggregate uses it
- **WHEN** `aggregate.js` needs the default sources config
- **THEN** it calls `loadDefaultSources()` and receives the same parsed object the previous `readFileSync` path returned

#### Scenario: verify-edgar uses it
- **WHEN** `verify-edgar.js` needs the default sources config
- **THEN** it calls `loadDefaultSources()` and receives the same parsed object

#### Scenario: prepare-digest uses it
- **WHEN** `prepare-digest.js` needs the default sources config
- **THEN** it calls `loadDefaultSources()` (replacing the static JSON import attribute) and receives the same parsed object

