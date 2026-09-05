## 1. Producer Size-Boundary Regressions

- [x] 1.1 Add focused tests for healthy/degraded candidates below, exactly at, and above a deliberately small `max_serialized_feed_bytes`, and verify the oversized cases fail before implementation while the inclusive boundary remains accepted.
- [x] 1.2 Add regression coverage proving an oversized publishable candidate produces the existing typed producer failure with actual/limit byte counts, publishes no candidate, leaves the active bundle and checkpoint unchanged, and verify the focused test fails before implementation.
- [x] 1.3 Add a source-completeness failure precedence regression proving existing Provider diagnostics remain authoritative even when the constructed failure bundle would exceed the configured limit.

## 2. Minimal Producer Enforcement

- [x] 2.1 After the existing source-failure branch, compute the exact canonical bundle total from the built manifest and artifact byte sequences, reject only totals greater than `max_serialized_feed_bytes` through `FeedExecutionError`, and verify all focused boundary, dry-run, publication, checkpoint, and failure-precedence tests pass.

## 3. Validation

- [x] 3.1 Run the directly affected Feed CLI and publication tests and verify all existing deterministic, fail-closed, dry-run, active-bundle, and checkpoint behavior remains green.
- [x] 3.2 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate enforce-serialized-feed-size-limit --strict`, `openspec validate --all --strict`, and `git diff --check`; record the exact results without running a real Provider dry-run.
