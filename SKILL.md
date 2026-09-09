---
name: follow-the-money
description: Generate the current evidence-based information digest from the published Feed.
disable-model-invocation: true
---

# Follow the Money

Generate the current evidence-based information digest from the validated
published Feed.

## Execution

```text
published Feed -> validation -> Host Agent summarization/formatting -> evidence-based information digest
```

Run `scripts/skill/prepare-feed` under
[the Feed contract](references/feed-contract.md), then apply
[the safety boundary](references/safety-boundary.md). Use only its validated
current output. Preserve degraded status, warnings, provenance, freshness,
coverage, and source-availability limits. On retrieval or validation failure,
surface the exact stderr and stop. Never substitute local, stale, partial,
historical, or unvalidated data.

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

For every Feed domain, report its total item count and reconcile every item as
individually summarized, represented through a consolidated summary, or
omitted. Disclose omissions as editorial compression; never justify them by
calling an item unimportant or irrelevant. The representation counts must
reconcile to the domain total.

The Host Agent may group related evidence across domains, derive editorial
headings, order content for readability, consolidate repetition, and compress
detail. These are presentation choices, not deterministic Feed results or
evidence of importance, priority, ranking, or another analytical finding.
Every factual summary must remain semantically supported by the cited Feed
items. If a source item contains analytical or predictive language, summarize
it only with clear source attribution and do not adopt it as a Host-Agent
conclusion.

Do not introduce or infer significance, anomaly, signal, causality, market
impact, prediction, investment judgment, investment recommendation, or trading
instruction. The digest preserves evidence and its limits; it does not add
financial analysis or trading direction.

GitHub Actions owns Provider collection and deterministic Feed production. The
Skill owns validated Feed consumption, while the Host Agent owns digest
summarization and formatting. The Feed remains evidence-only. Audit, Event
Structuring, and retained deterministic capabilities remain independent
private or retained capabilities and are not invoked by this digest path.
