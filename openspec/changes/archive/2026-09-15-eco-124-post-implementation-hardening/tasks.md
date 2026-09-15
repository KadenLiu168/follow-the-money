## 1. Baseline and SEC exact-form boundary

- [x] 1.1 Run the existing focused baseline with `.venv/bin/python -m pytest tests/test_sec_13f.py tests/test_adapters.py tests/test_feed_freshness.py tests/test_cftc_cot.py -q` and record any pre-existing failure before changing implementation.
- [x] 1.2 Extend `tests/test_sec_13f.py` with separate regressions for newer `13F-HR/A` after an exact `13F-HR`, amendment-only input, and both input permutations; verify exact candidate identity is stable and amendment-only raises `SchemaError`.
- [x] 1.3 If and only if Task 1.2 fails because production selection is non-exact, make the minimum correction in `src/follow_the_money/providers/sec_13f.py` (and adapter call site only if required), then verify `.venv/bin/python -m pytest tests/test_sec_13f.py -q` passes; otherwise leave production code unchanged.

## 2. SEC complete Provider slice regression

- [x] 2.1 Add `tests/test_sec_snapshot_slice.py` with deterministic A-H prior/current SEC-v2 slices where only A changes; verify the selected candidate still contains exactly A-H, uses the complete current slice, and does not perform company-level merge or drop B-H.
- [x] 2.2 Add a partial-acquisition case with one configured watched CIK absent; verify the SEC outcome becomes partial/failed with `not_evaluated` freshness, pipeline publication is rejected, and prior SEC items are not used to make the candidate publishable.
- [x] 2.3 If Tasks 2.1-2.2 expose a defect, fix only the existing SEC acquisition aggregation or configured-CIK completeness boundary and verify `.venv/bin/python -m pytest tests/test_sec_snapshot_slice.py tests/test_adapters.py tests/test_feed_cli.py tests/test_feed_freshness.py -q` passes; do not add company-level behavior to `src/follow_the_money/feed/snapshot.py`.

## 3. CFTC complete deterministic acquisition

- [x] 3.1 Extend `tests/test_cftc_cot.py` with a generated 150-market report and row-order permutations; verify every market enters normalization/comparison and canonical semantic output is identical for equivalent complete universes.
- [x] 3.2 Add adapter-level v2 pagination regressions using generated pages for more than 100 rows in both selected dates; verify deterministic offsets/order, all rows retained, and equivalent valid page partition/input grouping produces identical normalized canonical bytes or digest.
- [x] 3.3 Add adapter-level failure coverage for a missing/failing required continuation page and invalid swapped/repeated page ranges; verify acquisition raises typed failure before normalization and no partial semantic comparison is produced.
- [x] 3.4 If Tasks 3.1-3.3 expose truncation or incomplete termination, make the minimum fix in the existing CFTC v2 acquisition path in `src/follow_the_money/providers/adapters.py`, preserving fixed ordering, bounds, per-send management, and fail-closed behavior; verify `.venv/bin/python -m pytest tests/test_cftc_cot.py tests/test_adapters.py tests/test_cftc_activation.py -q` passes.

## 4. Trust-contract and scope verification

- [x] 4.1 Run the combined focused regression suite for SEC selection, SEC slice lifecycle, CFTC core, adapters, Feed CLI/boundary/freshness/determinism, and bundle publication; verify completeness, provenance, freshness, canonical identity, deterministic ordering, and non-exempt partial outcomes remain fail closed.
- [x] 4.2 Review the final diff and verify every production edit is justified by a failing regression; confirm no `snapshot.py` company merge, ECO-125 abstraction, schema/manifest/domain change, editorial logic, ranking, Digest behavior, LLM runtime, credential path, or unrelated refactor was introduced.
- [x] 4.3 Run `uv run python scripts/quality_gate.py` and verify unit, integration, regression, determinism, and workflow checks all pass.
- [x] 4.4 Run `openspec doctor`, `openspec validate eco-124-post-implementation-hardening --strict`, and `openspec validate --all --strict`; verify all planning and accepted contracts validate before completion.
