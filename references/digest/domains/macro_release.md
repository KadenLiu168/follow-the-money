# Macro Release Presentation Contract

## Domain Purpose

Present validated `macro_release` evidence as a factual release for its
Provider series, release time, reporting period, and explicitly available
observations. Preserve numeric value, unit, unknown reason, and source
provenance. The list below is a closed whitelist; it does not authorize facts
outside the listed paths.

## Evidence Fields

The closed whitelist for a `macro_release` item is:

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
- `payload.series_id`
- `payload.released_at`
- `payload.observation_period`
- `payload.actual.value`
- `payload.actual.unit`
- `payload.actual.unknown_reason`
- `payload.consensus.value`
- `payload.consensus.unit`
- `payload.consensus.unknown_reason`
- `payload.previous.value`
- `payload.previous.unit`
- `payload.previous.unknown_reason`
- `semantic_context.version` (when present)
- `semantic_context.entities[].role` (when present)
- `semantic_context.entities[].name` (when present)
- `semantic_context.entities[].type` (when present)
- `semantic_context.event.category` (when present)
- `semantic_context.event.occurred_at` (when present)
- `semantic_context.numeric_facts[].metric` (when present)
- `semantic_context.numeric_facts[].role` (when present)
- `semantic_context.numeric_facts[].value` (when present)
- `semantic_context.numeric_facts[].unit` (when present)
- `semantic_context.numeric_facts[].unknown_reason` (when present)
- `semantic_context.extension.type` (when present)
- `semantic_context.extension.indicator.id` (when present)
- `semantic_context.extension.indicator.name` (when present)
- `semantic_context.extension.period.period` (when present)
- `semantic_context.extension.revision.previous.value` (when present)
- `semantic_context.extension.revision.previous.unit` (when present)
- `semantic_context.extension.revision.revised.value` (when present)
- `semantic_context.extension.revision.revised.unit` (when present)

`semantic_context` is optional and must match `payload.type = macro_release`
when it is present. Legacy items may omit it. A previous-period observation,
consensus value, or another comparison is not a revision unless the explicit
semantic revision fields are present.

## Recommended Representation

Identify the Provider series and release time, state the observation period
when present, and report actual, consensus, or previous observations with their
validated values, units, and availability. Present a revision only when the
source-supported semantic revision contains both previous and revised values
for the same indicator and period. Keep a null observation period as null.

Null, explicitly unavailable, absent, or legacy-omitted evidence remains
missing. Do not reconstruct or infer a period, value, unit, revision, or
comparison from a title, release time, another item, historical Feed, external
knowledge, or `raw_metadata`; do not calculate an unstated observation.

## Forbidden Interpretation

Do not add importance, anomaly, ranking, causality, sentiment, direction,
market impact, signal, prediction, investment judgment, recommendation, or
trading instruction. Do not turn actual-versus-consensus or previous-period
facts into surprise, assessment, trend, forecast, or market meaning. Do not
relabel a previous-period observation as a revision. `raw_metadata` and every
unlisted field are outside the presentation evidence. Source-authored analysis
may be summarized only with clear attribution and without upgrading its
authority.
