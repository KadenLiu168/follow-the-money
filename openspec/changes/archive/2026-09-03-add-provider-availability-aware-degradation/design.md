## Context

See `proposal.md` for motivation and `specs/feed-evidence-pipeline/spec.md` for behavior. Today `FetchError` already carries a concrete HTTP status through the shared bounded-fetch boundary, while `ProviderOutcome.state` mixes acquisition completion with why work was unavailable. Coverage assessment treats every incomplete planned outcome as fatal. Feed and manifest production currently use major 2, accept majors 1 and 2, and publish only `healthy` or accepted `degraded` candidates; runtime state and product publication already have separate roots and commit rules.

This change crosses HTTP classification, outcome serialization, coverage assessment, semantic validation, snapshot handling, diagnostics, and schema compatibility. It must remain deterministic, credential-free, evidence-only, and fail closed for any condition not proven to be HTTP 401 or HTTP 403.

## Goals / Non-Goals

**Goals:**

- Classify access denial once at the shared Provider execution boundary using structured HTTP status metadata.
- Preserve acquisition state and availability as separate concepts.
- Make wholly blocked Providers publishable only through an explicit, validated `degraded` path.
- Make blocked coverage exemption deterministic and auditable without changing `config/providers.yaml`.
- Keep old active bundles usable for bounded migration while requiring new production to serialize availability.

**Non-Goals:**

- Treating partial Provider data as publishable degradation.
- Adding retries, fallback Providers, browser behavior, bypasses, proxies, or Provider-specific policy.
- Carrying old evidence forward when the current Provider is blocked.
- Changing Provider manifests, coverage memberships/minimums, checkpoint shape, artifact inventory, or Agent runtime surfaces.

## Decisions

### 1. Add availability beside the existing acquisition state

Extend the in-memory and serialized Provider outcome with:

- `availability`: `success | blocked | failed | disabled`
- `availability_reason`: bounded redacted string or null
- `upstream_http_status`: integer or null
- `affected_coverage_groups`: unique group IDs in ascending order

Keep the existing `state` and counters. A wholly access-denied Provider therefore retains the existing failed acquisition shape while declaring `availability = blocked`; pipeline assessment, not the `failed` boolean alone, decides whether that outcome is exempt. `disabled` is representable in planning classification but remains invalid as a serialized planned outcome because disabled Providers never enter the run plan.

This avoids overloading `state`, whose `healthy`, `empty`, `partial`, `failed`, and `skipped` values already encode evidence-completion semantics. Alternative: add `blocked` directly to `state`. Rejected because it conflates availability with completion and complicates existing counters and freshness logic.

### 2. Classify only from structured status metadata

At the common orchestration exception boundary, set `availability = blocked` only when the propagated concrete `upstream_http_status` is 401 or 403. Do not parse exception messages. All other exceptions map to `failed`; successful complete work maps to `success`. Existing retry behavior remains unchanged.

A blocked outcome is exempt only when no evidence was accepted and the terminal state is wholly failed rather than partial. If access denial occurs after accepted or otherwise incomplete sub-work, preserve `availability = blocked` for truthful cause diagnostics but keep the outcome non-exempt and pipeline-failing.

Alternative: classify in BLS and SSE adapters. Rejected because it creates Provider-specific exceptions and misses sibling callers of the shared fetch path.

### 3. Derive blocked exemption and effective coverage; do not configure it

For each validated planned outcome, derive `blocked_exempt` as:

```text
availability == blocked
and upstream_http_status in {401, 403}
and accepted == 0
and state == failed
and outcome identity/cardinality is valid
```

Do not serialize another exemption flag. For each mandatory group:

```text
effective_minimum = max(0, configured_minimum - blocked_exempt_member_count)
```

Count complete non-blocked members exactly as today. Any non-exempt incomplete Provider, malformed blocked claim, or count below the effective minimum remains `failure`. One or more blocked-exempt outcomes with no other hard failure produces `degraded`; no blocked exemption preserves existing status behavior.

This keeps the checked-in coverage matrix authoritative and makes the exceptional arithmetic reproducible. Alternative: edit group minimums or exclude specific Providers. Rejected because either globally weakens coverage or introduces source-specific ignore policy.

### 4. Make diagnostics structured at the outcome and rendered at existing boundaries

Populate `affected_coverage_groups` from the resolved run plan/configuration, not adapters. Validate ordering, uniqueness, exact membership, reason bounds/redaction, and agreement between availability, HTTP status, acquisition state, and pipeline status. Existing warnings and deployment summary rendering consume these fields in Provider ID order and retain current output bounds and non-gating behavior.

No separate diagnostics model or publication channel is introduced. The manifest remains the durable source; transient status remains outside publication and runtime state.

### 5. Produce logical Feed and manifest major 3; retain major 2 read compatibility

Adding required closed outcome fields and changing the semantic meaning of a failed acquisition under `pipeline.status = degraded` is incompatible with major 2 consumers. Bump newly produced logical Feed and manifest to major 3, require the availability fields there, and support major 2 as the immediately preceding read-compatible active bundle. Major 2 validates under its original semantics and does not receive synthetic availability. Stop supporting major 1 at these boundaries in accordance with the existing one-previous-major policy. The domain artifact schema remains unchanged because availability lives in the manifest/logical Feed Provider outcomes, not item payloads.

A major 2 active bundle may still supply complete prior slices under existing freshness checks. A currently blocked Provider never uses those slices as fallback.

Alternative: add optional fields to major 2. Rejected because old consumers reject the closed shape and cannot validate the new degraded semantics.

### 6. Preserve publication and checkpoint behavior

Reuse the existing accepted-`degraded` publication, dry-run, consumer, deployment finalization, and checkpoint paths. The change is limited to producing and validating the newly accepted source-degradation reason. A validated degraded bundle advances publication/checkpoint exactly like existing accepted degraded output; any malformed availability, non-exempt failure, publication error, or durability uncertainty keeps current failure behavior.

## Risks / Trade-offs

- [Every member of a mandatory group may be blocked and the Feed can still publish] → Require `degraded`, reduce the effective minimum only for proven 401/403 outcomes, list every affected group, and carry no prior evidence for blocked Providers.
- [An upstream or intermediary may return misleading 401/403 responses] → Report only the observed access denial, never infer its cause, and preserve canonical source identity and status evidence in bounded diagnostics.
- [Schema-major migration can invalidate major 1 active products] → Retain major 2 as the sole previous-major compatibility target and exercise migration/carry-forward fixtures before production switches to major 3.
- [Availability and acquisition state can drift] → Centralize derivation and enforce cross-field semantic validation before publication and consumption.
- [Sensitive response details could enter diagnostics] → Reuse existing redaction and output bounds; serialize status classification and a sanitized reason, never response bodies or credentials.

## Migration Plan

1. Add major 3 schema and semantic validation while retaining major 2 reads.
2. Add outcome availability derivation and focused classification/validation tests.
3. Add blocked-exemption assessment, snapshot isolation, and deterministic diagnostics tests.
4. Switch new Feed/manifest production to major 3 and exercise dry-run/publication/deployment paths with fixtures.
5. Roll back by reverting major 3 production before any major 3 bundle is activated. After activation, rollback requires a reader that still supports major 3; never rewrite or reinterpret an activated bundle as major 2.
