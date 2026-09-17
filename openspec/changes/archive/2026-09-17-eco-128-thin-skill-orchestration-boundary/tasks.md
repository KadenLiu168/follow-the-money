## 1. Characterize the Thin Ownership Boundary

- [x] 1.1 Update `tests/test_feed_documentation.py` so `SKILL.md` is required to retain its purpose, `disable-model-invocation`, four-stage pipeline, `scripts/skill/prepare-feed`, authoritative contract links, fail-closed/no-fallback behavior, and evidence-only safety boundary, while Feed details and Digest output requirements are asserted against their existing owner documents; run the focused test and verify the new non-duplication expectation fails against the current verbose `SKILL.md`.
- [x] 1.2 Update `tests/test_digest_presentation_contract.py` so the presentation hierarchy, not `SKILL.md`, is required to own `payload.type` domain dispatch, closed evidence fields, Host-Agent representation, and compression guidance; assert representative domain, semantic-field, output-section, and editorial-operation rules are absent from `SKILL.md`, then run the focused test and verify failure is limited to the current duplicated Skill prose.

## 2. Reduce SKILL.md to Runtime Orchestration and Safety

- [x] 2.1 Rewrite `SKILL.md` to contain only the existing frontmatter and purpose, the `validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest` pipeline, the `scripts/skill/prepare-feed` handoff and three authoritative contract links, exact failure/stop and no-fallback behavior, direct no-scope invocation, concise evidence-only prohibitions, and the Skill/Host-Agent responsibility handoff; verify both focused documentation test files pass.
- [x] 2.2 Inspect `git diff --name-only` and the textual diff to verify implementation changes are limited to `SKILL.md`, `tests/test_feed_documentation.py`, and `tests/test_digest_presentation_contract.py`, with no edits to current reference contracts, living specs, Feed producer, `DigestContext`, schemas, Provider contracts, configuration, generated Feed products, or runtime entries.

## 3. Verify Unchanged Runtime and Contract Ownership

- [x] 3.1 Run `.venv/bin/python -m pytest tests/test_feed_documentation.py tests/test_digest_presentation_contract.py tests/test_feed_prepare.py tests/test_digest_prepare.py -q` and verify the thin documentation boundary plus canonical `prepare-feed`/`DigestContext` behavior pass together.
- [x] 3.2 Perform a Host-level `/follow-the-money` smoke in an environment exposing the installed Skill and verify it consumes the current prepared context and emits an evidence-preserving Digest; if that Host entry is unavailable, record this acceptance evidence as unresolved and do not treat `prepare-feed` JSON as a substitute for final Digest generation.
- [x] 3.3 Run `.venv/bin/python scripts/quality_gate.py` and verify the canonical repository gate passes with unchanged five-domain/eight-Provider, deterministic, evidence-only, credential-free, and no-model guarantees.
- [x] 3.4 Run `openspec doctor`, `openspec validate eco-128-thin-skill-orchestration-boundary --strict`, `openspec validate --all --strict`, and `git diff --check`; verify the documentation-only Change, skipped specs, design, tasks, implementation scope, and current living contracts are coherent.
