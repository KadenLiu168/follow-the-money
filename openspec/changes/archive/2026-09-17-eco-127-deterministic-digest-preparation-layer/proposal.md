## Why

The Host Agent currently receives the full validated Feed and must itself locate
status, coverage, warnings, provenance, and the ECO-126 domain-eligible evidence
before it can summarize anything. ECO-127 introduces one deterministic preparation
boundary so the Agent receives a typed, versioned `DigestContext` and remains
responsible only for evidence-preserving summarization and formatting.

## What Changes

- Add a deterministic Digest preparation layer that consumes only the canonical
  current published Feed after the existing retrieval and validation path succeeds.
- Define a non-persisted, Agent-facing `DigestContext` with an explicit code-level
  type, context version, canonical JSON encoding, and deterministic derivation
  contract. Every value is fully derived from and bound to the validated Feed.
- Include Feed identity and window, pipeline status, warnings, coverage gaps,
  deterministic domain totals, Provider availability and freshness, and traceable
  provenance references.
- Apply the ECO-126 closed per-domain evidence rules before Agent consumption so
  `raw_metadata`, unlisted fields, absent evidence, and future unapproved Feed fields
  cannot become Digest evidence.
- Keep Feed schemas and artifacts as the sole evidence contract. `DigestContext`
  has no independent evidence schema, is never published or persisted, and cannot
  supply evidence or authority not present in its source Feed.
- Keep the Host Agent responsible for semantic-support assessment, summarization,
  editorial grouping, consolidation or omission, compression accounting, and final
  formatting. The preparation layer performs no prose generation, ranking,
  importance judgment, market interpretation, or other analysis.
- **BREAKING**: normal Skill preparation output changes from the complete logical
  Feed JSON object to the versioned canonical JSON `DigestContext` interface.
- Do not add an LLM/model runtime, prompt pipeline, renderer, template engine,
  Agent orchestration, historical-Feed access, fallback, or duplicated Feed
  validation logic.

## Capabilities

### New Capabilities

- `digest-preparation-contract`: Defines the typed, versioned, deterministic,
  non-persisted `DigestContext` derived exclusively from one validated current Feed.

### Modified Capabilities

- `digest-presentation-contract`: Moves closed evidence-field selection and domain
  dispatch into deterministic preparation while retaining presentation guidance and
  Host-Agent-owned prose behavior.
- `information-digest-invocation`: Changes normal Host-Agent input from the raw
  validated Feed to the Feed-bound `DigestContext` and preserves fail-closed current
  publication consumption.
- `skill-agent-responsibility-boundary`: Assigns deterministic Digest preparation to
  the Skill while retaining summarization, semantic-support assessment, and final
  formatting with the Host Agent.
- `agent-grounding-validation-contract`: Permits the typed Agent-facing context
  interface without introducing a second evidence authority, grounding validator,
  or final-output runtime.
- `skill-capability-surface`: Classifies Digest preparation as bounded current-Feed
  consumption machinery rather than a second semantic or evidence capability.

## Impact

- Adds a focused module under `src/follow_the_money/` for typed context preparation
  and canonical serialization, plus deterministic unit and invocation regressions.
- Changes `scripts/skill/prepare-feed` output and the corresponding Skill,
  reference, architecture, and invocation documentation.
- Reuses `consume_published_feed()` and the existing manifest, artifact, schema,
  semantic, provenance, identity, and digest validation path without altering it.
- Does not change `schemas/`, `providers/`, configuration, published Feed bytes,
  Feed identity, collection, publication, dependencies, or network topology.
