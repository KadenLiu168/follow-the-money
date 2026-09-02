## Why

The current mixed `feeds/latest.json` forces every consumer to load all evidence domains and provides no authoritative bundle inventory or whole-bundle integrity check. The Feed boundary should become explicit and independently consumable before further Host Agent enablement, without adding Agent runtime behavior.

## What Changes

- **BREAKING**: New Feed production publishes an authoritative `feed-manifest.json` plus one typed artifact for each existing payload discriminator: `news`, `macro_release`, `policy`, `market_data`, `flow`, `positioning`, `filing`, and `calendar`.
- Route each evidence item deterministically by `payload.type`; every domain artifact exists even when its item set is empty, and no provider-specific artifact is introduced.
- Move bundle-level generation, cutoff, producer, configuration, provider-outcome, pipeline, schema, identity, inventory, and integrity metadata into the manifest; domain artifacts contain only their bundle binding, domain identity, schema version, and evidence items.
- Validate required inventory, canonical artifact bytes, declared size and SHA-256, domain/type agreement, shared generation identity, reconstructed semantic identity, and provenance before consumption.
- Publish immutable generation-qualified candidate artifacts first and atomically replace `feed-manifest.json` only after the complete bundle validates; failed publication cannot change the active bundle. Successfully superseded artifact files are cleanup state, not retained Feed history.
- Preserve migration compatibility by allowing consumers to read a valid legacy `latest.json` only when `feed-manifest.json` is absent. New producers do not dual-write `latest.json`, because two independently replaced entry points cannot provide one atomic active-state guarantee.
- Update repository deployment allowlists, checkpoint/status matching, schemas, tests, and truthful Feed documentation for the bundle contract.
- Preserve credential-free deterministic collection, evidence provenance, ordering, coverage/degradation semantics, and the evidence-only boundary. Provider acquisition contracts and Agent/runtime capabilities remain unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Replace new single-file Feed production and consumption with a typed, manifest-led, integrity-validated, atomically activated Feed bundle while retaining manifest-absent legacy read compatibility.

## Impact

Affected surfaces include Feed assembly/validation/publication/consumption, `schemas/feed.schema.json` compatibility handling, new manifest and domain artifact schemas, repository-native deployment/finalization allowlists, generated-state CI path rules, Feed tests and fixtures, `feeds/`, status output, README/SKILL/runbook/architecture documentation, and the `feed-evidence-pipeline` living contract. No new dependency, storage service, provider behavior, public query API, LLM/model path, or Agent orchestration is introduced.
