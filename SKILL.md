---
name: follow-the-money
description: Generate the current evidence-based information digest from the published Feed.
disable-model-invocation: true
---

# Follow the Money

Generate the current evidence-based information digest from the published Feed.

## Execution

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
```

Run `scripts/skill/prepare-feed` under [the Feed contract](references/feed-contract.md).
It emits one canonical, non-persisted `DigestContext` version `2` after the current
validated Feed has been consumed. Consume `content.updates` as the default
substantive input and use `status.domains` and `status.limitations` only for
applicable conditional disclosure. Apply [the safety boundary](references/safety-boundary.md)
and the global [Digest presentation contract](references/digest/presentation-contract.md)
for the authoritative presentation rules. On retrieval, validation, or
preparation failure, surface the exact stderr and stop. Never substitute local,
stale, partial, historical, or unvalidated data.

Generate the digest immediately without requesting or accepting a company, asset,
topic, time range, research question, or other user-supplied scope.

Keep the Digest evidence-only and evidence-preserving. Do not introduce or
infer significance, anomaly, causality, market impact, prediction, investment
judgment, investment recommendation, or trading direction. This path does not
add financial analysis.

The Skill owns validated Feed consumption and the canonical `DigestContext`
handoff. The Host Agent owns evidence-preserving Digest summarization and
formatting.
