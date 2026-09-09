## Why

The current Skill and user-facing documentation describe `/follow-the-money` as producing a financial intelligence briefing, even though the live path only supplies a validated evidence Feed for Host-Agent synthesis. Now that deterministic Feed production and canonical published-Feed consumption are stable, the invocation contract must be corrected before adding more information sources so future expansion does not inherit an implied financial-analysis responsibility.

## What Changes

- Reposition `/follow-the-money` as an evidence-based information digest generated directly from the current validated published Feed.
- Replace financial-intelligence, research-report, significance, anomaly, signal, prediction, and investment-judgment output expectations with current updates, concise evidence summaries, provenance, freshness, coverage, and limitations.
- Preserve the scope-free invocation: the Skill does not request or accept a company, asset, topic, time range, research question, or other user-supplied scope, and it does not read historical Feeds or checkpoints.
- Permit the Host Agent to group related evidence, derive editorial headings, order content for readability, consolidate repetition, and compress detail, provided those transformations do not introduce unsupported facts or imply importance, anomaly, causality, market impact, prediction, or investment implications.
- Require transparent compression: report domain item totals and disclose summarized, consolidated, or omitted coverage rather than silently selecting “important” items.
- Keep GitHub Actions ownership of Provider collection and deterministic Feed production unchanged. Keep normal Skill consumption remote-only, validated, evidence-only, credential-free, and fail-closed.
- Keep the repository free of embedded LLM/model runtime, prompt pipelines, API-key/model configuration, new Providers, Feed schema changes, and financial judgment or trading output.
- Preserve the existing private on-demand Audit and Event Structuring boundaries and all retained deterministic capabilities without wiring them into the digest path.

## Capabilities

### New Capabilities

- `information-digest-invocation`: Defines the current published-Feed-to-Host-Agent information digest behavior, required output coverage, permitted editorial transformations, and prohibited analytical judgments. This invocation contract is Host-Agent-owned output behavior, not a seventh deterministic capability family or a repository LLM runtime.

### Modified Capabilities

- `skill-agent-responsibility-boundary`: Narrows the current user-facing Host-Agent responsibility from financial interpretation and research narrative to evidence-preserving digest summarization and formatting, while retaining existing ownership and authority rules for independent deterministic capabilities.
- `agent-grounding-validation-contract`: Applies the existing semantic-support and output-admissibility guarantees to information digests and removes current-product wording that implies a financial research output, without weakening grounding or deterministic-finding authority.

## Impact

Affected planning and documentation surfaces include `SKILL.md`, `AGENTS.md`, `references/architecture-boundary.md`, `references/feed-contract.md`, `references/safety-boundary.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, related user-facing documentation, and `tests/test_feed_documentation.py`. Existing Feed production and consumption implementation, Providers, configuration behavior, Feed schemas, Agent invocation schema/runtime, deterministic libraries, generated Feed products, and production caller topology remain unchanged. `openspec/config.yaml` requires no product wording change because it currently contains no project positioning or behavioral contract.
