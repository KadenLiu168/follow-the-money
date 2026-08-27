## 1. Focused RED Contract and Determinism Tests

- [x] 1.1 Extend Agent invocation contract fixtures with one minimal valid `event.structure` request and its exact closed success result; keep all existing `audit.text`, `audit.claims`, and typed-error fixtures valid.
- [x] 1.2 Add schema-negative fixtures for missing required Event fields, unknown envelope/input/key-fact/result fields, wrong types, whitespace identities, malformed canonical peer Event IDs, invalid timestamps/precision combinations, unsupported entry/origin types, invalid key-fact structure, and filing display-input conditions.
- [x] 1.3 Add schema-negative fixtures proving caller-supplied fact/Event/family IDs, complete Ledger bookkeeping, arbitrary labels/narrative, internal state, and `verified`, `grounded`, `factually_correct`, `entailed`, `answer_valid`, or `admissible` fields are not accepted.
- [x] 1.4 Add RED deterministic-core tests for mixed effective precisions across input permutations and separate processes with varied `PYTHONHASHSEED`, asserting `economic_effective_time.value` and `precision` come from the same first fact in canonical key-fact order.
- [x] 1.5 Add RED Event process fixtures for stable generated fact IDs, Event ID, evidence/key-fact ordering, `fully_known_at`, effective-time projections, story-family identity, coexistence pairs, display label, key-fact references, and byte-equivalent serialized result under semantic input permutations.

## 2. Closed Event Schema and Minimum Deterministic Mapping

- [x] 2.1 Extend only `schemas/agent-invocation.schema.json` with closed `request_event_structure` and `success_event_structure` variants under `contract_version: 1`; do not add `event.schema.json`, a Ledger schema, another root protocol, or a dependency.
- [x] 2.2 Define the exact bounded key-fact DTO and input conditions from the delta spec, including `FACT|CLAIM`, supported Event origins, nullable value/unit/effective time, declared precision, valid knowledge time, filing-only display fields, and optional canonical Event peers.
- [x] 2.3 Define the exact bounded Event result and ordered `fact_id` / `evidence_id` projection, omitting internal `schema_version`, complete Ledger/Event layouts, caller-owned duplicate inputs, authority/proof fields, narrative, and sibling capability results.
- [x] 2.4 Make the minimum root-cause correction in canonical Event construction so mixed-precision economic value/precision use the same first canonical key fact; change no other Event algorithm or adjacent behavior and make the RED cross-process test pass.
- [x] 2.5 Implement Event mapping locally in `agent_invocation.py` or one small dedicated helper: explicitly validate precision/value and provenance consistency, derive facts with the existing constructor, reject duplicate generated fact IDs, and build one invocation-local Ledger.
- [x] 2.6 Derive the current Event ID through existing canonical utilities, include it with optional story-family peers, form canonical pairs with optional coexisting peers, and invoke existing Event construction without copying identity, ordering, time, family, pair, or label algorithms.
- [x] 2.7 Map the Event result field by field, add fact/evidence references in fact-ID order, validate the complete success envelope against the shared schema, and discard all invocation-local state after the one request.

## 3. Runtime Dispatch, Fail-Closed Behavior, and Backward Compatibility

- [x] 3.1 Extend structural request classification so the exact supported set is `audit.text`, `audit.claims`, and `event.structure`, preserving unsupported-version → unsupported-operation → `invalid_request` precedence and literal dispatch with no registry or discovery path.
- [x] 3.2 Add real one-shot process tests for representative macro/default and filing Events, optional family/coexistence peers, exact DTO-to-core/result mapping, one JSON stdout response, process status `0`, and no stdout diagnostics.
- [x] 3.3 Add pre-construction tests proving unknown fields, malformed identities/times, unsupported fact inputs, absent evidence references, duplicate generated fact IDs, contradictory filing inputs, and forbidden authority/internal fields return `invalid_request` and never construct a Ledger or Event.
- [x] 3.4 Add a focused accepted-request failure test that forces unexpected Event execution or result validation failure and asserts one schema-valid `execution_failure`, non-zero status, no partial result, and no stdout traceback.
- [x] 3.5 Add explicit mapping-equivalence tests comparing `event.structure` output with direct existing fact/Event construction for identity, provenance, ordering, times, family/pairs, and labels without recursively serializing internal objects.
- [x] 3.6 Re-run the complete existing Audit contract/runtime fixtures and assert `audit.text` and `audit.claims` inputs, results, deterministic-negative exit `0`, failure precedence, and caller behavior remain backward compatible.

