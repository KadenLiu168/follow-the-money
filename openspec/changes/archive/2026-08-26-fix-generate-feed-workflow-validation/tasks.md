## 1. Reconfirm the Narrow ECO-48 Boundary

- [x] 1.1 Re-read the supplied ECO-48 scope and, if current Linear read access is available, confirm its Phase-4.5 milestone, no `blockedBy` relation, and `blocks` relation to ECO-49 without updating Linear; stop and report any dependency or scope conflict.
- [x] 1.2 Record the starting revision, worktree state, active OpenSpec Changes, current `feed-evidence-pipeline` requirement, and exact workflow/test surfaces; preserve unrelated work and confirm no Phase-5, Feed/Provider/schema/configuration, or archived-Change edit is needed.

## 2. Establish Actions-Semantic RED Evidence

- [x] 2.1 Add `tests/fixtures/workflows/invalid-workflow-level-runner-context.yml` outside `.github/workflows/` as an otherwise valid-looking workflow whose workflow-level `env` uses `${{ runner.os }}`; verify the selected upstream validator rejects it specifically because `runner` is unavailable there.
- [x] 2.2 Add the focused project-level regression before changing `generate-feed.yml`: require the exact `runs-on` labels and absence of workflow-level `RUNNER_LABEL` plus any runtime runner-label guard, and confirm the new assertion fails against the current duplicate-authority workflow while existing workflow tests remain the project-invariant owner.

## 3. Correct the Single Runner-Selection Authority

- [x] 3.1 Remove workflow-level `RUNNER_LABEL` and the `Fail on non-dedicated runner` runtime step from `.github/workflows/generate-feed.yml` without adding a replacement runtime label check.
- [x] 3.2 Update only the affected inline comments to state that `runs-on: [self-hosted, follow-the-money-feed]` makes matching labels a scheduler eligibility requirement; retain the exact opt-in job gate, persistent-root/marker/rate-state preflight ordering, `clean: false`, allowlisted staging, visible `git push` failure, and failure artifacts.
- [x] 3.3 Run the focused workflow regressions and `scripts/validate_workflows.py`; leave `scripts/validate_workflows.py` and `workflow_execution_plan(..., runner_labels=...)` unchanged unless a failing project-specific assertion proves a narrow stale dependency on the removed shell guard.

## 4. Add the Authoritative Actions-Aware CI Path

- [x] 4.1 Add `.github/actionlint.yaml` declaring `follow-the-money-feed` as an accepted custom self-hosted runner label through the supported label configuration, with no global suppression or unrelated ignore.
- [x] 4.2 Extend `.github/workflows/test.yml` with an explicit pre-merge Actions semantic validation step that provisions one literal pinned upstream `rhysd/actionlint` release without adding Python dependencies or a developer-global prerequisite.
- [x] 4.3 In that CI path, run the pinned binary over all real repository workflows and fail unless they pass; then run the same binary explicitly against the invalid fixture and fail if it returns zero.
- [x] 4.4 Execute the equivalent pinned validator commands locally, record that all real workflows return zero, and record that the fixture returns non-zero with an unavailable workflow-level `runner` context diagnostic rather than an unrelated YAML defect.

## 5. Complete Layered Acceptance

- [x] 5.1 Run the focused workflow tests covering opt-in, dedicated scheduling, persistence and durable rate-state ordering, non-destructive checkout, allowlisted publication, observable failure, and the removed redundant guard.
- [x] 5.2 Run `.venv/bin/python scripts/quality_gate.py` and confirm the existing Python workflow validator remains part of the canonical repository gate without any implicit `actionlint` executable dependency.
- [x] 5.3 Run `openspec doctor`, `openspec validate fix-generate-feed-workflow-validation --strict`, `openspec validate --all --strict`, and `git diff --check`; review the final diff against the ECO-48 allowlist and record any justified additional file before accepting it.
- [x] 5.4 Perform a final contract review proving no Feed execution/publication semantic, Provider/configuration/schema/status/financial behavior, retained-library wiring, Phase-5 Agent contract, dependency, real deployment state, archive, commit, or push changed; report GitHub server-side workflow acceptance as pending unless an actual GitHub evaluation was separately observed.
