## Context

See `proposal.md` for motivation. ECO-49 already owns the complete version-1 serialized boundary in `schemas/agent-invocation.schema.json`; its root deliberately accepts request, success-response, and error-response variants. The retained `ClaimAuditor` already supplies deterministic text and structured-claim behavior, including stable finding order and Skill-owned `SafetyLexicon` defaults, but current architecture tests reject every production caller.

ECO-50 therefore needs coordination and mapping only. The design must prove one private process boundary without changing the schema, Audit algorithms, Feed path, dependency set, or any deferred capability.

## Goals / Non-Goals

**Goals:**

- Implement one inspectable one-shot process entry with deterministic request classification and exactly two static Audit branches.
- Reuse the accepted root schema and existing Audit types while keeping request/response discrimination explicit.
- Preserve Audit-domain negative results in the success channel and preserve every result field and finding order.
- Make the post-ECO-50 caller graph mechanically testable and current-facing claims truthful.

**Non-Goals:**

- No generic dispatcher, registry, operation metadata, plugin system, configuration surface, transport abstraction, session, retry/rewrite mechanism, or future-operation seam.
- No Event mapping, Feed wrapper, mandatory research pipeline, new Audit rule, new policy source, public console script, or stable numeric failure-code allocation.

## Decisions

### 1. Use one private importable module as the process entry and adapter

Apply will add one small module under `src/follow_the_money/` that is executable with `python -m ...`, exposes a testable `main() -> int`, and contains parsing, classification, two direct dispatch branches, external/internal mapping, and response emission. It will not add `[project.scripts]`, a shell wrapper, a facade package, or separate registry/transport/domain layers. The module name remains implementation detail and is not documented as a stable Agent operation contract.

Alternative considered: separate executable, protocol, dispatcher, mapper, and error modules. Rejected because two operations and one transport do not justify five ownership surfaces.

### 2. Classify before root-schema validation, then reuse root validation

The entry reads `sys.stdin.buffer` once, decodes strict UTF-8, and uses the standard-library JSON parser once; empty input, malformed input, invalid UTF-8, and trailing additional JSON values become `invalid_json` by caught exception type.

For a parsed object, classification is structural and ordered:

1. an exact integer `contract_version` other than `1` produces `unsupported_contract_version`;
2. absent an unsupported major, an exact string `operation` outside the two supported names produces `unsupported_operation`;
3. all other values must be an object with exactly `contract_version`, `operation`, and `input`, then validate against `agent-invocation.schema.json`; failure produces `invalid_request`;
4. only the two known operation strings reach direct dispatch.

The exact request-envelope key check makes a root-valid success or error response ineligible before dispatch; root validation then reuses the accepted closed operation/input definitions without copying them into Python. Wrong-typed version or operation values are `invalid_request`, because they do not explicitly name a supported or unsupported major/operation. Python `bool` is not treated as an integer contract major.

Alternative considered: accept anything valid against the root schema. Rejected because it accepts response variants. Alternative considered: duplicate every schema constraint as hand-written Python validation. Rejected because that creates a second contract source.

### 3. Dispatch with two explicit branches and map values field by field

`audit.text` passes only `text` and optional `claim_id` to the existing text-audit method. `audit.claims` constructs internal claim and flow values from the accepted fields, converts arrays to the sequence forms already consumed by Audit, and maps absent `flows` to the existing empty-sequence semantic. Dispatch is an `if`/`elif`, not a mapping registry or reflection.

The result mapper copies `passed` and iterates the existing finding sequence once, preserving order and copying only `claim_id`, `category`, `detail`, and `severity`. The complete success envelope is validated against the accepted root schema before emission. Mapping or output-validation failure after accepted dispatch becomes `execution_failure`; it never produces a partial result.

Alternative considered: serialize dataclasses recursively. Rejected because internal names/layout would become accidental compatibility behavior and uncontrolled fields could cross the trust boundary.

