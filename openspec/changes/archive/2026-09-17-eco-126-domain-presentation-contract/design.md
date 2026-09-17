## Context

See `proposal.md` for motivation. The current `SKILL.md` correctly owns canonical current-Feed consumption and global Digest behavior, but it also contains filing subtype detail, `semantic_context` applicability, field-level presentation guidance, compression mechanics, and analytical prohibitions in one file. The accepted `information-digest-invocation` and `skill-agent-responsibility-boundary` specs already establish that the Digest is Host-Agent-owned output behavior, not a second deterministic repository capability.

The active Feed has exactly five payload types. `news`, `macro_release`, and `policy` may carry the closed ECO-130 `semantic_context`, including valid legacy omissions; `positioning` and `filing` never carry it. Positioning has typed current/previous/delta/comparison evidence, while filing contains materially different `form13f`, `form4`, and `beneficial_ownership` shapes. Every payload also contains `raw_metadata` in some versions or subtypes, but that open object is not a safe presentation authority.

## Goals / Non-Goals

**Goals:**

- Give every active Feed domain one reviewable owner for field-level Digest presentation rules.
- Make presentation evidence a closed whitelist so a Feed-schema addition cannot silently expand Host-Agent expression.
- Keep global evidence, compression, and safety rules singular and preserve all accepted accounting and attribution guarantees.
- Make structural regressions detectable without claiming that keyword matching can prove natural-language semantic safety.

**Non-Goals:**

- Changing or validating Feed data differently, enriching legacy items, parsing `raw_metadata`, or adding semantic fields.
- Making Host-Agent prose deterministic or introducing a serialized Digest contract.
- Adding runtime dispatch, rendering, templates, prompts, model invocation, orchestration, services, or new user inputs.
- Reworking README, architecture, or Feed documentation that already truthfully describes the global boundary unless a focused consistency assertion requires it.

## Decisions

### 1. Use a static reference hierarchy, not an execution stage

`SKILL.md` will continue to direct Feed preparation and fail-closed validation, then require the Host Agent to apply `references/digest/presentation-contract.md`. The global contract will link `compression.md` and exactly five files under `references/digest/domains/`; the matching domain file is chosen from the item's already validated `payload.type`.

```text
validated published Feed -------------------+
                                             |
global presentation contract ---------------+--> Host Agent --> Digest
matching domain contract by payload.type ----+
compression contract -----------------------+
```

This is documentation traversal by the Host Agent, not code dispatch. No reference file sits in the Feed data path or becomes a new runtime authority.

Alternative considered: add a domain resolver or template renderer. Rejected because the active discriminator is already validated and the requested behavior is normative presentation guidance, not deterministic output generation.

### 2. Make evidence-field lists normative and closed

Every domain file will use the same four primary sections: Domain Purpose, Evidence Fields, Recommended Representation, and Forbidden Interpretation. Evidence Fields will enumerate canonical validated field paths rather than friendly aliases. Common item identity/provenance paths must be stated explicitly where usable; domain payload and nested typed evidence must use current schema names. `raw_metadata` is excluded even when schema-valid.

The whitelist is closed: unlisted fields are unavailable to presentation, and a later Feed field requires an explicit contract update before use. Null, explicit unavailability, and absence remain limitations rather than extraction prompts. For the three ECO-130 domains, `semantic_context` paths are eligible only when present; a legacy omission never authorizes title parsing or context reconstruction.

Alternative considered: make Evidence Fields illustrative. Rejected because it would not establish domain ownership or prevent an additive Feed change from silently broadening Digest behavior.

Alternative considered: allow all schema-valid fields except a blacklist. Rejected because `raw_metadata` is intentionally open and future schema additions would become presentation authority without review.

### 3. Keep one contract per payload domain while representing real variants

The exact contract files are `news.md`, `macro_release.md`, `policy.md`, `positioning.md`, and `filing.md`. `filing.md` will contain separate representation subsections for `form13f`, `form4`, and `beneficial_ownership` within the one filing-domain owner. `positioning.md` may present validated current, previous, delta, comparison, and explicit derivation facts without translating them into direction, sentiment, signals, or market meaning.

News, macro, and policy contracts will describe both typed payload evidence and optional matching `semantic_context`. Macro will distinguish previous-period observations from explicit same-period revisions. Policy will present factual issuer/action/time/scope evidence without purpose or effect. News will preserve source attribution and avoid treating editorial order as importance.

