## ADDED Requirements

### Requirement: Configured evidence providers
The system SHALL load enabled providers from configuration through a common fetch-and-normalize interface, the default core configuration SHALL require no paid financial-data credential, and every enabled adapter SHALL have a checked-in verified contract manifest covering its fetch/redirect hosts, separately permitted evidence `source_link_hosts`, usage constraints, source timestamps, stable identity, pagination, rate limits, units, freshness, and fixture provenance. Each source-link rule SHALL use the design-defined closed canonical-host/subdomain/port/query/drop policy; item ingress SHALL require HTTPS, drop fragments/tracking parameters, and reject userinfo, IP/authority tricks, unlisted query material, common/provider credential names, malformed bare/truncated/non-hex percent escapes, any residual valid `%HH` after exactly one path/query decode, or any configured at-least-8-byte secret found as a substring of the once-decoded path/query before or after canonicalization, without recursive decoding or logging rejected material. Every normalized evidence URL SHALL be credential-free, bound to and validated against its owning provider before it can enter the Feed. The shipped v1 mandatory groups and minima SHALL exactly match the design matrix: Fed+BLS `us_official_macro_policy` 2/2, SEC `us_company_filings` 1/1, PBOC+NBS `china_official_macro_policy` 2/2, SSE+SZSE `china_exchange_evidence` 2/2, Yahoo-compatible with verified mappings for all 13 roles `china_hk_cross_asset_market` 1/1, and Fed+BLS+NBS calendar capabilities `future_calendar` 3/3. Only succeeded-with-accepted-items or manifest-permitted-empty outcomes count healthy, missing dashboard roles remain explicit and make that group incomplete, and shipped-default configuration/Apply completion SHALL fail if contract verification leaves any row unachievable.

Provider orchestration SHALL acquire one exclusive collection lock in the explicit output root before reading latest/capturing the cutoff and hold it through publication, so cooperating CLI processes sharing a provider/rate scope SHALL use that same root and SHALL NOT execute provider requests concurrently across processes. Lock waiting SHALL count against the 300-second command-start monotonic pre-commit deadline with its exact 15-second reserve, occupy no request-concurrency slot, and fail typed `collection_lock_timeout` with no call/artifact when it cannot fit. Under the lock, the closed output-root registry and per-`scope_id` token/refill/last-dispatch/cooldown state SHALL survive sequential processes/crashes through the design's atomic/fsync protocol. Only a scope absent from a valid registry may use the recoverable `initializing` to full-capacity-state to `active` first-use sequence before requests. An active scope with missing/partial/corrupt/unknown state, or a marked persistent root with missing/corrupt registry, SHALL fail closed rather than reset. Policy changes SHALL use the design's explicit zero-send conservative migration and never reset implicitly. Non-negative injected UTC elapsed time alone may refill, and wall-clock rollback SHALL grant no token. Every possible send SHALL durably debit and install the design's 24-hour provisional crash cooldown first; only confirmed pre-send failure MAY durably refund. Any controlled terminal outcome—including a complete response, HTTP error, connection failure, or timeout while the process can still update state—SHALL retain the debit but durably reconcile the provisional value to the greater of the normal policy next-eligible time and a valid `Retry-After`, allowing only policy-compliant retry. Crash/uncertain loss before reconciliation or state-write failure SHALL retain 24 hours and stop further calls. Within the run, orchestration SHALL enforce the design-defined 8-global/2-per-host concurrency limits, pagination/retry consumption, same-policy requirement for shared scopes, waits before request-concurrency admission, sequential provider pagination unless verified otherwise, provider-ID admission/stable join order, cancellation with no late Feed mutation, and no wait/attempt that cannot fit the remaining pre-commit deadline and reserve. All reversible work and staging `fsync` SHALL finish by second 285; an admitted filesystem publication SHALL then run non-cancellably to its normal result and MAY report `commit_elapsed_overrun` only in external machine-readable status/stderr after second 300 without changing Feed bytes.

Raw provider bytes SHALL be decoded only with the owning verified manifest's exact allowed charset and strict error handling; replacement decoding, heuristic charset sniffing, or conflicting BOM/header/meta declarations SHALL reject the response. Repository JSON and normalized strings SHALL then satisfy strict UTF-8/Unicode-scalar validation before any identity or persistence operation.

#### Scenario: Run with no paid data keys
- **WHEN** the Feed command runs with the default free-provider configuration and no paid financial-data key
- **THEN** it attempts every enabled free provider and can produce a valid Feed from the providers that respond

#### Scenario: Provider disabled
- **WHEN** a provider is marked disabled in configuration
- **THEN** the pipeline does not initialize or contact that provider

