## ADDED Requirements

### Requirement: NDJSON append is O(1) per entry

`append13DFiling` and `appendStateNdjson` MUST append a single serialized line to the target year/state file without reading and rewriting the entire existing file.

#### Scenario: Repeated appends do not rewrite the whole file
- **WHEN** `append13DFiling` is called N times for the same year
- **THEN** the resulting file MUST contain exactly N appended lines
- **AND** the implementation MUST NOT read the full file and rewrite it on each call

### Requirement: Corrupt lines are counted and surfaced

`read13DFilings` and `readStateNdjson` MUST count lines that fail JSON parsing and MUST surface the count (via return value and/or `validateManifest` diagnostics) rather than silently discarding them.

#### Scenario: A corrupt line is counted
- **WHEN** a year file contains one unparseable line among valid lines
- **THEN** the reader MUST return all valid entries
- **AND** the reader MUST report `skipped >= 1`

### Requirement: Invalid `filingDate` is rejected, not written to a NaN year

`append13DFiling` MUST validate `entry.filingDate` matches `^\d{4}-\d{2}-\d{2}$` before deriving the year. Entries with an invalid `filingDate` MUST be skipped (with a `console.warn`) and MUST NOT produce a file keyed by `NaN`.

#### Scenario: Invalid filingDate is quarantined
- **WHEN** `append13DFiling` receives an entry with `filingDate: "not-a-date"`
- **THEN** no file named containing `NaN` MUST be created
- **AND** the function MUST emit a warning and skip the entry

### Requirement: Manifest counts stay consistent under append

The per-year `count`/`firstDate`/`lastDate` in the manifest MUST be updated incrementally on each successful append and MUST match the file's actual line count as reported by `validateManifest`.

#### Scenario: Count matches file after appends
- **WHEN** K valid entries are appended to a year
- **THEN** `validateManifest` for that year MUST report `ok: true` with `count === K`
