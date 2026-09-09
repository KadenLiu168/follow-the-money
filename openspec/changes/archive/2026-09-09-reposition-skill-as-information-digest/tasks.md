## 1. Lock the Digest Contract in Tests

- [x] 1.1 Replace the obsolete briefing assertions in `tests/test_feed_documentation.py` with positive assertions for an evidence-based information digest, no user-supplied scope, current-Feed-only semantics, provenance/freshness/coverage/limitations, and transparent per-domain compression accounting; verify the focused test fails against the old Skill wording for the intended reasons.
- [x] 1.2 Add negative documentation assertions that normal Skill output does not require financial intelligence, significance, anomaly, signal, prediction, market-impact, investment-judgment, or trading sections while preserving remote-only and fail-closed assertions; verify failures identify stale current-product claims rather than valid Feed or retained-capability terminology.

## 2. Reposition the Skill and Its Loaded References

- [x] 2.1 Rewrite `SKILL.md` metadata, execution diagram, and output requirements around the current evidence-based information digest; include permitted editorial grouping/ordering/consolidation, attributable source language, reconciled per-domain coverage accounting, and prohibited analytical judgments, then verify the focused Skill documentation tests pass.
- [x] 2.2 Update `references/safety-boundary.md` so grounding and admissibility apply to the digest without claiming that the Skill provides financial intelligence or analysis; preserve unsupported-claim handling and the no-investment/trading boundary, then verify focused documentation tests pass.
- [x] 2.3 Update `references/architecture-boundary.md` and the consumption wording in `references/feed-contract.md` to distinguish deterministic Feed ownership from Host-Agent digest presentation while preserving canonical-main retrieval, validation, private-operation independence, and no-fallback behavior; verify focused caller-boundary tests pass.

## 3. Align Repository Contracts and User-Facing Positioning

- [x] 3.1 Update the architecture boundary in `AGENTS.md` to use the published Feed -> validation -> Host Agent summarization/formatting -> information digest model and to keep private Audit/Event operations outside normal Skill behavior; verify the corresponding documentation assertions pass.
- [x] 3.2 Update `README.md` and `README.zh-CN.md` so their lead positioning and current Skill behavior describe an evidence-based information digest rather than a financial research or intelligence product, while truthfully retaining the separate deterministic capability inventory and investment-safety boundary; verify English and Chinese claims are mutually consistent by focused terminology search and documentation tests.
- [x] 3.3 Update `docs/architecture.md` and any other user-facing current-product wording found by a focused audit to reflect Host-Agent digest presentation, transparent compression, and the no-financial-judgment boundary; preserve accurate descriptions of evidence domains and retained capabilities, then verify no stale current-product briefing or research-output claim remains.
- [x] 3.4 Update the `agent-grounding-validation-contract` living-spec Purpose from Agent-owned research output to neutral Agent-owned user-facing output, the only affected purpose text that delta operations cannot update; verify the Purpose remains consistent with this change’s modified requirements and does not weaken grounding guarantees.

## 4. Verify Unchanged Architecture and Contracts

- [x] 4.1 Review the final diff and verify no changes exist under `src/`, `providers/`, `config/`, `schemas/`, `.github/workflows/`, or generated `feeds/`, and that no Provider, Feed production/consumption behavior, schema, credential/model configuration, prompt runtime, or retained-capability caller was introduced.
- [x] 4.2 Run the focused documentation test module and verify all information-digest, caller-boundary, validation, and no-fallback regressions pass.
- [x] 4.3 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository quality gate passes without performing a live Feed dry run.
- [x] 4.4 Run `openspec doctor`, `openspec validate reposition-skill-as-information-digest --strict`, and `openspec validate --all --strict`; verify the active delta, all living specs, and repository OpenSpec state are valid.