#### Scenario: Provider completions arrive in different orders
- **WHEN** the same provider fixtures complete under different schedules within the concurrency limits
- **THEN** the normalized provider outcomes and Feed bytes remain in provider-ID stable order

#### Scenario: Provider contract is unverified
- **WHEN** an adapter lacks a current complete contract manifest
- **THEN** configuration validation prevents it from being enabled or counted as available coverage

#### Scenario: Evidence URL impersonates an allowed source
- **WHEN** a provider emits a non-HTTPS URL or one with userinfo, an IP literal, percent-encoded authority, an undeclared port, an exact/suffix-lookalike host, unlisted query material, or a credential outside its manifest's canonical `source_link_hosts` rules
- **THEN** the item is rejected before Feed identity or rendering without dereferencing the URL

#### Scenario: Two CLI collections share a provider scope
- **WHEN** a second cooperating process uses the same explicit output root while the first holds the collection lock
- **THEN** it waits without consuming provider concurrency, then re-reads latest and plans after acquisition, or fails `collection_lock_timeout` before any provider call when the shared deadline expires

#### Scenario: A dispatched request process crashes
- **WHEN** a process exits after the durable pre-send debit but before it can durably reconcile a response
- **THEN** the next process retains the debit and 24-hour provisional cooldown instead of resetting the scope's bucket or assuming the request was not received

#### Scenario: A controlled timeout remains retryable
- **WHEN** a dispatched attempt times out or loses its connection but the running process can durably reconcile rate state
- **THEN** the debit remains, the 24-hour crash provisional is replaced with the manifest-policy next-eligible time, and a transient retry may occur only after that time and within the remaining command deadline

#### Scenario: Feed commit crosses the nominal deadline
- **WHEN** all candidate bytes are staged and `fsync`ed and commit is admitted by second 285 but rename/parent `fsync` completes after second 300
- **THEN** the transaction finishes without cancellation or rollback, reports `commit_elapsed_overrun` only in external machine-readable command status/stderr if it otherwise succeeds, and leaves the already hashed Feed bytes unchanged

### Requirement: Evidence-only Feed generation
The Feed pipeline SHALL perform fetching, normalization, exact and conservative near deduplication, schema validation, and publication without invoking an LLM, and SHALL reject intelligence fields from Feed items.

#### Scenario: Feed command executes
- **WHEN** Feed generation is invoked
- **THEN** no LLM client, model, prompt, or LLM credential is loaded or called

#### Scenario: Intelligence field is introduced
- **WHEN** a normalized item contains importance, direction, price-in, money-flow interpretation, market regime, asset impact, or ranking data
- **THEN** Feed schema validation fails before publication

### Requirement: Unified envelope and typed payload
Every published Feed SHALL conform to the supported major version of `feed.schema.json`, include `schema_version`, `run_id`, fixed-window and collection timestamps, per-provider outcomes, mandatory non-Git-capable producer application closed file-hash descriptor, canonical redacted resolved Feed-config snapshot/hash, Feed-schema descriptor, and a sorted canonical redacted closed non-secret runtime-contract snapshot/hash for every enabled provider, with optional Git metadata and a canonical `content_digest` in the common envelope, and contain exactly one supported typed payload for `news`, `macro_release`, `policy`, `market_data`, `flow`, `positioning`, `filing`, or `calendar`. Each embedded provider snapshot SHALL contain the fetch/redirect/source-link/rate/time/identity/unit/freshness/empty-window rules needed to validate that provider's items/outcome without current local manifest bytes. The digest SHALL cover the canonical Feed projection including producer provenance but with both `content_digest` and `run_id` omitted, after which `run_id` SHALL derive from the fixed cutoff and digest and all embedded aggregate hashes/identities SHALL be recomputable without circularity. Consumer compatibility SHALL depend on the supported schema major, not equality with the consumer's current build/config/manifest fingerprints, and validation SHALL use the embedded provider snapshots.

#### Scenario: Valid macro release
- **WHEN** a provider emits a macro release with compatible actual, consensus, previous, and unit metadata
- **THEN** it is serialized as a valid `macro_release` payload under the common envelope

#### Scenario: Payload does not match item type
- **WHEN** an item declares `flow` but supplies a filing payload
- **THEN** validation rejects the Feed

#### Scenario: Feed schema major version is unsupported
- **WHEN** a producer emits an unknown or incompatible `schema_version`
- **THEN** validation fails closed before consumption or publication

