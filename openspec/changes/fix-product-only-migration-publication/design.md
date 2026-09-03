## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for required behavior. The deployment boundary supports two migrations under one `migration` mode: relocating complete legacy runtime state, and converting only a remaining `feeds/latest.json` after `.feed-state/` is already established. Publication reconstructs an allowlist in a separate command. It currently adds legacy runtime deletion candidates unconditionally, so Git rejects product-only migration because those paths are neither present nor tracked.

The correction must preserve repository-backed durability, exact path staging, zero-network migration, non-force fast-forward publication, and fail-closed validation of every required runtime and bundle path.

## Goals / Non-Goals

**Goals:**

- Make product-only migration stage only its exact generated additions and tracked deletion.
- Preserve exact legacy runtime deletions for complete runtime-state migration.
- Keep required generated paths fail-closed rather than applying a generic “ignore missing paths” policy.
- Reproduce the hosted failure at the real Git staging seam.

**Non-Goals:**

- Changing migration state formats, bundle schemas, checkpoint semantics, rate recovery, Provider behavior, or workflow topology.
- Broadening Git staging to a directory, worktree-wide add, force push, reset, or ignored path errors.
- Folding the blocked Provider runtime verification into this implementation Change.

## Decisions

### 1. Resolve optional legacy deletions from the repository index

Migration publication will construct and validate all required current runtime and bundle paths as it does today. It will require `feeds/latest.json` to be tracked by the repository index before removing it so its deletion belongs to the same generated-state commit. Legacy runtime deletion candidates under `feeds/` will be included only when the repository index identifies those exact paths as tracked. A deleted tracked path remains stageable; a nonexistent untracked candidate from product-only migration is excluded before `git add`.

This decision keeps Git as the authority for whether a deletion can belong to the generated-state commit and avoids weakening validation for required files. An untracked `latest.json` is invalid repository migration state and fails before local removal or publication.

**Alternative considered:** filter every missing allowlisted path immediately before staging. Rejected because that could silently omit a required runtime file or bundle artifact.

**Alternative considered:** add a new migration subtype to workflow outputs and CLI arguments. Rejected because repository index membership already distinguishes deletions, while another cross-command protocol would add unnecessary state and workflow surface.

### 2. Keep generic publication strict

The generic generated-state publisher will continue to reject an empty staged set, unrelated pre-staged paths, unexpected staged paths, commit failures, and push failures. The correction belongs in migration allowlist reconstruction, not in a permissive `git add` wrapper.

**Alternative considered:** use `git add --ignore-errors`, a directory-level add, or worktree-wide staging. Rejected because each weakens the closed generated-state boundary.

### 3. Test both migration forms with real temporary repositories

A product-only regression will create tracked `feeds/latest.json`, established `.feed-state/`, and no tracked legacy runtime paths; then it will execute migration publication against a temporary Git repository and assert the exact committed path set. Existing complete-legacy migration coverage will be strengthened as needed to prove tracked legacy runtime deletions still stage. Missing required generated artifact and untracked-`latest.json` assertions will guard against accidental generic missing-path filtering or deletion outside the generated-state commit.

Network execution is unnecessary for these deterministic tests. Hosted workflow execution remains post-delivery operational verification.

## Risks / Trade-offs

- [Repository index queries could accidentally broaden staging] → query only the already-derived exact legacy candidates and retain post-stage subset validation.
- [Fixing product-only migration could regress full legacy relocation] → cover both forms with repository-backed exact-path assertions.
- [A permissive missing-path filter could hide partial state] → apply tracked-deletion selection only to optional legacy candidates; continue validating required current paths before publication.

## Migration Plan

Deliver the contract delta, migration allowlist correction, and offline regressions together. Run focused deployment tests, the canonical repository quality gate, and strict OpenSpec validation. Then trigger the hosted workflow once to complete product-only migration without Provider work and a second time to exercise normal arming/collection subject to existing recovery bounds. Record the second invocation as handoff evidence for the separate Provider runtime verification; do not complete that Change within this one. Rollback is the code-and-spec revert; no serialized state format changes.
