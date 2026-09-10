# Architecture boundary

`follow-the-money` is a deterministic, typed, credential-free Evidence Feed
for Host Agents. The only repository capability is the current five-domain
Feed:

```text
published Feed -> validation -> Host Agent evidence-preserving digest
```

The Feed producer owns collection, normalization, provenance, freshness,
coverage, degradation, deterministic identity, canonical serialization, and
atomic manifest-led publication. The canonical consumer retrieves and validates
that product without collecting Providers or using local fallback.

The closed domains are `news`, `macro_release`, `policy`, `positioning`, and
`filing`. The required Providers are Federal Reserve, BLS, PBOC, NBS, SSE, SZSE,
SEC EDGAR, and CFTC.

The Host Agent owns evidence-preserving summarization and formatting: grouping,
headings, ordering, transparent consolidation/compression, semantic-support
assessment, and user-facing presentation. Neither side may turn presentation
choices into importance, causality, market impact, prediction, investment, or
trading judgment.

There is no repository Agent orchestration, model/LLM runtime, private
invocation path, Audit/Event capability, research engine, market analytics/state,
watchlist, scoring/ranking, or standalone public CLI product.
