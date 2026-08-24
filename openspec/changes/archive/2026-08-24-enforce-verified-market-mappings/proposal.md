## Why

ECO-26 made configuration and Provider declarations agree, but `mapping_verified: true` can still be a self-assertion with no mapping-level evidence, and production Yahoo planning currently lets unverified symbols enter the Feed under canonical financial role identities. ECO-27 closes that trust gap before ECO-31 by making verified mappings evidence-backed and executable only when their exact Provider/role/instrument/unit tuple is supported.

## What Changes

- Extend the existing Provider `role_mappings` contract so every verified mapping has one explicit, auditable verification-provenance declaration bound to its exact mapping tuple, while every unverified mapping has an explicit reason.
- Validate mapping provenance during existing static Provider resolution, including checked-in path existence, Provider ownership, tuple association, allowed authoritative HTTPS references, and structured Yahoo fixture `meta.symbol` identity when applicable, without startup network requests or generic document interpretation.
- Re-evaluate every shipped `mapping_verified: true` declaration under the new invariant; do not grandfather unsupported claims, and specifically prevent CSI 300 from remaining verified through its missing repository reference.
- Plan production Yahoo adapters only for verified mappings, while retaining every verified and unverified mapping in the resolved Provider contract and Feed `provider_contracts` snapshot.
- Fail through the existing configuration/startup category when an enabled market Provider has zero verified runnable mappings, unless the Provider is explicitly disabled.
- Remove or narrow Provider-level market coverage claims so they are a subset of verified runnable capability; do not add role-level coverage accounting.
- Preserve the Feed schema, identity/digest and publication contracts, credential-free operation, deterministic ordering, and the retained MarketSnapshot `unverified_mapping` guard.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Require evidence-backed mapping verification during static Provider resolution, gate canonical market-role adapter planning to verified mappings, retain complete mapping audit state, and keep Provider-level coverage truthful.
- `deterministic-research-engine`: Make the retained MarketSnapshot behavior for an unverified configured role explicitly fail closed as `unverified_mapping`, without adding a production caller.

## Impact

- Affected contracts and configuration: the existing Yahoo manifest `role_mappings`, canonical role compatibility declarations as needed to preserve single-field authority, and Provider-level market coverage policy.
- Affected runtime areas: manifest/config validation and composition, resolved Provider contracts and snapshots, production Yahoo adapter planning, and existing startup failure ordering.
- Affected tests: mapping-provenance validation, shipped mapping truth, pre-mutation static failure, verified-only adapter planning, zero-runnable-mapping handling, truthful coverage, Provider snapshots, MarketSnapshot regression, and existing Feed determinism/identity/degradation/publication suites.
- No new Provider, credential, mapping registry/service, semantic evidence engine, role-level coverage engine, Feed schema field, Agent runtime contract, or MarketSnapshot production wiring is introduced.
