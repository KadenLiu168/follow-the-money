## Why

Current `news`, `macro_release`, and `policy` items preserve source evidence but leave the Host Agent to rediscover the subject, event kind, reporting period, and displayable facts from titles, identifiers, and `raw_metadata`. ECO-130 adds a closed deterministic context beside the existing payload so the current validated Feed is directly useful for evidence-preserving Digest wording without adding interpretation or another runtime.

## What Changes

- Add one shared, closed `semantic_context` item structure with bounded entities, event/time facts, numeric facts, and a domain-discriminated extension; do not create parallel top-level News/Macro/Policy semantic schemas.
- Deterministically construct context for every newly acquired or replacement `news`, `macro_release`, and `policy` item from already normalized Provider evidence and fixed Provider-local mappings.
- Express news subjects, event categories, document facts, and explicitly referenced entities; macro indicator, reporting period, observations, and source-supported revisions; and policy issuer, type, action, effective date, and affected scope.
- Reuse ECO-125 canonical numeric parsing and validation for numeric context while preserving its bounded numeric-only responsibility; ECO-130 does not turn that primitive into a generic fact framework.
- Keep legacy structurally valid Feed v4 bundles readable and preserve existing byte-identical carry-forward, including carried slices whose cadence status becomes `stale`, while requiring newly acquired or replacement items in the three affected domains to contain valid context. Identical normalized evidence produces byte-identical context and canonical Feed identity; changing a context fact changes the existing semantic projection and digest.
- Reject unknown context members and analytical semantics such as impact, signal, prediction, recommendation, ranking, sentiment, or market direction.
- Preserve current payload discriminators, Provider manifests and contract versions, item identity, source provenance, acquisition, publication, freshness, snapshot, and Host-Agent presentation responsibilities.

## Capabilities

### New Capabilities

- `semantic-context`: Defines the single closed semantic-context primitive and deterministic News/Macro/Policy domain mappings, including evidence-only boundaries and numeric reuse.

### Modified Capabilities

- `feed-evidence-pipeline`: Requires semantic context on newly acquired or replacement `news`, `macro_release`, and `policy` items and includes it in canonical validation, identity, artifacts, and bounded legacy-read/carry compatibility.

## Impact

- Producer semantic layer: a shared context model/validator under `src/follow_the_money/semantic/` plus small Provider-specific News, Macro, and Policy mapping modules; no orchestration layer or network work is added.
- Provider normalization: Federal Reserve and PBOC policy, BLS/NBS/SSE/SZSE news, and NBS macro-release item construction attaches context after existing source extraction and payload normalization. Existing domain classification is retained, including BLS and unstructured NBS releases remaining `news`.
- Feed contract: `schemas/feed.schema.json`, artifact validation, semantic validation, canonical item bytes, `content_digest`, `run_id`, and representative fixtures/tests. Existing item IDs remain source-identity based and are not regenerated from context.
- Documentation: current schema/reference and Host-Agent evidence-only guidance where the new published field must be described.
- No new Provider, Provider request, credential, dependency, model/LLM runtime, ranking, analysis, recommendation, Digest generator, or Feed domain.
