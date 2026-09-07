---
name: follow-the-money
description: Generate the current evidence-based financial intelligence briefing from the published Feed.
disable-model-invocation: true
---

# Follow the Money

Generate the current evidence-based financial intelligence briefing from the
validated published Feed.

## Execution

```text
published Feed -> validation -> current evidence synthesis -> financial intelligence briefing
```

Run `scripts/skill/prepare-feed` under
[the Feed contract](references/feed-contract.md), then apply
[the safety boundary](references/safety-boundary.md). Use only its validated
current output. Preserve degraded status, warnings, provenance, freshness, and
coverage limits. On retrieval or validation failure, surface the exact stderr
and stop. Never substitute local, stale, partial, historical, or unvalidated
data.

Generate the briefing immediately without requesting or accepting a company,
asset, topic, time range, research question, or other user-supplied scope.
Treat “new” as evidence inside the current Feed window, not as a comparison with
a prior publication or checkpoint.

The briefing must contain:

1. Feed data status
2. Coverage
3. Latest capital-flow changes
4. New significant events
5. Anomalous signals
6. Data quality and missing-source notes

GitHub Actions owns Provider collection and deterministic Feed production. The
Skill consumes the current product; the Host Agent owns synthesis and narrative.
Feed remains evidence, not intelligence output.
