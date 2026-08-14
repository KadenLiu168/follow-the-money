## Context

The repository was first implemented from the still-active
`implement-follow-the-money-repository` Change as a script-first/LLM-last
standalone application and Agent Skill. Later archived Changes removed the
embedded LLM runtime and public CLI, then aligned typed Feed failures and the JSON
Schema boundary. Those later Changes updated only the capabilities they declared;
the original Change was never archived and three previously synced living specs
still describe resolver, editor, Brief, Bundle, replay, and model-era production
paths that no longer exist.

The resulting OpenSpec graph is structurally valid but semantically inconsistent:

```text
active change                           living specs
─────────────                           ────────────
implement-follow-the-money-repository   deterministic-core-retention  (current)
  └─ OpenAI / four passes / CLI          multi-component-resolver...   (removed)
                                         production-story-family...    (removed)
                                         production-market-state...    (partly retained,
                                                                         falsely wired)
```

Production reality is narrower. `providers/` and `feed/` implement the only live
path and publish `feed.schema.json`. Canonical, schema, configuration, and boundary
utilities support that path. Ledger, candidate, Event, market, state, watchlist,
scoring, selection, and safety modules are retained deterministic libraries, but
there is no post-Feed production orchestrator. Historical archives are valuable
evidence of how the repository reached this state, but they are not living
requirements.

OpenSpec 1.6.0 applies requirement-level `ADDED`, `MODIFIED`, `REMOVED`, and
`RENAMED` deltas but has no capability-directory deletion operation. Removing all
requirements would leave an invalid or misleading empty capability, so retiring a
whole living capability requires an explicit scoped deletion of its current spec
directory while its archived Change remains intact.

## Goals / Non-Goals

**Goals:**

- Make current specs plus active changes one non-contradictory description of the
  Agent-only Skill and deterministic engine that exist now.
- Preserve the full current Feed contract at the serialized external boundary.
- Describe retained internal deterministic behavior without claiming nonexistent
  production orchestration.
- Preserve exact historical Changes under `openspec/changes/archive/`.
- Provide requirement-to-code-to-test evidence and semantic gates in addition to
  structural OpenSpec validation.
- Leave a clean boundary on which a later Agent Contract Change can depend.

**Non-Goals:**

- Change application code, tests, configuration, schemas, providers, calculations,
  workflows, Feed data, or deployment state.
- Restore any LLM SDK, model/API-key configuration, prompt, pass runtime, public
  CLI, Brief pipeline, Bundle/replay, or live evaluation.
- Design `ResearchContext`, `AgentAnalysis`, `BriefContext`, Agent schemas, Agent
  orchestration, or final Brief validation.
- Rewrite archived Changes to make historical documents look current.
- Expand internal Python objects into serialized JSON Schema contracts.

## Decisions

### 1. Treat code, focused tests, and current runtime outputs as the factual baseline

Every proposed living requirement must trace to current implementation and focused
tests, or be an explicit negative architecture invariant. Old proposals, completed
task checkboxes, documentation, and aggregate green tests are supporting evidence,
not independent proof. Contradictions are resolved in favor of current code plus
the two post-runtime-removal archived Changes.

Alternative considered: accept the current four living specs because
`openspec validate --all --strict` passes. Rejected because validation checks
artifact structure, not whether required modules and paths still exist.

### 2. Archive the superseded original Change without syncing its delta specs

After separate explicit archive authorization, run:

```bash
openspec archive implement-follow-the-money-repository --skip-specs
```

The archive must occur before the normalized specs become authoritative. A normal
archive is prohibited because it would add the original six standalone/model-era
capabilities to main specs. The archived artifact remains unchanged as historical
evidence.

Alternative considered: rewrite the original Change in place. Rejected because it
would falsify the record of what was proposed and implemented.

### 3. Retire obsolete living capabilities instead of preserving tombstones

Delete only these current living spec directories during the normalization:

- `openspec/specs/multi-component-resolver-block-processing/`
- `openspec/specs/production-story-family-resolution/`
- `openspec/specs/production-market-state-pipeline/`

Their archived Changes remain untouched and recoverable. No other current spec is
removed. This direct deletion is necessary because OpenSpec 1.6.0 cannot express a
whole-capability deletion and requirement-only removal would leave an empty or
misnamed living capability.

