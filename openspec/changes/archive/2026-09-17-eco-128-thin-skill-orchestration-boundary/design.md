## Context

See `proposal.md` for motivation. The accepted contracts already separate the
runtime path and ownership:

```text
validated Feed -> DigestContext -> Host Agent -> evidence-preserving Digest
```

`references/feed-contract.md` owns retrieval, validation, Feed structure, and Feed
semantics. `references/digest/presentation-contract.md` and its child contracts own
Host-Agent representation and compression. `references/safety-boundary.md` owns the
evidence and authority limits. `SKILL.md` currently links all three but also restates
parts of each. The current tests encode some of that duplication by requiring output,
coverage, freshness, domain-dispatch, and presentation vocabulary directly in the
Skill instructions.

ECO-127 already made `scripts/skill/prepare-feed` the single current-Feed-to-
`DigestContext` entry. This Change must not alter that command, its output, or the
subsequent Host-Agent responsibility.

## Goals / Non-Goals

**Goals:**

- Make `SKILL.md` a thin executable handoff that is sufficient to invoke the existing
  preparation path and stop safely on failure.
- Retain concise, explicit evidence-only prohibitions at the invocation boundary while
  linking detailed rules to their single authoritative contracts.
- Make focused tests prove ownership and non-duplication rather than require copied
  contract prose.
- Preserve enough invocation instruction for `/follow-the-money` to proceed directly
  without asking for user-supplied research scope.

**Non-Goals:**

- Changing Feed, `DigestContext`, presentation, safety, or living OpenSpec
  requirements.
- Editing `src/`, `scripts/`, `schemas/`, `providers/`, configuration, generated Feed
  products, reference contracts, README files, or architecture documents.
- Adding a renderer, template, prompt pipeline, model runtime, new validation layer,
  or another evidence authority.
- Redesigning final Digest sections, domain representation, or compression behavior.

## Decisions

### 1. Use links as the ownership boundary

`SKILL.md` will keep direct links to the Feed contract, safety boundary, and global
Digest presentation contract. It will not summarize their detailed inventories or
rules. This leaves the Skill actionable while ensuring each rule has one descriptive
owner.

Alternative considered: remove the links and retain a compact copy of every rule.
That remains duplication and gives future maintainers no reliable authority path.

### 2. Keep only invocation-critical instructions in `SKILL.md`

The retained body will contain:

- purpose and existing frontmatter, including `disable-model-invocation: true`;
- the four-stage pipeline;
- `scripts/skill/prepare-feed` and its canonical non-persisted `DigestContext`
  handoff;
- exact-error-and-stop behavior with no local, stale, partial, historical, or
  unvalidated fallback;
- direct invocation without accepting user-supplied research scope;
- a concise evidence-only prohibition against unsupported analysis, financial
  judgment, recommendation, or trading direction;
- one sentence assigning preparation to the Skill and presentation to the Host Agent.

The body will omit the five-domain inventory, Provider coverage, Feed schema and
artifact detail, mandatory Digest sections, editorial operations, compression
accounting, `payload.type` dispatch, closed-field lists, and `semantic_context`
semantics.

Alternative considered: retain the mandatory Digest-section list and Host-Agent
operations because they are useful at runtime. Those instructions are already
normative in the presentation and invocation contracts; retaining them would defeat
the thin-boundary goal and preserve drift risk.

### 3. Test semantic ownership, not document size

Focused tests will require the purpose, pipeline, command, contract links, failure
behavior, no-fallback boundary, and evidence-only safety language in `SKILL.md`. They
will also require Feed detail in the Feed contract and presentation/detail ownership
in the presentation hierarchy while asserting representative duplicated rules are
absent from `SKILL.md`.

No maximum line count will be introduced. A line-count gate is formatting-sensitive
and would not prove that contract ownership is correct.

### 4. Treat runtime invariance and Host behavior as separate evidence

Repository verification will rerun deterministic preparation and invocation tests to
show the command and `DigestContext` behavior are unchanged, in addition to the
canonical quality gate. A Host-level `/follow-the-money` smoke is the direct evidence
that final Digest generation still occurs. If the Apply environment cannot perform
that Host invocation, the completion report must identify the missing acceptance
evidence rather than substitute `prepare-feed` output for a Digest.

## Risks / Trade-offs

- [Risk] Removing duplicated prose could make `SKILL.md` less self-contained. ->
  Mitigation: retain direct relative links to all three authoritative contracts and
  keep only the instructions required to execute safely.
- [Risk] Tests may continue to force deleted details back into `SKILL.md`. ->
  Mitigation: rewrite only the assertions that currently encode duplication and add
  explicit ownership/non-duplication checks.
- [Risk] A documentation-only diff could be mistaken for proof of Host-level output.
  -> Mitigation: distinguish repository preparation regressions from the required
  Host smoke and report any unavailable live evidence truthfully.
- [Trade-off] Some safety vocabulary remains in both `SKILL.md` and the safety
  boundary. This limited duplication is intentional because the user requires the
  invocation boundary itself to state evidence-only constraints; detailed safety
  semantics remain authoritative in the safety reference.

## Migration Plan

1. Characterize the intended thin Skill boundary with focused failing assertions.
2. Rewrite `SKILL.md` without changing referenced contracts or runtime files.
3. Run focused documentation, preparation, and invocation regressions; inspect the
   diff allowlist for out-of-scope files.
4. Run the canonical quality gate, strict OpenSpec validation, and the Host-level
   smoke when the environment exposes the installed Skill.

Rollback is a direct revert of `SKILL.md` and the two focused test files; there is no
data, schema, publication, or runtime migration.
