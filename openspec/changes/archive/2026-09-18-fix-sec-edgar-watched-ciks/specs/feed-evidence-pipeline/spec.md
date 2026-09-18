## ADDED Requirements

### Requirement: SEC 13F watched-company configuration is closed and fail-closed

The authoritative configuration SHALL contain a closed `watched_companies` selection
of normalized ten-digit SEC CIKs, each unique, embedded in the canonical Feed
configuration snapshot in deterministic CIK order. The CIK order in the embedded
snapshot SHALL be produced by deterministic runtime ordering of the configured
selection, independent of the checked-in list order. Unknown, duplicate, malformed,
or missing selection fields SHALL fail static resolution before Provider work or
persistent mutation, matching the `watched_form4_issuers` and
`watched_beneficial_ownership_filers` validation. A CIK SHALL be a normalized
ten-digit decimal string. Malformed or duplicate CIKs SHALL NOT be silently
corrected, deduplicated, or skipped at runtime.

#### Scenario: Malformed CIK is rejected

- **WHEN** `watched_companies` contains an entry whose `cik` is not a normalized
  ten-digit decimal string
- **THEN** static configuration resolution fails closed before any SEC Provider
  request and before any rate-registry or persistent state mutation

#### Scenario: Duplicate CIK is rejected

- **WHEN** `watched_companies` contains two entries with the same `cik`
- **THEN** static configuration resolution fails closed before any SEC Provider
  request and before any rate-registry or persistent state mutation

#### Scenario: Shipped watched-CIK set is pinned

- **WHEN** the shipped production configuration is resolved
- **THEN** the resolved watched-company CIK set equals the verified SEC identity
  set documented in `references/provider-source-verification.md`, and any silent
  drift in a shipped CIK fails the exact-set regression

#### Scenario: Runtime ordering is independent of list order

- **WHEN** the checked-in `watched_companies` list is not in CIK order
- **THEN** the embedded Feed configuration snapshot still orders the selection by
  normalized CIK, and acquisition iterates that deterministic order without
  requiring a checked-in ordering enforcement
