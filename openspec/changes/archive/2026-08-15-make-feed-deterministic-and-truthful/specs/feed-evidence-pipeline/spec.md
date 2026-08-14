## ADDED Requirements

### Requirement: Deterministic Feed aggregation and normalization
Provider work SHALL remain eligible for concurrent execution, but every Feed SHALL serialize one outcome for each provider represented by the collection plan in ascending `provider_id` order, including failed and skipped providers. Before duplicate comparison, duplicate-survivor selection, lineage merging, or final serialization, Feed items SHALL use the total order `(source.knowledge_available_at, id)`. Every merged `source_lineage` SHALL use the same contributing-item order, and no semantic result SHALL depend on provider completion order or input list order.

#### Scenario: Provider completion schedule changes
- **WHEN** the same provider results complete under different schedules
- **THEN** every Feed has the same `provider_outcomes` order and the same semantic identity

#### Scenario: Failed and skipped providers are present
- **WHEN** a collection plan produces successful, failed, and skipped provider outcomes
- **THEN** all outcomes are represented once and ordered by `provider_id` independently of when their terminal states were recorded

#### Scenario: Item input order changes
- **WHEN** the same evidence items are supplied in different permutations
- **THEN** duplicate survivors, dropped identities, merged lineage, final item order, and semantic identity are identical

### Requirement: Feed semantic identity is separate from execution audit metadata
`content_digest` SHALL be the canonical digest of an explicit semantic projection containing `schema_version`, `window`, `evidence_cutoff_at`, semantic provider outcomes, `producer`, `feed_config`, `feed_schema`, `provider_contracts`, `items`, and the pipeline semantic result. The semantic provider outcomes SHALL contain every serialized provider-outcome field except `retrieved_at`. The projection SHALL exclude `collection_started_at`, `collection_completed_at`, `generated_at`, provider `retrieved_at`, `content_digest`, `run_id`, and any undeclared top-level execution metadata. `run_id` SHALL continue to derive from the fixed cutoff and `content_digest`.

#### Scenario: Only execution timing changes
- **WHEN** two valid Feed envelopes have the same semantic projection and cutoff but different collection duration, provider `retrieved_at`, or `generated_at` values
- **THEN** they have the same `content_digest` and `run_id`

#### Scenario: Semantic evidence changes
- **WHEN** an item, provider semantic outcome, embedded producer contract, Feed configuration, window, cutoff, or pipeline semantic result changes
- **THEN** the recomputed `content_digest` changes

#### Scenario: Identity is validated by a consumer
- **WHEN** a Feed is consumed
- **THEN** validation reconstructs the explicit semantic projection, recomputes `content_digest` and `run_id`, and fails closed on any mismatch

#### Scenario: Existing supported-major Feed uses the legacy projection
- **WHEN** a previously published schema-major-compatible Feed is read during migration and its identity validates only under the former whole-envelope projection
- **THEN** the reader accepts that legacy artifact, while every newly produced Feed uses the semantic projection

### Requirement: Feed audit timestamps are truthful lifecycle observations
The pipeline SHALL obtain `collection_started_at` from the actual start of collection, capture one `evidence_cutoff_at` after collection starts and before any provider request, obtain a non-null provider `retrieved_at` when that provider request actually returns, obtain `collection_completed_at` only after all provider work has reached a terminal or fenced state, and obtain `generated_at` when the Feed envelope is finalized. Failed or skipped work that never returns a provider response SHALL retain null `retrieved_at`. The pipeline SHALL NOT derive audit timestamps by offsetting the cutoff, copying another lifecycle timestamp, or otherwise synthesizing an unobserved event.

#### Scenario: Successful collection lifecycle
- **WHEN** providers return and a Feed envelope is built
- **THEN** observed timestamps satisfy `collection_started_at <= evidence_cutoff_at <= each non-null retrieved_at <= collection_completed_at <= generated_at`

#### Scenario: Provider never returns evidence
- **WHEN** a provider is skipped or reaches its recorded terminal state before any response returns
- **THEN** its outcome has null `retrieved_at` rather than a synthetic timestamp

#### Scenario: Clock calls identify lifecycle events
- **WHEN** a deterministic test clock supplies distinct instants at collection start, cutoff capture, provider return, collection completion, and envelope generation
- **THEN** the Feed records those corresponding instants without fixed offsets or timestamp reuse

### Requirement: Canonical serializer owns published Feed bytes
Every dated or latest Feed byte sequence passed to publication SHALL equal the shared `canonical_bytes()` serialization of its validated Feed object. Feed-producing modules SHALL NOT use independent JSON serializer settings for published Feed bytes.

#### Scenario: Feed is serialized for publication
- **WHEN** a valid healthy or degraded Feed is admitted to publication
- **THEN** its dated and latest candidate bytes are produced by the shared canonical serializer and are byte-identical to `canonical_bytes(feed)`

### Requirement: Publication is idempotent by semantic identity
When a valid immutable dated artifact already exists at the path for a candidate's semantic `run_id`, publication SHALL validate that artifact and compare semantic identity rather than require equality with the candidate's execution-metadata bytes. If the semantic identities match, publication SHALL retain the existing dated bytes, report the run as idempotent, and use the retained immutable bytes for any required `latest.json` repair or replacement. Different semantic identity at the same dated path, invalid existing content, and identity mismatches SHALL continue to fail closed. Existing create-only dated publication, atomic latest replacement, monotonic latest ownership, and `fsync` durability requirements SHALL remain unchanged.

#### Scenario: Same semantic Feed runs with different audit timing
- **WHEN** a later execution has the same semantic `run_id` as an existing valid dated artifact but different truthful audit timestamps
- **THEN** publication retains the first immutable artifact, reports idempotent success, and does not raise an incompatible-content conflict

#### Scenario: Idempotent recovery repairs latest
- **WHEN** the semantic dated artifact exists but `latest.json` is absent or is owned by an older semantic identity
- **THEN** publication repairs `latest.json` from the retained dated artifact bytes rather than the later execution envelope

#### Scenario: Same path carries different semantic identity
- **WHEN** an existing dated path is invalid or its validated `content_digest` and `run_id` differ from the candidate semantic identity
- **THEN** publication fails closed without overwriting the immutable artifact
