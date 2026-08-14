## 1. Establish the Current Semantic Baseline

- [x] 1.1 Inventory every current requirement and active Change requirement, classify each as current, superseded, historical-only, or deferred, and record the evidence for that disposition.
- [x] 1.2 Trace every proposed `feed-evidence-pipeline` requirement to current implementation and focused tests, preserving the implemented provider, time, identity, provenance, degradation, rate, deadline, and publication semantics.
- [x] 1.3 Trace every proposed `deterministic-research-engine` requirement to current implementation and focused tests, and verify production caller status from the minimal Feed entry rather than documentation claims.
- [x] 1.4 Add a Change-local requirement-to-implementation-to-test trace matrix that records negative architecture audits, caller evidence, and the disposition of every retired capability.

## 2. Protect History and Resolve the Superseded Active Change

- [x] 2.1 Record an explicit allowlist for this Change, the pre-Apply active/current/archive OpenSpec paths, and unrelated worktree state; specifically preserve the existing unrelated `AUDIT-2026-08-12.md` deletion.
- [x] 2.2 Verify archived copies exist for the three stale living capabilities and capture their file identities before any living-spec deletion; do not edit historical archive contents.
- [x] 2.3 Stop and obtain separate explicit archive authorization for `implement-follow-the-money-repository`; after authorization, run exactly `openspec archive implement-follow-the-money-repository --skip-specs` and verify none of its six original delta capabilities were synced into current specs.

## 3. Materialize the Normalized Living Specs

- [x] 3.1 Remove only the living `multi-component-resolver-block-processing`, `production-story-family-resolution`, and `production-market-state-pipeline` spec directories, then verify their archived Change artifacts remain byte-identical.
- [x] 3.2 Materialize `feed-evidence-pipeline` as a canonical current spec from this Change's delta, with an accurate Purpose and no public-CLI, model, Brief, Bundle, replay, or Agent-workflow claim.
- [x] 3.3 Materialize `deterministic-research-engine` as a canonical current spec from this Change's delta, with an accurate Purpose and explicit no-production-orchestrator status for post-Feed libraries.
- [x] 3.4 Add this Change's two baseline-integrity requirements to the canonical `deterministic-core-retention` spec without changing its existing post-runtime-removal requirements or scenarios.
- [x] 3.5 Verify the only canonical living capabilities are `deterministic-core-retention`, `feed-evidence-pipeline`, and `deterministic-research-engine`, with no empty or tombstone capability directories.

## 4. Prove Semantic and Structural Consistency

- [x] 4.1 Audit all current specs and active Changes for positive requirements involving an LLM SDK/request, model/API key, prompts, token/retry/reasoning configuration, public CLI, resolver/analyst/editor/language-audit pass, production Brief, Bundle/replay, or live model evaluation; resolve every non-historical hit.
- [x] 4.2 Audit current specs for `ResearchContext`, `AgentAnalysis`, `BriefContext`, Agent schemas, and Agent orchestration, and verify they appear only as explicitly deferred scope rather than defined contracts.
- [x] 4.3 Complete the trace matrix with no untraced living requirement, no missing focused-test evidence for positive behavior, and no production-wiring claim unsupported by current imports or entry-path execution.
- [x] 4.4 Run `openspec doctor --json`, strict validation for this Change, and `openspec validate --all --strict --json`; require zero structural failures while reporting informational findings separately.
- [x] 4.5 Run the complete repository quality gate as non-regression evidence and verify no production code, tests, configuration, JSON Schema, provider manifest, workflow, generated Feed data, dependency, or deployment file changed.
- [x] 4.6 Review the final diff against the explicit allowlist, confirm unrelated worktree state is unchanged, and record the exact active-change and living-spec set as final acceptance evidence.

## 5. Prepare Separate Finalization

- [x] 5.1 Mark this Change Apply-complete only after every semantic and structural gate passes; do not archive, commit, push, or deliver without the corresponding separate explicit authorization.
- [x] 5.2 Record that final archival of `normalize-openspec-baseline` must use `--skip-specs` because its canonical living specs were materialized during Apply, preventing duplicate `ADDED Requirements` application.
