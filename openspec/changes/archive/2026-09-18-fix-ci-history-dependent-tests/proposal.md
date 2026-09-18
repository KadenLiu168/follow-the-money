## Why

The production-state regression tests in `tests/test_feed_deployment.py` intentionally materialize their trusted fixtures from real Git blobs of history commit `f7095a5` (the last Hosted-Runner production state before the workspace was contaminated). However, the `CI Quality Gate` workflow's `test` job uses `actions/checkout@v4` without `fetch-depth`, which defaults to a shallow checkout (`fetch-depth: 1`). The GitHub Hosted Runner therefore cannot resolve `f7095a5`, and every regression test fails with:

```text
git ls-tree --name-only f7095a5:.feed-state
fatal: Not a valid object name f7095a5:.feed-state
```

CI runs #39–#42 have all failed this way. The test contract requires access to `f7095a5`; the CI environment provides only the current commit. This change realigns the two without touching test or production semantics.

## What Changes

- Add `fetch-depth: 0` to the `test` job's `actions/checkout@v4` step in `.github/workflows/ci-quality-gate.yml`, giving the job full repository history so the regression tests can read the trusted production baseline commit `f7095a5`.
- No other change. In particular, `classify_generated_state` keeps its existing behavior (it already uses `fetch-depth: 0`), and no test, production code, or other workflow is modified.

## Capabilities

This change introduces no new capability and modifies no existing requirement. It is a CI execution-environment fix that aligns the hosted test runner with an existing test contract; the five-domain evidence Feed and all externally observable product behavior are unchanged.

Per the task definition, this change sets `skip_specs: true` in `.openspec.yaml`: no spec-level behavior changes, so no spec delta is written.

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- `.github/workflows/ci-quality-gate.yml`: `test` job checkout gains `fetch-depth: 0` (the only functional diff).
- CI cost: the repository is small (≈130 commits, near-zero pack size), so full-history checkout cost is negligible.
- No impact on `src/`, `tests/`, `config/`, `providers/`, `schemas/`, `scripts/`, `.feed-state/`, `feeds/`, or `generate-feed.yml`.
