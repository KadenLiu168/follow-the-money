## 1. Characterize the Contract Boundary

- [x] 1.1 Add failing tests in `tests/test_digest_presentation_contract.py` that compare the exact `references/digest/domains/*.md` filename set with `SUPPORTED_FEED_PAYLOAD_TYPES`, require the global contract to link `compression.md` and every domain contract exactly once, and verify failure is caused by the missing ECO-126 hierarchy.
- [x] 1.2 Add failing tests requiring every domain file to contain Domain Purpose, Evidence Fields, Recommended Representation, and Forbidden Interpretation sections; a closed-whitelist statement; missing-evidence behavior; and no eligible `raw_metadata`, then verify the cases fail for the intended missing contracts.
- [x] 1.3 Add failing regressions for global compression accounting, Skill delegation without domain-field duplication, and prohibited affirmative analytical instructions without banning the vocabulary needed to state negative safety rules; verify the focused test file fails only on unimplemented ECO-126 behavior.

## 2. Create the Static Presentation-Contract Hierarchy

- [x] 2.1 Create `references/digest/presentation-contract.md` and `references/digest/compression.md` with current validated-Feed input, Host-Agent ownership, domain selection by validated `payload.type`, allowed editorial operations, evidence/attribution limits, per-domain count reconciliation, consolidation traceability, omission disclosure, and explicit no-runtime language; verify the focused global and compression tests pass.
- [x] 2.2 Create `news.md`, `macro_release.md`, and `policy.md` under `references/digest/domains/` using canonical schema field paths, closed evidence whitelists, optional matching `semantic_context`, legacy-omission/null handling, factual recommended representations, and domain-specific forbidden interpretations; verify their focused contract tests pass and no rule reads or reconstructs `raw_metadata`.
- [x] 2.3 Create `positioning.md` with a closed whitelist for typed market identity, current/previous/delta/comparison/derivation evidence and prohibitions on directional or market interpretation; verify the positioning contract tests pass.
- [x] 2.4 Create one `filing.md` contract with closed common fields plus separate `form13f`, `form4`, and `beneficial_ownership` representation subsections, preserving typed comparison, amendment, transaction/holding, ownership, provenance, and limitation semantics without analytical conclusions; verify the filing and exact-one-domain tests pass.

## 3. Refactor the Skill Entry Point

- [x] 3.1 Refactor `SKILL.md` to retain canonical current-Feed preparation, fail-closed behavior, five-domain inventory, global Digest outputs, provenance/freshness/coverage, and safety ownership while linking and requiring the global presentation contract; verify domain-specific field/subtype rules reside only in the applicable reference contracts.
- [x] 3.2 Update `tests/test_feed_documentation.py` only where existing assertions intentionally move from `SKILL.md` to the presentation-contract hierarchy, preserve all other current invocation and negative capability assertions, and verify `.venv/bin/python -m pytest tests/test_digest_presentation_contract.py tests/test_feed_documentation.py -q` passes.
- [x] 3.3 Search current documentation and runtime surfaces for conflicting claims or accidental new presentation/runtime authority; change only directly conflicting current-facing documentation, and verify `git diff --name-only` contains no Feed schema, Provider, configuration, generated Feed, or `src/follow_the_money/` changes.

## 4. Complete Verification

- [x] 4.1 Run `uv sync --frozen --all-groups` and verify the locked development environment resolves without dependency changes.
- [x] 4.2 Run `.venv/bin/python scripts/quality_gate.py` and resolve only ECO-126 regressions until the canonical gate passes.
- [x] 4.3 Run `openspec doctor`, `openspec validate eco-126-domain-presentation-contract --strict`, and `openspec validate --all --strict`; verify all commands succeed and the implementation, tests, references, and accepted evidence-only Host-Agent boundary remain aligned.
