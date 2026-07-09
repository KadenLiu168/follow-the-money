## WHY

`state.seenFilings` is a map of accession number → timestamp with no eviction. Over long-running aggregation it grows unbounded, leaking memory and slowing state I/O.

## WHAT

Add a time-based TTL prune for `seenFilings` entries, applied when state is loaded, so stale entries are dropped before they are persisted again.

## ADDED Requirements

### Requirement: seenFilings entries are pruned after a TTL
The state loader SHALL drop `seenFilings` entries whose timestamp is older than `SEEN_FILINGS_TTL_DAYS` (default 90) when reading state.

#### Scenario: stale entry removed
- **WHEN** state is read and contains a `seenFilings` entry timestamped more than the TTL ago
- **THEN** that entry is absent from the returned state object

#### Scenario: fresh entry retained
- **WHEN** state is read and contains a `seenFilings` entry timestamped within the TTL
- **THEN** that entry is retained

### Requirement: TTL is a named, tunable constant
The prune window SHALL be defined by a single exported constant `SEEN_FILINGS_TTL_DAYS`.

#### Scenario: tuning
- **WHEN** a maintainer changes `SEEN_FILINGS_TTL_DAYS`
- **THEN** the prune threshold changes accordingly without other code edits
