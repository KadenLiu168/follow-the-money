# Feed Contract

## Envelope

`feed.schema.json` (JSON Schema 2020-12) defines the common envelope and a
`oneOf` payload for `news`, `macro_release`, `policy`, `market_data`, `flow`,
`positioning`, `filing`, and `calendar`. The envelope includes:

- `schema_version` (supported major; unknown/incompatible fails closed),
- `run_id` derived from the fixed cutoff plus the semantic `content_digest`,
- the half-open window `[window.start, evidence_cutoff_at)` (strictly
  advancing),
- truthful lifecycle timestamps and per-provider outcomes (exactly one
  outcome per planned provider, ascending `provider_id`, including failed
  and skipped outcomes),
- mandatory producer provenance: the closed path/size/file-hash application
  build descriptor, the canonical redacted resolved Feed-config snapshot and
  hash, the Feed-schema descriptor, and a sorted canonical redacted closed
  non-secret runtime-contract snapshot plus hash for every enabled provider,
  with optional Git metadata,
- `content_digest` — the canonical digest of the explicit semantic
  projection, not a whole-envelope checksum (see below).

## Semantic identity

`content_digest` is the SHA-256 of the canonical serialization of an
explicit allowlisted semantic projection:

- `schema_version`, `window`, and `evidence_cutoff_at`;
- semantic provider outcomes, ordered by `provider_id`, with the
  execution-audit `retrieved_at` removed;
- `producer`, `feed_config`, `feed_schema`, and `provider_contracts`;
- normalized items (stable `(source.knowledge_available_at, id)` total
  order, including merged `source_lineage` in the same contributing order);
- the pipeline semantic result: `status` and structured `coverage_gap`
  (free-form warning text is execution reporting and never promotes into
  identity).

`collection_started_at`, `collection_completed_at`, `generated_at`, every
provider `retrieved_at`, `git`, `content_digest`, `run_id`, and any
undeclared execution metadata are excluded. `run_id` continues to derive
from the fixed cutoff plus the digest (`{evidence_cutoff_at}::{digest[:32]}`),
so equal semantic evidence with different truthful execution timing keeps
one identity.

Identity is therefore a *semantic* identity, not a whole-file checksum.
Consumers reconstruct the projection, recompute both values, and fail
closed on any mismatch. Validation additionally attempts the former
whole-envelope projection for an already-published schema-v1 `latest.json`;
newly produced Feeds always use the semantic projection. Runtime continuity is
checkpoint-owned, and Git history is repository-level history rather than a
Feed archive or historical query API.

## Cutoff / time model

- The collection clock is injectable. The pipeline captures
  `collection_started_at` at the actual collection phase entry, then one
  injected wall-clock `evidence_cutoff_at` after collection starts and
  before any provider request, all after acquiring the exclusive collection
  lock (lock wait time never freezes a stale planning window).
- `retrieved_at` is recorded when a provider response actually returns and
  before normalization; failed or skipped work with no observed response
  keeps `retrieved_at: null` — never a synthetic timestamp.
- `collection_completed_at` is captured only after every provider outcome
  reached a terminal or fenced state; `generated_at` is captured at the
  final envelope-generation boundary before identity fields are attached.
- The pipeline never derives audit timestamps by offsetting the cutoff,
  copying another lifecycle timestamp, or otherwise synthesizing an
  unobserved event.
- The evidence window is `[window.start, evidence_cutoff_at)` and MUST
  strictly advance. A captured cutoff equal to or earlier than the checkpoint
  cutoff fails `non_advancing_cutoff` with zero provider calls and
  zero artifacts.
- An explicit null `.feed-state/feed-checkpoint.json` is the first-run
  bootstrap with `window.start = cutoff - 72h`. Steady-state planning reads
  only that checkpoint; a present but unreadable/partial/schema-invalid or
  digest-invalid `feeds/latest.json` is rejected by the existing publication or
  consumption boundary, not used as a continuity fallback.
