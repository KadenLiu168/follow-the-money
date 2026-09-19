# Digest Presentation Contract

This is static, Host-Agent-owned guidance for presenting the current validated
published Evidence Feed. It is applied after `scripts/skill/prepare-feed` has
succeeded and the command has emitted its non-persisted `DigestContext` version
`2`. The Feed, its validation result, source provenance, freshness, coverage,
degradation status, warnings, and limitations remain authoritative; the context
is only a deterministic Feed-bound view of it.

## Input and Domain Selection

Consume one validated `DigestContext` version `2`. `content.updates` is the
default substantive input, and `status.domains` plus `status.limitations` are
the only conditional non-substantive input. Deterministic preparation selects
exactly one domain contract from the item's already validated `payload.type`,
applies its closed current-membership rule, and constructs the eligible
reader-facing unit before Agent consumption; do not select a domain by title,
Provider name, source text, or an inferred subtype, and do not reclassify a
Feed item as current. The active domain contracts are:

- [News](domains/news.md)
- [Macro release](domains/macro_release.md)
- [Policy](domains/policy.md)
- [Positioning](domains/positioning.md)
- [Filing](domains/filing.md)

Use the shared [compression contract](compression.md) for claim support in every
domain. Selection, membership, and unit construction are preparation-owned and
are already reflected in the context. This does not add a resolver, serialized
Digest field, renderer, or runtime dispatch stage.

## Global Presentation Responsibilities

The Host Agent owns evidence-preserving summarization and formatting. It may
group related evidence by source or explicit document or event type, derive
editorial headings, order content for readability, consolidate
source-supported repetition, and compress detail. These operations are
presentation choices and do not establish importance, priority, ranking,
significance, or another Feed result.

Every factual statement must be semantically supported by the prepared updates
and their validated Feed evidence. Preserve the authority of the source and
attribute a source-authored analytical or predictive statement to that source;
do not present it as a Feed, Skill, or Host-Agent conclusion. A citation by
itself is not semantic support.

## Content-First Presentation Hierarchy

Content-first is a semantic priority between the substantive content and the
non-substantive status surface, not a ranking of Feed items. For a validated
Feed with prepared current updates, `content.updates` is the primary substantive
surface: the Digest first makes the deterministically eligible current updates
readable. `status.domains` and `status.limitations` are disclosed only when
their compact conditions materially affect a reader's understanding of that
content. A healthy Digest must not lead with a status, coverage, or accounting
report as an audit-first preamble.

This semantic priority does not prescribe fixed headings, heading levels,
section order, visual style, or fixed Markdown structure. It does not establish
importance or ranking, it does not make one item more significant, relevant, or
analytical than another, and it does not add an analysis or relevance filter.
Statement-local provenance
or attribution remains sufficiently close to the factual statement,
source-authored analysis, or consolidated summary that it supports.

A valid but degraded usable Feed may include a concise data-limitation caveat
before affected content only when it materially affects interpretation. The
caveat is narrow and must not present the Feed as healthy. It states only the
compact limitation the context discloses, such as an unavailable Provider and
its affected coverage groups or a structured coverage gap, rather than a
complete audit surface.

When `content.updates` is empty, the primary message accurately states that the
current Feed has no deterministically eligible current updates. It creates no
content from historical, external, inferred, or fabricated material. Compact
status distinguishes an empty window from explicitly old, carried, stale,
unproven-current, or unavailable conditions, and does not reproduce the
reference evidence behind them.

Content-first priority applies only after the Feed has been validated and
prepared. It does not alter or bypass the existing fail-closed behavior: a
retrieval, validation, or preparation failure still produces no normal Digest.

## Claim Support and Non-Exhaustiveness

Every factual claim the Digest presents must remain supported by one or more
prepared updates and traceable through them to their supporting Feed item IDs
and eligible original-source provenance. Internal Feed item IDs need not be
printed to the reader.

The Digest is selective rather than exhaustive. It is not required to display
every Feed item, every domain, or every prepared update, and it does not report
per-domain totals, individual/consolidated/omitted counts, or any other
representation accounting. An omission says nothing about importance,
significance, relevance, validity, or another editorial or financial judgment;
full evidence accounting remains in the authoritative Feed.

## Missing Evidence

Null, explicitly unavailable, absent, and legacy-omitted values remain missing.
Do not complete them from titles, snippets, free-form text, another item,
historical Feed data, checkpoints, external knowledge, or `raw_metadata`. Do not
silently substitute a different field or perform an unstated calculation.
Disclose a material limitation accurately when it affects the presentation.

## Safety and Runtime Boundary

Do not introduce or infer importance, anomaly, ranking, causality, sentiment,
direction, market impact, signal, prediction, investment judgment,
recommendation, or trading instruction. Domain contracts may describe these
terms only as forbidden interpretations. They do not authorize analytical
outputs.

The presentation-contract hierarchy is static guidance only: it is no runtime
and adds no renderer, template engine, prompt pipeline, model invocation, Agent
orchestration, standalone Digest service, or other runtime. It does not modify
Feed schemas, Providers, collection, validation, identity, publication, or
retrieval.
