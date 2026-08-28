## 1. Contract Trace and RED Regressions

- [x] 1.1 Confirm the linked Linear issue's scope, milestone, and `blockedBy` / `blocks`; then re-read this Change, `feed-evidence-pipeline` source-authority requirements, every repository `load_config` caller, current-facing documentation, and active Changes. Confirm there is no supported permissive/legacy YAML contract, and sequence or isolate the known AKShare/config-test and `_client_cache`/Feed-CLI overlaps without absorbing them. Stop for scope review if Linear is missing or blocked, contrary compatibility evidence appears, or a new semantic overlap exists.
- [x] 1.2 Add focused RED tests using copied shipped contracts that reject missing normative top-level and section fields, reject application-file `providers`/`coverage` declarations as wrong-authority keys, reject explicitly supplied unreadable or invalid Provider authorities as `ConfigError`, and prove a complete contract at an unrelated temporary path follows the same strict resolution semantics.
- [x] 1.3 Add a RED signature/source regression proving `load_config` requires the Provider registry and keyword-only manifest root, omitted required arguments raise Python `TypeError`, `strict` is no longer accepted, and no strict-mode path inference or permissive parser route remains; run the focused tests and record that they fail for the intended pre-change reasons.

## 2. Strict-Only Loader

- [x] 2.1 Change `load_config` to require `providers_path` and keyword-only `manifest_root`, retain `require_verified_enabled`, and remove `strict`, repository-path comparisons, inferred manifest roots, application/registry fallback merging, and `providers`/`coverage` from the application file's allowed top-level keys.
- [x] 2.2 Make each shared section parser unconditionally use its existing closed-section/required-key behavior; remove strict booleans, Python fallback reads, default object construction, permissive session/watched branches, `_parse_providers`, and the permissive `_parse_entities` without renaming or refactoring unrelated strict helpers.
- [x] 2.3 Preserve the existing manifest resolution, Provider identity/version and verification checks, coverage and rate-policy validation, compatibility-mirror checks, role/session/source-family references, response bounds, and validation-before-Feed-side-effects ordering.
- [x] 2.4 Update `_load_app_config` to stop passing `strict=True` while continuing to pass the same shipped config, Provider registry, verified-enabled policy, and manifest root; make no other Feed behavior change.

## 3. Repository Caller and Fixture Migration

- [x] 3.1 Update all repository `load_config` calls to provide explicit Provider authorities and remove `strict=True`; verify no caller passes `strict`, omits the registry/manifest for a successful load, or depends on file-location inference.
- [x] 3.2 Replace permissive minimal-config tests with complete strict fixtures or one-field controlled mutations of copied shipped contracts, preserving each test's original validation intent and avoiding a new fixture framework.
- [x] 3.3 Run `.venv/bin/python -m pytest tests/test_config.py tests/test_config_provider_normalization.py tests/test_manifest_registry.py tests/test_feed_pipeline.py tests/test_feed_determinism.py tests/test_no_llm_contract.py` and repair only failures attributable to this Change.
- [x] 3.4 Run scoped source checks confirming `strict is None`, path-based mode inference, permissive-only parsers, strict/non-strict parser parameters, normative `.get(..., default)` fallbacks, and application-file allowance of `providers`/`coverage` are absent from `src/follow_the_money/config/load.py`.

## 4. Contract and Repository Verification

- [x] 4.1 Confirm shipped config still resolves the same Provider enablement, verification, coverage, rate-policy, compatibility-mirror, provenance, and default application values; confirm no `config/model.py`, Provider inventory/manifest, schema, Agent/LLM runtime, retained capability, or archived Change modification entered the diff.
- [x] 4.2 Run `openspec doctor`, `openspec validate simplify-strict-config-resolution --strict`, and `openspec validate --all --strict`; confirm the intentional `skip_specs: true` zero-delta Change remains aligned with the living contract.
- [x] 4.3 Run `.venv/bin/python scripts/quality_gate.py` and `git diff --check`, inspect the final diff against every proposal non-goal, and record any unresolved compatibility conflict or follow-up issue without expanding this Change.
