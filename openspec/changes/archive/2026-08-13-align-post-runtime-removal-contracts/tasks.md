## 1. Lock Exit-Code Behavior with Tests

- [x] 1.1 Replace the message-coupled CLI classification fixtures with failing tests that assert `FeedInputError` exits `2` and `FeedExecutionError` exits `1`, including misleading messages that contain words associated with the opposite category.
- [x] 1.2 Add or retain focused tests proving malformed `argparse` usage exits `2`, malformed/invalid explicit cutoff or window input exits `2` without an uncaught traceback, and healthy plus degraded results both exit `0`.
- [x] 1.3 Add representative boundary tests for configuration/no-enabled-provider startup rejection and planning/integrity/runtime/publication failure so each reaches its specified typed category without inspecting message text.

## 2. Implement Typed Feed Failure Classification

- [x] 2.1 Introduce only the minimal `FeedCliError`, `FeedInputError`, and `FeedExecutionError` hierarchy in `src/follow_the_money/feed/cli.py`, preserving `FeedCliError` as the common expected-failure base for existing callers and tests.
- [x] 2.2 Translate configuration, invalid explicit invocation input, no-enabled-provider, and startup-capability failures to `FeedInputError` at the narrow boundary that knows their meaning; ensure expected failures produce concise stderr rather than tracebacks.
- [x] 2.3 Translate planning, collection, runtime, rate-state, schema, identity, integrity, deadline, filesystem-execution, publication, and durability failures to `FeedExecutionError`, including `non_advancing_cutoff` and invalid latest integrity as exit `1` outcomes.
- [x] 2.4 Update `main()` to map the two explicit exception types to exits `2` and `1` respectively, keep `argparse` behavior unchanged, and remove every exception-message substring check used for exit classification.
- [x] 2.5 Run the focused Feed CLI and retained no-LLM contract tests; confirm healthy/degraded `0`, execution `1`, usage/config/startup `2`, and no regression to a public CLI or LLM surface.

## 3. Align Long-Lived Documentation

- [x] 3.1 Remove the obsolete Git bootstrap section from `README.md` and `README.zh-CN.md` without replacing it with environment-dependent Git-state prose.
- [x] 3.2 Remove the `SKILL.md` Non-Go claim that the repository is not a Git checkout or lacks history/remotes, while preserving external scheduling/deployment and evidence-cutoff boundaries.
- [x] 3.3 Update `docs/architecture.md` to state that the Feed is the current serialized external contract validated by `feed.schema.json`, semantic checks, and identity/digest checks, while internal deterministic structures use typed interfaces, domain invariants/validation, and deterministic tests rather than standalone JSON Schemas.
- [x] 3.4 Search the scoped current documentation and main `deterministic-core-retention` spec to confirm no live claim remains that the repository is not Git-backed or that every internal retained structure has its own JSON Schema.

## 4. Verify Scope and Complete Gates

- [x] 4.1 Confirm no OpenAI dependency, project-owned LLM runtime, prompt, old pass schema, pipeline, public CLI, bundle/replay, LLM evaluation, or future Agent contract was added or restored, and confirm no provider, market mapping, scoring, selection, or `ClaimAuditor` behavior changed.
- [x] 4.2 Run `uv run pytest` and record the fresh passing result from the final stable revision (`409 passed in 24.12s`).
- [x] 4.3 Run `uv run ruff check src tests scripts`, `uv run ruff format --check src tests scripts`, and `uv run mypy src scripts`; resolve only failures attributable to this Change.
- [x] 4.4 Run `openspec validate align-post-runtime-removal-contracts --strict` and `openspec validate --all --strict`; resolve every Change-attributable specification failure.
- [x] 4.5 Run `uv run python scripts/quality_gate.py` after the final relevant edit and confirm the repository quality gate passes.
