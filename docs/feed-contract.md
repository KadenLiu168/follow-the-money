# Feed Contract

## Manifest-led bundle

New Feed production writes one authoritative `feeds/feed-manifest.json` and
exactly one generation-qualified artifact for each closed payload domain, in
this order:

1. `news`
2. `macro_release`
3. `policy`
4. `market_data`
5. `flow`
6. `positioning`
7. `filing`
8. `calendar`

Every artifact exists, including when its `items` array is empty. Its envelope
contains only `schema_version`, `run_id`, `domain`, and `items`. Items retain
the existing `feed.schema.json` payload shapes and are routed solely by
`payload.type`; Provider identity does not affect routing.

The manifest contains the logical Feed metadata, producer/configuration and
Provider contract snapshots, Provider outcomes, pipeline result, logical
`feed_schema` descriptor, physical `bundle_schemas` descriptors, and the exact
artifact inventory (`domain`, safe `path`, `item_count`, `size_bytes`, and
`sha256`). It contains no evidence item or financial interpretation.

The physical contracts are:

- `schemas/feed-manifest.schema.json`
- `schemas/feed-artifact.schema.json`
- `schemas/feed.schema.json` for the reconstructed logical identity and
  manifest-absent legacy reads.

## Semantic identity

`content_digest` remains the SHA-256 of the canonical serialization of the
explicit logical projection:

- `schema_version`, `window`, and `evidence_cutoff_at`;
- semantic Provider outcomes, ordered by `provider_id`, without
  execution-audit `retrieved_at`;
- `producer`, `feed_config`, `feed_schema`, and `provider_contracts`;
- globally ordered normalized items, including source lineage; and
- pipeline `status` and structured `coverage_gap`.

Lifecycle timestamps, Provider `retrieved_at`, Git metadata, physical schema
descriptors, artifact paths/sizes/checksums, `content_digest`, and `run_id` are
outside the projection. `run_id` remains
`{evidence_cutoff_at}::{content_digest[:32]}`. Splitting and reconstructing
unchanged logical evidence therefore preserves identity.

## Validation and consumption

Bundle validation is fail-closed. It requires canonical UTF-8 JSON, supported
schema majors, the exact eight-domain inventory in fixed order, safe
repository-relative generation paths, matching bytes/size/SHA-256, shared
`run_id`, matching domain/type, deterministic item order, unchanged
provenance, and a reconstructed Feed whose digest and `run_id` recompute
exactly. Missing, extra, duplicate, reordered, corrupt, mixed-generation,
traversal, or identity-invalid state is not consumable.

Consumers first check `feed-manifest.json`. If it exists, any manifest or
artifact error is terminal and `latest.json` is never used as fallback. Only
when the manifest is absent may a supported, fully validated legacy
`latest.json` be read. Healthy bundles are accepted; degraded bundles are
accepted with warnings; `pipeline.status: failure` is rejected. Freshness and
calendar-horizon checks remain the existing engine boundary checks.

## Cutoff, ordering, and health

The evidence window is `[window.start, evidence_cutoff_at)` and must advance
strictly. Persisted timestamps are RFC 3339 UTC. Items use the stable
`(source.knowledge_available_at, id)` order, and the calendar snapshot covers
the configured horizon. Source completeness, coverage/degradation semantics,
provenance, numeric bounds, and the evidence-only boundary are unchanged.

## Publication and continuity

Publication writes immutable `feed-<domain>-<sha256(run_id)[:32]>.json`
candidates first, using create-only same-parent staging, file and directory
`fsync`, then stages and atomically replaces `feed-manifest.json` as the sole
activation point. Monotonic ownership is the maximum
`(evidence_cutoff_at, content_digest)` tuple. Equal semantic identity with
identical inventory integrity is idempotent; stale, conflicting, unsafe, or
invalid candidates fail closed. A post-rename directory-`fsync` failure is
durability uncertainty: no rollback is claimed and the checkpoint does not
advance. Orphan and superseded files are cleanup state, never query history.

A successful status names `manifest_relative_path: "feed-manifest.json"` and
its `run_id`/cutoff; when publication removed a superseded generation, it also
carries those deleted relative artifact paths for exact Git staging. The
unchanged versioned checkpoint advances only after
accepted durable manifest ownership, and deployment validates it against that
manifest. Dry-run builds and validates the same in-memory bundle without
writing Feed products or advancing the checkpoint.

## Current-state migration

Deployment can split a valid current legacy `latest.json` into the equivalent
bundle without Provider requests. It activates the manifest, keeps
`latest.json` unchanged until the same generated-state commit stages its
deletion, and leaves the legacy product intact when validation or publication
fails. If a valid manifest already exists, migration treats it as the sole
authority and does not reinterpret `latest.json`.

## Minimal internal Feed entry

`python -m follow_the_money.feed.cli` (also
`scripts/feed/follow-the-money-feed`) accepts explicit config/product/runtime
roots, dry-run, and fixture clocks/windows. Exit codes remain:

- `0` — healthy/degraded success;
- `1` — generation, publication, schema, integrity, deadline, or runtime
  failure;
- `2` — usage, configuration, or startup-capability error.

The Feed is deterministic, credential-free, and evidence-only. It does not
contain an LLM/model path or Host Agent orchestration.
