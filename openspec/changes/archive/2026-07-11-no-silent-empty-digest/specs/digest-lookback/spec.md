## ADDED Requirements

### Requirement: Digest SHALL fail when a source feed is missing or corrupt

`scripts/prepare-digest.js` SHALL verify that `feed-13f.json` and the `feed-13dg/` directory both exist before producing a digest. If `feed-13f.json` is missing, `feed-13dg/` is missing, or `feed-13f.json` is corrupt (fails JSON parsing), the process SHALL print an error message to stderr naming the problem, SHALL exit with a non-zero status code, and SHALL NOT write any digest JSON to stdout.

This enforces the skill's "Partial output is worse than no output" rule: a digest built from an absent or corrupt source is partial and MUST NOT be emitted.

#### Scenario: Missing 13F feed fails loudly
- **WHEN** `prepare-digest.js` runs and `feed-13f.json` does not exist
- **THEN** it SHALL print an error to stderr mentioning the missing feed
- **AND** it SHALL exit with a non-zero status code
- **AND** stdout SHALL be empty (no digest written)

#### Scenario: Missing 13DG directory fails loudly
- **WHEN** `prepare-digest.js` runs and `feed-13dg/` does not exist
- **THEN** it SHALL exit with a non-zero status code
- **AND** stdout SHALL be empty

#### Scenario: Corrupt 13F feed fails loudly
- **WHEN** `prepare-digest.js` runs and `feed-13f.json` contains invalid JSON
- **THEN** it SHALL print an error to stderr mentioning corruption
- **AND** it SHALL exit with a non-zero status code
- **AND** stdout SHALL be empty

#### Scenario: Valid but empty feed still succeeds
- **WHEN** `feed-13f.json` and `feed-13dg/` both exist but contain no filings in the lookback window
- **THEN** the process SHALL exit 0 and emit a digest with empty `thirteenF` / `thirteenDG` arrays
- **AND** this SHALL NOT be treated as a failure (a present-but-empty source is legitimate, e.g. a non-filing day)
