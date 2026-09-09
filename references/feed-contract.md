# Published Feed Contract

## Retrieval

Normal Skill invocation runs `scripts/skill/prepare-feed`. It retrieves
`feeds/feed-manifest.json` first from the canonical-main
`raw.githubusercontent.com/KadenLiu168/follow-the-money/main/feeds/` root,
then retrieves exactly the manifest-declared artifacts into temporary storage.
It is credential-free, requires no GitHub token or Provider credentials, and
makes zero GitHub REST API requests.

A remote failure or validation failure is terminal. Never invoke the local producer.
There is no local fallback or stale, legacy, partial, or unvalidated substitute.
The local producer remains an explicit surface only for hosted Actions,
development, tests, Provider diagnostics, and operator runs.

## Manifest and artifacts

The manifest declares exactly one artifact for each closed domain, in this
order: `news`, `macro_release`, `policy`, `market_data`, `flow`, `positioning`,
`filing`, and `calendar`. Every artifact exists even when its `items` array is
empty.

Validation is fail-closed and requires:

- canonical UTF-8 JSON and supported schema versions;
- the exact ordered inventory with safe repository-relative paths;
- matching bytes, size, SHA-256, `run_id`, domain, payload type, and item order;
- unchanged provenance and source lineage;
- a reconstructed logical Feed whose `content_digest` and `run_id` recompute
  exactly.

Missing, extra, duplicate, reordered, corrupt, mixed-generation, traversal, or
identity-invalid state is not consumable. Retrieval time does not refresh any
evidence timestamp.

## Provenance, cutoff, and identity

The Feed's evidence window, `evidence_cutoff_at`, `run_id`, and
`content_digest` are authoritative. Keep payload observation/effective time,
source publication/update time, Provider retrieval/check time, and Feed
generation time distinct. Every cited claim must remain traceable to the
relevant Feed item and its source provenance.

The Feed is deterministic, credential-free, and evidence-only. It contains no
financial interpretation, Host-Agent orchestration, or LLM/model path.

## Freshness and degradation

Provider freshness and availability are explicit per Provider. Only a complete,
successful no-observation check may carry an unchanged slice from the fully
validated active bundle. Carried items retain identity, source times,
provenance, lineage, and origin contract hash.

A wholly blocked HTTP 401/403 Provider may produce a bounded degraded Feed
without prior-slice carry-forward. Other incomplete Provider work, partial data,
unconfirmed failures, and invalid coverage remain fatal. A valid degraded Feed
is consumable only with its warnings, availability, freshness, cutoff, and
coverage limits preserved in the information digest. Host-Agent grouping,
compression, and formatting do not alter deterministic Feed ownership or its
provenance and coverage semantics.

Normal Skill consumption supplies only this validated Feed to the Host Agent for
evidence-preserving information-digest presentation. It does not invoke Audit,
Event Structuring, or another retained deterministic capability.

See `docs/feed-contract.md` and `openspec/specs/feed-evidence-pipeline/spec.md`
for the authoritative full contract.
