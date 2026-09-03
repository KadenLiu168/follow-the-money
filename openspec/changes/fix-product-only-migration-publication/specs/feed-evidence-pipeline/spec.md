## MODIFIED Requirements

### Requirement: Current-state migration activates the first bundle without Provider work
Repository deployment SHALL recognize a valid current `feeds/latest.json` with no manifest as pre-bundle product state. A migration-only invocation SHALL deterministically split that validated Feed into the typed bundle, preserve its semantic `content_digest`, `run_id`, evidence, provenance, cutoff, pipeline, and checkpoint identity, publish the first manifest-led bundle through the bundle publication boundary, remove `latest.json` in the same repository generated-state commit, perform zero Provider requests, and exit before collection. When runtime state is already established in `.feed-state/`, product-only migration SHALL stage the required runtime files, generated manifest and exact artifact inventory, and tracked `latest.json` deletion without requiring nonexistent or untracked legacy runtime paths under `feeds/`. A complete legacy runtime-state migration SHALL continue to stage its exact tracked legacy runtime deletions. Missing or invalid required migration state SHALL fail closed without deleting the legacy product or advancing continuity.

#### Scenario: Valid current latest is migrated
- **WHEN** deployment finds a valid legacy latest, matching checkpoint, and no bundle manifest
- **THEN** it publishes an equivalent validated bundle, removes `latest.json` in the same generated-state commit, performs zero Provider requests, and leaves checkpoint identity unchanged

#### Scenario: Product-only migration has no legacy runtime paths
- **WHEN** valid runtime state is already established in `.feed-state/`, `feeds/latest.json` is tracked, and no legacy runtime paths under `feeds/` exist or are tracked
- **THEN** migration stages only the required runtime state, exact generated bundle inventory, and `latest.json` deletion without passing nonexistent legacy runtime paths to repository publication

#### Scenario: Complete legacy runtime state is relocated
- **WHEN** migration relocates complete tracked legacy runtime state from `feeds/` into `.feed-state/`
- **THEN** repository publication stages the exact new runtime additions and exact tracked legacy runtime deletions without broad or unrelated paths

#### Scenario: Legacy product is not tracked for deletion
- **WHEN** migration publication finds `feeds/latest.json` present but not tracked by the repository index
- **THEN** migration fails closed before removing it or committing a partial generated-state migration

#### Scenario: Legacy product cannot be trusted
- **WHEN** latest, checkpoint, schema, identity, provenance, or repository state is invalid or inconsistent
- **THEN** migration makes zero Provider requests and does not partially create or activate a bundle

#### Scenario: Required migration path is missing
- **WHEN** a required runtime file, manifest, or inventoried artifact is missing or inconsistent before publication
- **THEN** migration fails closed rather than silently omitting the required path or publishing partial state

#### Scenario: Bundle state already exists
- **WHEN** a valid manifest-led bundle is present
- **THEN** current-state migration does not reinterpret `latest.json` as another authority
