## ADDED Requirements

### Requirement: Canonical published Feed is consumed from one commit-pinned snapshot
Normal Skill Feed consumption SHALL resolve branch `main` of the public repository `KadenLiu168/follow-the-money` to one exact Git commit before retrieving Feed products. After resolution succeeds, that invocation SHALL retrieve `feeds/feed-manifest.json` and every Feed artifact from that immutable commit only; it SHALL NOT resolve the branch again or use a mutable branch URL for any bundle file. Commit discovery and Feed retrieval SHALL require no GitHub token or Provider credential.

The pinned manifest SHALL remain the only authoritative bundle entry point. The consumer SHALL retrieve exactly the artifact paths declared by its validated ordered inventory and SHALL NOT infer filenames, maintain another domain-to-path registry, enumerate the remote `feeds/` directory, or use Git history as a Feed query API.

#### Scenario: Published Feed is pinned before retrieval
- **WHEN** canonical branch discovery returns a valid exact commit and its pinned manifest declares a complete safe artifact inventory
- **THEN** the manifest and every artifact request use that same exact commit and the reconstructed logical Feed is associated with no mutable-branch read window

#### Scenario: Branch changes during one invocation
- **WHEN** repository `main` advances after an invocation has resolved its commit
- **THEN** that invocation continues to retrieve every bundle file from the already resolved commit and does not switch generations

#### Scenario: Manifest declares the artifact inventory
- **WHEN** a pinned manifest is accepted for retrieval
- **THEN** only its exact validated inventory paths are requested and no remote directory enumeration or independently derived artifact path is used

#### Scenario: Canonical commit cannot be resolved
- **WHEN** commit discovery fails, is rate-limited, returns an HTTP error, times out, or returns an invalid commit response
- **THEN** consumption fails closed with a precise retrieval failure and exposes no Feed

### Requirement: Normal Skill consumption never becomes Feed production
Normal Skill invocation SHALL use one minimal internal remote Feed consumer entry and SHALL NOT invoke Provider adapters, the local Feed producer, hosted deployment machinery, rate state, checkpoint, lease, or collection locks. The existing minimal local Feed producer SHALL remain available only for GitHub Actions, development, tests, Provider diagnostics, and explicit operator execution; its production, dry-run, state, diagnostics, and exit behavior SHALL remain unchanged.

Remote discovery, transport, validation, or consumability failure SHALL stop the invocation. It SHALL NOT fall back to local Provider collection, repository-local `feeds/` or `latest.json`, another repository, another branch or commit, a persistent cache, or any partially retrieved evidence. Remote consumption SHALL use temporary isolated storage only and SHALL leave repository `feeds/`, `.feed-state/`, and other persistent Feed state unchanged.

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
- **WHEN** a complete pinned healthy or degraded bundle is retrieved and accepted
- **THEN** temporary files are removed after the validated logical Feed is emitted and repository Feed products and runtime state remain unchanged

## MODIFIED Requirements

### Requirement: Minimal internal Feed entry reports bundle outcomes
Exactly one minimal internal Feed producer entry SHALL preserve existing configuration, explicit product/runtime roots, deterministic clock/window injection, deadline, status, `--dry-run`, source-completeness, Provider-availability diagnostics, and typed exit behavior. A successful publication status SHALL expose `feed-manifest.json` as the product entry path and matching `run_id` and cutoff. Dry-run SHALL build and validate the same in-memory manifest and domain artifacts without writing bundle products or advancing the checkpoint. Existing Provider work, rate-state, lock, and exit-code semantics SHALL remain unchanged. This producer entry SHALL NOT be the normal Skill consumption entry.

#### Scenario: Successful publication is reported
- **WHEN** a healthy or accepted degraded bundle is durably activated
- **THEN** the producer command exits `0` and status names `feed-manifest.json` with matching identity and cutoff

#### Scenario: Dry run succeeds
- **WHEN** dry-run produces a valid healthy or degraded bundle candidate
- **THEN** the producer command exits `0`, reports the candidate, creates or replaces no bundle product, and does not advance the checkpoint

#### Scenario: Blocked degradation is reported
- **WHEN** blocked exemption is the only source-acquisition issue
- **THEN** the producer command exits `0` with `degraded` status and deterministic diagnostics naming each blocked Provider, reason, and affected coverage group

#### Scenario: Source completeness fails
- **WHEN** planned source work has non-exempt incompleteness
- **THEN** the producer command preserves deterministic Provider diagnostics, exits `1`, and does not admit a bundle to publication

### Requirement: Feed bundle consumption rejects invalid or failed products
The consumer health boundary SHALL first validate canonical manifest bytes and the complete ordered safe inventory before using it for local or remote artifact discovery. It SHALL then validate every required artifact and its integrity, reconstruct the logical Feed, and apply the existing structural, identity, Provider freshness, pipeline, warning, provenance, and calendar-horizon semantics through the same semantic authority used for repository-local bundles. It SHALL accept healthy bundles, accept degraded bundles while preserving exact warnings and Provider availability metadata, and reject `pipeline.status = failure`. A consumer needing one domain MAY parse only that domain's evidence after validating hashes and required existence for the complete inventory.

Remote consumption SHALL NOT reinterpret retrieval time, invocation time, or Git commit time as evidence freshness, source publication time, or Provider availability. It SHALL NOT add a consumer-level maximum Feed age, contact Providers to verify a degraded outcome, carry forward evidence, substitute another source, or add remote transport metadata to the logical Feed schema or identity.

#### Scenario: Healthy bundle is consumed
- **WHEN** a complete valid local or commit-pinned remote bundle is healthy and satisfies the existing embedded Feed semantics
- **THEN** the consumer accepts it and can select evidence by manifest domain inventory

#### Scenario: Degraded bundle is consumed
- **WHEN** a complete valid local or commit-pinned remote bundle is degraded and satisfies the existing embedded Feed semantics
- **THEN** the consumer accepts it and preserves manifest pipeline warnings and Provider availability metadata without contacting a Provider

#### Scenario: Structurally valid failure bundle is presented
- **WHEN** bundle files pass structure and identity checks but pipeline status is `failure`
- **THEN** the consumer rejects it as non-consumable

#### Scenario: Retrieval occurs after publication
- **WHEN** invocation time, retrieval time, or pinned commit time is later than the Feed's source-semantic timestamps
- **THEN** those transport times do not replace or refresh `evidence_cutoff_at`, collection timestamps, Provider freshness, source publication time, or evidence identity
