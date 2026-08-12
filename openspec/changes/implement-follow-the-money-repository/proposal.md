## Why

`Follow the Money` needs a complete, reproducible repository that turns free China and US financial evidence into a daily 08:30 Asia/Shanghai Morning Money Brief without delegating deterministic work to an LLM or presenting investment instructions. The repository must make every important factual claim traceable, degrade visibly when sources fail, and support regression evaluation as providers, prompts, scoring weights, or the single configured model change.

## What Changes

- Create the complete Python-based repository, configuration, JSON Schemas, provider adapters, deterministic pipelines, structured LLM passes, CLI entry points, replayable run-audit bundles, documentation, fixtures, and GitHub Actions workflows; the scheduled Feed template requires a separately provisioned dedicated self-hosted runner with a persistent shared output root.
- Generate `feeds/latest.json` and dated audit feeds from free official and public financial sources without any LLM call, while isolating provider failures and reporting degraded operation.
- Convert Feed evidence into candidate blocks and canonical atomic events with deterministic normalization, deduplication, entity resolution, market analytics, evidence linking, and constrained semantic resolution.
- Calculate evidence confidence, surprise, reaction observability, event significance, morning relevance, story redundancy, and final Brief selection in scripts rather than prompts.
- Analyze only verified shortlisted event packets through the OpenAI Responses API and one configured compatible model, with strict structured output, evidence-bound claims, explicit uncertainty, and no authority to add facts.
- Render and validate the fixed Chinese Morning Money Brief format, separating facts, observations, mechanisms, implications, price-in assessments, and direct versus indirect flow evidence.
- Add offline deterministic tests plus an explicit credentialed evaluation mode covering event recall, ranking quality and stability, duplicate stories, unsupported claims, causal overclaim, provider degradation, partial-feed days, and prompt/model comparisons without claiming live-model bit-for-bit reproducibility.
- Schedule Feed collection near 08:20 Asia/Shanghai while recording and displaying one fixed evidence cutoff captured before provider requests; external Skill scheduling remains a deployment concern rather than being falsely represented by the Feed workflow.

## Capabilities

### New Capabilities

- `feed-evidence-pipeline`: Configured providers fetch, normalize, deduplicate, validate, and publish evidence-only Feed artifacts with source health and graceful degradation.
- `deterministic-evidence-engine`: The Skill validates Feed health, resolves entities, creates candidate blocks, computes market observations and reaction observability, and builds an auditable Evidence Ledger.
- `semantic-event-resolution`: One configured OpenAI Responses API model extracts supported atomic events and resolves only ambiguous semantic relationships under strict structured-output, untrusted-input, and evidence-reference constraints.
- `event-analysis-and-ranking`: Verified events receive evidence-bound financial analysis, deterministic significance and morning-relevance scores, confidence gates, redundancy penalties, and stable final selection.
- `brief-synthesis-and-audit`: The system produces the fixed Chinese Morning Money Brief through structured synthesis, deterministic rendering, and script plus LLM claim audits that prohibit unsupported facts and trading instructions.
- `regression-evaluation`: Golden-day fixtures and explicit offline/live modes evaluate recall, precision, duplication, claim support, causal language, degraded feeds, order-invariant deterministic stages, and prompt/model comparisons.

### Modified Capabilities

None. This repository has no existing product capability specifications.

## Impact

- Adds the complete application under this repository, including `config/`, `schemas/`, `providers/`, `scripts/`, `prompts/`, `feeds/`, ignored local `runs/`, `tests/`, `evals/`, `docs/`, and GitHub Actions workflows.
- Introduces Python 3.12 runtime dependencies for HTTP/RSS ingestion, YAML and JSON Schema validation, exchange calendars, testing, and one OpenAI Responses API adapter.
- Requires no paid financial-data key for the core Feed. Full semantic resolution and narrative analysis require one OpenAI credential and one compatible configured model; without them the CLI can produce only a separately typed, explicitly requested deterministic degraded report.
- Defines a GitHub Actions workflow template that can write immutable run-scoped daily Feed artifacts plus `latest.json` with scoped `contents: write` only after a Git remote, branch policy, dedicated self-hosted runner, and persistent shared output root/rate state are configured; ephemeral hosted runners or best-effort caches do not satisfy the source-rate contract, and protected-branch, persistence, or publication failures remain visible failures rather than silently succeeding.
- Does not add event memory, historical-Feed consumption, automated trading, recommendations, multi-model routing, provider fallback models, or a real-time market terminal.
