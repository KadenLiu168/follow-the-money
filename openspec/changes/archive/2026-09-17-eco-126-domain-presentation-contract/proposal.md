## Why

The information-digest Skill currently keeps global Feed-consumption, safety, compression, and domain-specific presentation guidance in one instruction file. ECO-130 has made the source-supported semantics of `news`, `macro_release`, and `policy` explicit, while `positioning` and `filing` already have materially different typed payloads, so continuing to add field-level presentation rules to `SKILL.md` would blur domain ownership and make the Host-Agent evidence boundary harder to review.

## What Changes

- Introduce a static Digest presentation-contract hierarchy with one global contract, one shared compression contract, and exactly one presentation contract for each active Feed domain: `news`, `macro_release`, `policy`, `positioning`, and `filing`.
- Define each domain contract as a closed normative whitelist of validated `source`, typed `payload`, and applicable `semantic_context` fields that the Host Agent may express. `raw_metadata`, absent values, and fields not listed by the contract do not become presentation evidence.
- Require null, explicitly unavailable, and legacy-omitted evidence to remain missing rather than being reconstructed from titles, other items, historical Feeds, external knowledge, or `raw_metadata`.
- Preserve the existing evidence-only and Host-Agent-owned boundary: presentation may group, order, consolidate, compress, and summarize, but may not add facts, significance, ranking, causality, sentiment, market interpretation, prediction, recommendation, or trading judgment.
- Refactor `SKILL.md` to retain current-Feed consumption, global digest output, failure, and safety requirements while delegating field-level presentation guidance through the global presentation contract.
- Add focused contract tests for exact domain coverage, required contract structure and links, closed evidence-field ownership, compression accounting, prohibited affirmative analytical instructions, and prevention of domain-specific rule drift back into `SKILL.md`.
- Keep Feed schemas, Providers, collection, validation, identity, publication, retrieval, and runtime behavior unchanged. No resolver, renderer, template engine, prompt pipeline, model orchestration, or digest service is added.

## Capabilities

### New Capabilities

- `digest-presentation-contract`: Defines the static global, compression, and per-domain rules that constrain Host-Agent presentation of the validated current Evidence Feed without creating another repository semantic capability or runtime stage.

### Modified Capabilities

None. The accepted `information-digest-invocation`, `skill-agent-responsibility-boundary`, and `semantic-context` requirements remain unchanged; this Change adds a more specific presentation contract beneath those existing boundaries.

## Impact

- Adds `references/digest/presentation-contract.md`, `references/digest/compression.md`, and five files under `references/digest/domains/`.
- Narrows `SKILL.md` to global invocation and evidence-boundary responsibilities and links it to the presentation-contract hierarchy.
- Adds `tests/test_digest_presentation_contract.py` and adjusts existing documentation assertions only where they currently require field-level guidance to remain in `SKILL.md`.
- Does not change `schemas/`, `providers/`, `src/follow_the_money/`, Feed artifacts, configuration, dependencies, network behavior, or public runtime entry points.