Alternative considered: one contract per Provider or filing subtype. Rejected because the accepted external discriminator is the five-domain `payload.type`; Provider/subtype contracts would create overlapping ownership and violate the exactly-one rule.

### 4. Put compression accounting in one shared contract

`compression.md` will carry the accepted per-domain equation:

```text
domain total = individually summarized + represented through consolidation + omitted
```

It will also own supporting-item traceability, omission disclosure, and the prohibition on importance/relevance rationales. Domain files may recommend grouping shapes but will not redefine accounting or omission policy.

Alternative considered: repeat compression rules in every domain file. Rejected because identical global guarantees would drift independently and obscure whether a domain has weaker omission semantics.

### 5. Refactor SKILL.md by responsibility, not by domain-name deletion

`SKILL.md` must still identify the five-domain Feed, global output sections, current-window meaning, Feed status/provenance/freshness/coverage, fail-closed behavior, and the evidence-only safety boundary. It will link the global presentation contract and require the applicable domain contract.

Field-level and subtype-specific guidance will move out. Tests will not prohibit domain names in `SKILL.md`, because the active Feed inventory is a global consumption fact; they will prohibit domain-specific headings or representative field/subtype rules from returning there.

Alternative considered: reduce `SKILL.md` to only a link. Rejected because invocation, failure, and global output requirements must remain visible at the Skill entry point.

### 6. Validate structure and affirmative instructions instead of banning safety vocabulary

`tests/test_digest_presentation_contract.py` will compare the domain filename set with the canonical active payload-type constant, require the global contract to link the compression contract and each domain contract exactly once, require the common section structure, assert the closed-whitelist and missing-evidence clauses, exclude `raw_metadata` from eligible fields, and verify the Skill delegation boundary.

The contracts must name terms such as ranking, impact, and prediction to prohibit them, so a bare forbidden-word scan would reject correct safety text. Negative tests will instead reject known affirmative analytical instructions or analytical section requirements such as ranking events, scoring items, classifying bullish/bearish direction, predicting outcomes, recommending trades, or adding market-impact sections. Existing global documentation tests remain responsible for the wider Feed-only boundary.

Alternative considered: ban individual analytical words anywhere in the files. Rejected because it makes the required Forbidden Interpretation sections impossible to write and provides false assurance about grammar and meaning.

## Risks / Trade-offs

- [Risk] Closed field lists can lag a legitimate future Feed addition. -> Treat that friction as intentional review control; the new field remains ineligible until its domain contract and tests are deliberately updated.
- [Risk] Markdown tests can become a second parser or duplicated schema authority. -> Test file inventory, headings, links, core clauses, and selected invalid instructions only; rely on schema tests for wire shape and human/OpenSpec review for presentation semantics.
- [Risk] Filing's three subtypes can make one domain file long. -> Use subtype subsections inside the single owner rather than creating overlapping contracts or genericizing materially different evidence.
- [Risk] Moving text can accidentally weaken global invocation or compression guarantees. -> Characterize the current Skill assertions first, preserve global clauses, add hierarchy-specific regressions, and run the canonical quality gate.
- [Risk] A source-authored analytical statement could be mistaken for a Host-Agent conclusion. -> Preserve the existing attribution-only exception in the global and domain forbidden-interpretation rules.

## Migration Plan

1. Add focused failing contract tests for the exact hierarchy, closed Evidence Fields structure, missing-evidence behavior, compression accounting, analytical-instruction boundary, and Skill responsibility split.
2. Create the global, compression, and five domain reference files from the current validated schema and accepted living specs, including filing subtype sections and optional/legacy `semantic_context` behavior.
3. Refactor only domain-specific and compression detail out of `SKILL.md`; retain invocation, failure, global Digest output, and evidence/safety requirements, and add the global contract link.
4. Adjust existing documentation tests only where their assertions intentionally move to the new contract files. Do not change schemas, source, Providers, configuration, artifacts, or runtime entries.
5. Run focused tests, the canonical quality gate, and strict OpenSpec validation.

Rollback removes the new reference hierarchy and its tests and restores the moved instructions to `SKILL.md` as one coherent documentation change. No Feed, persisted data, or runtime migration is involved.
