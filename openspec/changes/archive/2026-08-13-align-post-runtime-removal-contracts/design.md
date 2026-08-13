## Context

The archived `remove-standalone-runtime` Change intentionally left one minimal internal Feed entry for the Agent Skill and retained deterministic financial modules without restoring a standalone application. Its `0/1/2` exit contract is sound, but `main()` currently decides between exits `1` and `2` by searching exception text. In addition, long-lived documentation still contains bootstrap-only Git claims, while the retained-core specification overstates JSON Schema coverage beyond the sole surviving serialized contract, `feed.schema.json`.

This cleanup must align implementation, tests, documentation, and the current main OpenSpec without changing Feed behavior, financial calculations, providers, deployment state, or the Agent-only architecture.

## Goals / Non-Goals

**Goals:**

- Make expected Feed failure categories explicit in types and preserve the existing public exit meanings: healthy/degraded `0`, execution `1`, input/configuration/startup capability `2`.
- Ensure expected invalid configuration and explicit invocation input fail without an uncaught traceback.
- Remove obsolete Git-bootstrap claims while retaining real deployment and evidence-cutoff boundaries.
- Describe only the validation contracts that exist: JSON Schema at the serialized Feed boundary and typed/domain/test validation for internal deterministic structures.
- Keep the change small, directly testable, and free of new dependencies or product surfaces.

**Non-Goals:**

- Restoring or redesigning `llm.py`, `pipeline.py`, `brief_cli.py`, the public CLI, OpenAI integration, prompts, old pass schemas, bundle/replay, or LLM evaluation.
- Designing `ResearchContext`, `AgentAnalysis`, `BriefContext`, prepare/evaluate/validate protocols, Agent E2E, or any future Agent delivery contract.
- Changing providers, SEC/Yahoo coverage, market mappings, scoring, selection, or `ClaimAuditor` behavior.
- Adding JSON Schemas for ledger, candidate, market, watchlist, scoring, or selection objects.
- Changing Git remotes, workflow enablement, runners, scheduling, publication, or any external deployment state.

## Decisions

### 1. Express the two expected failure categories with a minimal exception hierarchy

`FeedCliError` remains the common expected-error base. `FeedInputError` represents invalid invocation, configuration, or startup-capability rejection and maps to exit `2`; `FeedExecutionError` represents planning, collection, runtime, validation, integrity, deadline, rate-state, filesystem execution, publication, or durability failure and maps to exit `1`. `main()` catches these concrete categories and never inspects exception messages.

`argparse` remains responsible for parser-level usage failures and retains its native exit `2`. Successful `FeedRunResult` values retain their existing `0` behavior for both healthy and degraded status.

Alternative considered: attach an integer to a single exception or maintain a message/error-code registry. That either permits arbitrary exit values or adds an unnecessary parallel classification table. Two subclasses are the smallest representation of the contract.

### 2. Translate failures at the narrow boundary that knows their meaning

Configuration loading errors, malformed or invalid explicit cutoff/window values, absence of an enabled provider, and startup capability rejection become `FeedInputError` before collection can proceed. Once a valid invocation enters Feed planning or execution, failures become `FeedExecutionError`; this includes a non-advancing cutoff, invalid existing latest Feed, collection-lock timeout, provider/runtime failure, rate-state failure, schema or identity rejection, deadline expiry, publication, durability, and execution-time filesystem failure.

The implementation must use caught exception types and the phase in which an error occurs, not substrings such as `config`, `invalid`, `provider`, or `non_advancing`. Existing lower-level domain exceptions may remain unchanged when the Feed boundary can translate them unambiguously.

Alternative considered: propagate every lower-level exception directly to `main()`. That would couple the entry point to many implementation modules and still leave ordinary parsing/configuration exceptions uncaught. Translation at the Feed boundary keeps the CLI contract local.

### 3. Test classification independently from message wording

Focused tests will prove `FeedInputError` always maps to `2` and `FeedExecutionError` always maps to `1`, including adversarial messages whose words suggest the opposite category. Tests also retain coverage for native `argparse` exit `2` and healthy/degraded exit `0`. Existing tests that only need a common expected Feed failure may continue to assert `FeedCliError`; only classification tests need concrete subclasses.

### 4. Delete transient Git-state prose instead of replacing it

The READMEs' bootstrap-boundary sections and the Skill's claim that the repository is not a Git checkout or lacks history/remotes will be removed. They will not be replaced by positive Git-state claims because checkout, history, and remote configuration are development/deployment facts rather than the Skill's durable product contract.

The documentation will retain the meaningful boundaries that a checked-in workflow is not proof of enabled scheduling, deployment prerequisites remain external, and `evidence_cutoff_at` defines Feed coverage.

### 5. Reserve JSON Schema claims for explicit serialized boundaries

The current external serialized artifact is the Feed. It must validate against `feed.schema.json` and continue to satisfy semantic and identity/digest validation. Ledger, candidate blocks, market snapshot/state, watchlist, scoring intermediates, and selection inputs remain internal deterministic structures. Their correctness is enforced by typed Python interfaces, domain invariants and validation, and deterministic tests; they are not required to have standalone JSON Schemas.

The delta spec modifies the current main `deterministic-core-retention` requirements. The archived Change remains historical evidence and is not rewritten.

Alternative considered: create JSON Schemas for every retained structure. That would invent external contracts, expand maintenance surface, and pre-empt future Agent-boundary design solely to satisfy inaccurate prose.

## Risks / Trade-offs

- **[A lower-level exception is translated into the wrong category]** → Keep translations at phase-aware boundaries and add representative tests for configuration, explicit inputs, planning/integrity, and execution failures.
- **[A broad catch hides an unexpected programming defect]** → Catch only expected domain, configuration, parsing, and filesystem exception types; do not add a catch-all `Exception` that converts defects into routine CLI outcomes.
- **[Tests accidentally preserve message coupling]** → Include messages containing misleading words and assert category solely from subclass type.
- **[Documentation becomes less descriptive after removing Git prose]** → Retain only durable deployment and evidence-cutoff boundaries that affect operation and correctness.
- **[The corrected spec is interpreted as weakening Feed validation]** → State explicitly that Feed JSON Schema, semantic validation, identity, and digest checks remain mandatory; only nonexistent per-internal-object schemas are disclaimed.