- A gap > 72h uses the bounded bootstrap start and records the uncovered
  interval as a structured `coverage_gap` (plus a warning); an exact 72h gap
  starts at the prior cutoff.
- Collection timestamps satisfy `collection_started_at <= evidence_cutoff_at
  <= each non-null retrieved_at <= collection_completed_at <= generated_at`.
- The scheduled workflow starts near 08:20 Asia/Shanghai (00:20 UTC);
  `Asia/Shanghai` is a display/schedule zone, all persisted instants are
  RFC 3339 UTC.

## Payload time semantics

| Payload | Knowledge time | Effective/reference time |
| --- | --- | --- |
| `news` | `published_at` or later `updated_at` | `occurred_at` or publication |
| `macro_release` | `released_at` | release instant; period is reference |
| `policy` | `published_at`/`announced_at` | `effective_at` or announcement |
| `filing` | acceptance/publication instant | acceptance/publication |
| `flow` | publication/availability instant | measurement `as_of` |
| `positioning` | report publication instant | report/measurement `as_of` |
| `market_data` | `as_of` + availability lag | observation `as_of` |
| `calendar` | announcement/update time | future `scheduled_at` |

The v1 calendar snapshot covers `[evidence_cutoff_at, +26h)` and persists
`calendar_horizon_end`. `retrieved_at` is audit metadata and never
establishes cutoff eligibility. Post-cutoff publications/revisions and
observations not source-available at cutoff are rejected.

## Health and degradation

- A planned Provider is complete for group counting only when it reaches
  `healthy` or returns a contract-permitted `empty` result; accepted and
  fetched item counts do not determine completeness.
- An incomplete planned Provider or deficient mandatory coverage group is
  `failure`, retains Provider diagnostics, and does not replace the last valid
  `latest.json`.
- A source-complete Feed with `items: []` remains a normal successful Feed and
  advances the evidence window through the usual latest publication.
- Existing `degraded` semantics remain available for accepted non-source
  conditions.
- Intelligence fields (importance, direction, price-in, regime, impact,
  ranking) are rejected from Feed items.

## Publication

- `feeds/latest.json` is the only Feed product. Publication uses unpredictable
  same-parent/same-device staging, create-only writes, file and parent-directory
  `fsync`, ownership validation immediately before commit, and same-directory
  atomic replacement followed by parent-directory `fsync`.
- Every latest byte sequence passed to publication is the shared
  `canonical_bytes()` serialization of its validated Feed object; no
  module-local JSON serializer settings are used for Feed artifacts.
- A valid current latest with the candidate's semantic `run_id`,
  `content_digest`, and cutoff is an idempotent accepted owner; its existing
  canonical bytes are retained even when excluded audit bytes differ. A stale
  candidate or incompatible equal owner fails closed without creating another
  Feed product.
- Rename success followed by parent-`fsync` failure returns
  `commit_durability_unknown`; the product remains visible but checkpoint
  advancement is refused because durability is uncertain.
- The scheduled GitHub workflow runs on GitHub-hosted `ubuntu-latest` at
  `20 0 * * *` (08:20 Asia/Shanghai), uses `feeds/` for Feed products and
  `.feed-state/` for repository-backed runtime state, and publishes only
  through the durable migration/bootstrap/lease/finalization boundary. The
  evidence cutoff remains runtime-derived rather than the nominal schedule.

## Minimal internal Feed entry

- The minimal internal entry (`python -m follow_the_money.feed.cli` behind
  `scripts/feed/follow-the-money-feed`) supports explicit config/product/
  runtime-state roots, `--dry-run`, fixture clocks/windows, and deterministic exit codes
  (0 healthy/degraded, 1 generation/publication failure, 2 usage/config).
- `--dry-run` publishes no `latest.json` and advances no checkpoint, but real
  sends still lock and durably debit/reconcile rate state; an explicit no-send
  fixture dry run may leave rate state unchanged.
- There is no LLM adapter anywhere: the Feed pipeline is fully deterministic
  and credential-free, and no public user-facing CLI product form exists.
