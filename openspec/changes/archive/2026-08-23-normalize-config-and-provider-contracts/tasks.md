## 1. RED Source-Authority Coverage

- [x] 1.1 Add config fixture mutations proving representative top-level, Feed (including `lock_timeout_seconds`), scoring, Market State, calendar, safety-lexicon, and rate-registry YAML values reach the resolved model; delete one required field from each section and assert `ConfigError` rather than a Python fallback, then run the focused tests and record the expected RED failures before implementation.
- [x] 1.2 Add enabled-Provider manifest tests for missing/invalid YAML, unsupported `contract_version`, Provider-ID mismatch, incomplete required facts, and failed verification, plus a manifest-owned runtime-value mutation that needs no matching contract edit in `config/providers.yaml`.
- [x] 1.3 Add migration-parity tests proving retained mirrors pass only when equal and fail on mismatch; add a coverage fixture where one Provider belongs to multiple matrix rows and prove no Provider-level `group` controls membership.
- [x] 1.4 Add a single-resolved-contract test that mutates an authoritative manifest host/rate/charset/limit/empty-window field and proves adapter rules, applicable orchestration behavior, and the embedded `provider_contracts` snapshot observe the same resolved value.
- [x] 1.5 Add Feed startup-boundary tests for malformed static contracts asserting zero Provider/client calls, no adapter collection, no output-root/rate-registry mutation, no dated publication, and byte-for-byte unchanged or absent `latest.json`.
- [x] 1.6 Add regression fixtures pinning the existing 13 roles, Provider assignments, symbols/instruments, units, `mapping_verified` values, coverage groups/minimums, Feed health behavior, and deterministic identity behavior before normalization.

## 2. Normalize Checked-in Ownership

- [x] 2.1 Make every application/domain section in `config/config.yaml` closed and complete, add explicit currently hidden normative values such as `feed.lock_timeout_seconds`, and preserve every current effective runtime value.
- [x] 2.2 Reduce `config/providers.yaml` to a versioned registry of Provider ID plus shipped enablement and the complete coverage matrix; remove redundant Provider-contract fields where narrow, or mark only unavoidable legacy fields as validation-only mirrors.
- [x] 2.3 Complete the existing Provider manifests with the common/runtime facts required by current adapters and snapshots, preserving the current Provider set, credential-free behavior, fixture provenance, mapping declarations, symbols, units, and verification facts exactly.
- [x] 2.4 Document the final field-ownership matrix next to the authoritative configuration contracts without adding a parallel runtime specification or claiming ECO-27 verification work.

## 3. Strict Application Configuration Resolution

- [x] 3.1 Add closed allowed/required-key validation for every top-level and nested application-owned section and make supported config/registry schema versions mandatory.
- [x] 3.2 Parse and explicitly construct every `FeedLimits`, `Scoring`, `MarketState`, `CalendarPolicy`, `SafetyLexicon`, `RateRegistry`, session, source-family, entity, role, watched-company, and top-level `AppConfig` field from YAML without normative `.get(..., default)` fallbacks.
- [x] 3.3 Validate value domains and cross-references, including unique identities, canonical role order, role-to-Provider/session/source-family references, global-bound versus Provider-limit compatibility, and complete coverage membership/minimums.
- [x] 3.4 Keep harmless dataclass defaults only where production construction always supplies the field explicitly, and make all source-mutation and required-field RED tests pass without broad model refactoring.

## 4. One Resolved Provider Contract

- [x] 4.1 Make the existing manifest loader strictly validate supported versions, identity, verification evidence, authentication/protocol, hosts, source links, charset/content type, request/response limits, rate, pagination, empty-window, current Provider-specific behavior, mappings, and fixture provenance with no hidden normative manifest defaults.
- [x] 4.2 Compose each registry entry and authoritative manifest into one immutable resolved `ProviderEntry` in deterministic Provider-ID order; derive coverage only from `CoverageMatrix` and enforce parity for any retained mirror.
- [x] 4.3 Validate existing role/manifest mapping overlap structurally while preserving all financial mapping facts; fail closed on contradiction and leave evidence-based verification decisions to ECO-27.
- [x] 4.4 Change production adapter/registry construction to accept the resolved Provider entries and existing application-owned context, remove adapter filesystem manifest re-reads and second parsing paths, and retain the current adapter set and protocol behavior.
- [x] 4.5 Route rate policy, host concurrency, enablement, empty-window semantics, coverage assessment, transport/source-link constraints, and Provider snapshot construction through the same resolved entries.
- [x] 4.6 Emit deterministic redacted `provider_contracts` snapshots from resolved entries, keep coverage rows in the Feed configuration snapshot, and preserve the external Feed schema and ECO-25 semantic projection/digest/run-ID algorithms.

## 5. Fail-Closed Startup and Contract Alignment

- [x] 5.1 Complete static application/registry/manifest/reference resolution before output-root preparation, deadline/lock acquisition, latest planning, rate-registry construction, adapter creation, or collection, mapping failures to the existing startup/configuration outcome category.
- [x] 5.2 Make the startup side-effect tests pass for every malformed or inconsistent static-contract case while leaving later latest/filesystem/network/runtime failures in their existing phases and preserving ECO-24 outcomes.
- [x] 5.3 Update `README.md`, `README.zh-CN.md`, `SKILL.md`, and directly relevant config/provider documentation only where their current authority or runtime claims would otherwise become stale; retain the Agent-only Provider → Feed → Host Agent boundary.
- [x] 5.4 Review the implementation diff against ECO-26 scope and remove any mapping research/change, new Provider or coverage group, Feed schema change, Agent-contract type, LLM/model path, speculative framework, or unrelated cleanup.

## 6. Verification

- [x] 6.1 Run `.venv/bin/python -m pytest -q tests/test_config.py tests/test_manifest_registry.py tests/test_provider_contract.py tests/test_adapters.py tests/test_feed_cli.py tests/test_feed_pipeline.py tests/test_feed_boundary.py tests/test_feed_determinism.py tests/test_no_llm_contract.py` and resolve all focused regressions.
- [x] 6.2 Run `.venv/bin/python scripts/quality_gate.py` and require the canonical full pytest, Ruff, and mypy gates to pass without substituting a weaker command set.
- [x] 6.3 Run `openspec doctor`, `openspec validate normalize-config-and-provider-contracts --strict`, and `openspec validate --all --strict`; confirm proposal, design, delta spec, tasks, implementation, tests, and truthful docs agree.
- [x] 6.4 Record final evidence that current market mapping facts, Provider and coverage sets, ECO-24 degradation semantics, ECO-25 identity semantics, credential-free operation, no-LLM boundary, and external Feed schema remain unchanged, and list any scope-external finding for its later Linear issue.
