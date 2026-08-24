## MODIFIED Requirements

### Requirement: Deterministic market snapshot
Given a validated Feed and closed role configuration, `build_market_snapshot` SHALL
produce one immutable snapshot in configured role order with dashboard rows, current
moves, current-excluded z-scores, anomaly flags, classifier input maps, equity
breadth, macro-surprise votes, missing or unknown reasons, and contributing evidence
IDs. Price, index, FX, commodity, and crypto roles SHALL use simple returns; yield
roles SHALL use basis-point changes. Each available z-score SHALL compare the current
change with exactly the preceding 20 eligible changes through the precision-50
`ROUND_HALF_EVEN` Decimal formulas, and the anomaly boundary SHALL be the configured
absolute z-score threshold. An unverified configured mapping SHALL remain explicitly
unknown with reason `unverified_mapping` even if a matching Feed item is present.
Other ineligible, stale, post-cutoff, wrong-unit, session-incompatible, or insufficient
observations SHALL remain explicitly unknown instead of being filled. This retained
deterministic capability SHALL NOT gain a production orchestration caller through
market-mapping enforcement.

#### Scenario: Price role has sufficient history
- **WHEN** a price-like role has 22 eligible consecutive closes with non-zero reference standard deviation
- **THEN** the snapshot computes 21 simple returns, compares the last with the preceding 20, and retains Decimal precision until output quantization

#### Scenario: Yield role has sufficient history
- **WHEN** a yield role has 22 eligible percent-unit closes with non-zero reference standard deviation
- **THEN** the snapshot computes basis-point changes and exposes the result through `yield_change_zs` without mislabelling the raw level as a return

#### Scenario: Mapping remains unverified
- **WHEN** the configured role has `mapping_verified` false, including when a matching canonical-role Feed item is present
- **THEN** the role remains present in canonical order with unknown reason `unverified_mapping` and no calculated metric

#### Scenario: Observation is incompatible
- **WHEN** required history is missing, stale, post-cutoff, wrong-unit, session-incompatible, or has zero reference standard deviation
- **THEN** the role remains present in canonical order with an explicit unknown reason and no invented metric
