# config-loading-unified Specification

## Purpose
TBD - created by archiving change low-priority-cleanup. Update Purpose after archive.

## ADDED Requirements

### Requirement: single shared user-config loader
The system SHALL expose `loadUserConfig()` from `lib/config/load-user-config.js` that
safely reads `~/.follow-the-money/config.json`. When the file is missing, unreadable, or
fails to parse, `loadUserConfig()` SHALL return a default object with at least
`language: "en"`. `prepare-digest.js` SHALL use it to obtain the render `language`, and
`check-alerts.js` SHALL use it instead of its inline
`join(homedir(), '.follow-the-money', 'config.json')` path.

#### Scenario: prepare-digest reads language via shared loader
- **WHEN** `prepare-digest.js` needs the user's render language
- **THEN** it calls `loadUserConfig()` and reads `language` from the result

#### Scenario: check-alerts uses shared loader
- **WHEN** `check-alerts.js` needs to read `~/.follow-the-money/config.json`
- **THEN** it calls `loadUserConfig()` rather than constructing the path inline

#### Scenario: missing or corrupt config returns defaults
- **WHEN** `~/.follow-the-money/config.json` does not exist or contains invalid JSON
- **THEN** `loadUserConfig()` SHALL return an object with `language: "en"`
- **AND** it SHALL NOT throw
