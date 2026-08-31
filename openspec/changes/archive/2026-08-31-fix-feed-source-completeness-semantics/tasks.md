## 1. Lock the source-completeness contract with focused tests

- [x] 1.1 Update `tests/test_feed_pipeline.py` to prove `healthy` and contract-permitted `empty` planned Providers are complete, permitted empty counts toward mandatory coverage, and accepted/fetched counts do not determine completeness or coverage.
- [x] 1.2 Add assessment regressions proving `failed`, `partial`, `skipped`, and non-permitted `empty` planned Providers produce `failure` even when another Provider returns accepted evidence.
- [x] 1.3 Add fail-closed assessment cases for missing, duplicate/ambiguous, unknown-state, or identity-mismatched terminal outcomes without adding a second outcome model.
- [x] 1.4 Prove assessment uses only the actual run plan plus resolved contracts: unplanned disabled CFTC and unverified Yahoo mappings create no synthetic outcome or completeness obligation, while future legitimately planned Providers participate automatically.

## 2. Enforce completeness and coverage at the existing assessment boundary

- [x] 2.1 Pass the actual planned Provider identities into `assess_pipeline()` and validate plan uniqueness and exact matching terminal outcomes using existing resolved configuration and `ProviderOutcome` data.
- [x] 2.2 Reuse one outcome/contract predicate for Provider completeness and mandatory coverage counting, preserving optional-group behavior and deterministic Provider/warning ordering.
- [x] 2.3 Remove accepted evidence quantity from the health predicate and make any incomplete planned Provider or deficient mandatory group return `failure`; retain `degraded` support without adding a new degraded condition.

## 3. Preserve publication, window, and diagnostics behavior

- [x] 3.1 Add CLI tests proving a fully source-complete `items: []` run exits `0`, publishes a schema-valid dated Feed, replaces `latest.json`, retains Provider outcomes/current cutoff/normal identity metadata, and makes the next run start from that new cutoff.
- [x] 3.2 Add CLI tests proving source-incomplete runs exit non-zero, never call publication, create no new dated Feed, leave the previous latest unchanged, and report `provider_id`, state, existing error/message, and warnings through existing transient output.
- [x] 3.3 Replace the zero-evidence-specific failure message with diagnostics derived from existing Provider outcomes while keeping Feed schema, status persistence, canonical identity, and publisher code unchanged.
- [x] 3.4 Add a deployment regression proving ECO-62 finalization preserves the original source-completeness failure result while persisting only existing allowlisted RateRegistry/lease safety state; change `deployment.py` only if that regression exposes a real propagation defect.

## 4. Align truthful documentation and verify preserved boundaries

- [x] 4.1 Update only documentation that explicitly describes zero accepted evidence as failure or incomplete planned source work as publishable degradation, including `docs/feed-contract.md`; retain generic `degraded` and exit-code documentation where still accurate.
- [x] 4.2 Confirm `schemas/feed.schema.json`, `config/providers.yaml`, Provider manifests/transports, generated-state allowlists, workflows, RateRegistry, lease/recovery, and Host-Agent/analytics surfaces have no ECO-63 changes.
- [x] 4.3 Run `.venv/bin/python -m pytest tests/test_feed_pipeline.py tests/test_feed_cli.py tests/test_feed_deployment.py` and the relevant existing configuration/planning regressions for disabled CFTC and verified-only Yahoo mappings.
- [x] 4.4 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate fix-feed-source-completeness-semantics --strict`, `openspec validate --all --strict`, and `git diff --check`; record only fresh results.
