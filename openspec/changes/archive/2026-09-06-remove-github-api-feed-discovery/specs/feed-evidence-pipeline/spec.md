## ADDED Requirements

### Requirement: Canonical published Feed is consumed directly from the canonical main branch
Normal Skill Feed consumption SHALL retrieve `feeds/feed-manifest.json` directly from branch `main` of the public repository `KadenLiu168/follow-the-money` through `raw.githubusercontent.com`, then SHALL retrieve every Feed artifact from the same canonical repository, branch, and `feeds/` root. It SHALL perform no GitHub REST API request, SHALL NOT resolve or require a Git commit SHA, and SHALL require no GitHub token or Provider credential.

The validated manifest SHALL remain the only authoritative bundle entry point. The consumer SHALL retrieve exactly the artifact paths declared by its validated ordered inventory and SHALL NOT infer filenames, maintain another domain-to-path registry, enumerate the remote `feeds/` directory, use Git history as a Feed query API, or substitute a different repository, branch, or product root. Integrity and semantic validation SHALL remain authoritative across the mutable-branch read window; if branch movement or any other remote condition yields an unavailable, mixed-generation, inconsistent, or otherwise invalid bundle, consumption SHALL fail closed without retrying against another source or exposing evidence.

#### Scenario: Published Feed is retrieved without GitHub API discovery
- **WHEN** normal Skill consumption begins
- **THEN** its first remote request retrieves `feeds/feed-manifest.json` from the canonical repository's `main` branch on `raw.githubusercontent.com`, and the invocation makes zero requests to `api.github.com`

#### Scenario: Manifest declares the artifact inventory
- **WHEN** the canonical-main manifest is accepted for retrieval
- **THEN** only its exact validated inventory paths are requested under the same canonical `main/feeds/` root and no remote directory enumeration or independently derived artifact path is used

#### Scenario: Main advances during one invocation
- **WHEN** repository `main` advances between manifest and artifact retrieval and the returned files no longer form the complete manifest-declared bundle
- **THEN** size, digest, schema, generation, or semantic identity validation rejects the invocation and no partial logical Feed is exposed

#### Scenario: Canonical raw retrieval fails
- **WHEN** the canonical-main manifest or any declared artifact is rate-limited, unavailable, redirected, times out, returns an HTTP error, or otherwise cannot be retrieved under the existing bounded transport contract
- **THEN** consumption fails closed with a precise retrieval failure and does not query the GitHub REST API or another source

## MODIFIED Requirements

### Requirement: Feed bundle consumption rejects invalid or failed products
The consumer health boundary SHALL first validate canonical manifest bytes and the complete ordered safe inventory before using it for local or remote artifact discovery. It SHALL then validate every required artifact and its integrity, reconstruct the logical Feed, and apply the existing structural, identity, Provider freshness, pipeline, warning, provenance, and calendar-horizon semantics through the same semantic authority used for repository-local bundles. It SHALL accept healthy bundles, accept degraded bundles while preserving exact warnings and Provider availability metadata, and reject `pipeline.status = failure`. A consumer needing one domain MAY parse only that domain's evidence after validating hashes and required existence for the complete inventory.

Remote consumption SHALL NOT reinterpret retrieval time or invocation time as evidence freshness, source publication time, or Provider availability. It SHALL NOT add a consumer-level maximum Feed age, contact Providers to verify a degraded outcome, carry forward evidence, substitute another source, or add remote transport metadata to the logical Feed schema or identity.

#### Scenario: Healthy bundle is consumed
- **WHEN** a complete valid local or canonical-main remote bundle is healthy and satisfies the existing embedded Feed semantics
- **THEN** the consumer accepts it and can select evidence by manifest domain inventory

#### Scenario: Degraded bundle is consumed
- **WHEN** a complete valid local or canonical-main remote bundle is degraded and satisfies the existing embedded Feed semantics
- **THEN** the consumer accepts it and preserves manifest pipeline warnings and Provider availability metadata without contacting a Provider

#### Scenario: Structurally valid failure bundle is presented
- **WHEN** bundle files pass structure and identity checks but pipeline status is `failure`
- **THEN** the consumer rejects it as non-consumable

#### Scenario: Retrieval occurs after publication
- **WHEN** invocation time or retrieval time is later than the Feed's source-semantic timestamps
- **THEN** those transport times do not replace or refresh `evidence_cutoff_at`, collection timestamps, Provider freshness, source publication time, or evidence identity

### Requirement: Normal Skill consumption never becomes Feed production
Normal Skill invocation SHALL use one minimal internal remote Feed consumer entry and SHALL NOT invoke Provider adapters, the local Feed producer, hosted deployment machinery, rate state, checkpoint, lease, or collection locks. The existing minimal local Feed producer SHALL remain available only for GitHub Actions, development, tests, Provider diagnostics, and explicit operator execution; its production, dry-run, state, diagnostics, and exit behavior SHALL remain unchanged.

Remote retrieval, transport, validation, or consumability failure SHALL stop the invocation. It SHALL NOT fall back to local Provider collection, repository-local `feeds/` or `latest.json`, another repository, another branch or commit, a persistent cache, or any partially retrieved evidence. Remote consumption SHALL use temporary isolated storage only and SHALL leave repository `feeds/`, `.feed-state/`, and other persistent Feed state unchanged.

#### Scenario: Remote retrieval fails
- **WHEN** any required remote operation exhausts its permitted bounded attempt or returns an unusable response
- **THEN** the invocation exposes a typed precise failure, produces no logical Feed, invokes no Provider or local producer, and mutates no persistent Feed product or runtime state

#### Scenario: Remote bundle validation fails
- **WHEN** the manifest or any required artifact is missing, unsafe, non-canonical, unsupported, schema-invalid, size- or digest-mismatched, mixed-generation, identity-invalid, or otherwise non-consumable
- **THEN** the whole invocation fails closed without local fallback, stale local substitution, or partial evidence output

#### Scenario: Local producer is explicitly operated
- **WHEN** GitHub Actions, a developer, a test, a diagnostic, or an operator explicitly invokes the existing local Feed producer
- **THEN** the producer retains its existing behavior independently of the normal Skill remote consumer entry

#### Scenario: Remote consumption completes
- **WHEN** a complete canonical-main healthy or degraded bundle is retrieved and accepted
- **THEN** temporary files are removed after the validated logical Feed is emitted and repository Feed products and runtime state remain unchanged

## REMOVED Requirements

### Requirement: Canonical published Feed is consumed from one commit-pinned snapshot
**Reason**: Commit discovery adds a GitHub REST API dependency and anonymous rate-limit failure mode that is not needed to establish Feed semantic integrity.

**Migration**: Normal Skill consumers retrieve the manifest and its declared artifacts from the canonical `raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feeds/` root and rely on the unchanged fail-closed bundle validation boundary.
