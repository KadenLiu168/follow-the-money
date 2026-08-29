# Runbooks (English)

## Configuration

```bash
uv sync --frozen --all-groups
```

The deterministic engine is credential-free: no API key or model is ever
required. The repository reads explicit `--config` / `--output-root` paths and
never reads `~/.follow-the-money/config.json` implicitly.

## Feed generation

```bash
# Dry run (no publication):
uv run python -m follow_the_money.feed.cli --dry-run
# or: scripts/feed/follow-the-money-feed --dry-run

# Real local run with the repository output root:
uv run python -m follow_the_money.feed.cli --output-root feeds \
  --status-file feed-status.json
```

Exit `0` for a healthy or degraded Feed (warnings on stderr/status), `1` for
generation/publication failure, `2` for usage/config. No credential is
required.

## GitHub deployment

`generate-feed.yml` is active on GitHub-hosted `ubuntu-latest`, at `20 0 * * *`
(08:20 Asia/Shanghai), and through `workflow_dispatch`. The workflow uses
`feeds/` for both Feed output and repository-backed RateRegistry state. Its
runtime cutoff is captured after the job starts; 08:20 is only the schedule.

Before declaring it operational, verify repository Actions `contents: write`
and branch policy permit the workflow identity to make ordinary fast-forward
commits to `main`.

### First bootstrap and recovery

1. Disable any prior external scheduler before the first
   bootstrap; do not import unverifiable state.
2. Dispatch `generate-feed.yml` manually. Static configuration and resolved
   Provider contracts are checked first. A clean repository creates only the
   RateRegistry marker, registry, exact scope files, and a `bootstrap` lease;
   it makes zero Provider requests and publishes that state with a normal
   fast-forward commit.
3. Read `feeds/feed-run-lease.json` and wait until `recovery_not_before`.
   A run before that boundary fails closed without resetting state.
4. Dispatch the workflow again. It publishes `in_progress` and all required
   state before Feed execution, then publishes terminal exact state after
   controlled completion. A runner or publication failure leaves remote
   `in_progress` as the recovery signal.

The workflow never force-pushes or destructively resets a branch. A normal
fast-forward conflict fails before Provider work when arming; after Provider
work, a final publication conflict preserves remote `in_progress`.

### Generated-state allowlist and rollback

Only these paths may be published by the deployment helper:

- `feeds/.follow-the-money-persistent`
- `feeds/rate-registry.json`
- the exact `feeds/scope-<digest>.json` files named by the registry
- `feeds/feed-run-lease.json`
- `feeds/latest.json` and a successful dated `feeds/daily/<date>/<run_id>.json`

Locks, status files, staging, temporary files, bundles, and debug/failure
workspaces remain ignored and are never staged. To roll back, use GitHub's
native workflow-disable control and preserve the last remote lease and rate
state; do not reset generated state or restart an external scheduler from an
uncertain run.

## Tests

```bash
uv run pytest
uv run python scripts/quality_gate.py
```

The quality gate includes workflow validation, actionlint in CI, lint, format,
type-checking, the credential-free test suite, and the offline wheel build.

## Durable output-root registry

Cross-root concurrent use of the same Provider/rate scope is unsupported:
cooperating processes sharing a scope must share the same output root.

- The output root holds `rate-registry.json` (versioned) plus one per-`scope_id`
  state file, all updated by same-directory atomic replace plus file/parent
  `fsync` under the collection lock.
- New scope: recoverable `initializing -> full-capacity state -> active`
  first-use sequence. Recovery may complete an `initializing` entry only after
  validating no request was admitted.
- An active scope with missing/partial/corrupt/unknown-schema state, or a
  marked persistent root with missing/corrupt registry, fails closed.
- Wall-clock rollback grants no tokens; refill uses only non-negative injected
  UTC elapsed time.
- Every possible send durably debits one token and installs the 24-hour
  provisional crash cooldown; confirmed pre-send failure may refund; controlled
  terminal outcomes retain the debit but reconcile to policy/`Retry-After`.

## Known limitations

- Versioned heuristic scores bias events with missing data; component coverage
  is exposed and priority scores are never returns or recommendations.
- The retained scoring/selection rules and `ClaimAuditor` have no production
  caller yet: the structured Agent delivery contract is deferred to a future
  Change.
