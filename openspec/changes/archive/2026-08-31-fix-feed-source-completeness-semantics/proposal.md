## Why

Scheduled Feed publication now makes the existing health predicate operationally unsafe: a complete evidence window with no accepted items fails, while incomplete planned Provider work can be published when another Provider returns evidence. The Feed must judge collection success from the actual run plan and resolved Provider contracts, not evidence quantity, so `latest.json` advances only after complete source collection.

## What Changes

- **BREAKING** Replace the zero-accepted-evidence failure rule with a planned-Provider completeness rule: `healthy`, or contract-permitted `empty`, is complete; `failed`, `partial`, `skipped`, non-permitted `empty`, missing, duplicate, or ambiguous terminal outcomes fail the run.
- Evaluate mandatory coverage from complete planned Providers, including contract-permitted empty Providers, rather than accepted evidence counts.
- Preserve `degraded` only for already accepted non-source conditions; planned source incompleteness always produces `pipeline.status = failure`, a non-zero exit, and no Feed publication.
- Admit and normally publish source-complete empty Feeds, including dated output, `latest.json`, deterministic identity metadata, Provider outcomes, and the current evidence cutoff.
- Expose the responsible existing `ProviderOutcome` data in transient failure diagnostics without adding a Feed schema field, a second failure model, or a repository-persisted status artifact.
- Preserve resolved planning authority, Provider enablement and mapping gates, existing hard failures, and ECO-62 deployment, RateRegistry, lease/recovery, finalization, and non-force Git semantics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Revise collection health, mandatory coverage, empty-Feed publication, failure diagnostics, and exit/publication behavior around planned Provider completeness.

## Impact

- Primary implementation and focused tests: `src/follow_the_money/feed/plan.py`, `src/follow_the_money/feed/cli.py`, `tests/test_feed_pipeline.py`, and `tests/test_feed_cli.py`.
- `src/follow_the_money/feed/deployment.py` and `tests/test_feed_deployment.py` change only if narrowly required to preserve original Feed failure diagnostics or exit propagation through existing finalization.
- Documentation that currently states zero-evidence failure or source-incomplete degradation must be updated truthfully.
- No Provider configuration, Provider transport, Feed schema, generated-state allowlist, workflow schedule, Host-Agent boundary, or dependency change is intended.
