## Why

The current `DigestContext` projects every validated Feed item and requires visible per-domain reconciliation, which turns Feed completeness into an exhaustive reader-facing audit report. The normal Digest needs a deterministic reader-structuring boundary that preserves the complete Feed as authority while exposing only explicitly proven current updates, compact domain status, and material limitations to the Host Agent.

## What Changes

- **BREAKING** Replace normal Agent-facing `DigestContext` v1 with v2: retain the Feed binding, replace complete `domains[].items[]` and full Provider outcomes with `content.updates[]`, compact `status.domains[]`, and closed `status.limitations[]`.
- Add a typed, deterministic `DigestUpdateUnit` with a closed unit type, explicit event-time semantic, closed evidence surface, source provenance, deterministic identity, and traceability to supporting Feed item IDs.
- Classify current membership only from closed domain authorities: news publication time, macro release time, policy announcement time, and SEC acceptance time. Keep Form 13F current-state evidence out of substantive content when its acceptance predates the Feed window, and retain Form 4 and beneficial-ownership entries as one accession-level update each.
- Keep CFTC positioning rows out of substantive content when the Provider slice is carried, stale, or lacks explicit shared report publication identity sufficient to construct one report-level update; emit only a compact deterministic status.
- Compress unavailable Provider and coverage conditions into closed material-limitation descriptors instead of exposing the complete Provider audit surface.
- Replace Feed-wide presentation accounting with claim-level traceability: every presented factual claim remains supported by a prepared update and Feed evidence, but Feed items are not required to become Digest statements.
- Preserve Host-Agent ownership of evidence-preserving summarization, source-supported presentation grouping, headings, readability ordering, consolidation, and formatting while removing Host-Agent responsibility for membership classification and exhaustive omission accounting.
- Preserve Feed schemas, canonical bytes, identity, publication, Provider acquisition, retrieval validation, evidence authority, and fail-closed behavior; add no Digest schema, persisted context, renderer, prompt pipeline, model runtime, or orchestration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `digest-preparation-contract`: Replace exhaustive v1 projection with deterministic v2 update construction, domain membership classification, compact status and limitation derivation, ordering, traceability, and canonical guarantees.
- `digest-presentation-contract`: Make prepared current updates the substantive input, replace visible reconciliation with claim-level traceability and non-exhaustive reader-facing compression, and evolve each domain contract around reader-facing units and current-membership authority.
- `information-digest-invocation`: Require normal `/follow-the-money` consumption to use `DigestContext` v2 and disclose only material limitations rather than complete Feed and Provider accounting.
- `skill-agent-responsibility-boundary`: Move current-membership and reference-state classification into deterministic preparation while retaining evidence-preserving editorial presentation in the Host Agent.

## Impact

- Primary runtime: `src/follow_the_money/digest.py` and `scripts/skill/prepare-feed` output contract.
- Contract guidance: `SKILL.md`, `references/digest/`, `references/feed-contract.md`, architecture/feed-contract documentation, READMEs, and runbooks that describe v1 or exhaustive accounting.
- Verification: Digest preparation, presentation-contract, documentation, caller-boundary, safety, and determinism regressions, including a large reference-state fixture with few current updates.
- Unchanged systems: Feed and artifact schemas, Provider manifests/configuration, collection, snapshot selection, publication, remote consumption, Feed identity, and persistent state.