#### Scenario: Feed identity is recomputed
- **WHEN** a consumer validates a published Feed
- **THEN** it first recomputes aggregate hashes from the embedded producer descriptors/config/provider-contract snapshots, revalidates provider-bound items from those snapshots, omits `content_digest` and `run_id` from the canonical projection, recomputes the digest and cutoff-derived run ID, and rejects any internal provenance, digest, or identity mismatch without comparing producer hashes to the current consumer build/manifests

### Requirement: Bounded evidence content
News-like Feed items SHALL contain only title, snippet, source metadata, timestamps, URL, resolved hints, and typed metadata; the pipeline SHALL NOT store full copyrighted article bodies. After strict manifest-declared source decoding, every normalized textual value SHALL contain only Unicode scalar values; lone high/low surrogates and category `Cs` SHALL be rejected before NFC, strict-UTF-8 byte counting, hashing, or publication. Before Decimal construction, every raw numeric token SHALL satisfy the design's 64-byte, 24-significant-digit, exponent `[-12,12]` lexical bound. Persisted financial values SHALL be canonical plain decimal strings with no exponent/negative zero, within the same byte/digit bounds and common absolute `10^18` guard, and SHALL satisfy the owning embedded provider contract's required closed field/unit domain. Invalid non-positive price/index/FX/commodity/crypto levels, negative volume/open-interest/count levels, undeclared signed ranges, excess digits/exponents, and special/locale/binary-float values SHALL be rejected before Feed publication.

#### Scenario: Article is normalized
- **WHEN** a source response contains a full article body
- **THEN** the normalized Feed retains only the bounded evidence fields permitted by the schema

#### Scenario: Numeric token is adversarial or outside its domain
- **WHEN** a provider emits an oversized coefficient, huge exponent, special value, zero/negative price, negative volume, or another value outside its manifest field/unit domain
- **THEN** the item/value is rejected before Decimal arithmetic and the exact invalid token cannot consume unbounded resources or enter the Feed

### Requirement: Stable identity and conservative deduplication
The pipeline SHALL assign stable deterministic item IDs, remove duplicate normalized URLs and same-source near duplicates, retain source-lineage records for cross-source URL duplicates, and retain independently originated cross-source reports as separate evidence.

#### Scenario: Same URL collected twice
- **WHEN** two source records normalize to the same canonical URL
- **THEN** exactly one Feed item is published for that URL

#### Scenario: Two sources report the same event
- **WHEN** independent sources publish similar evidence with different URLs
- **THEN** both evidence items remain available for later corroboration

#### Scenario: Two domains mirror one wire story
- **WHEN** reports share an original publisher or syndication lineage
- **THEN** their provenance is retained but they count as one source family for corroboration

### Requirement: Source tiers and provenance
Every Feed item SHALL identify its source ID, name, tier, and kind, using Tier 1 for primary sources, Tier 2 for professional financial media, and Tier 3 for social or professional commentary.

#### Scenario: Tier 3 evidence is normalized
- **WHEN** an enabled commentary source emits an item
- **THEN** the item remains explicitly marked Tier 3 and is not promoted to a higher tier by normalization

### Requirement: Raw lookback observations
Market-data items MAY contain a configured bounded series of raw timestamped observations so that the latest Feed alone supports rolling analytics; observations SHALL be serialized in strict chronological order with finite values and explicit units, and the Feed SHALL NOT store calculated importance, regime, or investment interpretation with them.

#### Scenario: Market lookback is available
- **WHEN** a market provider returns the configured lookback for an instrument
- **THEN** the Feed preserves the raw values, timestamps, units, and available volumes in chronological order

#### Scenario: Lookback is incomplete
- **WHEN** fewer observations than requested are available
- **THEN** the Feed records the available facts without filling or inventing missing observations

#### Scenario: Duplicate timestamp conflicts
- **WHEN** one instrument contains the same observation timestamp with incompatible values
- **THEN** provider validation records a conflict and does not silently select a value

### Requirement: Payload-specific temporal semantics
Every payload SHALL carry the design-defined source knowledge time, effective/reference time, and selection basis. Delta `news`, `macro_release`, `policy`, `filing`, and `flow` items SHALL be selected by knowledge time in `[window.start, evidence_cutoff_at)`; bounded `market_data` lookbacks, the current bounded `positioning` report, and current future-`calendar` snapshots MAY contain effective/reference or knowledge times before `window.start` only when their source availability was before cutoff. The v1 calendar snapshot SHALL cover `[evidence_cutoff_at, evidence_cutoff_at + 26h)` and persist `calendar_horizon_end`. `retrieved_at` SHALL remain audit metadata and SHALL NOT establish cutoff eligibility.

