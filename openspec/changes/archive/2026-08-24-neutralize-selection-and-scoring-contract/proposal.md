## Why

The retained scoring and selection libraries still encode Analyst, verification-packet, Editor, and Brief delivery assumptions even though the current architecture ends at deterministic Feed evidence and leaves post-Feed libraries without a production orchestration caller. ECO-29 must remove those obsolete workflow and presentation contracts before ECO-31 aligns the pre-Agent baseline, while preserving the useful deterministic mathematics, evidence-quality gates, ordering, and redundancy handling.

## What Changes

- Preserve the existing five-component significance model, categorical maps, missing-data and coverage behavior, freshness/exposure/catalyst relevance arithmetic, `0.70 * significance + 0.30 * relevance` formula, and normative Decimal semantics for equivalent semantic inputs.
- **BREAKING** Replace Brief-owned scoring terminology, including `Brief Priority`, with a workflow-neutral base-priority contract; neutralize `Morning Relevance` terminology only as a semantic rename with identical inputs, weights, operation order, and numerical results.
- **BREAKING** Replace the historical selection contract with deterministic ranking whose inputs contain only event identity/time, base priority, deterministic confidence, component coverage, and existing story-family/coexistence information.
- Preserve unresolved-confidence and minimum-component-coverage ineligibility, but remove `analysis_present`, `packet_passed`, `conflict_free`, and `breaking_label`; resolved high, medium, and low confidence values are otherwise rankable.
- **BREAKING** Remove full/compact and Breaking/Unconfirmed output state, Brief thresholds and size limits, and sparse-Brief warnings. Ranking returns the complete eligible set after family-penalty processing, without replacement tiers or limits.
- Preserve frozen base ordering, configured family penalty and zero floor, canonical first-to-later pair exemption, non-transitive pair semantics, and deterministic final ordering exactly.
- Atomically align the closed scoring configuration, focused tests, and `docs/scoring.md`; removed keys are rejected rather than accepted as aliases or hidden fallbacks.
- Keep scoring and ranking as retained typed Python libraries with no production caller or external serialized schema, and leave future Host Agent input/output and orchestration contracts undefined.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-research-engine`: Neutralize the versioned scoring and deterministic selection requirements into workflow-neutral scoring and complete ranking while preserving arithmetic, quality gates, ordering, and family-penalty semantics.
- `deterministic-core-retention`: Align the retained-library summary with neutral event relevance, base priority, and complete ranking so the living baseline does not continue to require removed Brief formats.

## Impact

- Primary implementation: `src/follow_the_money/scoring.py` and `src/follow_the_money/selection.py`, including breaking internal Python symbol and dataclass-field changes with no compatibility aliases because repository tracing found no non-test caller.
- Closed configuration: `config/config.yaml`, `src/follow_the_money/config/model.py`, and `src/follow_the_money/config/load.py`; retain arithmetic, coverage, and family-penalty configuration while removing Brief-only thresholds and counts and atomically renaming any neutralized relevance field.
- Tests: primarily `tests/test_scoring.py`, `tests/test_config.py`, `tests/test_config_provider_normalization.py`, and `tests/test_no_llm_contract.py`, with exact numerical parity and neutral ranking-contract regressions.
- Focused documentation and contract: `docs/scoring.md`, the two affected requirements in `openspec/specs/deterministic-research-engine/spec.md`, and the directly contradictory retained-library summary in `openspec/specs/deterministic-core-retention/spec.md` when applied.
- No dependency, Feed/provider/market/confidence/ClaimAuditor change; no production wiring, external scoring/ranking schema, Agent-owned structure, archived-history edit, ECO-30 audit work, or ECO-31 general baseline cleanup.
