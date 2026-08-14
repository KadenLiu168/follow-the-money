## 1. Deterministic RED Coverage

- [x] 1.1 Add provider-completion permutation tests covering healthy, failed, and skipped outcomes; assert stable `provider_id` ordering, semantic projection, `content_digest`, and `run_id`.
- [x] 1.2 Add item-permutation tests for exact-URL and same-source near duplicates; assert identical survivor, dropped IDs, `source_lineage`, final item order, projection, digest, and run ID.
- [x] 1.3 Add an injected-clock lifecycle test with distinct collection-start, cutoff, provider-return, collection-completion, and envelope-generation instants; assert exact timestamp sources and ordering and reject synthetic offset/reused timestamps.
- [x] 1.4 Add literal legacy and semantic identity vectors plus mutations proving runtime timestamps do not change semantic identity while each semantic projection member does.
- [x] 1.5 Add canonical-Feed-byte and publication regression tests for same semantic identity with different audit timing, latest recovery from retained dated bytes, and semantic mismatch failure.

## 2. Stable Collection and Item Normalization

- [x] 2.1 Initialize and aggregate provider outcomes by stable provider identity without serializing worker completion order, then emit exactly one planned outcome in ascending `provider_id` order.
- [x] 2.2 Centralize the `(source.knowledge_available_at, id)` item key and apply it before grouping/comparison, survivor selection, dropped-ID production, lineage merge, and final Feed ordering.
- [x] 2.3 Canonicalize other set-like semantic members by their declared stable identities and make all provider/item permutation tests pass without changing provider concurrency or acquisition behavior.

## 3. Truthful Lifecycle and Semantic Identity

- [x] 3.1 Capture real collection start, cutoff, provider return, collection completion, and Feed generation instants in orchestration and pass them explicitly into the builder; remove cutoff offsets and copied/synthetic timestamps.
- [x] 3.2 Implement the allowlisted semantic projection with ordered semantic provider outcomes, embedded producer/config/schema/provider contracts, normalized items, and structured pipeline status while excluding execution audit metadata.
- [x] 3.3 Recompute and validate `content_digest` and cutoff-derived `run_id` from the semantic projection, retaining an exact legacy whole-envelope read path for already-published supported-major artifacts and writing no new legacy identities.
- [x] 3.4 Strengthen semantic validation for stable outcome/item ordering and `collection_started_at <= evidence_cutoff_at <= non-null retrieved_at <= collection_completed_at <= generated_at`, including null retrieval for work with no observed response.
- [x] 3.5 Replace Feed artifact JSON serialization with shared `canonical_bytes()` and verify every candidate admitted to publication is its canonical byte representation; leave unrelated JSON paths unchanged.

## 4. Semantic Publication Idempotency

- [x] 4.1 On an existing dated path, validate canonical stored Feed identity and treat matching semantic `run_id`/`content_digest` as idempotent even when excluded audit bytes differ; retain the stored immutable bytes.
- [x] 4.2 Repair or replace `latest.json` for an idempotent run from the retained dated bytes, preserving byte equality between dated/latest views and existing monotonic ownership rules.
- [x] 4.3 Keep invalid existing artifacts and same-path semantic mismatches fail-closed, and rerun deadline, create-only, atomic replacement, recovery, `fsync`, and equal-cutoff ownership mutation coverage to prove durability architecture is unchanged.

## 5. Verification and Contract Alignment

- [x] 5.1 Update Feed identity/serialization documentation and schema-semantic comments to describe semantic digest versus execution audit metadata without changing the schema major or unrelated contracts.
- [x] 5.2 Run focused Feed gates with `.venv/bin/python -m pytest -q tests/test_dedupe.py tests/test_feed_boundary.py tests/test_feed_pipeline.py tests/test_gate_13_1.py tests/test_gate_13_2.py tests/test_no_llm_contract.py` and resolve all failures.
- [x] 5.3 Run `.venv/bin/python scripts/quality_gate.py` and require the full test, Ruff lint/format, and mypy gates to pass.
- [x] 5.4 Run `openspec validate make-feed-deterministic-and-truthful --strict` and `openspec validate --all --strict`; confirm the implementation changes only the authorized Feed pipeline, tests, schema-semantic documentation, and this Change's task checkboxes.
