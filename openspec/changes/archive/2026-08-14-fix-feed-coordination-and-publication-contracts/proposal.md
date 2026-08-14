## Why

The normalized Feed baseline requires production dry runs to retain request
coordination, pre-commit work to finish before the 15-second reserve, and latest
ownership to be independent of publication order. Fresh Stage 3 review found that
the current implementation and tests do not satisfy those three contracts, so the
baseline cannot yet be accepted or archived.

## What Changes

- Make production-adapter `--dry-run` acquire the output-root collection lock and
  use durable rate state for every possible provider send while continuing to avoid
  dated and latest Feed publication.
- Separate reversible publication preparation from the non-cancellable commit so
  candidate staging and required pre-commit `fsync` complete by second 285, or fail
  before any dated/latest rename.
- Make latest ownership deterministic by selecting the maximum
  `(evidence_cutoff_at, content_digest)` tuple, including equal-cutoff candidates
  submitted in either order and idempotent recovery after partial publication.
- Add focused regression tests for real-provider dry-run coordination, staging that
  crosses the reserve boundary, and both latest-ownership submission orders.
- Reconcile the three reopened trace rows in `normalize-openspec-baseline` only
  after the repaired implementation and tests provide fresh passing evidence.
- Do not change Feed schemas, provider manifests, financial calculations, CLI exit
  categories, dated artifact identity/layout, or unrelated runtime behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Clarify the existing coordination, deadline-admission,
  and monotonic-publication requirements with regression scenarios that close the
  three Stage 3 evidence gaps.

## Impact

- Affected implementation: `src/follow_the_money/feed/cli.py` and
  `src/follow_the_money/feed/publish.py`.
- Affected tests: focused Feed CLI/publication/deadline/concurrency regression tests.
- Affected OpenSpec state: this Change's artifacts and, after successful Apply and
  verification, the three reopened evidence rows/tasks in
  `normalize-openspec-baseline`.
- No dependency, schema, provider-manifest, workflow, generated Feed, deployment,
  or external-state change is intended.
