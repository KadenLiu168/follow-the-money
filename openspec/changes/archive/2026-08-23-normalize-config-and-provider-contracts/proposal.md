## Why

The shipped Feed configuration presents YAML and checked-in Provider manifests as explicit, versioned runtime truth, but production loading still ignores some YAML values, silently falls back to Python defaults, and lets adapters and Feed orchestration consume independently interpreted Provider contracts. ECO-26 closes this trust-boundary gap before ECO-27 evaluates the evidence supporting specific market mappings, so the contract the Feed embeds is guaranteed to be the contract its adapters execute.

## What Changes

- Assign one authoritative source to every runtime field: `config/config.yaml` owns application and deterministic-domain configuration, Provider manifests own Provider-specific contract facts, and `config/providers.yaml` owns enablement and coverage policy.
- Make production resolution require, parse, validate, and explicitly pass every normative YAML-owned value instead of silently relying on Python dataclass defaults or `.get(..., default)` fallbacks.
- Strictly compose registry policy with supported checked-in manifests into the existing resolved `AppConfig` / `ProviderEntry` boundary before normal Feed execution.
- Route adapter construction, transport and source-link rules, rate behavior, empty-window semantics, host-concurrency planning, enablement, coverage assessment, and Feed `provider_contracts` snapshots through the same resolved Provider contract.
- Treat any temporarily retained duplicate Provider field as a validation-only compatibility mirror; fail startup on mismatch and prevent it from independently controlling runtime behavior.
- Make coverage-matrix membership the sole authority for coverage groups, including Providers that participate in multiple groups; a Provider-level `group` field does not define coverage membership.
- Fail with the existing startup/configuration failure category on missing, unsupported, unverified, or inconsistent static contracts before Provider requests and before normal persistent Feed runtime mutation.
- Preserve existing Provider set, mapping facts, Feed schema, ECO-24 degradation semantics, ECO-25 identity semantics, credential-free operation, and the Provider → Feed → Host Agent architecture.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Require one authority per production configuration field and one manifest-derived resolved Provider contract shared by adapters, orchestration, coverage/rate behavior, and embedded Feed snapshots, with fail-closed static startup validation.

## Impact

- Affected runtime areas: configuration models and loading, Provider manifest validation/composition, adapter construction, Feed startup ordering, rate and host-concurrency planning, coverage assessment, and Provider contract snapshot construction.
- Affected checked-in configuration: `config/config.yaml`, `config/providers.yaml`, and existing `providers/*/manifest.yaml` declarations may be normalized without changing current Provider or market-mapping truth.
- Affected tests: configuration source authority and missing-field failures, manifest authority/version/identity/verification, compatibility-mirror parity, multi-group coverage, single-contract adapter/snapshot parity, and pre-mutation startup failure boundaries.
- Affected contract: the existing `feed-evidence-pipeline` living capability; no new capability, Feed schema major, external Provider, dependency, credential path, Agent contract, embedded LLM runtime, or later-milestone architecture is introduced.
