# Published Feed Contract

## Retrieval

Normal Skill invocation runs `scripts/skill/prepare-feed`. It retrieves
`feeds/feed-manifest.json` first from the canonical-main raw `feeds/` root
(`https://raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feeds/`), then
retrieves exactly the manifest-declared artifacts into temporary storage. It is
credential-free, makes no Provider request or GitHub REST API request, and has
no local, stale, legacy, partial, or unvalidated fallback.

## Manifest and artifacts

The manifest declares exactly one artifact for each domain, in this order:
`news`, `macro_release`, `policy`, `positioning`, and `filing`. Every artifact
exists even when empty.

Validation is fail-closed and requires canonical UTF-8 JSON, supported schema
versions, the exact ordered inventory with safe paths, matching bytes/size/hash,
matching `run_id` and domain, deterministic item order, and a reconstructed
logical Feed whose `content_digest` and `run_id` recompute exactly. Missing,
extra, duplicate, reordered, corrupt, mixed-generation, traversal, and
identity-invalid state is not consumable.

## Provenance, cutoff, and identity

The Feed's fixed half-open window, `evidence_cutoff_at`, `run_id`, and
`content_digest` are authoritative. Payload observation/effective time, source
publication/update time, Provider retrieval/check time, and Feed generation time
remain distinct. Every item retains traceable source provenance. The Feed is
deterministic, credential-free, and evidence-only; it contains no financial
interpretation or Agent runtime.

## Freshness and degradation

Provider freshness and availability are explicit per Provider. Only a complete,
successful no-observation check may carry an unchanged slice from the fully
validated active bundle. Carried items retain identity, source times, provenance,
lineage, and origin contract hash.

A wholly blocked HTTP 401/403 Provider may produce bounded degraded status when
coverage permits it. Other incomplete work, partial data, unconfirmed failure,
and invalid coverage remain fatal. A valid degraded Feed is consumed with its
warnings, availability, freshness, cutoff, and coverage limits intact.

See `docs/feed-contract.md` and
`openspec/specs/feed-evidence-pipeline/spec.md` for the full contract.
