## ADDED Requirements

### Requirement: Production Feed activates CFTC weekly positioning evidence
The shipped production Feed plan SHALL enable the existing verified, credential-free CFTC Provider and publish its accepted `positioning` items in the typed positioning domain artifact inventoried by `feed-manifest.json`. The Provider outcome and embedded Provider contract SHALL preserve CFTC identity, Tier 1 provenance, the authoritative weekly cadence with `data_as_of` reference time, and its declared validity window. CFTC evidence SHALL remain evidence-only and SHALL NOT contain signals, ranking, scoring, interpretation, or investment conclusions.

#### Scenario: Production planning includes CFTC
- **WHEN** the shipped production Provider configuration is resolved
- **THEN** CFTC is enabled, its verified contract is embedded in the Feed manifest, and exactly one planned CFTC outcome is required

#### Scenario: A new CFTC report is available
- **WHEN** a complete CFTC check returns a valid report whose canonical semantic content is new or changed and whose authoritative `positioning.as_of` is within the weekly validity window
- **THEN** the current CFTC slice deterministically replaces the prior slice, its freshness is `fresh`, and its items are published only in the positioning domain artifact with original source and payload timestamps

#### Scenario: No new weekly report is available
- **WHEN** a complete daily CFTC check returns no new observation and a fully validated prior CFTC slice remains within the declared weekly validity window
- **THEN** the prior slice is carried unchanged with freshness `valid_unchanged`, current operational retrieval and generation timestamps are recorded independently, and no source, knowledge, or `positioning.as_of` timestamp is rewritten

#### Scenario: CFTC fails after a prior snapshot exists
- **WHEN** current CFTC acquisition fails, is partial, or otherwise remains incomplete while a prior valid CFTC slice exists
- **THEN** the CFTC outcome remains incomplete with freshness `not_evaluated`, the prior slice does not substitute for current success, and the failed candidate is not published

#### Scenario: Published CFTC evidence is inspected
- **WHEN** a consumer validates a successfully published bundle containing CFTC positioning evidence
- **THEN** the manifest and positioning artifact expose the CFTC Provider outcome, provenance, originating contract hash, cadence status, and unchanged source-semantic timestamps required by the existing Feed contracts
