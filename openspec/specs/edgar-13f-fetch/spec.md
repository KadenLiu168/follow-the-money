# edgar-13f-fetch Specification

## Purpose
TBD - created by archiving change fix-13f-infotable-selection. Update Purpose after archive.
## Requirements
### Requirement: infoTable selected by canonical filename first

`fetchThirteenFXml` MUST select the 13F information table file by the canonical name `form13fInfoTable.xml` (case-insensitive) when present in the filing directory `index.json`, before applying any size-based heuristic.

#### Scenario: Canonical name present and smaller than cover page
- **WHEN** `index.json` lists both `form13fInfoTable.xml` and a larger cover-page `.xml`
- **THEN** `fetchThirteenFXml` MUST fetch `form13fInfoTable.xml`

### Requirement: Heuristic fallback only when canonical name absent

When no file named `form13fInfoTable.xml` exists, `fetchThirteenFXml` MAY fall back to the largest `.xml` file, but MUST NOT fall back to `primaryDocument` (the cover page) as a holdings source.

#### Scenario: Canonical name absent, use largest xml
- **WHEN** `index.json` has no `form13fInfoTable.xml` but has other `.xml` files
- **THEN** the function MUST use the largest `.xml` file

#### Scenario: Both absent, no silent cover-page parse
- **WHEN** `index.json` resolves to no usable infoTable file and `primaryDocument` is a cover page
- **THEN** the function MUST throw (not parse the cover page as holdings)

### Requirement: Empty holdings from parse is an error

`parseThirteenF` MUST throw when the parsed result contains zero holdings, so the caller does not silently emit an empty position set.

#### Scenario: Parse yields no infoTable rows
- **WHEN** `parseThirteenF` parses an XML that contains no `<infoTable>` rows
- **THEN** the function MUST throw a descriptive error