Alternative considered: transform them into negative tombstones. Rejected because
future Agents would still see obsolete capability names such as `production-*` and
could mistake absence documentation for a supported product surface.

### 4. Use two detailed capabilities beneath the architecture guardrail

The normalized living baseline has three layers:

```text
deterministic-core-retention     architecture and forbidden surfaces
            │
            ├── feed-evidence-pipeline
            │     live provider → Feed → validation → publication path
            │
            └── deterministic-research-engine
                  retained post-Feed libraries; no production orchestrator
```

`feed-evidence-pipeline` is extracted from the original implemented Feed delta and
updated only where product terminology changed: “minimal internal Feed entry”
replaces public CLI language, while provider, cutoff, identity, provenance,
degradation, rate-state, deadline, and publication semantics remain unchanged.

`deterministic-research-engine` consolidates retained internal contracts that were
previously scattered across model-era capabilities. It records exact deterministic
ownership and current wiring status without defining future Agent-facing shapes.

Alternative considered: create one capability per retained module. Rejected as
unnecessary fragmentation before the Agent Contract establishes stable external
boundaries.

### 5. Keep JSON Schema at the Feed boundary and Python contracts internally

The Feed remains the only current serialized external artifact and must validate
against `feed.schema.json` plus semantic, identity, digest, provenance, and temporal
invariants. Ledger, candidate blocks, Events, market snapshot/state, watchlist,
scoring, selection, and audit inputs remain internal Python structures protected by
types, domain invariants, and deterministic tests. This Change adds no schema solely
to make the baseline appear more formal.

### 6. Separate structural validation from semantic acceptance

Acceptance uses both:

- OpenSpec structure: `openspec doctor --json` and
  `openspec validate --all --strict --json`.
- Semantic tracing: every living requirement maps to implementation and focused
  tests; current specs and active changes contain no positive requirement for a
  removed runtime surface; all claimed production callers are verified by imports
  or entry-path execution.

The repository quality gate is rerun as non-regression evidence even though no
business code is expected to change. Existing unrelated worktree changes are
excluded from the Change.

## Risks / Trade-offs

- **[A retained behavior is accidentally lost while extracting the Feed spec]** →
  Trace every original Feed requirement to current code/tests and record any
  deliberate wording change; do not shorten contracts merely for readability.
- **[A removed production claim is reintroduced under a new name]** → Require
  call-graph evidence for every production-wiring statement and state the no-caller
  boundary explicitly.
- **[Normal archive syncs the old model-era delta specs]** → Require the exact
  `--skip-specs` command and separate archive authorization; verify the resulting
  current spec set immediately afterward.
- **[Capability deletion loses history]** → Delete only living spec directories;
  preserve archived Changes and verify their files before and after normalization.
- **[The new deterministic engine spec pre-designs the Agent Contract]** → Specify
  only existing Python inputs, outputs, invariants, and caller status; prohibit
  Agent-facing objects and orchestration in scope and acceptance.
- **[Structural validation passes despite semantic drift]** → Make the trace matrix,
  removed-surface audit, and caller audit required acceptance evidence.
- **[Unrelated worktree state is overwritten]** → Use an explicit path allowlist and
  leave the existing unrelated `AUDIT-2026-08-12.md` deletion untouched.

## Migration Plan

1. Build a current requirement-to-implementation-to-test inventory and verify the
   exact three stale living capabilities and the superseded active Change.
2. Obtain separate explicit authorization, then archive
   `implement-follow-the-money-repository` with `--skip-specs`; verify no original
   delta was synced.
3. Remove only the three obsolete living capability directories and verify their
   historical archived copies remain.
4. Materialize the normalized `deterministic-core-retention`,
   `feed-evidence-pipeline`, and `deterministic-research-engine` living specs through
   the normal OpenSpec sync/archive lifecycle for this Change.
5. Run structural validation, semantic tracing, caller checks, and the repository
   quality gate; confirm production files and unrelated worktree state are unchanged.

Rollback is OpenSpec-only: restore the three living spec directories and active
Change directory from version control if validation fails before delivery. Do not
roll back or modify archived historical content or production code.

## Open Questions

None. The future Agent Contract deliberately remains a separate Change after this
baseline is normalized and accepted.
