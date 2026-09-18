# Design: restore-feed-production-state

## Context

See `proposal.md` for motivation. The facts this design builds on were verified
against the repository on 2026-09-18:

| Durable fact | Trusted baseline `f7095a5` | Contaminated `HEAD` (from `139a0b0`) |
|---|---|---|
| registry `root_identity` | `/home/runner/work/follow-the-money/follow-the-money/.feed-state` | `/Users/kaden/follow-the-money/.feed-state` |
| checkpoint `previous_success.evidence_cutoff_at` | `2026-09-08T04:50:10.689Z` | `2026-08-10T17:00:00.000Z` |
| lease | `deployment_run_id: 34438934934-1`, `state: failure`, recovery elapsed | `20260910-generated-state-1`, `state: success` |
| rate scopes | 4 registered (incl. `yahoo_market`), dispatch state at 2026-09-10 | 3 registered, dispatch state rolled back to 2026-08-10 |
| `feeds/` product | v3, eight domains, cutoff 2026-09-08 | v4, five domains, cutoff 2026-08-10 |

Additional constraints established during exploration and implementation:

- No commit after `139a0b0` has touched `.feed-state/`; the restore surface for the
  runtime state is exactly `f7095a5`'s content for `.feed-state/`.
- Current provider manifests map all eight providers to exactly three rate scopes
  (`us_gov`, `china_gov`, `sec_edgar`). Their capacity/refill/interval values and
  registry policy fingerprints are identical between `f7095a5` and current config,
  so the restored registry passes `_validate_existing_state` on the runner.
  `yahoo_market` is the only registered scope without a current policy.
- **The v3 → v4 migration path is structurally infeasible for this bundle** and is
  dropped. Verified by running the real `f7095a5` blobs through
  `prepare_deployment()` (fixture tests): `migrate_feed()` preserves the v3
  Provider outcomes (seven Providers `state=empty`, `availability=success`) but
  validates the migrated product under the current target contracts, and ECO-124
  (commit `c8d712d`, after the baseline) changed cftc's `empty_valid_for_window`
  to `false`. The migration fails closed with `availability=success disagrees with
  Provider outcome`; even bypassing that, cftc would leave `cftc_positioning`
  coverage deficient, producing a `failure` pipeline that `publish_bundle()`
  refuses. This is accepted spec semantics (the resolved Provider contract is the
  sole authority for `empty_valid_for_window`), so the recovery avoids the
  migration branch instead of changing it.
- With no active product in `feeds/` (no manifest), `prepare_deployment()` on
  established state takes the normal armed path directly; the workflow's `collect`
  is gated on `mode == 'armed'`, so a single dispatch runs the full
  prepare → collect → finalize recovery.
- `plan_window()` (accepted fixed-advancing-window semantics) handles the ~10-day
  checkpoint gap by design: a gap beyond the configured maximum uses the bounded
  bootstrap lookback (72 hours) and records the uncovered interval as an explicit
  coverage-gap warning. Only the most recent 72 hours are fetched; the
  2026-09-08 → `window.start` interval remains an explicit historical gap.
- `RateRegistry` has no scope-deregistration API, and `_validate_existing_state`
  deliberately skips policy checks for registered scopes that have no current
  policy (obsolete scopes are tolerated).

## Goals / Non-Goals

**Goals:**

- Make `generate-feed` pass `prepare` again on the GitHub Hosted Runner with the
  real production continuity (checkpoint, lease, rate state) from `f7095a5`.
- Complete the recovery with ONE manually dispatched armed run that publishes a
  fresh v4 product, advancing the checkpoint from the 2026-09-08 baseline while
  recording the historical coverage gap explicitly.
- Pin the recovery-critical behavior with deployment-level regression tests that
  use fixtures extracted from the real `f7095a5` production blobs.

**Non-Goals:**

- Everything listed in the proposal's Non-goals (no migration run, no CI guards,
  no `yahoo_market` scope removal, no run-history cleanup, no NBS/BLS fixes, no
  `root_identity` weakening).
- No changes to `src/` production code, schemas, or configuration.

## Decisions

### D1: Runtime-state restoration is a pure git-level state replacement

`git restore --source=f7095a5 -- .feed-state` restores the real production runtime
state verbatim. Acceptance: `git diff f7095a5 -- .feed-state` is empty after the
restore commit.

Alternative rejected: a checked-in reconciliation script. The restore is a one-time
operation whose audit trail is the restore commit itself; a script would be a second
recovery mechanism the architecture boundary does not want.

### D2: The obsolete `yahoo_market` scope is tolerated, not removed (user decision D1=B)

The restored registry intentionally keeps `yahoo_market` and its scope file
`.feed-state/scope-3b806f91752a2756.json`. Removing it would require a new
`RateRegistry` deregistration API (none exists) and a new migration semantic;
current validation already tolerates registered scopes without a configured
policy. Explicit deregistration is deferred to Change 2.

Consequence: the restore commit must re-add the `yahoo_market` scope file — a
registry expecting four scope files with only three on disk fails closed with
"rate scope files are missing/partial or orphaned" (covered by Test D).

### D3: `feeds/` is emptied; the recovery is a single armed run (user decision, revises the original migration-based D3/D5)

