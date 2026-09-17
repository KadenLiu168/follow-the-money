# Positioning Presentation Contract

## Domain Purpose

Present validated `positioning` evidence as a typed report of the identified
market, observation time, position, metrics, explicit comparison state, and
explicit arithmetic derivation. Preserve units, unavailable reasons, and
source provenance. The list below is a closed whitelist enforced by
deterministic preparation; it does not authorize facts outside the listed
paths.

## Evidence Fields

The closed whitelist for a `positioning` item is:

- `id`
- `provider_id`
- `source.id`
- `source.name`
- `source.tier`
- `source.kind`
- `source.url`
- `source.published_at`
- `source.updated_at`
- `source.knowledge_available_at`
- `source.original_publisher`
- `source.syndication_origin`
- `source_lineage[].id`
- `source_lineage[].provider_id`
- `source_lineage[].source_id`
- `source_lineage[].original_publisher`
- `source_lineage[].syndication_origin`
- `payload.type`
- `payload.instrument_id`
- `payload.as_of`
- `payload.position.value`
- `payload.position.unit`
- `payload.position.unknown_reason`
- `payload.market_identity.cftc_contract_market_code`
- `payload.market_identity.contract_market_name`
- `payload.current_metrics.net_noncommercial.value`
- `payload.current_metrics.net_noncommercial.unit`
- `payload.current_metrics.net_noncommercial.unknown_reason`
- `payload.current_metrics.noncommercial_long.value`
- `payload.current_metrics.noncommercial_long.unit`
- `payload.current_metrics.noncommercial_long.unknown_reason`
- `payload.current_metrics.noncommercial_short.value`
- `payload.current_metrics.noncommercial_short.unit`
- `payload.current_metrics.noncommercial_short.unknown_reason`
- `payload.current_metrics.noncommercial_spreading.value`
- `payload.current_metrics.noncommercial_spreading.unit`
- `payload.current_metrics.noncommercial_spreading.unknown_reason`
- `payload.current_metrics.open_interest.value`
- `payload.current_metrics.open_interest.unit`
- `payload.current_metrics.open_interest.unknown_reason`
- `payload.previous_metrics.net_noncommercial.value` (when present)
- `payload.previous_metrics.net_noncommercial.unit` (when present)
- `payload.previous_metrics.net_noncommercial.unknown_reason` (when present)
- `payload.previous_metrics.noncommercial_long.value` (when present)
- `payload.previous_metrics.noncommercial_long.unit` (when present)
- `payload.previous_metrics.noncommercial_long.unknown_reason` (when present)
- `payload.previous_metrics.noncommercial_short.value` (when present)
- `payload.previous_metrics.noncommercial_short.unit` (when present)
- `payload.previous_metrics.noncommercial_short.unknown_reason` (when present)
- `payload.previous_metrics.noncommercial_spreading.value` (when present)
- `payload.previous_metrics.noncommercial_spreading.unit` (when present)
- `payload.previous_metrics.noncommercial_spreading.unknown_reason` (when present)
- `payload.previous_metrics.open_interest.value` (when present)
- `payload.previous_metrics.open_interest.unit` (when present)
- `payload.previous_metrics.open_interest.unknown_reason` (when present)
- `payload.delta_metrics.net_noncommercial.value` (when present)
- `payload.delta_metrics.net_noncommercial.unit` (when present)
- `payload.delta_metrics.net_noncommercial.unknown_reason` (when present)
- `payload.delta_metrics.noncommercial_long.value` (when present)
- `payload.delta_metrics.noncommercial_long.unit` (when present)
- `payload.delta_metrics.noncommercial_long.unknown_reason` (when present)
- `payload.delta_metrics.noncommercial_short.value` (when present)
- `payload.delta_metrics.noncommercial_short.unit` (when present)
- `payload.delta_metrics.noncommercial_short.unknown_reason` (when present)
- `payload.delta_metrics.noncommercial_spreading.value` (when present)
- `payload.delta_metrics.noncommercial_spreading.unit` (when present)
- `payload.delta_metrics.noncommercial_spreading.unknown_reason` (when present)
- `payload.delta_metrics.open_interest.value` (when present)
- `payload.delta_metrics.open_interest.unit` (when present)
- `payload.delta_metrics.open_interest.unknown_reason` (when present)
- `payload.comparison.status`
- `payload.comparison.previous_as_of`
- `payload.comparison.reason`
- `payload.derivations.net_noncommercial.formula_id`

Positioning does not carry `semantic_context`. A null or unavailable metric
remains in that state. The `previous_metrics`, `delta_metrics`, comparison,
and derivation paths authorize only the typed evidence explicitly present;
they do not authorize an inferred holding delta.

## Recommended Representation

Identify the market using `market_identity` when present, state the observation
time, and report current metrics with their units and availability. Report
previous and delta metrics only when present, label comparison status and
reason, and state the explicit `net_noncommercial` formula when using that
derivation. Keep the result as a typed observation rather than a directional
description.

Null, explicitly unavailable, or absent evidence remains missing. Do not
reconstruct or infer a market identity, previous report, delta, direction, or
meaning from `instrument_id`, another item, historical Feed, external
knowledge, or `raw_metadata`.

## Forbidden Interpretation

Do not add importance, anomaly, ranking, causality, sentiment, bullish or
bearish direction, signal, prediction, market impact, investment judgment,
recommendation, or trading instruction. Do not translate current, previous,
delta, comparison, or arithmetic derivation evidence into trader behavior,
market meaning, or an inferred change not present in the Feed. `raw_metadata`
and every unlisted field are outside the presentation evidence.
