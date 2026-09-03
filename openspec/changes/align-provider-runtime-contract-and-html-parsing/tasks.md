## 1. Add Offline Regressions

- [x] 1.1 Extend the existing injected fake client to record outbound headers, then add failing tests for resolved user-agent propagation, non-identity header merging, case-insensitive override prevention, and unchanged SEC EDGAR endpoint/identity behavior; verify the new tests fail against the pre-fix shared request path for the expected reasons.
- [x] 1.2 Add production-shaped PBOC/NBS-style HTML fixtures covering separated and compact valid dates, unrelated navigation links, invalid month/day tokens, and multiple candidate tokens; verify the new tests reproduce the prior incidental calendar exception and define stable first-valid extraction.
- [x] 1.3 Add or retain focused assertions that malformed date-like links are ignored while undecodable responses and transport failures remain typed failures; verify the tests distinguish parser robustness from Provider success/failure semantics.

## 2. Correct Shared Provider Behavior

- [x] 2.1 Update the shared adapter fetch boundary to remove caller-supplied user-agent keys case-insensitively, add the exact resolved Provider user-agent, and preserve all other additional headers; verify the request metadata tests from 1.1 pass without changing `bounded_fetch` or adding configuration.
- [x] 2.2 Remove the redundant SEC-specific user-agent injection so SEC uses the shared authority; verify the SEC request endpoint and descriptive manifest-resolved identity tests pass.
- [x] 2.3 Update shared HTML index extraction to inspect candidates in existing source and left-to-right order, skip only invalid calendar candidates, and select the first valid candidate; verify all tests from 1.2 and 1.3 pass without a new parser dependency or broad exception suppression.

## 3. Verify Contract and Repository Invariants

- [x] 3.1 Run `.venv/bin/python -m pytest tests/test_adapters.py tests/test_feed_pipeline.py tests/test_feed_cli.py` and verify request parsing, typed Provider failures, retry behavior, source completeness, and no-publication-on-failure regressions pass.
- [x] 3.2 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes.
- [x] 3.3 Run `openspec doctor`, `openspec validate align-provider-runtime-contract-and-html-parsing --strict`, and `openspec validate --all --strict`; verify all OpenSpec checks pass.
- [ ] 3.4 After delivery, trigger the existing hosted Feed workflow and record whether the resolved user-agent and malformed-link defects are absent while reporting any upstream blocking, throttling, network, or other external Provider failures truthfully rather than treating Provider success as required.
  - Attempt `33714332955` failed while publishing durable pre-network state; collection was skipped, so neither runtime defect was exercised.