The contaminated `d2125e4e...` v4 generation is deleted and the v3 bundle is NOT
restored: with no active product, `prepare_deployment()` classifies established
state, validates it, and returns `mode=armed` directly — the first manual
`workflow_dispatch` after the restore commit runs the full
prepare → collect → finalize recovery. Planning reads the restored checkpoint
(2026-09-08) as the sole continuity authority; the over-threshold gap yields the
bounded 72-hour bootstrap window plus an explicit gap warning for
`[2026-09-08T04:50:10.689Z, window.start)`. The published v3 Feed remains
available in git history at `f7095a5`.

Alternatives rejected:

- Restoring the v3 bundle as a migration input: structurally infeasible under the
  current accepted contracts (see Context); the migration branch fails closed.
- Running the migration locally and committing its v4 output: would fabricate a
  production `root_identity` and product outside the approved deployment path.
- Changing `migrate_feed()` semantics or reverting the cftc manifest: both are
  accepted-contract changes outside this restore's scope.

### D4: Test coverage is deployment-level against real extracted fixtures (user decision D3=a)

Tests use fixture state extracted from the `f7095a5` git blobs (checkpoint, lease,
registry, all four scope files, and the v3 manifest/artifact set for the
fail-closed test), with `root_identity` rewritten to the fixture's `tmp_path` root
**inside the test builder only** — production restores never rewrite
`root_identity`. Fixture provenance (source commit and the rewrite rule) is
documented in the fixture builder.

Alternative rejected: git-history-based base→head validation in CI — that is
Change 2's anti-regression scope.

### D5: One manual dispatch with a post-run verification gate (user decision, revises the original two-dispatch plan)

1. Dispatch `generate-feed` (workflow_dispatch) → armed run → collect → finalize.
2. Verify the pushed result: `feeds/feed-manifest.json` is v4, five-domain, with a
   cutoff advancing from the 2026-09-08 baseline; the plan recorded the bounded
   72-hour window with the explicit coverage-gap warning;
   `.feed-state/` retains the real state until finalize advances the checkpoint
   (lease back to terminal, checkpoint at the new cutoff). If collect fails, the
   failure must be a new, real Provider/runtime error, not state contamination.

## Test plan (deployment-level, `tests/test_feed_deployment.py`)

| Test | Assertion | Spec/behavior pinned |
|---|---|---|
| A | Real-fixture state + no product → `prepare` returns `mode=armed`; the restored checkpoint (2026-09-08 cutoff) is preserved through preparation; the lease re-arms | Checkpoint is the sole continuity authority; fail-closed preflight |
| A′ | Real checkpoint cutoff + current cutoff → `plan_window` yields the bounded 72h bootstrap window with the explicit gap warning `[2026-09-08, window.start)` | Fixed advancing window: over-threshold gap handling |
| B | The real v3 bundle present as active product → `prepare` fails closed with the typed migration error | Resolved contract is the sole `empty_valid_for_window` authority; migration input rejection |
| C | Retained scopes (`us_gov`, `china_gov`, `sec_edgar`) keep their real `last_dispatch_wall` / `refill_wall_anchor` through preparation (not reset to bootstrap defaults) | Rate-state fail-closed validation; no second rate model |
| D | A registered scope without a current policy (`yahoo_market`) is tolerated; its scope file is required and preserved | Existing tolerance semantics (regression pin for D2) |
| E | `root_identity` equal to the runtime root's `resolve()` passes; any mismatch fails closed with the existing typed error | Fail-closed registry validation |
| F | A current v4 active product is treated as current (no migration branch); the migration branch is entered only for `schema_version == 3` | Previous-major read-compatibility is migration-only |

## Risks / Trade-offs

- [Local machines cannot run `prepare` against the restored state — `root_identity`
  mismatches `/Users/kaden/...` and fails closed] → This is the intended safety
  boundary. Local verification is limited to the fixture-based tests plus the
  quality gate; end-to-end verification happens on the runner (D5 gate).
- [Restored rate states are stale; token refill arithmetic on the collect grants
  full tokens] → Correct continuity semantics: refill is derived from the real
  anchors, not reset. Not a regression.
- [The first armed run publishes a product that skips the 2026-09-08 →
  `window.start` interval] → Accepted: the gap is recorded explicitly as a
  coverage-gap warning per accepted semantics; the alternative (migration) is
  infeasible. The v3 product remains retrievable from git history.
- [Recovery run pushes a bot commit to `main`] → The push contains only
  `.feed-state/` and manifest-inventoried `feeds/` paths, which the accepted
  CI-exclusion requirement already covers.
- [The armed run could fail at Provider work (e.g., NBS/BLS)] → Failure is typed
  and diagnosable via the existing diagnostics step; the restore commit is a
  normal commit and can be reverted to retry.

## Migration Plan

1. Land the restore commit (D1 + D3) plus tests and any runbook update.
2. Verify locally: `pytest` (focused, then full), `ruff`, `mypy`,
   `scripts/quality_gate.py`, `openspec validate --strict`.
3. Push; confirm CI path-exclusion applies to the restore commit's changed paths.
4. Dispatch `generate-feed` once (armed run); apply the D5 verification gate.
5. Rollback strategy: `git revert` of the restore commit restores the pre-change
   tree (the contaminated state), which is no worse than today; the real
   recovery inputs (`f7095a5` blobs) are immutable in git history.

## Open Questions

None.
