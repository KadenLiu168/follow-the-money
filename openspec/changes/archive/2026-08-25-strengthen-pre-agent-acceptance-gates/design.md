## Context

See `proposal.md` for motivation. ECO-31 is archived and the current living capability set is exactly `deterministic-core-retention`, `feed-evidence-pipeline`, and `deterministic-research-engine`. The live repository path is Evidence Providers -> deterministic Feed -> Host Agent reasoning and narrative; ledger, candidate/event, market/state, watchlist, scoring/ranking, and `ClaimAuditor` are retained deterministic libraries that may intentionally have no production orchestration caller.

The repository already has focused Feed and deterministic-library suites, `tests/test_no_llm_contract.py`, workflow boundary checks, and `.venv/bin/python scripts/quality_gate.py`. The archived `normalize-openspec-baseline/traceability.md` records a useful earlier matrix, but subsequent archived Changes changed current requirements and evidence. It is therefore seed material, not the ECO-32 acceptance result.

The issue context supplied for ECO-32 places it after ECO-31 and before Phase 4. Apply must reconfirm any accessible Linear blocker state, current active Changes, living specs, worktree state, implementation, tests, and caller graph before recording acceptance.

## Goals / Non-Goals

**Goals:**

- Produce one current, reviewable acceptance decision covering every living Requirement and every critical Pre-Agent architecture boundary.
- Make caller status and historical disposition explicit rather than inferring architecture from module existence or old trace evidence.
- Reuse existing focused regressions and the canonical quality gate without creating a second framework.
- Keep the Apply diff narrow enough to prove that the baseline was evaluated rather than changed to pass.

**Non-Goals:**

- Changing Feed, Provider, configuration, schema, deterministic-library, publication, deadline, rate-state, dependency, CI, or workflow behavior.
- Adding or modifying tests unless a discovered evidence gap is first surfaced as an explicit scope decision outside the assumed zero-test-change design.
- Defining any Phase-4 Agent object, schema, adapter, runtime, protocol, call sequence, or production orchestration.
- Treating retained no-caller libraries as incomplete or wiring them into the Feed.
- Rewriting archived Changes or turning trace metadata into a runtime/serialized contract.

## Decisions

### 1. Strengthen the existing acceptance requirement only

ECO-32 will modify the existing `Baseline acceptance uses semantic trace evidence` requirement under `deterministic-core-retention`. Its full inherited requirement block and all inherited scenario names remain in the delta, with scenarios added for complete Phase-3 evaluation, caller-state distinction, reconciled historical evidence, fail-closed gap handling, and the deferred future boundary.

Alternatives rejected:

- A new verification capability would make project process a parallel permanent domain surface.
- A zero-delta documentation Change would leave the final Phase-3 acceptance conditions implicit.
- Requirements for individual test filenames would make the permanent contract depend on an incidental test layout.

### 2. Create the fresh trace during Apply, from a frozen current inventory

At Apply start, create `traceability.md` inside this Change and record the inspected revision/worktree, active Changes, exact living capability set, and every current Requirement heading. Generate the inventory from the three living specs, then reconcile it manually; do not begin with a copied historical matrix. The trace is Change-local verification evidence, not a fourth living capability or a runtime manifest.

Use one row per current Requirement with these columns:

| Field | Meaning |
| --- | --- |
| Capability / Requirement | Exact current living heading and stable identity |
| Disposition | `current-positive`, `current-negative`, or a documented equivalent |
| Implementation / invariant | Current source/config/schema/docs surface, or the absence rule being audited |
| Caller status | `live-production`, `retained-no-caller`, `negative-invariant`, or `not-applicable`, with caller evidence where relevant |
| Focused evidence | Existing executable tests or a reproducible static/caller audit |
| Result | `accepted`, `rejected`, or `blocked`, recorded only from fresh evidence |

Maintain a separate removed/superseded disposition section. Seed it from the archived `normalize-openspec-baseline/traceability.md`, then verify each reused disposition against current specs, source, tests, all subsequent archived Changes, and current entry-path reachability. Use `historical-superseded` (or an equally explicit label) and never edit the archive.

### 3. Treat production wiring as a caller-graph fact

