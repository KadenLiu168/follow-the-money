## Why

Hosted Feed executions exposed two repository-owned correctness defects: the shared Provider fetch path does not consistently apply manifest-resolved request identity, and shared HTML index parsing can abort on malformed date-like tokens in unrelated links. Fixing these now aligns runtime behavior with the accepted Provider contract while preserving truthful visibility of external Provider failures.

## What Changes

- Make every request routed through `BaseAdapter` use the resolved Provider `user_agent`.
- Preserve adapter-specific additional headers while preventing them from overriding the manifest-owned user-agent authority.
- Make the shared lightweight HTML index parser ignore malformed or unrelated date-like candidates instead of aborting Provider normalization.
- Preserve supported Provider date formats, URL validation, provenance, acquisition-window, retry, rate, timeout, and Feed completeness semantics.
- Add deterministic offline regression coverage for request-header propagation and merging, SEC EDGAR compatibility, production-shaped HTML links, malformed navigation links, invalid date-like values, and multiple candidates.
- Keep external blocking, throttling, network instability, and other genuine Provider failures visible and typed; this change does not make Provider success unconditional.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Clarify that the resolved Provider user-agent controls shared outbound requests and that shared HTML index candidate extraction ignores malformed unrelated date-like inputs without weakening evidence admission or Provider failure semantics.

## Impact

- Affected implementation: shared Provider request plumbing and shared HTML index extraction in `src/follow_the_money/providers/adapters.py`.
- Affected tests: deterministic offline Provider adapter and Feed regression tests, primarily `tests/test_adapters.py` and only existing orchestration tests needed to prove unchanged failure semantics.
- Contract impact: additive clarification of existing `feed-evidence-pipeline` behavior; no Provider manifest/schema redesign, new configuration authority, dependency, public API, coverage membership, or architecture change.
- Operational impact: post-delivery hosted verification may confirm repository-owned defects are gone, but external Provider success is not an acceptance precondition.
