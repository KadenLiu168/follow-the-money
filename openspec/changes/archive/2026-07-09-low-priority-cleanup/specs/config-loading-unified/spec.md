## WHY

`config/default-sources.json` is loaded three different ways: `prepare-digest.js` uses a static `import ... with { type: 'json' }` attribute, while `aggregate.js` and `verify-edgar.js` use `readFileSync` + `JSON.parse`. Mixed loading styles are inconsistent and a maintenance hazard.

## WHAT

Provide one shared `loadDefaultSources()` and route all three call sites through it.

## ADDED Requirements

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