### 4. Reuse the existing Skill-owned Audit policy without runtime configuration

The adapter constructs the existing auditor with its existing default Skill-owned `SafetyLexicon` semantics. It accepts no policy, lexicon, config path, environment setting, credential, or model value and does not load the Feed/provider configuration graph. This adds no policy source and preserves the already tested standalone Audit behavior.

Alternative considered: load the complete repository configuration for every one-shot Audit. Rejected because the accepted Agent contract has no runtime config input and Audit does not require provider startup. Alternative considered: parse only the YAML safety section in the adapter. Rejected because that would duplicate configuration parsing and authority.

### 5. Keep process failure binary and capability failure separate

Every accepted Audit result—including empty inventory, duplicates, outside-inventory submissions, missing evidence, ownerless confirmed flow, and prohibited instructions—emits a success response and returns `0`, even when `passed` is false. Invocation errors emit exactly one accepted error response and return one implementation-chosen non-zero value; tests assert only non-zero.

Parsing and schema failures are caught by their concrete exception/type boundary. Unexpected exceptions are caught only around accepted operation execution/mapping and become `execution_failure`. Error selection never inspects exception text. Tracebacks and diagnostics, if emitted, go only to stderr; stdout is written once with the final JSON response.

Alternative considered: assign one exit number per error code. Rejected because ECO-49 intentionally leaves the exact non-zero taxonomy unstable.

### 6. Prove the boundary at process, mapping, and caller-graph levels

Focused tests will invoke the private module as a process for representative success, deterministic-negative, and trust-boundary cases. A focused in-process entry test may replace the module's auditor symbol with a failing test double to force `execution_failure` while exercising the real `main` response/status path; production code gets no injection framework.

Mapping fidelity tests compare the external result with a known internal result, including a synthetic internal warning only at the mapper boundary, without adding an Audit rule. Architecture tests narrow the current blanket `ClaimAuditor` ban to an exact allowlist for the new module and continue scanning Feed, legacy workflow, Event, Market, Watchlist, Confidence, Scoring, and Ranking paths. Call-count tests prove one addressed operation executes once and no retry, rewrite, or sibling capability call occurs.

### 7. Reconcile existing contract owners instead of adding an Audit-runtime capability

Apply will update the six delta-owned living specs and only the stale caller/runtime statements in `SKILL.md`, both READMEs, `docs/architecture.md`, and relevant architecture tests. Audit becomes `live-production` under the project's existing status vocabulary; Feed remains independently `live-production`; the other four post-Feed families remain `retained-no-production-caller`. Archived Changes, `schemas/feed.schema.json`, and unchanged capability requirements remain untouched.

## Risks / Trade-offs

- [Root schema accepts responses as well as requests] → Require the exact request envelope before root validation and cover both success- and error-response-shaped stdin.
- [Broad exception handling could misclassify invalid requests] → Complete structural/schema validation before the execution boundary and catch unexpected exceptions only after dispatch eligibility is established.
- [Mapping drift could suppress or alter findings] → Copy the five contracted result fields directly, preserve iteration order, validate the emitted envelope, and compare mapper output with the internal result in focused tests.
- [Architecture wording could imply Feed-to-Audit or mandatory Audit] → Document two independent live capabilities and assert the caller graph rather than drawing a pipeline edge.
- [Future operations could tempt premature generalization] → Keep two literal dispatch branches; ECO-51 extends the accepted envelope and implementation only through its own Change.

## Migration Plan

1. Add focused RED runtime tests and narrow the existing caller regression to the single intended adapter path.
2. Add the one private module and minimum mapping/classification logic until focused tests pass.
3. Reconcile the six living specs and current-facing documentation with the verified caller graph, then run repository and OpenSpec gates.
4. Roll back by removing the private module and its focused tests and reverting only ECO-50 living-spec/documentation status changes; Feed and internal Audit behavior require no data or schema migration.
