# Runbooks (English)

## Configuration

```bash
uv sync --frozen --all-groups
```

The deterministic engine is credential-free: no API key or model is ever
required. The repository reads explicit `--config` / `--output-root` paths
and never reads `~/.follow-the-money/config.json` implicitly.

## Feed generation

```bash
# Dry run (no publication):
uv run python -m follow_the_money.feed.cli --dry-run
# or: scripts/feed/follow-the-money-feed --dry-run

# Real run with an explicit output root:
uv run python -m follow_the_money.feed.cli --output-root feeds \
  --status-file feed-status.json
```

Exit `0` for a healthy or degraded Feed (warnings on stderr/status), `1` for
generation/publication failure, `2` for usage/config. No credential is
required.

## Tests

```bash
uv run pytest            # full credential-free suite
uv run python scripts/quality_gate.py   # lint, format, type-check, workflow, build
```

## GitHub deployment

The scheduled Feed workflow (`generate-feed.yml`) is a template. Before
enabling:

1. Set `FOLLOW_THE_MONEY_FEED=true` (repository/environment variable).
2. Provision a dedicated self-hosted runner labelled
   `follow-the-money-feed`.
3. Mount a persistent shared output root shared by every invocation for the
   relevant provider scopes, containing the deployment persistence marker
   (`.follow-the-money-persistent`) and durable rate-state paths.
4. Grant `contents: write` and confirm branch policy (protected-branch
   rejection fails visibly; the output is uploaded as an artifact).

Cross-root concurrent use of the same provider/rate scope is unsupported:
cooperating processes sharing a provider scope MUST share the same output
root (the application collection lock is rooted there).

## Durable output-root registry (operational contract)

- The output root holds `rate-registry.json` (versioned) plus one
  per-`scope_id` state file, all updated by same-directory atomic replace
  plus file/parent `fsync` under the collection lock.
- New scope: recoverable `initializing -> full-capacity state -> active`
  first-use sequence. Recovery may complete an `initializing` entry only
  after validating no request was admitted.
- An active scope with missing/partial/corrupt/unknown-schema state, or a
  marked persistent root with missing/corrupt registry, fails closed.
- Policy changes use the explicit zero-send conservative migration (new
  fingerprint, zero tokens, cooldown no earlier than old cooldown and now +
  new refill period) and never reset implicitly.
- Wall-clock rollback grants no tokens; refill uses only non-negative
  injected UTC elapsed time.
- Every possible send durably debits one token and installs the 24-hour
  provisional crash cooldown; confirmed pre-send failure may refund;
  controlled terminal outcomes retain the debit but reconcile to
  policy/`Retry-After`.

## External scheduling

Schedule Feed generation after the evidence cutoff is available; v1 marks a
Feed stale when lag > 30 minutes and refuses generation over 2 hours.

## Known limitations

- Versioned heuristic scores bias events with missing data; component
  coverage is exposed and priority scores are never returns or
  recommendations.
- The retained scoring/selection rules and `ClaimAuditor` have no production
  caller yet: the structured Agent delivery contract is deferred to a future
  Change.