#### Scenario: Previously announced calendar event remains upcoming
- **WHEN** a calendar item was announced before `window.start`, was known before cutoff, and its `scheduled_at` remains inside the configured future-calendar horizon
- **THEN** the current calendar snapshot may include it so the latest-only Brief can select it by `scheduled_at`

#### Scenario: Market value was not available at cutoff
- **WHEN** an observation `as_of` precedes cutoff but its explicit or manifest-derived source availability is at or after cutoff
- **THEN** the observation is rejected from the run rather than admitted from its market timestamp alone

#### Scenario: Retrieval completes after cutoff
- **WHEN** a provider retrieves an otherwise eligible item after the fixed cutoff
- **THEN** `retrieved_at` records collection latency but neither makes post-cutoff knowledge eligible nor disqualifies evidence whose source knowledge time was before cutoff

### Requirement: Graceful provider degradation
A single provider failure SHALL NOT terminate collection from other providers; the Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes and SHALL classify the pipeline as `degraded` when at least one valid item exists but any enabled provider or shipped critical coverage group is incomplete. A provider manifest SHALL declare whether an empty result is valid for the requested window; a permitted empty outcome counts as healthy for its group but does not itself satisfy the independent at-least-one-accepted-item rule, while unexpected-empty, partial, failed, disabled, and skipped outcomes do not count toward a group minimum. No accepted item across all enabled providers is a pipeline failure regardless of transport success.

#### Scenario: Critical group minimum is missed
- **WHEN** a non-empty Feed has fewer than the required healthy members in any shipped v1 critical coverage group
- **THEN** the Feed publishes only as `degraded` with the exact deficient group and member outcomes recorded

#### Scenario: One provider times out
- **WHEN** one enabled provider times out and another succeeds
- **THEN** the Feed is validated and published with `pipeline.status = degraded` and a source-specific warning

#### Scenario: No valid items can be produced
- **WHEN** every enabled provider fails or every item is invalid
- **THEN** the pipeline reports `failure` and does not replace the last valid `feeds/latest.json`

#### Scenario: All providers are disabled
- **WHEN** configuration enables no provider
- **THEN** configuration fails and no Feed is generated

#### Scenario: Every enabled provider succeeds with no item
- **WHEN** all enabled requests complete successfully but the pipeline accepts no item
- **THEN** the pipeline reports `failure`, records each empty outcome, and does not replace the last valid `feeds/latest.json`

#### Scenario: A provider has a permitted empty window
- **WHEN** its verified manifest permits an empty result for that window and configured coverage remains satisfied by other accepted items
- **THEN** the provider records `empty` without degrading the pipeline solely for being empty

#### Scenario: One provider page is partially invalid
- **WHEN** a provider returns valid items before a page or item validation failure
- **THEN** valid items and rejection counters are retained, the provider and pipeline are degraded, and no failure is hidden

### Requirement: Actual Feed window and freshness metadata
The Feed SHALL record a strictly advancing half-open `[window.start, evidence_cutoff_at)` interval with `window.start < evidence_cutoff_at`, capture the cutoff once after acquiring the exclusive collection lock and before provider requests, record collection start/completion and per-provider request/retrieval times separately, validate applicable wall-clock order `collection_started_at <= evidence_cutoff_at <= request/retrieved_at <= collection_completed_at <= generated_at`, use a monotonic clock for deadlines, persist instants as RFC 3339 UTC, and display `Asia/Shanghai` schedule metadata; it SHALL NOT claim coverage through collection completion or beyond the fixed cutoff. Before calling providers, scheduled planning SHALL compare the captured cutoff with the current valid latest cutoff and fail typed `non_advancing_cutoff` without a dated artifact when the new cutoff is equal or earlier; a waiting cooperating run SHALL re-read latest and plan only after it acquires the lock, never from a pre-lock frozen window.

#### Scenario: Feed timestamps move backward
- **WHEN** any applicable request/retrieval, completion, or generation timestamp violates the required wall-clock order
- **THEN** Feed validation fails before publication even if monotonic timeout accounting succeeded

#### Scenario: Scheduled collection spans several minutes
- **WHEN** the workflow captures its cutoff at 08:20 and finishes collection at 08:24 Asia/Shanghai
- **THEN** the Feed cutoff remains 08:20 and generation metadata records the later completion instead of claiming coverage through 08:24 or 08:30

#### Scenario: Provider returns a post-cutoff publication
- **WHEN** an event-like item is published or revised at or after `evidence_cutoff_at`
- **THEN** that revision is excluded from this run and recorded in rejection health rather than creating look-ahead evidence

#### Scenario: Source supplies only a publication date
- **WHEN** an event-like item has date precision but no usable publication instant
- **THEN** it is eligible only after that source-local date has fully elapsed and retains its date-precision marker

