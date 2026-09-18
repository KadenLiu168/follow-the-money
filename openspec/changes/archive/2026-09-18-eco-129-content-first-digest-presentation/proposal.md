## Why

The current Digest presentation authority requires content and audit information but
does not define their semantic priority, so a final Digest can still lead with Feed
status, coverage, or reconciliation before reaching the current Feed content. The
presentation contract needs to make current-window content the primary reading
surface while retaining complete auditability.

## What Changes

- Define a content-first semantic presentation hierarchy in the global Digest
  presentation contract without prescribing Markdown headings, heading levels,
  fixed section order, or visual style.
- Make current-window updates the primary substantive surface for a healthy Feed
  with presentable updates, while keeping status, coverage, freshness, warnings,
  reconciliation, and limitations as a complete secondary audit surface.
- Permit a concise pre-content caveat for a degraded but usable Feed only when the
  limitation materially affects interpretation; the caveat does not replace the
  complete audit context.
- Require a valid Feed with no presentable updates to say so accurately, create no
  content, and then expose enough status, cutoff, coverage, and limitations to
  distinguish an empty window from collection or Provider problems.
- Preserve local provenance and attribution near the statements they support, and
  preserve all existing compression reconciliation, traceability, and omission
  disclosure semantics while changing only their presentation priority.
- Keep `SKILL.md` as the thin orchestration boundary established by ECO-128 and add
  focused regression coverage that prevents it from becoming a second presentation
  authority or reintroducing audit-first ordering.

Non-goals are a fixed Markdown template or headings; a renderer, prompt pipeline,
LLM/model runtime, or Agent orchestration; changes to `DigestContext`, Feed schemas,
Providers, collection, publication, retrieval, validation, deterministic
preparation, compression semantics, or failure behavior; and any ranking,
importance, relevance, significance, analysis, or filtering capability.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `digest-presentation-contract`: Require content-first Host-Agent presentation while
  preserving audit information, evidence proximity, empty-window truthfulness,
  compression accounting, and the existing static-guidance/runtime boundary.

## Impact

- Contract: `openspec/specs/digest-presentation-contract` gains the accepted
  content-first presentation requirement through this Change's delta spec.
- Documentation: `references/digest/presentation-contract.md` becomes explicit about
  primary content, secondary audit context, material degradation caveats, and
  zero-update behavior.
- Tests: `tests/test_digest_presentation_contract.py` gains static semantic
  regressions without asserting a fixed heading or template.
- `SKILL.md` already contains no numbered Digest-output ordering after ECO-128; no
  prose change is planned unless Apply discovers a current contradictory instruction.
- Runtime and data surfaces remain unchanged, including `src/`, `scripts/`,
  `schemas/`, `providers/`, configuration, collection, publication, and the shared
  compression and domain presentation contracts.
