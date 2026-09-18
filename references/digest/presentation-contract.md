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

## Content-First Presentation Hierarchy

Content-first is a semantic priority between the content and audit surfaces,
not a ranking of Feed items. For a valid healthy Feed with presentable
current-window updates, those updates are the primary substantive surface: the
Digest first makes the available current Feed content readable. The secondary
audit surface remains complete and includes Feed data status,
`evidence_cutoff_at`, domain and Provider coverage, freshness, warnings,
degradation, source availability, reconciliation, consolidation traceability,
omission disclosure, and limitations. A healthy Digest must not lead with a
full status, coverage, or reconciliation report as an audit-first preamble.

This semantic priority does not prescribe fixed headings, heading levels,
section order, visual style, or fixed Markdown structure. It does not make one
item more important, significant, ranked, relevant, or analytical than
another, and it does not add an analysis or relevance filter. Statement-local
provenance or attribution remains sufficiently close to the factual statement,
source-authored analysis, or consolidated summary that it supports; global
Provider, coverage, and reconciliation metadata may remain in the secondary
audit surface.

A valid but degraded usable Feed may include a concise data-limitation caveat
before affected content only when it materially affects interpretation. The
caveat is narrow, does not replace the complete audit context, and must not
present the Feed as healthy. Complete status, coverage, freshness, warnings,
availability, degradation, and limitation information remains visible in the
secondary audit surface.

When there are zero presentable current-window updates in a valid Feed, the
primary message accurately states that the current Feed window has no
presentable updates. It creates no content from historical, external, inferred,
or fabricated material. The message is followed by status, evidence cutoff,
coverage, Provider or source availability, and applicable limitations that
distinguish an empty window from collection or Provider problems.

Content-first priority applies only after the Feed has been validated and
prepared. It does not alter or bypass the existing fail-closed behavior: a
retrieval, validation, or preparation failure still produces no normal Digest.

Content-first changes presentation priority only. The shared compression
contract remains mandatory: per-domain reconciliation, traceability to every
supporting item in a consolidation, and omission disclosure remain visible
audit information, without using importance or relevance as the presentation
or omission rationale.

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
