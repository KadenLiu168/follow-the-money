## Why

The Feed is the sole evidence boundary for future Agent consumers, but its current identity can change with provider completion order, item input order, and truthful execution timing. The pipeline needs a reproducible semantic identity without disguising runtime audit metadata as deterministic evidence.

## What Changes

- Preserve concurrent provider execution while canonicalizing every enabled provider outcome by `provider_id`, including failed and skipped outcomes.
- Define one stable item order for duplicate-survivor selection, lineage merging, and final Feed ordering so input permutations cannot change the semantic result.
- Capture collection, retrieval, completion, and generation timestamps at their real lifecycle events; prohibit cutoff-derived or otherwise synthetic audit timestamps.
- Replace whole-envelope hashing with an explicit semantic Feed projection that includes the evidence cutoff, window, producer/config/contract descriptors, semantic provider outcomes, items, and pipeline semantic result while excluding execution-only timestamps.
- Derive both `content_digest` and `run_id` from that semantic projection and the fixed cutoff so equal semantic inputs retain equal identity across different execution timings.
- Route serialized Feed artifacts through the shared `canonical_bytes()` implementation instead of module-local JSON serialization.
- Align publication idempotency with semantic identity: retain the first immutable dated artifact for an existing semantic `run_id`, use those retained bytes when repairing or aligning `latest.json`, and do not treat later truthful timestamp differences as incompatible content.
- Preserve the existing schema major, provider acquisition contracts, Agent boundary, and publication durability architecture.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Define deterministic semantic identity and ordering, truthful lifecycle timestamps, canonical Feed serialization, and semantic-identity publication idempotency.

## Impact

- Affected runtime areas: Feed collection orchestration, provider outcome aggregation, item deduplication and lineage normalization, Feed validation/identity projection, envelope construction, and publication idempotency.
- Affected contract surfaces: `feed.schema.json` semantic invariants and the bytes stored under `feeds/daily/**` and `feeds/latest.json`; no schema major-version redesign is intended.
- Affected tests: provider scheduling permutations, item permutations, lifecycle clock capture, semantic/runtime identity separation, canonical serialization, and repeated semantic publication/recovery.
- No new external dependency, provider contract, acquisition behavior, Agent contract, scoring path, LLM runtime, or publication durability primitive is introduced.
