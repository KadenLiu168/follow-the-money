## 1. Characterize the Content-First Contract

- [x] 1.1 Extend `tests/test_digest_presentation_contract.py` with semantic regressions requiring current-window updates as the primary substantive surface; complete secondary status, cutoff, coverage, freshness, warning, degradation, availability, reconciliation, traceability, omission, and limitation information; a bounded material-degradation caveat; truthful zero-update behavior; and no fabricated content, then run `.venv/bin/python -m pytest tests/test_digest_presentation_contract.py -q` and verify the new hierarchy assertions fail against the pre-change global contract while existing presentation-contract regressions still pass.
- [x] 1.2 Add ownership assertions that `SKILL.md` does not encode audit-first or content-first output ordering and add no assertions for fixed final-Digest headings, heading levels, section order, or templates; rerun the focused test and verify any remaining failure concerns only the missing global presentation hierarchy.

## 2. Establish the Global Presentation Hierarchy

- [x] 2.1 Update `references/digest/presentation-contract.md` to distinguish the primary content surface, secondary audit surface, concise material-degradation caveat, and valid zero-update behavior while retaining evidence-only, local provenance, missing-evidence, safety, Host-Agent ownership, static-guidance, and no-runtime boundaries; run `.venv/bin/python -m pytest tests/test_digest_presentation_contract.py -q` and verify all focused regressions pass.
- [x] 2.2 Confirm the contract makes content-first a semantic priority rather than importance, ranking, significance, analysis, relevance filtering, or a fixed Markdown structure, and verify the focused negative assertions pass without adding a renderer, template, prompt, model, or orchestration instruction.
- [x] 2.3 Re-read `SKILL.md` after the contract update and leave it unchanged if it still contains only orchestration, failure, safety, and authority links; verify the ownership assertions pass and document any evidenced contradiction before proposing a Skill edit rather than adding presentation prose speculatively.
- [x] 2.4 Inspect `git diff --name-only` and the textual diff and verify implementation changes are limited to `references/digest/presentation-contract.md` and `tests/test_digest_presentation_contract.py`, with no changes to `src/`, `scripts/`, `DigestContext`, `schemas/`, `providers/`, configuration, collection/publication, `references/digest/compression.md`, or `references/digest/domains/*.md`.

## 3. Verify Contract and Repository Consistency

- [x] 3.1 Run `.venv/bin/python -m pytest tests/test_digest_presentation_contract.py tests/test_feed_documentation.py -q` and verify the content-first hierarchy, thin-Skill ownership, five-domain inventory, compression ownership, safety vocabulary, and static Host-Agent boundary pass together.
- [x] 3.2 Run `openspec doctor`, `openspec validate eco-129-content-first-digest-presentation --strict`, and `openspec validate --all --strict`; verify the proposal, design, delta spec, tasks, living capabilities, and current changes are coherent.
- [x] 3.3 Run `.venv/bin/python scripts/quality_gate.py` and `git diff --check`; verify the canonical gate passes and no whitespace error or out-of-scope runtime/data change is present.

## 4. Stage-3 Review Repairs

- [x] 4.1 Add focused assertions for the delta spec's local-provenance and fail-closed-failure scenarios, which previously had no regression coverage, and add the missing fail-closed sentence those assertions require in `references/digest/presentation-contract.md`.
- [x] 4.2 Scope the content-first assertions to the `## Content-First Presentation Hierarchy` section so pre-existing safety vocabulary elsewhere in the contract cannot satisfy them vacuously.
- [x] 4.3 Narrow the `SKILL.md` ownership assertion to duplicated ordering vocabulary so that pointing at the named contract stays permitted while re-encoding its ordering or surface terms stays blocked.
- [x] 4.4 Reflow the new section's paragraph wrapping; rerun focused tests, strict target/all OpenSpec validation, and the canonical quality gate.
- [x] 4.5 Confirm the changed-file set stays limited to `references/digest/presentation-contract.md`, `tests/test_digest_presentation_contract.py`, and this Change's artifacts.
