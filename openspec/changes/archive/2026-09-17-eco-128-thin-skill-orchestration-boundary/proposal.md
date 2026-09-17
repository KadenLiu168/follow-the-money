## Why

`SKILL.md` currently repeats Feed structure, Digest output, Host-Agent presentation,
and semantic-field rules that already belong to accepted Feed, presentation, safety,
and `DigestContext` contracts. This duplication obscures ownership and can drift from
the authoritative contracts even though normal `/follow-the-money` behavior is
already defined elsewhere.

## What Changes

- Reduce `SKILL.md` to the Skill purpose, the
  `validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest`
  pipeline, `scripts/skill/prepare-feed` invocation, fail-closed behavior, links to
  the authoritative contracts, and the evidence-only safety boundary.
- Remove duplicated Feed schema/domain/Provider descriptions, Digest output-format
  requirements, Host-Agent presentation and compression rules, and semantic-field
  rules already enforced by `DigestContext` preparation.
- Keep Feed rules in the Feed contract, Digest formatting in the presentation
  contract, and safety rules in the safety boundary; do not rewrite those contracts
  when their existing ownership is already complete.
- Update focused documentation regressions so they enforce the thin orchestration
  boundary and the existing ownership split instead of requiring duplicated rules in
  `SKILL.md`.
- Preserve runtime behavior and make no change to Feed production, current-Feed
  retrieval or validation, `DigestContext`, schemas, Provider contracts, publication,
  or Host-Agent output behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This Change aligns Skill instructions and their static regression coverage with
the accepted `information-digest-invocation`, `digest-presentation-contract`,
`digest-preparation-contract`, and `skill-agent-responsibility-boundary` requirements;
it does not change externally observable behavior or a living requirement.

## Impact

- Documentation: `SKILL.md` only.
- Tests: focused ownership assertions in `tests/test_feed_documentation.py` and
  `tests/test_digest_presentation_contract.py`.
- Runtime and contract surfaces intentionally unchanged: `src/`, `scripts/`,
  `schemas/`, `providers/`, `config/`, `feeds/`, current reference contracts, and
  living specs.
- Verification covers the static ownership boundary, deterministic preparation and
  invocation regressions, the canonical quality gate, strict OpenSpec validation,
  and an available Host-level `/follow-the-money` smoke without treating repository
  preparation output as the final Digest.