The trace will audit the minimal Feed entry and its transitive local call/import path. Provider configuration, collection, normalization, Feed validation/identity, health, and publication claims must resolve to real production callers. Retained ledger, candidate/event, market/state, watchlist, scoring/ranking, and audit capabilities must be checked independently and recorded as `retained-no-caller` wherever that remains the accepted state.

Static import closure alone is not sufficient for a positive production claim; inspect the actual entry and call sites. Conversely, absence from the production closure is expected evidence for retained libraries and must not trigger placeholder wiring.

### 4. Reuse executable evidence by contract category

Map current Requirements to existing suites rather than manufacture ECO-32-specific tests:

- Production Feed: Provider/startup resolution, fixture-backed generation, schema/semantic validation, provenance, identity/digest, deterministic output, degradation/coverage, rate/deadline, durable publication/recovery, and invocation/workflow boundaries.
- Retained libraries: ledger, entity and candidate grouping, Event/family utilities, market analytics/state, watchlist, scoring, ranking, safety audit, deterministic behavior, fail-closed boundaries, and intentional no-caller status.
- Architecture: no LLM SDK/runtime/request, prompts, model/API-key configuration, legacy fixed pipeline, public product CLI, or credential dependency.

Specific evidence paths and test names belong in `traceability.md` and `tasks.md`. If a row has no sufficient current evidence, mark acceptance blocked and surface the gap; do not silently add tests or weaken the Requirement.

### 5. Use layered gates with one canonical executable orchestrator

Verification order is:

1. Complete the requirement inventory, historical reconciliation, caller audit, and focused evidence mapping.
2. Run focused existing tests needed to validate individual trace rows and record actual results.
3. Run `.venv/bin/python scripts/quality_gate.py` as the sole repository-wide executable gate.
4. Run `openspec doctor`, `openspec validate strengthen-pre-agent-acceptance-gates --strict`, and `openspec validate --all --strict`.
5. Perform final semantic review across the supplied ECO-32 scope, living specs, implementation, tests, `AGENTS.md`, `SKILL.md`, and current-facing architecture docs.
6. Mark every row and the overall decision accepted only if all evidence is current and all gates pass.

No real-network Feed dry run is required: fixture-backed deterministic evidence covers this acceptance-only Change, while a production `--dry-run` may mutate rate state.

### 6. Fail closed on scope drift

The expected Apply allowlist is limited to:

- this Change's artifacts, including the Change-local delta, `traceability.md`, and task completion state.

The living specs, production code, tests, configuration, Providers, schemas, workflows, dependencies, CI/deployment files, generated Feed data, archived Changes, and unrelated worktree content are excluded. A need to touch any excluded surface is a contradiction or evidence-gap decision that stops acceptance for user review. Synchronizing the accepted delta into the living spec belongs to a separately authorized sync/archive lifecycle.

## Risks / Trade-offs

- [Risk] A large matrix can become checkbox evidence. -> Require exact current headings, concrete source/audit references, caller status, fresh command results, and a per-row outcome before overall acceptance.
- [Risk] Historical trace paths and conclusions may be stale after later Changes. -> Use history only as a seed for removed/superseded disposition and re-derive all current rows from living specs.
- [Risk] A passing quality gate can mask an untraced semantic contradiction. -> Run final requirement/caller/docs review after structural and executable gates and keep semantic acceptance independent.
- [Risk] Static searches can produce false positives from archives or planning text. -> Separate current-facing surfaces from archived history and classify each hit rather than deleting historical evidence.
- [Risk] The acceptance Change could become a test or CI refactor. -> Reuse current suites and the canonical quality gate; stop on a genuine evidence gap instead of expanding scope.
- [Risk] Phase-4 terminology could leak into the accepted baseline. -> Treat future concepts only as prohibited/deferred categories and reject any positive schema or topology definition.

## Migration Plan

1. Apply the Change only after a separate explicit request, producing the fresh trace and acceptance evidence without changing the living spec or runtime surfaces.
2. If any trace row or gate fails, leave Phase 3 unaccepted, record the exact blocker, and obtain a separate scope decision before remediation.
3. If all rows and gates pass, record Phase-3 acceptance in the Change evidence. Linear updates, archive, commit, push, and Phase-4 work remain separate authorization boundaries.
4. Rollback, if needed before archive, is limited to reverting the ECO-32 OpenSpec delta and Change-local evidence; no production migration exists.
