# Positioning Presentation Contract

## Domain Purpose

Present the validated `positioning` domain truthfully without exposing market
rows as substantive content. The validated Feed remains the authoritative
positioning evidence, including its market identity, observation time,
position, metrics, comparison state, and derivation. The list below is a closed
whitelist enforced by deterministic preparation; it does not authorize facts
outside the listed paths.

## Reader-Facing Unit

This contract version exposes no reader-facing positioning unit. Preparation
constructs a `positioning_report` unit only once the accepted Feed contract
exposes enough explicit shared report identity and publication-time evidence to
do so without grouping rows by Provider, date, title, similarity, or row
coincidence. Until then, no market row, metric, comparison, or derivation is
part of `content.updates`, and the positioning domain is represented only by the
compact `positioning/cftc` status descriptor.

## Current Membership

Membership is evaluated for the whole selected positioning slice against the
half-open Feed window `[window.start, window.end)`. `payload.as_of` alone is
never positioning publication time or current-membership authority. A Provider
freshness record with a non-null carry provenance yields
`positioning/cftc/carried_reference_state`; a contract-proven stale selected
slice yields `positioning/cftc/stale_reference_state`; any other selected slice
yields `positioning/cftc/current_membership_unproven`. A source-supported
`data_as_of` is retained in the compact descriptor only when it is
deterministically equal across the selected slice. An absent slice yields
`positioning/cftc/domain_empty`.

## Supporting Evidence

This contract exposes no positioning unit evidence. The only positioning value
exposed to the Host Agent is the compact status descriptor and, when the
selected slice agrees, its `data_as_of`. Every other positioning field stays in
the validated Feed and remains unavailable to the Digest until this contract
and the preparation implementation deliberately add it, so a reference row
count, market row, or metric value can never be reconstructed into substantive
content.

## Evidence Fields

The closed whitelist for a `positioning` item is:

- `payload.as_of`

## Recommended Representation

State the compact positioning status accurately when it affects a reader's
understanding: carried, stale, or unproven-current reference state, and an empty
domain. Refer to `data_as_of` only as the observation time the Feed supports.
Do not describe a market, a position, a metric, a change, a comparison, or a
derivation, because none of them is part of the prepared context.

Null, explicitly unavailable, or absent evidence remains missing. Do not
reconstruct or infer a market identity, previous report, delta, direction, or
meaning from `instrument_id`, another item, historical Feed, external knowledge,
or `raw_metadata`. Do not treat the absence of positioning rows from
`content.updates` as unimportant, insignificant, or irrelevant evidence.

## Forbidden Interpretation

Do not add importance, anomaly, ranking, causality, sentiment, bullish or
bearish direction, signal, prediction, market impact, investment judgment,
recommendation, or trading instruction. Do not translate a compact reference
state into trader behavior, market meaning, or an inferred change, and do not
present a status descriptor as a market conclusion. `raw_metadata` and every
unlisted field are outside the presentation evidence.