#### Scenario: First run has no previous cutoff
- **WHEN** the `feeds/latest.json` path is actually absent
- **THEN** v1 sets `window.start = evidence_cutoff_at - 72h` and records that bootstrap coverage origin

#### Scenario: Existing latest Feed is invalid
- **WHEN** the latest path exists but is unreadable, partial, schema-invalid, digest/run-ID-invalid, or otherwise fails integrity validation
- **THEN** planning fails typed `invalid_latest_integrity` with zero provider calls and zero dated/latest writes rather than treating corruption as a first run

#### Scenario: Previous cutoff is beyond the v1 gap threshold
- **WHEN** the new cutoff minus the current latest cutoff is greater than 72 hours
- **THEN** v1 uses `evidence_cutoff_at - 72h` as the bounded start and records the older uncovered interval as a coverage-gap warning; an exact 72-hour gap instead starts at the previous cutoff

#### Scenario: Scheduled cutoff does not advance
- **WHEN** a newly captured scheduled cutoff is equal to or earlier than the current valid latest Feed cutoff
- **THEN** planning returns `non_advancing_cutoff` before any provider call and creates no dated or latest artifact

### Requirement: Auditable publication
A successful or degraded Feed run SHALL validate before create-only publication to `feeds/daily/YYYY-MM-DD/<run_id>.json` and atomic replacement of `feeds/latest.json`. Local publication SHALL retain the already acquired exclusive output-root collection lock, use unpredictable same-parent/same-device staging, create-only writes, file and staging-directory `fsync`, a platform atomic no-replace dated rename, a same-directory atomic latest replace, and parent-directory `fsync` after each rename; unavailable primitives SHALL fail startup capability validation. Failure before rename SHALL expose no target. Rename success followed by parent-`fsync` failure SHALL return `commit_durability_unknown`, leave the complete candidate untouched, perform no later stage or rollback, and rely on integrity-checked retry/recovery; after latest replacement it SHALL make no unsupported claim whether the old or new complete valid latest tuple survives a later crash. Publication SHALL remain idempotent for the same run ID and digest and defensively use the maximum `(evidence_cutoff_at, content_digest)` tuple for externally prepared candidates and deterministic recovery/latest ownership, and the daily workflow SHALL stage only those explicit Feed paths and expose publication failure.

The scheduled GitHub Feed workflow SHALL run only on an explicitly labelled dedicated self-hosted runner with one configured persistent output root shared by every invocation for the relevant provider scopes. Startup SHALL verify a deployment-owned persistence marker and durable rate-state capability before requests. An ephemeral hosted runner, a fresh output root, or a best-effort cache SHALL fail this workflow contract rather than initialize a new full rate bucket; workflow enablement and runner/volume provisioning remain external deployment actions.

#### Scenario: Valid Feed is generated
- **WHEN** schema validation succeeds
- **THEN** the run-scoped dated artifact is durable before latest is replaced and both contain the same validated payload for that run

#### Scenario: Repository write is rejected
- **WHEN** GitHub branch policy rejects the Feed commit
- **THEN** the workflow fails visibly and retains the generated output as a workflow artifact

#### Scenario: Stale prepared candidate reaches publication
- **WHEN** a recovery/import candidate with an older cutoff is submitted after a newer valid latest Feed
- **THEN** it may retain its immutable dated artifact but cannot replace the newer latest Feed

#### Scenario: Equal-cutoff variants are submitted in either order
- **WHEN** two valid externally prepared candidates have the same cutoff and different content digests
- **THEN** both may retain immutable dated artifacts, the greater digest owns latest regardless of submission order, and the variant conflict remains visible in publication outcomes

#### Scenario: Publication fails after dated write
- **WHEN** the dated artifact is durable but latest replacement fails
- **THEN** the previous valid latest remains unchanged and the run reports publication failure that can be retried idempotently

### Requirement: Feed CLI outcome contract
The `follow-the-money feed` command SHALL support explicit configuration and clock/window injection for fixtures, `--dry-run`, an explicit output root, and deterministic exit behavior without reading machine-global configuration.

#### Scenario: Degraded Feed validates
- **WHEN** a partial Feed is valid and publication or dry-run output succeeds
- **THEN** the command exits zero while its machine-readable status and stderr warning identify degradation

#### Scenario: Dry run is requested
- **WHEN** `--dry-run` is set
- **THEN** the command validates and reports the candidate Feed without changing latest or dated artifacts; any real provider request still acquires the collection lock and durably updates shared rate state, while an explicit no-send fixture dry run may leave rate state unchanged
