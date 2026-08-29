## Why

The deterministic Evidence Feed is implemented, but its checked-in GitHub Actions workflow is still a disabled self-hosted template whose durable rate state lives outside the repository. ECO-62 closes that deployment gap by making the repository itself the conservative cross-run state boundary for an active daily GitHub-hosted job, without changing Feed or Host-Agent semantics.

## What Changes

- Run the daily `20 0 * * *` Feed workflow on GitHub-hosted `ubuntu-latest`, remove the mandatory `FOLLOW_THE_MONEY_FEED` opt-in and external `FOLLOW_THE_MONEY_OUTPUT_ROOT`, and use repository `feeds/` directly as the output root.
- Persist only an explicit allowlist of published Feed artifacts, existing RateRegistry files and persistence marker, and one minimal deployment lease; keep locks, status, staging, debug, and other transient files untracked.
- Add a zero-network repository bootstrap and a durable remote `in_progress` lease that must be fast-forward pushed before Provider work; enforce a bounded Feed-start window so `recovery_not_before` covers the latest permitted start, the existing 300-second command deadline, and the configured crash cooldown.
- Recover an incomplete run only after its conservative boundary and only when authoritative resolved Provider rate policies prove the crash cooldown covers every enabled scope's refill horizon and minimum interval; retain RateRegistry as the sole exact rate-state authority.
- Finalize exact local rate state and terminal lease state on both successful and controlled failed runs, publish Feed artifacts only on Feed success, preserve workflow failure outcomes, and leave remote `in_progress` state as the recovery signal when final publication fails or the runner disappears.
- Use non-force optimistic Git updates and explicit generated-state staging; prevent generated-state-only commits from recursively running the full CI workflow while retaining full CI for mixed or source changes.
- Update Actions-aware workflow validation, focused no-network deployment/recovery tests, and documentation that distinguishes scheduled Feed generation from later Host-Agent reasoning and states 08:20 Asia/Shanghai with a runtime-derived evidence cutoff.
- Treat repository Actions write permission and branch policy as an external deployment prerequisite that must be verified before ECO-62 is declared operational.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `feed-evidence-pipeline`: Replace the disabled self-hosted/external-root deployment contract with a GitHub-hosted repository-native schedule, durable pre-network lease, conservative incomplete-run recovery, exact allowlisted finalization, and generated-commit CI behavior while preserving existing Feed, RateRegistry, and Agent boundaries.

## Impact

- Workflows and validation: `.github/workflows/generate-feed.yml`, `.github/workflows/test.yml`, `scripts/validate_workflows.py`, `tests/test_workflows.py`, and focused deployment-state tests.
- Deployment state: repository-owned `feeds/`, `.gitignore`, the existing RateRegistry serialization, persistence marker, and one small internal lease helper; `providers/rate.py` changes only if a minimal query is required.
- Documentation and contract: `openspec/specs/feed-evidence-pipeline/spec.md`, `README.md`, `README.zh-CN.md`, `SKILL.md`, and deployment/runbook documentation.
- External prerequisite: GitHub Actions must have `contents: write`, and branch policy must permit the workflow's non-force fast-forward generated-state commits. No Provider credential, external state service, Feed schema change, Host-Agent invocation, LLM runtime, or retained-capability activation is introduced.
