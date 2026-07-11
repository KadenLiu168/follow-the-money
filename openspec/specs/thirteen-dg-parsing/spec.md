# thirteen-dg-parsing Specification

## Purpose
TBD - created by archiving change fix-d7-13dg-html-parse. Update Purpose after archive.
## Requirements
### Requirement: 13D/G parser extracts ownership percent and shares for HTML-shape filings
The system SHALL parse HTML-shape 13D/G primary documents and produce `ownershipPercent` and `sharesOwned` equal to the numeric values stated in the filing, including the percentage's `%` suffix and the share count's thousands separators. This is the dominant modern EDGAR filing shape and was previously returning `0` and `1` respectively.

#### Scenario: HTML-shape filing with Percent of Class and Aggregate Amount
- **WHEN** `parseThirteenDG` is called on an HTML-shape document containing `Percent of Class 6.8%` and `Aggregate Amount Beneficially Owned 1,234,567`
- **THEN** the result has `ownershipPercent` equal to `6.8` and `sharesOwned` equal to `1234567`

#### Scenario: Percentage suffix does not break parsing
- **WHEN** the percent raw value contains a `%` suffix (e.g. `"6.8%"`)
- **THEN** `ownershipPercent` is the Number `6.8`, not `0` and not `NaN`

#### Scenario: Thousands separators do not break parsing
- **WHEN** the shares raw value contains comma separators (e.g. `"1,234,567"`)
- **THEN** `sharesOwned` is the Number `1234567`, not `1`

### Requirement: 13D/G parser preserves SGML-shape behavior
The system SHALL continue to parse SGML-shape 13D/G filings and produce the same `issuerName`, `issuerTicker`, `ownershipPercent`, and `sharesOwned` values as before this change. The fix MUST NOT alter behavior for non-empty `stopLabels` callers.

#### Scenario: Existing SGML fixture parses unchanged
- **WHEN** `parseThirteenDG` is called on the SGML-shape fixture `13d-primary-doc.html` with form type `SC 13D`
- **THEN** the result equals `{ issuerName: 'Jet.AI Inc', issuerTicker: 'JTAI', ownershipPercent: 6.8, sharesOwned: 4500000, intent: 'active' }`

### Requirement: Numeric fields are normalized before conversion
The system SHALL strip non-numeric decorations — percentage `%`, thousands commas, and any trailing label text — from the `ownershipPercent` and `sharesOwned` raw strings and extract the first numeric token before converting to Number. This guards against over-capture when the value is followed by other fields.

#### Scenario: Trailing label text after shares is ignored
- **WHEN** the shares raw value is `"1,234,567 Shared Voting Power ..."`
- **THEN** `sharesOwned` is `1234567`

#### Scenario: Missing or non-numeric raw yields zero
- **WHEN** the raw value is empty, `null`, or contains no numeric token
- **THEN** the corresponding numeric field is `0` (never `NaN`)