## 4. Authority, Caller Graph, Feed Independence, and Truthful Status

- [x] 4.1 Add call-count and import/caller-graph tests proving one Event request invokes only Event Structuring once; it does not invoke Audit, Feed, Market, Watchlist, Confidence, Scoring, Ranking, retry, rewrite, entity resolution, candidate grouping, or another operation.
- [x] 4.2 Narrow the existing no-production-caller regression only enough to allow the private invocation adapter to call canonical Event construction; continue rejecting Event callers from Feed, Audit, market/watchlist/confidence/scoring/ranking, legacy workflow, and every unrelated source path.
- [x] 4.3 Add authority tests proving Agent-supplied Event type, entities, fact/evidence selections, peer hypotheses, and display inputs remain Agent-owned; generated identities/ordering do not upgrade verification, grounding, factuality, entailment, correctness, or admissibility.
- [x] 4.4 Run deterministic Feed schema/generation/publication/evidence-only regressions with fixtures and assert Feed neither invokes nor is wrapped by Event Structuring; confirm `schemas/feed.schema.json`, provider/configuration behavior, and the Feed entry remain unchanged without a real-network dry run.
- [x] 4.5 Apply the four Change deltas to `agent-runtime-invocation-contract`, `skill-capability-surface`, `skill-agent-responsibility-boundary`, and `deterministic-research-engine`, reconciling only Purpose/current wording made stale by the verified caller.
- [x] 4.6 Update only stale caller/status statements in `SKILL.md`, `README.md`, `README.zh-CN.md`, and `docs/architecture.md`: describe on-demand `event.structure` as the sole Event caller, keep Audit/Feed independent, and leave Market, Confidence/Watchlist, and Scoring/Ranking retained and unwired.
- [x] 4.7 Review schema, implementation, tests, specs, and docs for forbidden additions: no Ledger mini-API/state/handle, automatic Feed/Event/Audit chain, registry/discovery/framework, second transport, LLM/model/credential runtime, narrative/proof claim, external internal-layout schema, or unrelated refactor.

## 5. Final Verification

- [x] 5.1 Run focused Agent schema/runtime, Ledger/Event, determinism, caller-graph, authority, no-LLM, and Feed regression tests with `.venv/bin/python -m pytest`; record exact commands and results.
- [x] 5.2 Run `git diff --check`, inspect the complete diff against the ECO-51 planning allowlist, and confirm unrelated worktree content, archived Changes, dependencies, provider/configuration files, and `schemas/feed.schema.json` remain untouched.
- [x] 5.3 Run `openspec doctor`, `openspec validate integrate-agent-evidence-event-structuring --strict`, and `openspec validate --all --strict` and resolve only ECO-51-attributable failures.
- [x] 5.4 Run `.venv/bin/python scripts/quality_gate.py` and report the exact canonical result without substituting a weaker gate or running the side-effecting real Feed dry run.
- [x] 5.5 Confirm the final caller graph and acceptance checklist: `event.structure` is the only new operation, Evidence/Event Structuring is on-demand `live-production`, existing Audit is backward compatible, Feed is unchanged/evidence-only, the three deferred families remain `retained-no-production-caller`, and no unresolved contract/code/test/doc conflict is hidden.
