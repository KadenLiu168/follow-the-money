## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for the acceptance requirement. The current `generate-feed.yml` already declares `runs-on: [self-hosted, follow-the-money-feed]`, but also assigns `${{ runner.labels }}` in workflow-level `env` and rechecks the label in a shell step. GitHub Actions does not make `runner` available at that workflow key, while the current PyYAML validator intentionally checks repository deployment invariants rather than GitHub's expression-context grammar.

The authoritative local Python gate already executes `scripts/validate_workflows.py`. ECO-48 must add an explicit Actions-aware CI check without replacing that validator, creating a Python wrapper dependency, requiring a developer-global binary, or changing the Feed execution/publication path.

## Goals / Non-Goals

**Goals:**

- Make the real workflow definition valid before job creation and leave `runs-on` as the single dedicated-runner authority.
- Give GitHub Actions semantics and follow-the-money deployment invariants distinct validators and explicit acceptance evidence.
- Exercise the same Actions-aware binary against both real workflows and one intentionally invalid unavailable-context fixture.
- Keep CI provisioning reproducible by pinning one upstream `actionlint` release in workflow configuration.

**Non-Goals:**

- Reimplementing GitHub's expression/context rules in Python or pytest.
- Moving `actionlint` into `scripts/quality_gate.py`, `pyproject.toml`, or `uv.lock`.
- Redesigning CI, reusable workflows, Feed scheduling, persistence, Provider execution, publication, schemas, status contracts, or Phase-5 Agent architecture.
- Treating GitHub server-side acceptance as verified unless an actual GitHub run or evaluation supplies that evidence.

## Decisions

### 1. Remove the duplicate runtime label path completely

Delete workflow-level `RUNNER_LABEL` and the `Fail on non-dedicated runner` step. Keep the exact `runs-on: [self-hosted, follow-the-money-feed]` declaration and update only the adjacent explanatory comments: the GitHub scheduler makes a job eligible only for a runner matching every required label, so a later shell inspection adds no independent protection.

Do not replace the removed step with a job-level or step-level `runner` expression. Alternatives rejected:

- Moving the expression to a context-valid runtime location would preserve two authorities for one scheduling policy.
- Keeping a literal/textual label check would test workflow text rather than scheduler eligibility.

### 2. Add upstream `actionlint` as a separate explicit CI acceptance step

Extend `.github/workflows/test.yml` with a clearly named Actions semantic validation step. Provision the upstream `rhysd/actionlint` executable from one literal pinned release tag in CI, then invoke that exact binary directly. The pin belongs only to CI implementation configuration and is not copied into the OpenSpec requirement.

Add `.github/actionlint.yaml` with only the repository's `follow-the-money-feed` custom self-hosted label in the supported self-hosted-runner label configuration. Do not disable the corresponding check globally or add unrelated ignores.

Alternatives rejected:

- Extending `scripts/validate_workflows.py` would create a partial second GitHub Actions interpreter that will drift from GitHub semantics.
- Replacing the Python validator would lose repository-owned persistence, ordering, allowlisting, and failure-observability checks.
- Adding `actionlint-py` or another Python wrapper would couple an application/dev dependency to a CI-only concern.
- Requiring `actionlint` from `scripts/quality_gate.py` would make the canonical local Python gate depend on untracked machine-global state.

### 3. Validate real workflows and reject one out-of-scan fixture with the same binary

The CI step first runs `actionlint` over the repository's actual `.github/workflows/` files using `.github/actionlint.yaml`. It then explicitly invokes the same binary against `tests/fixtures/workflows/invalid-workflow-level-runner-context.yml`, which is outside automatic real-workflow discovery and deliberately places `${{ runner.os }}` in workflow-level `env`. CI succeeds only if the real scan returns zero and the fixture invocation returns non-zero; an accepted fixture is an explicit CI failure.

Keeping the fixture outside `.github/workflows/` prevents the intentional defect from invalidating the repository's real workflow set. A pytest reimplementation or a literal search for `runner.labels` would not prove the expression-context defect class and is rejected.

### 4. Preserve project-level validation with one focused single-authority regression

Keep `scripts/validate_workflows.py` unchanged unless its current project-specific assertions demonstrably fail because the removed runtime step was part of an assertion. The existing `workflow_execution_plan(..., runner_labels=...)` remains a small model of scheduler eligibility and persistent capability reachability; it is not the removed shell guard and needs no redesign.

Add the minimum assertion in the existing workflow-focused tests that the generate job still has the exact dedicated `runs-on` labels and that no workflow-level `RUNNER_LABEL` or runtime label-guard step remains. Existing tests and the Python validator continue to own opt-in, pre-check ordering, persistence marker, durable rate state, checkout cleanup, publication allowlisting, push failure, and failure-artifact behavior.

### 5. Verify in layers without claiming remote GitHub evidence

Apply verification uses:

1. focused workflow tests;
2. the pinned `actionlint` binary on real workflows;
3. an asserted non-zero result for the invalid fixture;
4. `.venv/bin/python scripts/quality_gate.py`;
5. `openspec doctor`, named strict validation, all strict validation, and `git diff --check`.

These checks establish repository acceptance evidence. They do not establish GitHub server-side evaluation; that acceptance criterion remains pending until observed in GitHub after separately authorized delivery.

## Risks / Trade-offs

- [Risk] The pinned `actionlint` release eventually becomes stale. -> Update the literal CI pin in a separate maintenance change when upstream fixes or GitHub syntax changes require it; keep the semantic contract version-agnostic.
- [Risk] The custom runner label is rejected despite valid repository scheduling policy. -> Declare only `follow-the-money-feed` in `.github/actionlint.yaml` instead of disabling self-hosted-label checks.
- [Risk] A shell regression treats any fixture failure as success, including an unrelated parse error. -> Keep the fixture otherwise minimal and valid-looking, and inspect the validator diagnostic during Apply to confirm the failure is the unavailable `runner` context before recording evidence.
- [Risk] CI provisioning differs from local developer environments. -> Keep the binary acquisition and invocation self-contained in the CI step, and record the equivalent pinned local verification command during Apply without changing the Python quality gate.
- [Trade-off] GitHub server-side evaluation cannot be proven by local `actionlint`. -> Report local semantic validation accurately and defer criterion 20 until an actual GitHub evaluation is observed.

## Migration Plan

1. Apply the workflow correction, validator configuration, invalid fixture, CI step, and focused regression as one narrow diff.
2. Run the layered local and OpenSpec gates before any delivery; do not run the scheduled Feed or mutate persistent rate state.
3. After separately authorized delivery, observe GitHub's workflow evaluation and CI result before claiming server-side acceptance.
4. Roll back by reverting this Change's implementation diff; no Feed data, schema, Provider, configuration, or persistent-state migration is involved.
