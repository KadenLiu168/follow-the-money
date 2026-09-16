## Why

The current SEC EDGAR contract publishes deterministic 13F current-state evidence but cannot represent Form 4 ownership events, so the Feed cannot preserve who reported an ownership filing, the issuer and security involved, the reported transaction or holding, and the post-transaction state. ECO-131 adds that evidence as a bounded SEC vertical slice without introducing insider-trading analysis or a generic semantic graph.

## What Changes

- Keep Feed schema major v4, the closed five-domain set, and `domain = filing`; add a versioned `filing_subtype` distinction for 13F and Form 4 payloads.
- Evolve the SEC EDGAR production contract to version 3 while retaining bounded read compatibility for valid SEC contract versions 1 and 2.
- Add an authoritative `watched_form4_issuers` configuration selection, initially containing only Berkshire Hathaway issuer CIK `0001067983`, and embed it in the canonical Feed configuration snapshot.
- Acquire exact Form `4` and `4/A` filings accepted inside the advancing Feed window from each watched issuer's SEC submissions `recent` listing, require proof that the listing covers the full window, and fetch every selected primary ownership XML without truncation.
- Add a Provider-specific deterministic Form 4 core and closed structured payload for issuer identity, reporting owners and complete relationships, non-derivative and derivative transactions, standalone holdings, post-transaction amounts, ownership nature, amendments, remarks, and bounded field-linked footnotes.
- Reuse ECO-125 measured numeric facts and owned decimal normalization for source numeric values while keeping identity, text, time, relationship, entry association, and payload projection SEC-specific.
- Publish one filing item per accession and stable entry identities based on accession, SEC table, and source ordinal; preserve deterministic ordering and canonical-byte identity.
- Treat Form 4/A as an independent evidence event with its SEC-supplied original-submission date; do not infer an amended accession, merge history, or designate an effective version.
- Bound Form 4 acquisition to at most 20 eligible filings per window and fail closed on incomplete listing coverage, bound exhaustion, unsupported or malformed XML, dangling footnotes, or any omitted eligible filing/entry.
- Preserve the evidence-only boundary: no bullish/bearish label, signal, score, confidence, importance, recommendation, inferred holding delta, transaction-value calculation, or investment interpretation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Extend the existing SEC filing contract with watched-issuer Form 4/Form 4-A event acquisition, deterministic structured ownership evidence, SEC contract-version-3 validation, and mixed 13F-current-state/Form-4-window slice semantics.

## Impact

- SEC Provider acquisition and pure parsing logic under `src/follow_the_money/providers/`, including production adapter construction and the existing managed per-send transport.
- Strict configuration models/loaders and the canonical Feed configuration snapshot.
- SEC manifest version/support tables, fixture provenance, request bounds, and embedded Provider contract validation.
- `schemas/feed.schema.json` and semantic Feed validation for versioned filing subtypes, Form 4 structures, exact issuer selection, identity, ordering, numeric, footnote, and source-time invariants.
- SEC snapshot completeness logic so v3 validates the complete 13F state plus the current-window Form 4 event set without retaining unbounded filing history.
- Focused SEC/Form 4 fixtures and tests plus Feed determinism, compatibility, boundary, regression, and documentation updates.
- No new dependency, credential, Provider, Feed domain, public CLI, model runtime, Agent orchestration, or trading capability.
