## Why

The SEC Feed can publish deterministic 13F current state and Form 4 ownership events, but it cannot preserve Schedule 13D/13G beneficial-ownership disclosures or their source-supported changes. ECO-132 adds that evidence as a bounded SEC vertical slice while retaining the five-domain, credential-free, evidence-only architecture.

## What Changes

- Keep Feed schema major v4 and `domain = filing`; evolve SEC EDGAR to Provider contract v4 with `filing_subtype = beneficial_ownership` alongside the existing `form13f` and `form4` subtypes.
- Add a separate authoritative `watched_beneficial_ownership_filers` selection, initially containing only Berkshire Hathaway reporting filer CIK `0001067983`.
- Select exact `SCHEDULE 13D`, `SCHEDULE 13D/A`, `SCHEDULE 13G`, and `SCHEDULE 13G/A` filings accepted inside the advancing Feed window, deduplicated by accession across configured filers.
- Parse only verified SEC-native structured XML forms through bounded form-specific 13D and 13G parsers; do not add a generic SEC parser or legacy HTML/text parser.
- Publish one accession-based filing item containing issuer and ownership-class identity, source-ordered reporting persons and explicitly reported groups, current beneficial ownership facts, optional voting/dispositive-power facts, amendment metadata, and document-local source-field support.
- Resolve the nearest earlier comparable filing by filer, issuer, and ownership class through a bounded per-run reverse scan of official submissions history; compare internal ownership positions by explicit CIK or exact normalized source name.
- Reuse ECO-125 measured and derived numeric facts for exact `current - previous` share and percentage-point deltas while retaining current and previous accession provenance in the Provider-specific payload.
- Distinguish source-supported comparison, proved initial filing, and typed unavailability; never substitute zero for missing history or skip an unsupported nearer filing in favor of an older parseable filing.
- Preserve independent amendment events without inferring `amends_accession`, effective version, investment intent, control intent, takeover likelihood, market impact, signal, or recommendation.
- Continue one `sec_edgar` outcome and whole-Provider replacement for the mixed 13F state, Form 4 event, and beneficial-ownership event slice; historical enrichment filings do not become accumulated top-level events.
- Correct the SEC request-budget regression to include existing Form 4 sends, add bounded 13D/G current/history sends, and raise the pre-commit deadline only to the verified value required by the complete SEC v4 worst-case request shape while leaving SEC rate policy unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Extend the versioned SEC filing contract with bounded Schedule 13D/13G acquisition, structured beneficial-ownership evidence, deterministic previous-comparable enrichment, SEC v4 mixed-slice validation, and truthful request-budget admission.

## Impact

- SEC Provider manifest/version support, verified source documentation, request bounds, and fixture provenance under `providers/sec_edgar/`.
- Strict configuration models/loaders and the canonical Feed configuration snapshot.
- SEC acquisition adapters and a Provider-specific beneficial-ownership pure core under `src/follow_the_money/providers/`, reusing the existing managed transport and semantic numeric primitives.
- `schemas/feed.schema.json`, semantic Feed validation, canonical identity, SEC completeness checks, and whole-slice snapshot selection.
- Feed deadline configuration and request-budget regression coverage; SEC rate limits remain unchanged.
- Focused structured 13D/13G fixtures, parser/comparison/provenance tests, SEC v1-v3 compatibility tests, deterministic Feed regressions, and truthful documentation updates.
- No new dependency, credential, Provider, Feed domain, public CLI, model runtime, Agent orchestration, generic SEC framework, investment analysis, or trading capability.
