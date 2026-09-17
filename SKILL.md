---
name: follow-the-money
description: Generate the current evidence-based information digest from the published Feed.
disable-model-invocation: true
---

# Follow the Money

Generate the current evidence-based information digest from the validated
published five-domain Evidence Feed (`news`, `macro_release`, `policy`,
`positioning`, and `filing`).

## Execution

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
```

Run `scripts/skill/prepare-feed` under
[the Feed contract](references/feed-contract.md), then apply
[the safety boundary](references/safety-boundary.md) and the global [Digest
presentation contract](references/digest/presentation-contract.md). The
command emits one canonical, non-persisted v1 `DigestContext` after the
validated current Feed has been consumed. Preparation applies the one domain
contract selected by the item's validated `payload.type` and the closed
evidence-field rules; the Host Agent applies representation and the shared
compression contract. Preserve degraded status, warnings, provenance,
freshness, coverage, and source-availability limits. On retrieval, validation,
or preparation failure, surface the exact stderr and stop. Never substitute
local, stale, partial, historical, or unvalidated data.

Generate the digest immediately without requesting or accepting a company,
asset, topic, time range, research question, or other user-supplied scope.
Treat “current” or “new” as evidence belonging to the current Feed window; do
not claim comparison with a prior publication or checkpoint unless that
comparison is explicitly present in a validated Feed item.

The digest must contain:

1. Feed data status and evidence cutoff
2. Domain and Provider coverage and source availability
3. Current updates from the Feed
4. Source provenance and freshness
5. Data-quality, unavailable-source, and compression limitations

The Host Agent may group related evidence across domains, derive editorial
headings, order content for readability, consolidate repetition, and compress
detail. These are presentation choices, not deterministic Feed results or
evidence of importance, priority, ranking, or another analytical finding. Use
the presentation hierarchy for representation and compression accounting;
closed field selection is already applied in `DigestContext`. Every factual summary must remain semantically
supported by the cited Feed items. If a source item contains analytical or
predictive language, summarize it only with clear source attribution and do
not adopt it as a Host-Agent conclusion.

Do not introduce or infer significance, anomaly, signal, causality, market
impact, prediction, investment judgment, investment recommendation, or trading
instruction. The digest preserves evidence and its limits; it does not add
financial analysis or trading direction.

GitHub Actions owns collection and deterministic Feed production. The Skill
owns validated Feed consumption, while the Host Agent owns evidence-preserving
digest summarization and formatting. The Feed remains evidence-only; this path
does not invoke a private analysis, audit, event, ranking, or trading runtime.
