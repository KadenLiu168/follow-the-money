## ADDED Requirements

### Requirement: Feed JSON read has distinct bootstrap and strict modes

`lib/store/feed-json.js` SHALL expose two separate readers for the consolidated 13F feed file:

- `readFeedJsonOrInit(path)` SHALL return `DEFAULTS()` (an empty feed with `thirteenF: []`) when the file is missing or fails to parse. This mode is ONLY for bootstrap/aggregation write paths (`pipeline-a.js`, `upsert13FFiling`).
- `readFeedJsonStrict(path)` SHALL throw an `Error` when the file is missing or fails to parse. This mode is for read/digest paths and MUST NOT silently return an empty feed.

A read path MUST NOT achieve "empty on missing" by calling `readFeedJsonOrInit`; it MUST call `readFeedJsonStrict` so that absence or corruption is surfaced as an error rather than masquerading as "no data".

#### Scenario: Bootstrap mode tolerates a missing file
- **WHEN** `readFeedJsonOrInit` is called with a path that does not exist
- **THEN** it SHALL return an object with `thirteenF: []` and `schemaVersion: 1` (no throw)

#### Scenario: Strict mode rejects a missing file
- **WHEN** `readFeedJsonStrict` is called with a path that does not exist
- **THEN** it SHALL throw an `Error` whose message names the missing file

#### Scenario: Strict mode rejects a corrupt file
- **WHEN** `readFeedJsonStrict` is called on a file containing invalid JSON
- **THEN** it SHALL throw an `Error` whose message indicates corruption

#### Scenario: Strict mode returns normalized feed on success
- **WHEN** `readFeedJsonStrict` is called on a valid feed file
- **THEN** it SHALL return the same normalized object shape as `readFeedJsonOrInit` would (merged `DEFAULTS()`, `thirteenF`, `stats`)
