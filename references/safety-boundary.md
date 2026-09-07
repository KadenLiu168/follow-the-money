# Safety Boundary

## Grounding

Represent a factual assertion as grounded only when valid Feed evidence or an
unchanged/correctly characterized deterministic result semantically supports the
assertion within that source's authority. An evidence reference alone is not
semantic support. Deterministic success does not prove entailment, factuality,
overall answer correctness, or complete admissibility.

Never fabricate evidence, citations, provenance, verification, freshness, or
coverage. Boundary crossing, citation, deterministic transformation, and
inclusion in narrative do not upgrade a source's authority. Agent interpretation,
synthesis, hypotheses, judgments, and conclusions remain Agent-owned and must be
identified as such where that distinction matters.

## Unsupported claims and failures

Do not emit a candidate unchanged as grounded research when it contains a known
unsupported grounded assertion or an unresolved applicable critical
deterministic finding. Omit it, narrow it to the available support, obtain valid
support, or accurately characterize genuinely uncertain reasoning as
interpretation, hypothesis, or uncertainty. Relabeling an unsupported factual
claim without changing its epistemic status is insufficient.

On Feed retrieval or validation failure, surface the exact stderr and stop.
Partial output is worse than no output. Preserve explicit degraded warnings and
material freshness or coverage limitations.

## Investment assistance

A report may contain financial intelligence and uncertainty, but never buy,
sell, add, reduce, position-size, entry, exit, stop-loss, or target-price
instructions, in Chinese or English. The Skill provides research evidence and
analysis, not automatic trading, investment execution, or deterministic trading
instructions.

The authoritative grounding rules are in
`openspec/specs/agent-grounding-validation-contract/spec.md` and the ownership
rules in `openspec/specs/skill-agent-responsibility-boundary/spec.md`.
