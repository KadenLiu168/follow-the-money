## Context

See `proposal.md` for motivation. The accepted architecture has one live evidence-only Feed and a set of typed, deterministic post-Feed libraries with no production orchestration caller. `feed-evidence-pipeline` owns the detailed live Feed contract, `deterministic-research-engine` owns the detailed retained-domain contracts, and `deterministic-core-retention` protects the negative runtime and wiring boundaries.

ECO-33 is the first Phase-4 semantic contract Change. It must make the Skill's capability ownership explicit without converting internal Python boundaries into Agent contracts or deciding the responsibility, trust, grounding, or runtime questions assigned to later Changes.

## Goals / Non-Goals

**Goals:**

- Establish one normative, closed, semantic catalog that future contract work can reference.
- Ground every catalog family by reference to already accepted living behavior rather than restating formulas or algorithms.
- Make current execution status auditable and truthful while preserving the Feed-only production topology.
- Keep implementation machinery replaceable behind the semantic boundary.
- Make the Phase-3-to-Phase-4 transition explicit in the one living-baseline requirement whose old wording would otherwise conflict.

**Non-Goals:**

- Design an Agent data model, serialized boundary, callable facade, protocol, adapter, orchestration topology, or runtime.
- Allocate operational responsibility, mutation authority, trust, grounding, validation, unsupported-claim handling, retry, or rewrite behavior.
- Modify production behavior, tests, schemas, configuration, Providers, financial formulas, dependencies, or caller wiring.
- Turn architecture status labels into executable data or add tests that merely hard-code Markdown catalog names.

## Decisions

### 1. Use one semantic catalog with six capability families

The new `skill-capability-surface` capability groups behavior by stable semantic purpose: Evidence Feed; Evidence and Event Structuring; Market Analytics and State; Confidence and Watchlist; Scoring and Ranking; and Deterministic Audit. The catalog is closed for ECO-33 so future work cannot silently infer extra capabilities from modules, classes, or helper functions.

Alternative considered: mirror individual Python modules, functions, or dataclasses. Rejected because that would couple the future Skill-Agent contract to refactorable implementation layout and would create an accidental method-level API design.

Alternative considered: collapse every post-Feed behavior into one generic deterministic-engine capability. Rejected because it would not answer which distinct semantic behaviors the Skill owns and would give ECO-34/ECO-35 an ambiguous boundary.

### 2. Reference detailed living contracts instead of duplicating them

Each catalog family states its purpose, ownership, status, key boundary, and authoritative existing capability. Detailed Feed semantics remain in `feed-evidence-pipeline`; detailed ledger, Event, market, confidence, watchlist, scoring, ranking, and audit semantics remain in `deterministic-research-engine`.

Alternative considered: copy the detailed formulas, thresholds, schemas, and scenarios into the new spec. Rejected because duplicated normative truth would drift and would make ordinary domain evolution appear to require two parallel contract edits.

### 3. Treat execution status as an architecture assertion

`live-production` identifies only the Evidence Feed. `retained-no-production-caller` identifies each of the five post-Feed families. These labels are normative descriptions used during spec, documentation, and caller-graph review; they are not values implemented in runtime code, configuration, schema, or a capability registry.

Alternative considered: add a machine-readable capability registry. Rejected because ECO-33 does not define capability discovery, enablement, runtime invocation, or a consumer for such data. A registry would prematurely choose a Phase-5 mechanism.

### 4. Keep internal infrastructure behind the semantic boundary

Provider adapters/manifests, HTTP/rate/lock/configuration machinery, serialization and digest helpers, publication filesystem mechanics, similarity primitives, internal helpers, and Python layout remain implementation details. They may continue to be governed by their owning living specs where behavior is normative, but they do not become Host-Agent capability names.

Alternative considered: expose operational Feed subcomponents as capabilities. Rejected because future Host-Agent integration relies on Feed behavior and invariants, not on the repository's current collection implementation.

### 5. Modify only the obsolete Phase-3 sentence

The `deterministic-core-retention` delta copies the complete `OpenSpec living baseline matches the active architecture` requirement and preserves all inherited scenario names. It replaces the blanket requirement to leave the future Agent Contract undefined with the narrower rule that the semantic Skill capability surface may be defined while concrete Agent contracts and runtime integration remain deferred.

`Baseline acceptance uses semantic trace evidence` remains unchanged because it records what the ECO-32 acceptance Change did not introduce. Beginning Phase 4 does not rewrite that historical/process acceptance fact.

Alternative considered: broadly rewrite both baseline requirements. Rejected because it would blur ECO-32's acceptance evidence with ECO-33's new semantic contract and exceed the minimal delta.

### 6. Apply is documentation-and-contract alignment only

Apply will add/sync the OpenSpec delta and update only stale current-facing language in `SKILL.md`, `README.md`, `README.zh-CN.md`, and `docs/architecture.md`. The wording will distinguish what is defined now from ECO-34, ECO-35, Agent-schema/invocation/orchestration, and Phase-5 decisions that remain deferred. `AGENTS.md` will remain unchanged unless Apply finds a directly contradictory development gate that cannot truthfully stand; no such contradiction is currently expected.

Verification will use artifact inspection, strict OpenSpec validation, the canonical repository quality gate, and a fresh static caller/schema/import review. Existing runtime regressions provide evidence that production behavior remains unchanged; no runtime behavior will be manufactured for coverage.

## Risks / Trade-offs

- [Semantic family wording drifts from detailed domain contracts] → Keep detailed algorithms exclusively authoritative in existing living capabilities and phrase the new catalog as references plus boundaries.
- [A reader mistakes `retained-no-production-caller` for an enablement state or future API promise] → Normatively forbid runtime/config/schema/registry representation and explicitly state that naming a capability adds no caller.
- [Documentation implies the whole Skill-Agent contract is now complete] → Use a two-part statement: semantic capability surface defined; responsibility, trust, grounding, Agent schemas, invocation, orchestration, and runtime still deferred.
- [Planning accidentally causes production wiring or schema expansion during Apply] → Keep production code, `schemas/`, Providers, configuration, and imports outside the task allowlist; verify caller graph and schema inventory after edits.
- [The narrow MODIFIED delta loses inherited scenarios during archive] → Preserve the complete requirement block and all inherited scenario names, then validate strictly before Apply and archive.

## Migration Plan

1. Add the new living capability through this Change's delta and apply the narrow `deterministic-core-retention` requirement modification.
2. Update only current-facing documents whose Phase-3 gate language becomes stale.
3. Verify no production/runtime/schema/caller change, run the canonical quality gate, and run required OpenSpec checks.
4. If review finds any unintended runtime, schema, or wiring change, revert that out-of-scope edit rather than adapting the semantic contract to it.

No data migration, deployment, compatibility shim, or runtime rollback is required because ECO-33 changes contracts and documentation only. Before archival, rollback is removal of this active Change's attributable contract/documentation edits; archival remains a separate authorization boundary.
