# Feed production runbook

The scheduled workflow produces the current five-domain Evidence Feed. It
runs without API keys or paid-data credentials.

## Normal path

1. `prepare` refreshes `main`, validates configuration and Provider manifests,
   checks the separate `.feed-state/` layout, and arms the deployment lease.
2. `collect` verifies the lease, captures a fixed cutoff, runs the eight enabled
   Providers, validates provenance/freshness/coverage, and writes the staged
   product under `feeds/`.
3. `finalize` verifies the status file and checkpoint, persists the terminal
   lease, and stages only the manifest, its five active artifacts, and durable
   runtime state.
4. The workflow commits and pushes a normal fast-forward update to `main`.

The active entry is `feeds/feed-manifest.json`; its inventory names exactly
`news`, `macro_release`, `policy`, `positioning`, and `filing` artifacts.

## Failure handling

A failed or incomplete required Provider produces a typed failure and is not
silently replaced by prior evidence. A bounded HTTP 401/403 blocked Provider
may produce an accepted degraded Feed when coverage semantics permit it. The
workflow preserves failure diagnostics without publishing a failed Feed.

Do not hand-edit Feed identity, artifact hashes, checkpoint, rate state, or
lease state. Re-run through the producer/deployment path with deterministic
fixtures for testing. A previous eight-domain product must use the explicit
bounded migration path before it can become current; mixed generations are
invalid.

## Consumer boundary

The Skill uses `scripts/skill/prepare-feed`, which retrieves the canonical
manifest and its five artifacts only. It does not call Providers, use local
state, or fall back to a stale/partial product.
