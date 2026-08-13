## Context

The repository was built in August 2026 as both a standalone application and
an Agent Skill, and shipped a complete embedded LLM runtime: one configured
model driving four structured passes (resolver, analyst, editor,
language-audit) through a Responses API adapter with per-pass timeout,
retry, output-token, and response-size limits; a Brief CLI; cost-budgeted
live evaluation against a versioned price table; and prompt/model
fingerprinted run bundles with deterministic replay.

The product direction is now fixed: `follow-the-money` is only an Agent
Skill. Host agents already own LLM, context, reasoning, tool runtime, model
configuration, token management, and retry/timeout handling, so the embedded
runtime is duplicate architecture. The future architecture (recorded here as
direction, not as this Change's scope) is:

```text
Feed / Providers → deterministic prepare → ResearchContext → Agent →
AgentAnalysis → deterministic validate + score + select → BriefContext →
Agent → Brief → deterministic claim/evidence validation
```

The key structural fact that makes this pivot mechanically cheap is that the
LLM was already an exchangeable provider of structured dictionaries: only
`llm.py`, `brief_cli.py`, and `pipeline.py` touch the runtime, while the
validation/merge functions (`resolve_block`, `merge_analysis`,
`merge_editor_output`, `audit_language_findings`) are pure deterministic
functions over structured inputs, and `run_pipeline(saved_llm=...)` already
replays recorded structured outputs through the deterministic path.

## Goals / Non-Goals

**Goals:**

- Remove every trace of the project owning or invoking an LLM: no SDK
  dependency, no API-key/model configuration, no prompts, no LLM request.
- Cancel the standalone application / public CLI product form; keep only a
  minimal internal Feed invocation surface for Agent/Skill use.
- Retain the deterministic financial engine and the deterministic rules
  that remain valuable: evidence collection, ledger, candidate blocks,
  market state, watchlist, scoring/selection rules, the `ClaimAuditor`
  safety audit, canonical/provenance utilities, and schema validation.
- Keep the repository in an honest, tested, documented transitional state:
  no placeholder architecture fills the removed resolver/analyst/editor
  passes, and no new Agent delivery contract is designed in this Change.

**Non-Goals:**

- Designing or implementing the future Agent delivery contract
  (ResearchContext / AgentAnalysis / BriefContext shapes, schemas, or
  validation).
- Making the retained pipeline appear functional by faking analysis inputs
  or re-wiring scoring/selection to a new caller.
- Creating an in-repo `legacy/` or `archive/` directory for removed code;
  git history is the retention mechanism.
- Preserving the old four-pass schemas, Brief schema, golden-dataset replay
  fixtures, or run-bundle replay as live artifacts.
- Adding any new LLM, external service, credential, or network dependency.

## Decisions

### 1. Delete the embedded LLM runtime entirely, including validation layers tied to the old contract

The OpenAI SDK, `llm.py`, `prompts/`, the `llm:` configuration section,
`LlmRuntime`/`PassConfig`, LLM environment variables, and `eval_live.py` are
pure runtime and are deleted. The pass-validation layer —
`engine/resolution.py`, `merge_analysis`, `merge_editor_output`,
`audit_language_findings`, and their schemas — is deterministic but exists
only to validate the old four-pass contract, which is explicitly not the
future; it is deleted with that contract. All of it remains recoverable from
git history; no `legacy/` directory is created.

Rejecting "keep the merge functions for the future": their input contracts
are the old pass schemas; keeping them would either preserve dead schema
coupling or require reshaping them now, which is future-architecture work
explicitly out of scope. `engine/resolution.py` is deleted whole because
`pipeline.py` is its only production consumer.

### 2. Delete the public CLI product form; keep one minimal internal Feed entry

`cli.py`, `__main__.py`, `[project.scripts] follow-the-money`,
`brief_cli.py`, `pipeline.py`, and the `scripts/skill/follow-the-money-skill`
wrapper are deleted. The only surviving invocation is a minimal Feed entry
used by the Agent/Skill: a small `main()` on `feed/cli.py` (preserving the
current feed arguments and exit-code contract) behind the existing
`scripts/feed/follow-the-money-feed` wrapper, which calls the deterministic
feed pipeline directly instead of a public CLI.

The distinction is the consumer: an internal tool interface for the Skill is
not a user-facing product. `feed` remains because the Skill's primary product
is the evidence Feed; `brief`/`eval`/`replay` are LLM-era products and go.

### 3. Retain the upstream deterministic half of the future architecture

The future architecture's "deterministic prepare" stage already exists today
and is fully deterministic: providers/Feed → evidence ledger → candidate
blocks → market snapshot and state → watchlist/dashboard. These modules are
retained unchanged in behavior: `feed/`, `providers/`, `ledger.py`,
`boundary.py` (used by `feed/cli.py`), `canonical.py`, `unicode.py`,
`schema.py`, `engine/candidates.py`, `engine/entities.py`,
`engine/feed_health.py`, `market/`, `watchlist.py`, and `state.py`.

This is not an accident of scope; it is the anchor for the retention
boundary: this Change keeps exactly the deterministic core that the future
architecture's prepare stage needs, and nothing that exists only to serve
the old four-pass contract.

### 4. Retain scoring/selection and the ClaimAuditor as a no-caller deterministic core

`scoring.py` and `selection.py` are pure deterministic rules (significance,
morning relevance, priority, eligibility, formats, family penalty,
coexistence) whose future caller is the AgentAnalysis validation stage. They
are retained with their tests but no production caller; this is not a
placeholder because nothing fakes inputs to them. `ClaimAuditor` (safety
lexicon and trading-instruction detection) is retained for the same reason:
the future Brief validation will still need it. `audit_language_findings`
(language-audit pass output mapping) is deleted with its pass.

### 5. Remove LLM-era evaluation and provenance machinery

`eval_offline.py`, `eval_live.py`, `eval_metrics.py`, the golden-dataset
four-pass fixtures (recorded LLM outputs, replay contracts,
`evals/dataset/pass_outputs/`), `scripts/build_golden_dataset.py`, and
`bundle.py` (brief run-bundles and replay) are deleted, along with
`scripts/refresh_golden_sources.py` whose only purpose is maintaining that
dataset. Raw provider snapshots in `evals/dataset/sources/` survive only
where retained deterministic tests consume them as fixtures.

The "evidence/provenance and audit capability" this Change preserves is the
deterministic one: canonical digests, Feed identity/validation, the safety
lexicon, and schema validation — not the LLM-era bundle/replay trail, whose
only producer was the deleted Brief CLI.

### 6. Configuration and environment become credential-free

`config.yaml` drops the `llm:` section and the `audit_severity` section
(whose only consumer is the deleted language-audit pass); `config/model.py`
drops `LlmRuntime`/`PassConfig`; `config/load.py` drops LLM loading and its
empty-model startup rejection. `.env.example` drops all OpenAI and per-pass
timeout variables. The surviving configuration fails closed only on
deterministic contracts (providers, scoring, sessions, roles, safety
lexicon).

### 7. The transitional state is explicit in docs and the Skill contract

`SKILL.md` is rewritten for the transitional state: the Skill collects the
evidence Feed and hands the evidence to the host Agent, which currently
performs analysis and Brief writing itself; the structured Agent contract
and the fixed Brief pipeline are deferred to a future Change. READMEs,
`docs/architecture.md`, `docs/evaluation.md`, `.github/workflows/`, and
`scripts/quality_gate.py` (the `--help` CLI check) are updated to match.
This keeps the repository honest: deterministic core live and tested, Agent
orchestration not yet established.
