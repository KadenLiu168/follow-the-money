## ADDED Requirements

### Requirement: New News, Macro, and Policy evidence carries validated semantic context

Every newly acquired Feed v4 item whose payload discriminator is `news`, `macro_release`, or `policy` SHALL carry exactly one `semantic_context` matching that domain and the retained payload/source facts. The six currently emitting Provider paths SHALL be covered according to their existing output contracts: Federal Reserve and PBOC policy; BLS, NBS, SSE, and SZSE news; and NBS macro releases. Existing domain classification SHALL remain unchanged, including BLS releases and unstructured NBS releases remaining `news` unless a separate Provider-contract change authorizes another payload type.

Semantic enrichment SHALL run after existing source extraction and payload normalization and before item admission. It SHALL perform no Provider request, historical Feed lookup, credential access, orchestration, or payload reclassification. A required context construction or validation failure SHALL reject the item through the existing Provider outcome and publication boundary rather than publish evidence without its required context.

Positioning and filing items SHALL retain their existing typed payload semantics and SHALL NOT acquire `semantic_context` under this Change. Provider manifests, embedded Provider contract versions, payload-type declarations, coverage, freshness, and acquisition behavior SHALL remain unchanged.

A fully validated pre-ECO-130 v4 Provider slice MAY continue to omit context only when the existing snapshot contract carries that complete slice byte-for-byte and records its prior run in non-null `freshness.carried_forward_from_run_id`. The independently evaluated freshness status MAY be `valid_unchanged` or `stale` according to the existing cadence window. The Producer SHALL NOT rewrite carried item bytes merely to add context. The next complete current slice that replaces that legacy slice SHALL require context on every affected-domain item it contains; partial, failed, or blocked work SHALL NOT be used as a migration trigger or fallback.

#### Scenario: Newly generated affected-domain item is valid
- **WHEN** a supported Provider produces a valid new `news`, `macro_release`, or `policy` item
- **THEN** item admission and publication require its matching valid semantic context

#### Scenario: Required mapping fails
- **WHEN** an affected-domain item cannot produce a complete valid context from its normalized evidence and closed mapping
- **THEN** the item is rejected and existing Provider completeness and pipeline publication rules determine the failed or partial outcome

#### Scenario: Existing domain classification is preserved
- **WHEN** BLS or an unstructured NBS release is normalized under its current Provider contract
- **THEN** the item remains `news` and receives news context rather than being reclassified as `macro_release`

#### Scenario: Unaffected domain adds context
- **WHEN** a positioning or filing item contains `semantic_context`
- **THEN** validation rejects the item as outside the ECO-130 domain boundary

#### Scenario: Legacy slice is carried unchanged
- **WHEN** a fully validated pre-ECO-130 affected-domain slice remains eligible for existing whole-slice carry-forward and records non-null `carried_forward_from_run_id`
- **THEN** the Producer preserves its contextless item bytes and prior-run provenance rather than rewriting source evidence during migration

#### Scenario: Carried legacy slice ages to stale
- **WHEN** a contextless carried legacy slice from a scheduled or weekly Provider passes beyond its declared validity window while complete current acquisition still establishes no changed observation
- **THEN** the slice remains byte-identical with non-null `carried_forward_from_run_id`, its freshness becomes `stale`, and context omission alone does not change existing Provider completeness or pipeline publication status

#### Scenario: Current slice replaces a legacy slice
- **WHEN** complete current acquisition selects a new or changed affected-domain slice after a contextless legacy slice
- **THEN** every selected current item contains valid semantic context and the legacy omission is not propagated into the replacement

### Requirement: Semantic context participates in canonical Feed identity

The complete validated `semantic_context` SHALL participate in canonical item bytes, domain artifact bytes, the logical Feed semantic projection, `content_digest`, and cutoff-derived `run_id`. Repeated generation from identical validated evidence and mapping rules SHALL preserve identical context, canonical ordering, artifact bytes, digest, and run identity. Changing any retained semantic-context fact at the same cutoff SHALL change canonical item content and Feed identity while the existing source-derived item `id` remains unchanged.

No execution observation, mapping diagnostic, internal numeric-fact object, or non-published extraction state SHALL enter the semantic projection. Existing deterministic global item ordering by `(source.knowledge_available_at, id)`, domain artifact ordering, publication, snapshot selection, and carry-forward rules SHALL remain unchanged.

#### Scenario: Same evidence is regenerated
- **WHEN** identical Provider fixtures are processed repeatedly with the same cutoff and fixed mappings
- **THEN** semantic contexts, canonical item/artifact bytes, `content_digest`, and `run_id` are identical

#### Scenario: One context fact changes
- **WHEN** a source-supported subject, category, period, observation, revision, issuer, action, date, or scope fact changes at the same cutoff
- **THEN** the item ID remains source-derived while canonical item content, `content_digest`, and `run_id` reflect the changed evidence

#### Scenario: Only input order changes
- **WHEN** equivalent source maps, entity candidates, numeric facts, or affected scopes arrive in another order
- **THEN** total ordering and duplicate rules produce the same canonical Feed bytes and identity

### Requirement: Feed v4 retains bounded legacy reads across semantic-context activation

New production SHALL continue to emit Feed `schema_version = 4`. The current consumer SHALL accept an otherwise valid previously published v4 bundle whose `news`, `macro_release`, and `policy` items predate ECO-130 and omit `semantic_context`. When `semantic_context` is present on an affected legacy or current item, the consumer SHALL validate its entire closed shape and consistency with the item; it SHALL NOT ignore malformed, mismatched, unknown, or analytical context.

This bounded omission compatibility SHALL apply only to reading legacy v4 evidence and to the exact non-null `carried_forward_from_run_id` exception above, including carried `valid_unchanged` and `stale` slices. Newly acquired or replacement affected-domain items SHALL still require context before publication, and no Provider contract-version bump or hash-based behavior selection SHALL be introduced to distinguish old and new items.

#### Scenario: Legacy v4 item omits context
- **WHEN** the current consumer reads an otherwise valid previously published v4 bundle containing an affected-domain item without `semantic_context`
- **THEN** validation accepts the legacy omission under the bounded read path

#### Scenario: Present legacy context is malformed
- **WHEN** any v4 affected-domain item contains `semantic_context` with a mismatched domain, inconsistent payload fact, unknown member, or forbidden analytical meaning
- **THEN** validation rejects the bundle rather than treating context as optional untyped metadata

#### Scenario: New production omits context
- **WHEN** the current Producer attempts to publish a newly acquired or replacement affected-domain item without `semantic_context`
- **THEN** pre-publication validation fails even though the bounded consumer path can read a legacy omission
