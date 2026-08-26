## Why

The scheduled Feed workflow currently reads `runner.labels` from workflow-level `env`, where the `runner` context is unavailable, so GitHub Actions can reject the workflow before the opt-in Feed job is created even though repository-specific validation passes. ECO-48 closes this Phase-4.5 baseline gap before Phase 5 by adding an authoritative GitHub-Actions-aware semantic check while preserving the existing deterministic Feed deployment contract.

## What Changes

- Remove the invalid workflow-level `runner` expression and the redundant runtime runner-label guard from `generate-feed.yml`; retain `runs-on: [self-hosted, follow-the-money-feed]` as the sole dedicated-runner scheduling authority and make comments describe scheduler enforcement truthfully.
- Add pinned upstream `actionlint` validation to the explicit pre-merge CI path, with repository configuration that recognizes the custom self-hosted runner label without globally suppressing label validation.
- Keep validation ownership separated: `actionlint` checks GitHub Actions syntax, expressions, context availability, and workflow-key semantics, while `scripts/validate_workflows.py` and the existing workflow tests continue to check follow-the-money deployment invariants.
- Add one invalid workflow fixture outside `.github/workflows/` and a CI regression proving the same validator accepts real workflows but rejects unavailable workflow-level context usage.
- Add only the focused project-level regression needed to preserve `runs-on` as the single runner-selection authority; retain opt-in, persistence, durable rate-state, non-destructive checkout, allowlisted publication, and observable failure behavior unchanged.
- Exclude Feed/Provider/schema/configuration/financial behavior changes and all Phase-5 Agent contracts, runtimes, DTOs, schemas, adapters, orchestration, and retained-library wiring.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Require the accepted Feed deployment workflow to pass GitHub Actions workflow-definition and expression/context semantic validation in the authoritative pre-merge path, in addition to existing repository-specific deployment invariant checks.

## Impact

The planned implementation is limited to `.github/workflows/generate-feed.yml`, `.github/workflows/test.yml`, `.github/actionlint.yaml`, one invalid workflow fixture under `tests/fixtures/workflows/`, the minimum focused workflow-test assertion, and this Change. It adds a pinned CI-only upstream validator without adding a Python dependency or making `scripts/quality_gate.py` depend on a globally installed executable. `scripts/validate_workflows.py`, production source, Feed schemas, Provider/configuration contracts, generated Feed behavior, archived Changes, and Phase-5 architecture remain unchanged unless a demonstrated project-specific stale assertion requires a narrowly justified adjustment during Apply.
