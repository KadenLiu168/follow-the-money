# Change: restore-feed-production-state

## Why

Commit `139a0b0` ("Archive simplify-to-feed-only-skill change", 2026-09-10) committed a
locally generated `.feed-state/` runtime state and a synthetic `feeds/` product to
`main`, overwriting the real GitHub Hosted Runner production state. Since then every
`generate-feed` run fails during `prepare` with `rate registry root_identity is
inconsistent` — the fail-closed check correctly rejecting a registry whose
`root_identity` is `/Users/kaden/...` instead of the runner path. Beyond
`root_identity`, the contamination also rolled back production continuity
(checkpoint `previous_success` from 2026-09-08 to 2026-08-10), rolled back rate
dispatch/refill state, replaced the real lease with a synthetic success, and replaced
the last trusted production Feed (v3, evidence cutoff 2026-09-08) with a v4 bundle
whose evidence cutoff regressed to 2026-08-10. The last trusted production runtime
state is commit `f7095a5` ("feeds: failure").

The originally proposed v3 → v4 migration recovery is structurally infeasible and is
dropped: `migrate_feed()` preserves the v3 Provider outcomes but validates them under
the current target contracts, and ECO-124 (commit `c8d712d`, after the trusted
baseline) changed cftc's `empty_valid_for_window` to `false`. The v3 production
bundle records cftc (and six other Providers) as `state=empty` with
`availability=success`, so the migrated product fails closed on
`availability=success disagrees with Provider outcome`; even bypassing that, cftc
would leave `cftc_positioning` coverage deficient, producing a `failure` pipeline
that `publish_bundle()` refuses to publish. This behavior is the accepted spec
semantics (the resolved Provider contract is the sole authority for
`empty_valid_for_window`); it is pinned by tests, not changed.

## What Changes

- Restore `.feed-state/` verbatim from `f7095a5`: real checkpoint (previous_success
  2026-09-08), real terminal-failure lease (`deployment_run_id: 34438934934-1`,
  recovery boundary already elapsed), real RateRegistry (`root_identity` =
  `/home/runner/work/follow-the-money/follow-the-money/.feed-state`), and the four
  real rate scope states including `yahoo_market`.
- Empty `feeds/` by deleting the contaminated Aug-10 v4 generation. The v3 bundle is
  NOT restored as a migration input: with no active product, `prepare_deployment()`
  takes the normal armed path directly, and the published v3 Feed remains available
  in git history at `f7095a5`.
- Recovery runs as ONE manually dispatched `generate-feed` run: `prepare` returns
  `mode=armed` (restored lease is terminal, run id differs), then the workflow's
  normal `collect` → `finalize` executes. Planning continues from the restored
  checkpoint (2026-09-08); the gap exceeds the configured maximum, so the run uses
  the bounded bootstrap lookback (only the most recent 72 hours are fetched) and
  records the uncovered 2026-09-08 → `window.start` interval as an explicit
  coverage gap, per the accepted fixed-advancing-window semantics.
- Add focused deployment-level regression tests that pin existing specified
  behavior against fixtures extracted from the real `f7095a5` production state:
  armed preparation from restored state with checkpoint continuity, the bounded
  72h window with explicit gap warning, fail-closed rejection of the real v3
  bundle as a migration input, retained rate scope continuity, `root_identity`
  fail-closed semantics, and tolerance of the obsolete `yahoo_market` registered
  scope.

No production source code changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change restores durable production state and adds regression coverage for
behavior that is already specified and accepted (fixed advancing Feed window with
bounded bootstrap lookback and coverage-gap reporting, deployment preflight
fail-closed classification, rate-state fail-closed validation in
`openspec/specs/feed-evidence-pipeline/spec.md`). No requirement text changes, so
this change sets `skip_specs: true`.

## Impact

- `.feed-state/feed-checkpoint.json`, `.feed-state/feed-run-lease.json`,
  `.feed-state/rate-registry.json`, `.feed-state/scope-*.json`: restored to the
  exact `f7095a5` blobs (including re-adding `.feed-state/scope-3b806f91752a2756.json`
  for the tolerated obsolete `yahoo_market` scope).
- `feeds/`: emptied — the contaminated `d2125e4e...` v4 generation files are deleted
  and no v3 bundle is restored; the directory contains no manifest until the first
  successful armed run publishes a fresh v4 product.
- `tests/test_feed_deployment.py` (and extracted production-state fixtures): new
  regression tests; no changes to `src/`.
- `.github/workflows/generate-feed.yml`: unchanged.
- Runbooks (`docs/runbooks/`): updated with the one-step manual recovery procedure
  if the existing text does not already cover dispatch-triggered recovery runs.

## Non-goals

- No v3 → v4 migration run. The bounded 72h bootstrap window leaves the
  2026-09-08 → `window.start` interval as an explicit coverage gap.
- No CI anti-regression guards (checkpoint monotonicity, cutoff regression guards,
  generated-state push protection, base-to-head semantic validation) — that is
  Change 2 (`guard-feed-generated-state`).
- No removal of the obsolete `yahoo_market` registered scope. Current validation
  already tolerates registered scopes without a configured policy; explicit scope
  deregistration is deferred to Change 2.
- No GitHub Actions historical run cleanup.
- No NBS/BLS Provider fixes; if the recovery run fails at Provider work, that is a
  new independent failure.
- No weakening, bypassing, or auto-rewriting of the `root_identity` fail-closed
  check; no hard-coded `/home/runner` substitution; no `.feed-state` deletion and
  re-bootstrap; no whole-repository revert to `f7095a5`.
