## Why

ECO-31 aligned the living baseline with the current Pre-Agent architecture, but the evidence needed to accept that baseline remains distributed across living requirements, tests, repository tooling, and historical trace material. Before Phase 4 defines a Skill-Agent contract, the repository needs one fresh, explicit, auditable decision that the complete current baseline is semantically consistent and protected by existing executable evidence.

## What Changes

- Strengthen the existing baseline-acceptance requirement so acceptance requires a complete current semantic trace across all three living capabilities, including explicit dispositions, caller status, focused evidence, and per-requirement results.
- Require the acceptance decision to combine Production Feed regressions, retained deterministic-library regressions, no-LLM and architecture-boundary evidence, the canonical repository quality gate, OpenSpec structural validation, and a final semantic consistency review.
- Create fresh Change-local traceability evidence by reconciling every current living requirement with current implementation, tests, negative invariants, and the current caller graph; reuse historical dispositions only after confirming that they remain true.
- Preserve the architecture under evaluation: no production behavior, tests, configuration, providers, schemas, workflows, dependencies, CI, runtime metadata, or future Agent contract is introduced merely to satisfy acceptance.
- Reuse `.venv/bin/python scripts/quality_gate.py` and existing focused tests; do not add a parallel acceptance runner or replacement test matrix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deterministic-core-retention`: Strengthen `Baseline acceptance uses semantic trace evidence` into the explicit final Phase-3 Pre-Agent acceptance contract while preserving all existing scenarios and architecture guardrails.

## Impact

The planned Apply is limited to ECO-32 Change artifacts: the minimal Change-local delta and fresh traceability evidence. It does not directly edit the living spec, change production APIs, runtime topology, Feed behavior, deterministic-library behavior, dependencies, CI, or deployment. Spec sync/archive, Linear updates, delivery, and Phase 4 Skill-Agent contract design remain separately authorized steps after this acceptance gate passes.
