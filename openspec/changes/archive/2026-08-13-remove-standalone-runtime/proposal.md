## Why

`follow-the-money` was originally implemented to serve two roles at once: a
standalone financial-news application and a Skill callable by AI Agents. It
therefore carries a complete embedded LLM runtime — OpenAI SDK, API-key/model
configuration, a Responses API adapter, four constrained LLM passes
(resolver/analyst/editor/language-audit), per-pass timeout/retry/token/
reasoning controls, a Brief CLI, cost-budgeted live evaluation, and
prompt/model fingerprint, bundle, and replay machinery.

The product direction is now settled: `follow-the-money` exists only as an
Agent Skill. Host agents (Claude Code, Codex, or other compatible agents)
already provide LLM, context, reasoning, tool runtime, model configuration,
token management, and retry/timeout handling. Maintaining a second LLM
runtime duplicates that architecture and adds nested Agent → Skill → Python →
LLM calls, extra credential configuration, vendor coupling, and a large
maintenance surface of tests, schemas, fixtures, and bundles.

The new long-term position is:

> Evidence-grounded financial research Skill for AI Agents.

The Agent understands, reasons, and expresses; `follow-the-money` supplies
facts, rules, deterministic computation, and verifiability. This Change
removes the project's own LLM capability and cancels the standalone
application / public CLI product form while retaining the deterministic
financial engine that remains valuable.

## What Changes

- Remove the embedded LLM runtime: OpenAI SDK dependency, `llm.py` Responses
  adapter, the `prompts/` files, per-pass timeout/retry/token/reasoning
  controls, the `llm:` configuration section, `LlmRuntime`/`PassConfig`, and
  all LLM environment variables.
- Remove the four-pass LLM topology and its orchestration: `pipeline.py`,
  `brief_cli.py`, and the public `follow-the-money` CLI
  (`cli.py` / `__main__.py` / `[project.scripts]`) with its `feed`, `brief`,
  `eval`, and `replay` subcommands.
- Remove the old four-pass contract layer: `analysis.py`, `editor.py`,
  `brief.py`, `render.py`, the language-audit pass in `audit.py`, the
  pass-validation module `engine/resolution.py`, and the associated schemas
  (`resolver-output`, `analyst-output`, `editor-output`,
  `language-audit-output`, `event`, `analysis`, `verified-event-packet`,
  `brief`, `degraded-report`, `run-manifest`).
- Remove LLM-era evaluation and provenance machinery: `eval_offline.py`,
  `eval_live.py`, `eval_metrics.py`, the golden-dataset four-pass fixtures
  (recorded LLM outputs, replay contracts, `pass_outputs/`),
  `scripts/build_golden_dataset.py`, and `bundle.py` brief run-bundles and
  replay.
- Retain the deterministic financial engine: Feed collection and provider
  adapters, the evidence ledger, candidate-block construction, entity
  resolution, market snapshot and state classification, watchlist, canonical
  digests, schema validation, and provider-bound provenance.
- Retain as a no-caller deterministic core with their tests: `scoring.py`,
  `selection.py`, and the `ClaimAuditor` safety audit.
- Keep one minimal internal Feed invocation surface for Agent/Skill use; no
  public user-facing CLI product form remains.
- Update `SKILL.md`, READMEs, `.env.example`, docs, workflows, and the
  quality gate to the transitional state: the deterministic core is live and
  tested, while Agent orchestration over the core is intentionally deferred
  to a future Change.

This Change intentionally leaves the repository in a transitional state:
deterministic core retained, new Agent delivery contract not yet built. No
placeholder architecture is introduced to make an old pipeline appear
functional.

## Capabilities

### New Capabilities

- `deterministic-core-retention`: Defines the retained post-removal contract —
  no embedded LLM runtime, a functional evidence-only Feed behind exactly one
  minimal internal invocation surface, retained deterministic rules with
  tests and no production wiring, and credential-free fail-closed
  configuration.

### Modified Capabilities

None. The removal targets capabilities described in the still-active
`implement-follow-the-money-repository` change; no synced main-spec
capability is altered by this Change.

## Impact

- Affected code: `pyproject.toml`, `src/follow_the_money/` (LLM, pipeline,
  brief, editor, analysis, render, eval, bundle, CLI modules),
  `config/` (LLM and audit-severity sections), `.env.example`, `prompts/`,
  `schemas/`, `evals/`, `scripts/` (golden-dataset builder, skill wrapper,
  quality gate), `.github/workflows/`, `docs/`, `SKILL.md`, READMEs, and the
  tests that exercise removed modules.
- Affected contracts: dependency set, CLI surface, configuration schema,
  environment variables, shipped schemas, and the Skill orchestration
  contract.
- Dependencies: no new dependency or service is introduced; `openai` is
  removed. All remaining capability is deterministic and credential-free.
