## 1. Code change

- [x] 1.1 In `lib/enrich/normalize-value-units.js`, add an idempotency guard after the `explicitlySmall` short-circuit and before the `sum` computation: `if (entry.valueUnitAdjusted === true) return entry;`. (Per design Decision 1.)
- [x] 1.2 In `lib/enrich/normalize-value-units.js`, expand the file header Heuristic block to state explicitly: "Idempotent: an entry with `valueUnitAdjusted === true` is returned unchanged." (Per design Decision 2.)
- [x] 1.3 In `lib/enrich/period-diff.js`, update the comment block at lines 8-13 to reference `openspec/specs/value-units-normalization` instead of asserting "normalizeValueUnits is idempotent, so this is a no-op". (Per design Decision 2.)
- [x] 1.4 In `scripts/prepare-digest.js`, update the comment at lines 47-48 to remove the "Idempotent for already-normalized entries" sentence and reference the new spec instead. (Per design Decision 2.)

## 2. Test matrix

- [x] 2.1 In `tests/enrich/normalize-value-units.test.js`, add a test case `'keeps already-normalized entry unchanged (idempotency on raw sum < $1M)'`. Construct an entry with raw sum < $1M (e.g., Baupost-style shape from the existing test on line 36, but with raw sum $500K), call `normalizeValueUnits` twice, and assert the second call's `holdings[].valueUsd` equals the first call's output (no further ×1000), `valueUnit === 'thousands'`, `valueUnitAdjusted === true`. (Per design Decision 3.)
- [x] 2.2 In `tests/enrich/period-diff.test.js`, add an end-to-end test using ARK 2017-06-30 / 2017-09-30 shapes: build a current entry and a raw prior, pre-normalize the prior once, pass `normalizedFeed` to `periodDiff`, and assert `priorTotalValueUsd` equals the once-normalized prior sum and `deltaPct` is a sensible small positive number (not -99% or similar). This locks in the realistic bug-fix scenario.
- [x] 2.3 Run the full test suite (`npm test` or `npx vitest run`) and confirm no regressions in `tests/enrich/`.

## 3. Verification against the bug

- [x] 3.1 Re-run the reproduction script from the explore session (ARK 2017-09-30 vs 2017-06-30, raw sum $513,594). Confirm `priorTotalValueUsd === 513,594,000` (not $513,594,000,000) and `deltaPct ≈ +0.5952` (sign and magnitude both restored).
- [x] 3.2 Run `scripts/prepare-digest.js` once with `--lookback 3650` to include ARK's early periods in `f13Filtered`. Inspect the output and confirm ARK's `summary.deltaPct` for current period 2017-09-30 (or any 2017-12-31 current whose prior is in the bug zone) is in a reasonable range, not sign-flipped.
- [x] 3.3 Spot-check that filers whose raw sum ≥ $1B after first call (e.g., ARK 2023+, Baupost 2017+) still produce `valueUnit: 'dollars'` and unchanged holdings — i.e., the ≥$1B natural short-circuit path is not disturbed.

## 4. Archive

- [ ] 4.1 After all of the above pass, run `openspec archive fix-normalize-value-units-idempotency` to move the change (including its spec) into `openspec/changes/archive/` and surface the new `value-units-normalization` capability into `openspec/specs/`.