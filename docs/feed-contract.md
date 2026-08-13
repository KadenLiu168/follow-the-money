# Feed Contract

## Envelope

`feed.schema.json` (JSON Schema 2020-12) defines the common envelope and a
`oneOf` payload for `news`, `macro_release`, `policy`, `market_data`, `flow`,
`positioning`, `filing`, and `calendar`. The envelope includes:

- `schema_version` (supported major; unknown/incompatible fails closed),
- `run_id` derived from the fixed cutoff plus the canonical digest,
- the half-open window `[window.start, evidence_cutoff_at)` (strictly
  advancing),
- collection timestamps and per-provider outcomes,
- mandatory producer provenance: the closed path/size/file-hash application
  build descriptor, the canonical redacted resolved Feed-config snapshot and
  hash, the Feed-schema descriptor, and a sorted canonical redacted closed
  non-secret runtime-contract snapshot plus hash for every enabled provider,
  with optional Git metadata,
- `content_digest` covering the canonical projection with `content_digest`
  and `run_id` omitted (non-circular).

## Cutoff / time model

- One injected wall-clock `evidence_cutoff_at` is captured after acquiring
  the exclusive collection lock and before any provider request.
- The evidence window is `[window.start, evidence_cutoff_at)` and MUST
  strictly advance. A captured cutoff equal to or earlier than the latest
  valid cutoff fails `non_advancing_cutoff` with zero provider calls and
  zero artifacts.
- An actually absent `feeds/latest.json` is a first-run bootstrap with
  `window.start = cutoff - 72h`. A present but unreadable/partial/schema-
  invalid/digest-invalid latest fails `invalid_latest_integrity`.
- A gap > 72h uses the bounded bootstrap start and records the uncovered
  interval as a warning; an exact 72h gap starts at the prior cutoff.
- Collection timestamps satisfy `collection_started_at <= evidence_cutoff_at
  <= request/retrieved_at <= collection_completed_at <= generated_at`.
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

- A member is healthy for group counting only when it succeeds with accepted
  items or returns a manifest-permitted empty result.
- A deficient mandatory coverage group marks a non-empty Feed `degraded`.
- Zero accepted items across all enabled providers is `failure` regardless
  of transport success and does not replace the last valid latest.
- Intelligence fields (importance, direction, price-in, regime, impact,
  ranking) are rejected from Feed items.

## Publication

- Create-only `feeds/daily/YYYY-MM-DD/<run_id>.json` (date = cutoff in
  Asia/Shanghai) before atomic replacement of `feeds/latest.json`.
- Unpredictable same-parent/same-device staging, create-only writes,
  file/staging-directory `fsync`, platform atomic no-replace dated rename,
  same-directory atomic latest replace, and parent-directory `fsync` after
  each rename.
- Same run ID + digest is an idempotent no-op; an existing path with
  incompatible content fails.
- Rename success followed by parent-`fsync` failure returns
  `commit_durability_unknown`; recovery re-applies the maximum
  `(evidence_cutoff_at, content_digest)` tuple rule.
- The scheduled GitHub workflow runs only on a dedicated labelled
  self-hosted runner with a persistent shared output root and durable rate
  state; an ephemeral hosted runner/fresh root fails the contract.

## Minimal internal Feed entry

- The minimal internal entry (`python -m follow_the_money.feed.cli` behind
  `scripts/feed/follow-the-money-feed`) supports explicit config/output
  roots, `--dry-run`, fixture clocks/windows, and deterministic exit codes
  (0 healthy/degraded, 1 generation/publication failure, 2 usage/config).
- `--dry-run` publishes nothing but real sends still lock and durably
  debit/reconcile rate state; an explicit no-send fixture dry run may leave
  rate state unchanged.
- There is no LLM adapter anywhere: the Feed pipeline is fully deterministic
  and credential-free, and no public user-facing CLI product form exists.
