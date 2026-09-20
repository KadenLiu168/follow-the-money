# Architecture boundary

`follow-the-money` is a deterministic, typed, credential-free Evidence Feed
for Host Agents. The only repository capability is the current five-domain
Feed:

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
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

After canonical Feed consumption, the Skill deterministically prepares one
typed, versioned, non-persisted `DigestContext` version `2`. The context is a
bounded view of the validated Feed, not a second evidence schema or authority;
it is never published, cached, checkpointed, or used to replace Feed identity.
Closed domain field selection, current-membership classification, reader-unit
construction, reference-state classification, compact domain status, and
material limitations happen in this preparation step. The Host Agent owns
representation, semantic-support assessment, summarization, editorial
operations, and final formatting; it does not reclassify Feed evidence or
account for every Feed item.

The item-level `semantic_context` is a closed evidence projection attached only
to newly acquired or replaced `news`, `macro_release`, and `policy` items. It
does not generate a Digest or add analytical meaning. Valid legacy previous-
major omissions remain readable, and eligible contextless carried slices retain
their original bytes; `filing` and `positioning` remain outside this field.

The item-level `source_content` sibling is likewise closed evidence, not an
analysis surface: DigestContext exposes only its `text`, `format`, and
`truncated` values for current units, never its extraction method or document
digest, and preparation performs no URL access or document parsing. Bounded
official text may support attributed factual statements, but it never
reconstructs an absent structured semantic field and a truncated extract is
never presented as the complete official document.

There is no repository Agent orchestration, model/LLM runtime, private
invocation path, Audit/Event capability, research engine, market analytics/state,
watchlist, scoring/ranking, or standalone public CLI product.
