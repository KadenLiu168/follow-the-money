# Macro Release Presentation Contract

## Domain Purpose

Present validated `macro_release` evidence as a factual release for its
Provider series, release time, reporting period, and explicitly available
observations. Preserve numeric value, unit, unknown reason, and source
provenance. The list below is a closed whitelist enforced by deterministic
preparation; it does not authorize facts outside the listed paths.

## Reader-Facing Unit

Preparation exposes one `macro_release` unit for each macro-release item whose
membership it proves. The unit carries the closed unit domain `macro_release`,
its `macro_release` unit type, the Provider identity, the item's closed source
provenance, an event-time semantic of kind `released_at`, the closed supporting
evidence, and a trace of the supporting Feed item IDs. The unit identifier is
the deterministic function of the unit type and those Feed item IDs. A
macro-release item that is not proven current yields no unit.

## Current Membership

Membership is evaluated against the half-open Feed window
`[window.start, window.end)`. The only accepted authority is
`payload.released_at`. A release time inside the interval yields exactly one
current unit; an explicitly earlier release time yields
`macro_release/no_current_update`; a missing, invalid, at-or-after-end, or
otherwise unusable release time yields
`macro_release/current_membership_unproven`. Observation period, actual,
consensus, previous, and revision values remain supporting evidence inside that
one unit and never become additional updates; source and retrieval times are
never substituted for the release authority.

## Supporting Evidence

The closed whitelist below is the item-level inventory. Preparation maps it
into the unit without opening it: the item identifier becomes the unit trace,
`provider_id` becomes the unit Provider identity, the item `source.*` and
`source_lineage[].*` paths become the unit source provenance, and the
`payload.*` and `semantic_context.*` paths become the unit supporting evidence,
with `payload.*` nested under its payload member and `semantic_context.*` under
its semantic-context member. Nothing outside this inventory is exposed, and no
Feed item becomes a Digest statement by itself.

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
