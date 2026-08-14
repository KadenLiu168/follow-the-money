## Why

The production repository has converged on an Agent-only Skill plus deterministic
financial engine, but the OpenSpec living baseline still mixes that architecture
with superseded standalone, embedded-LLM, resolver, Brief, Bundle, and replay
requirements. Before defining the future Agent Contract, current specs and active
changes must become one non-contradictory source of truth that describes the code
and product boundary that exist now.

## What Changes

- **BREAKING** Retire the living `multi-component-resolver-block-processing`,
  `production-story-family-resolution`, and `production-market-state-pipeline`
  capabilities because they require runtime surfaces removed by
  `remove-standalone-runtime`; retain their archived Changes as historical evidence.
- Archive the completed but superseded `implement-follow-the-money-repository`
  Change with `--skip-specs` so its original standalone/internal-LLM delta specs
  never become current requirements. This lifecycle action requires separate
  explicit archive authorization before Apply performs it.
- Establish `feed-evidence-pipeline` as the detailed contract for the only live
  production path: credential-free provider collection, deterministic Feed
  normalization and validation, provenance, rate/deadline discipline, and durable
  publication through the minimal internal Feed entry.
- Establish `deterministic-research-engine` as the contract for retained internal
  deterministic structures and rules, distinguishing utilities consumed by the
  Feed from post-Feed research, scoring, selection, and safety libraries that
  intentionally have no production orchestration caller yet.
- Extend `deterministic-core-retention` with a living-baseline integrity requirement:
  current specs and active changes must not positively require removed LLM/runtime
  surfaces, while historical archives may continue to describe them.
- Add a requirement-to-implementation-to-test trace matrix and semantic validation
  gates; do not treat structural `openspec validate` success as proof that the
  baseline matches production reality.
- Do not modify production code, financial behavior, providers, schemas, tests,
  workflows, deployment state, or the historical contents of archived Changes.
- Do not define or implement `ResearchContext`, `AgentAnalysis`, `BriefContext`,
  Agent schemas, Agent orchestration, or the future Brief contract.

## Capabilities

### New Capabilities

- `feed-evidence-pipeline`: Defines the current credential-free Feed collection,
  external serialized boundary, provenance, failure, and durable-publication
  contracts behind the minimal internal invocation surface.
- `deterministic-research-engine`: Defines the retained deterministic preparation,
  market, Event, scoring, selection, and safety-library contracts together with
  their current production-wiring status.

### Modified Capabilities

- `deterministic-core-retention`: Adds an explicit OpenSpec living-baseline
  integrity requirement without changing the established Agent-only architecture
  or any runtime behavior.

### Retired Capabilities

- `multi-component-resolver-block-processing`: Remove from current specs; its
  resolver-output, unresolved-Bundle, and replay requirements belong only to the
  removed four-pass runtime.
- `production-story-family-resolution`: Remove from current specs; retain the
  surviving pure family-ID and selection rules under
  `deterministic-research-engine`, without claiming live/replay pipeline wiring.
- `production-market-state-pipeline`: Remove from current specs; retain the
  surviving pure market snapshot and classification rules under
  `deterministic-research-engine`, without editor, Brief, Bundle, or replay claims.

## Impact

- Affected OpenSpec state: `openspec/specs/`, the active
  `implement-follow-the-money-repository` lifecycle state, and the new
  `normalize-openspec-baseline` artifacts.
- Historical archived Changes remain unchanged and continue to record the evolution
  from script-first/LLM-last to Agent-only.
- Production code, APIs, dependency set, JSON Schemas, provider behavior, financial
  calculations, test behavior, workflows, generated Feed data, and external
  deployment state are unchanged.
- After normalization, the next Agent Contract Change can depend on a baseline that
  cleanly separates the live Feed, retained deterministic engine, and deliberately
  unimplemented Agent-native workflow.
