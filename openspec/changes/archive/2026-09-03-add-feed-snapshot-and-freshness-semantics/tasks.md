## 1. Provider Cadence Contract

- [x] 1.1 Add focused RED tests for the closed cadence/reference/window combinations, missing and unknown fields, no inferred defaults, and resolved/embedded parity; then replace the opaque Provider freshness string with the structured immutable contract and verify `.venv/bin/python -m pytest tests/test_provider_contract.py tests/test_config_provider_normalization.py` passes.
- [x] 1.2 Update every existing enabled Provider manifest with source-supported `cadence`, `reference_time`, and required `valid_for_seconds` values without activating any Provider or adding a Feed lookup table; verify static configuration loading and checked-in Provider contract tests pass.

## 2. Freshness Schema and Evaluation

- [x] 2.1 Add focused RED schema tests, then advance new logical/manifest production to the freshness-capable major with required closed outcome freshness fields while retaining preceding-major reads and the unchanged domain-artifact/evidence payload schema; verify both supported-major fixtures and invalid status/nullability combinations through the Feed schema tests.
- [x] 2.2 Add the minimum pure payload/source reference-time mapping and cadence evaluator using the fixed cutoff and resolved Provider contract; verify deterministic tests cover weekly daily checks, scheduled unchanged data, event-driven unchanged data, fresh observations, expired market-session observations, missing/ambiguous/future reference times, and invariance to retrieval/generated timestamps.

## 3. Validated Snapshot Selection

- [x] 3.1 Load the active manifest-led bundle only as an optional post-acquisition input through the existing full validator, partition its evidence by `provider_id`, and verify missing, preceding-major, corrupt, failed, mixed, or identity-invalid active products never become a window/checkpoint authority or hidden fallback.
- [x] 3.2 Add deterministic canonical current-versus-prior Provider-slice selection without a new store or history merge; verify new identities and same-ID semantic revisions replace the prior slice, unchanged complete acquisition carries exact prior items, item IDs/source times/provenance/lineage and origin contract hash are preserved, and input/order permutations produce identical output.
- [x] 3.3 Preserve the existing source-completeness gate before carry-forward; verify failed, partial, skipped, non-permitted-empty, missing, duplicate, ambiguous, and identity-mismatched current outcomes receive `not_evaluated`, cannot select prior evidence, exit non-zero, do not publish, do not advance the checkpoint, and leave the active bundle unchanged.

## 4. Feed Assembly, Identity, and Consumption

- [x] 4.1 Integrate selected Provider slices and freshness objects into Feed assembly, canonical ordering, semantic validation, `content_digest`, `run_id`, bundle split/reconstruction, and dry-run candidates; verify audit-only `retrieved_at`/`generated_at` changes do not change semantic identity while freshness/origin/carry-forward changes do.
- [x] 4.2 Extend manifest-first consumption and first-run compatibility so a fully validated preceding-major active bundle may seed a new-major slice while new production emits only the new major; verify `fresh`, `valid_unchanged`, `stale`, `no_snapshot`, and `not_evaluated` remain explicit without changing Provider completeness, pipeline status, atomic publication, or checkpoint ownership.
- [x] 4.3 Run the focused Feed boundary, bundle, determinism, pipeline, CLI, checkpoint, deployment-separation, and deployment tests and repair only ECO-77 regressions: `.venv/bin/python -m pytest tests/test_feed_boundary.py tests/test_feed_bundle.py tests/test_feed_determinism.py tests/test_feed_pipeline.py tests/test_feed_cli.py tests/test_feed_checkpoint.py tests/test_feed_deployment_separation.py tests/test_feed_deployment.py`.

## 5. Truthful Contract Documentation

- [x] 5.1 Update `docs/feed-contract.md`, `docs/configuration.md`, schema references, README/SKILL text that describes Feed timestamps or freshness, and deterministic fixtures/examples so they distinguish observation/effective, source publication/update, retrieval/check, and generation time and state that carry-forward never masks Provider failure; verify scoped repository searches expose no stale opaque-policy or timestamp-refresh claim.

## 6. Acceptance Gates

- [x] 6.1 Run `openspec doctor`, `openspec validate add-feed-snapshot-and-freshness-semantics --strict`, and `openspec validate --all --strict`; resolve every contract validation failure.
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py` and `git diff --check`, and verify the canonical repository gate passes without a real-network Feed dry run, new Provider activation, unrelated changes, archive, commit, or push.
