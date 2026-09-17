# Digest Presentation Contract

This is static, Host-Agent-owned guidance for presenting the current validated
published Evidence Feed. It is applied after
`scripts/skill/prepare-feed` has succeeded and the command has emitted its
non-persisted `DigestContext`. The Feed, its validation result, source
provenance, freshness, coverage, degradation status, warnings, and limitations
remain authoritative; the context is only a deterministic Feed-bound view.

## Input and Domain Selection

Use the current validated Feed through its prepared `DigestContext` and current
Feed window. Deterministic preparation selects exactly one domain contract from
the item's already validated `payload.type`; do not select by title, Provider
name, source text, or an inferred subtype. The active
domain contracts are:

- [News](domains/news.md)
- [Macro release](domains/macro_release.md)
- [Policy](domains/policy.md)
- [Positioning](domains/positioning.md)
- [Filing](domains/filing.md)

Use the shared [compression contract](compression.md) for accounting in every
domain. This selection is preparation-owned and is already reflected in the
context. It does not add a resolver, serialized Digest field, renderer, or
runtime dispatch stage.

## Global Presentation Responsibilities

The Host Agent owns evidence-preserving summarization and formatting. It may
group related evidence, derive editorial headings, order content for
readability, consolidate repetition, and compress detail. These operations are
presentation choices and do not establish importance, priority, ranking,
significance, or another Feed result.

The Digest must expose Feed data status and `evidence_cutoff_at`, domain and
Provider coverage, source provenance, freshness, current-window updates, and
data-quality or unavailable-source limitations. Preserve degraded status,
warnings, source availability, and coverage gaps. “Current” and “new” refer to
membership in the current Feed window, not comparison with a historical Feed
or checkpoint.

Every factual statement must be semantically supported by the cited validated
Feed evidence. Preserve the authority of the source and attribute a
source-authored analytical or predictive statement to that source; do not
present it as a Feed, Skill, or Host-Agent conclusion. A citation by itself is
not semantic support.

## Missing Evidence

Null, explicitly unavailable, absent, and legacy-omitted values remain missing.
Do not complete them from titles, snippets, free-form text, another item,
historical Feed data, checkpoints, external knowledge, or `raw_metadata`. Do
not silently substitute a different field or perform an unstated calculation.
Disclose a material limitation accurately when it affects the presentation.

## Safety and Runtime Boundary

Do not introduce or infer importance, anomaly, ranking, causality, sentiment,
direction, market impact, signal, prediction, investment judgment,
recommendation, or trading instruction. Domain contracts may describe these
terms only as forbidden interpretations. They do not authorize analytical
outputs.

The presentation-contract hierarchy is static guidance only: it is no runtime
and adds no
renderer, template engine, prompt pipeline, model invocation, Agent
orchestration, standalone Digest service, or other runtime. It does not modify
Feed schemas, Providers, collection, validation, identity, publication, or
retrieval.
