## Why

`load_config` currently exposes both the accepted fail-closed configuration contract and a path-dependent permissive compatibility path that fills missing normative values from Python defaults. The second path is not used by the production Feed, contradicts the living source-authority contract, and makes trust-boundary behavior depend on file location.

## What Changes

- Make every successful `load_config` call use the existing strict validation and Provider-manifest resolution path.
- **BREAKING for direct Python callers**: remove the repository-level `strict` keyword and require callers to supply a resolvable Provider registry and manifest root instead of selecting semantics through arguments or path inference. The accepted product surface remains the internal Feed entry; no external configuration API is introduced or changed.
- Delete parser code used only by the permissive path, including hidden application/domain defaults and strict/non-strict branches inside section parsers.
- Keep the existing authority split, resolved Provider contract, verification, coverage, rate-policy, compatibility-mirror, Feed evidence, identity, and publication behavior unchanged.
- Update tests that construct incomplete legacy/custom YAML to use complete strict fixtures or controlled mutations of shipped configuration, and add focused fail-closed/path-independence regressions.
- Preserve living specifications unchanged with `skip_specs: true`: this Change removes a non-conforming implementation path rather than defining new behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `feed-evidence-pipeline` already requires one authoritative source per normative field, explicit materialization without Python or loader defaults, strict Provider-manifest composition, and fail-closed startup. This Change aligns the implementation with that accepted contract.

## Impact

- Primary implementation: `src/follow_the_money/config/load.py` and the explicit Feed caller in `src/follow_the_money/feed/cli.py`.
- Tests: configuration fixtures and callers under `tests/`, especially source-authority and Provider normalization coverage.
- Repository Python-call compatibility: callers passing `strict`, omitting the Provider registry, or relying on inferred/default manifest resolution must migrate to explicit strict inputs. `load_config` is re-exported for repository use, but no living specification or current-facing documentation promises it as an external product API; the breaking internal signature change is recorded here rather than hidden.
- No change to `config/model.py`, shipped configuration ownership, Provider inventory, schemas, dependencies, Agent/LLM runtime, Feed output contracts, or archived Changes.
