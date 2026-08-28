## Context

See `proposal.md` for motivation. `src/follow_the_money/config/load.py` currently contains one accepted strict resolver and one permissive compatibility resolver behind `strict: bool | None`, including path-based mode inference. The production Feed already supplies the checked-in Provider registry, manifest root, and `strict=True`. Repository tests are the only other discovered callers. Although `follow_the_money.config` re-exports `load_config` for repository use, the living specs expose only the internal Feed entry and current-facing documentation does not promise an external configuration API or permissive legacy/custom YAML support.

The living `feed-evidence-pipeline` requirement “Single authoritative production configuration” already requires explicit authoritative fields, no loader/Python defaults, strict manifest composition, and fail-closed validation. This Change therefore has no delta spec.

Two independent untracked Changes appeared during planning. `remove-unimplemented-akshare-provider` overlaps Provider configuration and configuration tests but is an explicit non-goal here; `prune-unused-artifacts` touches `_client_cache` in `feed/cli.py`, which is also excluded here, without changing the loader call. Apply must re-establish the active-Change baseline and must not absorb either Change's edits.

## Goals / Non-Goals

**Goals:**

- Make the loader signature and implementation expose exactly one strict contract.
- Preserve validation ordering far enough to retain focused syntax/encoding failures while requiring explicit Provider inputs for successful resolution.
- Reduce maintenance surface primarily by deletion, without changing the resolved `AppConfig` model or shipped runtime values.
- Leave one focused regression surface proving path-independent fail-closed behavior and preserved Provider resolution.

**Non-Goals:**

- Designing a compatibility loader, migration adapter, configuration abstraction, serialized schema, or alternate registry.
- Reformatting or renaming strict helpers merely because `strict` becomes redundant.
- Changing Provider inventory, enablement, manifests, adapters, Feed evidence semantics, output identity, publication, or retained no-caller libraries.
- Cleaning unrelated helpers, caches, dependencies, or archived OpenSpec history.

## Decisions

### 1. Make Provider resolution inputs explicit

Change the callable contract to require `config_path`, `providers_path`, and keyword-only `manifest_root`; retain `require_verified_enabled` as the existing policy switch. Remove `strict` and every path comparison that inferred validation semantics or a default manifest root.

This is preferable to keeping optional arguments that always fail later: the signature will describe the only successful contract and repository callers will expose omitted authority immediately as Python `TypeError`. An explicitly supplied but unreadable or invalid registry/manifest authority remains a configuration failure reported as `ConfigError`. It is also preferable to a second compatibility function because no repository requirement or documented consumer owns legacy/custom YAML behavior.

The loader will still parse the application YAML first so invalid UTF-8, lone-surrogate, and top-level-closure tests retain their direct error classification when supplied explicit Provider inputs. Successful loading cannot proceed without both Provider authorities.

### 2. Collapse onto the existing strict parser behavior

Retain the current `_closed_section`, required-key, enum, cross-reference, manifest-resolution, verification, coverage, rate-policy, and compatibility-mirror validators. Remove `_parse_providers`, the permissive `_parse_entities`, permissive session/watched construction, and all fallback reads or object-default construction reachable only when `strict` was false.

For shared parser functions, remove the `strict` parameter and make the existing strict branch unconditional. Keep existing strict-only helper names when renaming would add churn without changing behavior. Do not create a new parser class, mode enum, wrapper, or schema.

### 3. Read each field only from its accepted authority

Read application/domain sections only from `config/config.yaml`, registry policies and coverage only from the supplied Provider registry, and Provider contract facts only through the supplied manifest root. Remove `providers` and `coverage` from the application file's allowed top-level keys so wrong-authority declarations fail closed rather than being merged or ignored. Do not use `.get(..., default)` for normative fields.

Compatibility mirrors remain validation-only. Existing checks for Provider identity/version, verification evidence, host/rate policies, coverage, role mappings, response bounds, and cross-source references remain in the strict flow and continue to run before Feed execution side effects.

### 4. Migrate tests to strict authorities, not synthetic permissive models

Prefer copying shipped `config/config.yaml`, `config/providers.yaml`, and `providers/` into `tmp_path`, then mutate the one field under test. Where a small fixture remains clearer, make it a complete strict fixture with manifests rather than rebuilding fallback behavior.

Update every repository call to pass the explicit manifest root and remove `strict=True`. Add regressions for missing required top-level/section fields, missing Provider registry or manifest authority, and a complete contract copied to an unrelated temporary path. The temporary-path test must resolve identically to the shipped contract apart from the controlled path and must not depend on repository-path inference.

Do not add a broad new fixture framework; reuse the existing copied-contract helper pattern in `tests/test_config_provider_normalization.py` where practical.

### 5. Preserve Feed behavior while simplifying its call

Remove only `strict=True` from `_load_app_config`; it already supplies the shipped config, Provider registry, verified-enabled policy, and manifest root. No other Feed orchestration or error mapping changes are required.

## Risks / Trade-offs

- [Risk] An undocumented external Python caller may rely on `strict=False`, omitted Provider inputs, or path inference. → Mark the signature removal as breaking, keep the Change reviewable, and stop Apply if concrete supported compatibility evidence is discovered.
- [Risk] Converting old minimal fixtures could accidentally weaken a validation assertion. → Base strict tests on copied shipped contracts and mutate one condition at a time; preserve exact error assertions where the contract still owns them.
- [Risk] Deleting conditionals may accidentally skip a strict cross-check. → Trace each removed branch and retain the current strict validation sequence; run the existing source-authority, manifest, coverage, verification, provenance, and default-config suites.
- [Risk] A large mechanical test migration could obscure the production change. → Centralize only the already-repeated copied-contract setup and avoid unrelated fixture/refactor work.
- [Risk] Concurrent Apply of the AKShare or unused-artifact Changes could create an ambiguous shared-file/test baseline. → Recheck active Changes before Apply, sequence or isolate the work, and keep this Change's diff allowlisted to its strict-loader contract rather than resolving their scope here.

## Migration Plan

1. Add or convert focused tests so all calls provide explicit Provider authorities and the new path-independence/fail-closed cases describe the target behavior.
2. Remove the mode parameter, inference, permissive branches, and permissive-only helpers; update the Feed call without changing its supplied authorities.
3. Run focused configuration/Provider regressions, then the canonical repository and OpenSpec gates.

Rollback is the ordinary source revert of this Change. It requires no data migration because configuration files, manifests, models, Feed artifacts, and persisted rate state are unchanged.
