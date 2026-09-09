## Context

See `proposal.md` for motivation. The live product path is already split between deterministic repository behavior and Host-Agent presentation: GitHub Actions collects and publishes an evidence-only Feed, normal Skill invocation retrieves and validates that Feed, and the Host Agent produces user-facing text. The current `SKILL.md`, safety reference, architecture wording, and documentation tests nevertheless prescribe a financial intelligence briefing with significance and anomaly-oriented sections.

The Feed schema contains evidence and explicit health, provenance, freshness, availability, and coverage semantics; it does not contain a digest, ranking, anomaly result, or financial interpretation. Market Analytics, Confidence/Watchlist, and Scoring/Ranking remain retained without a production caller. Audit and Event Structuring remain independent private operations.

## Goals / Non-Goals

**Goals:**

- Make the normal Skill invocation contract accurately describe Host-Agent summarization and formatting of the current validated Feed.
- Keep editorial transformations useful while making evidence support, compression, and omission visible.
- Establish terminology and regression checks that distinguish an information digest from financial analysis.
- Keep repository, Skill, Host Agent, Feed, and independent deterministic-operation ownership unambiguous.

**Non-Goals:**

- Defining a serialized digest schema or deterministic renderer.
- Making Host-Agent prose deterministic or guaranteeing identical grouping across invocations.
- Changing Feed collection, normalization, publication, retrieval, validation, identity, provenance, freshness, coverage, or degradation behavior.
- Removing, renaming, or wiring retained deterministic capabilities.
- Adding Providers, data sources, model runtime, prompt runtime, API credentials, trading behavior, or investment assistance.

## Decisions

### 1. Define a Host-Agent invocation contract, not a seventh deterministic family

`information-digest-invocation` governs observable normal Skill behavior after a Feed has been validated. The produced digest remains Host-Agent-owned. The existing six-family deterministic capability catalog remains closed and unchanged.

Alternative considered: add “Information Digest” to `skill-capability-surface`. Rejected because that would incorrectly imply repository ownership of LLM synthesis and would change the accepted deterministic capability inventory.

### 2. Replace analytical sections with an evidence-oriented output skeleton

The Skill instructions and user-facing docs will consistently require:

1. Feed status and cutoff;
2. coverage and source availability;
3. current updates;
4. provenance and freshness;
5. data-quality and compression limitations.

Topic groups inside current updates may adapt to Feed contents. Fixed financial sections such as capital-flow changes, significant events, and anomalous signals will be removed because they imply comparisons or analytical capabilities that the current caller graph does not provide.

Alternative considered: retain the old section names while adding disclaimers. Rejected because disclaimers do not remove the implied significance, anomaly, and financial-judgment contract.

### 3. Allow editorial transformation but prohibit epistemic upgrades

The Host Agent may group related items across domains, derive headings, reorder for readability, consolidate repetition, and compress detail. Those actions are presentation choices only. They must not introduce unsupported facts or be characterized as deterministic ranking, importance, anomaly, causality, market impact, prediction, or investment implications.

A source’s own analytical language may be summarized only with clear attribution. This preserves information present in public evidence without converting source opinion into a Skill or Host-Agent conclusion.

Alternative considered: permit only item-by-item transcription. Rejected because it would not provide a useful digest and would scale poorly as Providers expand.

### 4. Make compression auditable without adding a digest schema

For each Feed domain, the digest will state the total item count and reconcile every item into one of three presentation categories: individually summarized, represented through consolidation, or omitted. Omission is disclosed as editorial compression and cannot be justified through an unsupported importance claim.

This is a semantic output requirement enforced through Skill instructions and documentation regression tests, not a new JSON contract. No final-output schema or deterministic completeness engine is introduced.

Alternative considered: require every item to be expanded. Rejected because it prevents useful compression. Silent highlight selection was also rejected because, without user scope or an accepted ranking caller, it creates hidden relevance judgment.

### 5. Preserve the current Feed and failure boundaries verbatim

Normal invocation continues to use `scripts/skill/prepare-feed`, consume only the canonical-main published Feed, validate fail-closed, accept valid degraded products with warnings, and stop on retrieval or validation failure. No local fallback, Provider call, historical lookup, retained-capability chaining, or partial digest is added.

Existing Feed behavior tests remain authoritative. Documentation tests will change only where they currently enforce the obsolete briefing terminology or where new consistency assertions are needed.

### 6. Synchronize authoritative and user-facing language surgically

Implementation will update the Skill contract, coding-agent architecture boundary, Skill-loaded references, English and Chinese README positioning, architecture documentation, affected living-spec purpose wording, and focused documentation tests. Other financial terms that accurately describe evidence domains, prohibited interpretation inside Feed, retained capability contracts, or investment-safety boundaries will remain; the change does not perform a global word purge.

`openspec/config.yaml` remains unchanged because it contains no product positioning or behavioral contract. Feed schemas, Agent invocation schema, workflow configuration, generated Feed artifacts, and provider code remain unchanged.

## Risks / Trade-offs

- **[Risk] Editorial ordering may be perceived as importance ranking** -> Documentation will label grouping and order as presentation choices and prohibit importance claims.
- **[Risk] Per-domain accounting adds output verbosity** -> Keep accounting concise while requiring counts to reconcile; detailed item expansion is not required.
- **[Risk] Source-authored analysis may be mistaken for the digest’s conclusion** -> Require explicit source attribution and prohibit authority upgrades.
- **[Risk] Broad terminology replacement could erase accurate retained-capability or safety documentation** -> Update only current-product claims and preserve factual descriptions of retained libraries and evidence boundaries.
- **[Risk] Documentation-only tests cannot validate arbitrary Host-Agent prose semantically** -> Test the enforceable Skill instructions and cross-document contract; retain semantic grounding as a Host-Agent responsibility rather than claiming deterministic proof.

## Migration Plan

1. Update the accepted contract delta and the living-spec purpose text that cannot be changed through a delta operation.
2. Rewrite the normal Skill instructions and Skill-loaded references around the information-digest contract.
3. Align `AGENTS.md`, README files, architecture documentation, and any other current-product claims found by a focused terminology audit.
4. Replace obsolete briefing assertions in `tests/test_feed_documentation.py` with positive digest-boundary and negative financial-judgment assertions.
5. Run focused documentation tests, the canonical repository quality gate, and strict OpenSpec validation.

Rollback consists of reverting the documentation, tests, and living-spec synchronization together. No data, schema, runtime, Feed, or deployment migration is required.
