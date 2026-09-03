## 1. Contract Tests

- [x] 1.1 Update shipped-configuration and registry tests to require verified CFTC enablement in the resolved production plan while preserving its non-mandatory coverage status; verify the focused configuration/registry tests fail before activation and pass afterward
- [x] 1.2 Add a deterministic production-path test for a newly available CFTC report and verify the published manifest inventories the item only in the positioning artifact with CFTC provenance, weekly cadence metadata, `fresh` status, and original source-semantic timestamps
- [x] 1.3 Add a deterministic consecutive-run test in which the next complete CFTC check has no new report and verify the prior slice is carried unchanged with `valid_unchanged`, unchanged evidence timestamps, and independently updated retrieval/generation timestamps
- [x] 1.4 Add a deterministic CFTC failure test with a prior valid snapshot and verify the outcome remains incomplete with `not_evaluated`, the command fails, and the active bundle is not replaced

## 2. Production Activation

- [x] 2.1 Enable CFTC in the authoritative checked-in Provider activation policy without adding a coverage row or Provider-specific Feed wiring; verify normal configuration resolution plans the existing CFTC adapter exactly once
- [x] 2.2 Remove directly affected stale claims that CFTC is production-disabled while preserving the manifest-owned weekly cadence, credential-free provenance, typed positioning payload, and optional/non-mandatory coverage contract; verify documentation and contract tests agree with the shipped configuration

## 3. Verification

- [x] 3.1 Run the focused CFTC adapter, configuration, Feed freshness, bundle-routing, and production orchestration tests and verify all new and existing cases pass deterministically
- [x] 3.2 Run `openspec doctor`, `openspec validate activate-cftc-market-feed --strict`, and `openspec validate --all --strict`; verify all OpenSpec checks pass
- [x] 3.3 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes without Feed dry-run or real Provider network access
