## ADDED Requirements

### Requirement: atomic JSON write
The system SHALL provide `atomicWriteJSON(path, obj)` in `lib/store/atomic-write.js` that writes `JSON.stringify(obj, null, 2)` to a temporary file (`${path}.${process.pid}.${Date.now()}.tmp`) and atomically renames it to `path`. The write MUST be atomic (no reader observes a partially written file), and MUST throw if the underlying write or rename fails.

#### Scenario: content matches inline writer
- **WHEN** `atomicWriteJSON(path, obj)` is called
- **THEN** the bytes written to `path` MUST equal `JSON.stringify(obj, null, 2)` exactly

#### Scenario: write is atomic via rename
- **WHEN** `atomicWriteJSON(path, obj)` completes
- **THEN** the file at `path` MUST contain the full serialized content (never a partial/torn write), and no stray `.tmp` file MUST remain

#### Scenario: failure propagates
- **WHEN** the destination directory does not exist or is not writable
- **THEN** `atomicWriteJSON` MUST throw (and MUST NOT leave a corrupt `path`)

### Requirement: atomic text write
The system SHALL provide `atomicWriteText(path, str)` in `lib/store/atomic-write.js` that writes the raw `str` to a temporary file and atomically renames it to `path`, with the same atomicity and error-propagation guarantees as `atomicWriteJSON`.

#### Scenario: raw string written atomically
- **WHEN** `atomicWriteText(path, str)` is called
- **THEN** the file at `path` MUST contain exactly `str` and MUST be written atomically

### Requirement: store writers use the shared helper
The JSON store writers (`lib/store/feed-json.js`, `lib/store/state-json.js`, `lib/store/manifest.js`) MUST perform their file writes through `atomicWriteJSON` (or `atomicWriteText` where appropriate) and MUST NOT contain inline `writeFileSync` + `renameSync` tmp-file logic.

#### Scenario: no inline tmp+rename in store writers
- **WHEN** the store writer modules are inspected
- **THEN** they MUST import the shared helper from `lib/store/atomic-write.js` and MUST NOT define their own `${path}.${process.pid}.${Date.now()}.tmp` write block
