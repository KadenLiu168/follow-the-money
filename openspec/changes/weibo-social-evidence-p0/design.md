# Design

## Context

See `proposal.md` for motivation and the eight capability deltas for normative behavior. This is a planned contract change, not a description of current production.

Observed current implementation:

- `feed/bundle.py` fixes five domains, logical/manifest major 5 and artifact major 2; only major 4 is an explicit migration input.
- `feed/plan.py::assess_pipeline()` permits first-resource blocked exemptions but otherwise fails incomplete planned Providers even when their coverage row is optional.
- `feed/cli.py` constructs `ManagedProviderClient`, runs Provider work concurrently, treats `execution_failure` as a hard boundary, selects snapshots, validates and publishes, then advances the checkpoint. `providers/session.py` controls each real GET/redirect send. There is no existing external-process transport bridge.
- `config/model.py` has authoritative `ProviderEntry`, `CoverageRow`, rate and freshness contracts, but no Social accounts. `providers/manifest.py` currently rejects credentialed authentication.
- `.github/workflows/generate-feed.yml` schedules 00:20 UTC daily on hosted Ubuntu and persists arming, lease, rate and checkpoint state through exact repository commits. Accepted degraded Feed steps succeed; failure-only Actions diagnostics are not a notification mechanism for them.
- `digest.py` and current Skill/reference contracts expose only DigestContext v2 and five closed domains. Presentation reference inventory tests require one domain document for each supported domain.

The colleague plan and handoff are accepted historical findings. They report Cookie dependence, a necessary `remove_html_tag=0`, misleading process exit/request statistics, Shanghai naive times, closed-like backend filtering, source-directory output and successful local/hosted acquisition. Their original report, fixture captures, branch and backend checkout are unavailable here. This design does not reinterpret those findings as a demonstrated transport hook, pagination proof, license grant or independently reproduced experiment.

## Goals / Non-Goals

**Goals:**

- Preserve the existing hard execution and evidence trust boundaries while adding one explicitly optional acquisition path.
- Make success, complete-empty, unavailable and disabled distinguishable from the single validated Feed alone.
- Keep Social unavailable without allowing a slow or broken backend to consume the core publication reserve.
- Make implementation and activation gates explicit enough that an agent cannot turn missing backend support into an undocumented exception.

**Non-Goals:**

- No generic credential system, social framework, network proxy service, persistent alert store or second checkpoint.
- No backend source fork, vendor copy, global monkey patch or automatic login.
- No continuous Social archive, complete historical coverage, deleted-post recovery, arbitrary link extraction or media metadata in P0.
- No new narrative runtime: mandatory disclosure is typed preparation plus Host-Agent instructions and acceptance checks.

## Decisions

### 1. One Feed, optional acquisition, no continuity recovery

Retain one checkpoint and append Social to the fixed domain order. Social is an event slice, not retained reference state. The user has accepted that a successful degraded publication at T1 loses automatic recovery of Social `[T0,T1)` and the next run starts at T1. New accounts join the current global window; they do not trigger an account-specific bootstrap.

Alternative rejected: hold the global checkpoint until Weibo recovers. That would undermine independent core progress. Per-account recovery state and overlapping backfill were also rejected as outside the approved product semantics.

The embedded Weibo contract records `automatic_backfill = false`; this is the authority for the Digest limitation, rather than a preparation-time configuration lookup.

### 2. A hard backend feasibility gate precedes dependent runtime implementation

Use focused `providers/weibo_social.py` for FTM semantics and, if separation is useful, `providers/weibo_crawler.py` for external execution. Reuse the existing `fetch(window, client)` / network-free `normalize(raw, window)` boundary. The external backend remains pinned and unmodified.

Before building the runtime bridge, inspect the exact revision read-only and record, in this design, all of:

1. The supported request/session injection seam covering profile, listing, detail, retry and redirect calls. Show how every actual send will re-enter the existing FTM managed-send authority without a second rate-state owner.
2. The process/request handoff mechanism, complete request-path inventory, response observation propagation and inability of the admitted backend path to send invisibly. A process invocation cannot count as one send. Any narrow process bridge must remain Weibo-specific, bounded and non-public; a generic proxy is not authorized.
3. The exact source-supported terminal traversal events and the data retained to distinguish successful exhaustion/window completion from a swallowed error, false empty, repeated page, partial file or bound exhaustion.
4. The source-side account-UID binding, canonical post-ID representation, HTML/emoji classification rule, long-text expansion and supported timestamp/edited-content behavior.
5. A permissions/isolation mechanism preventing the backend from reading repository Git credentials or unrelated secrets. A temporary working directory and environment filtering alone do not establish filesystem isolation.

These are pass/fail feasibility checks, not open-ended implementation choices. No compatible seam is assumed to exist. If any cannot be achieved within the approved unmodified-backend approach, stop the dependent tasks and request a revised integration decision; do not implement a bypass or report the Change complete. This staged gate is the approved approach, not permission to replace the backend or build a framework.

Alternative rejected: run the CLI, inspect its final JSON, and trust exit zero or crawler counters. The accepted handoff explicitly disproves these success/rate proxies, and final JSON alone can erase completion evidence.

### 3. Configuration and manifest responsibilities remain singular

Add immutable Social account rows in `config/config.yaml` with exact closed fields from the Social spec. Reject duplicates, unsupported platforms and unknown values before state mutation. Serialize in account-ID order and include the registry in the semantic Feed snapshot. Keep `weibo_social` activation and its optional coverage row in `config/providers.yaml`; never add it to `REQUIRED_PROVIDER_IDS` or make core providers optional.

The Weibo manifest is the authority for revision, reproducible backend environment descriptor, verified fetch/redirect/source-link rules, session-cookie authentication, stable IDs, Tier 3 provenance, event cadence, completion and empty semantics, text/reference bounds, maximum enabled accounts, bounded traversal shape, acquisition duration, cleanup bound and fixture provenance. Numerical bounds must be derived and pinned before dependent implementation, not invented from the anecdotal 134-post run. The manifest/config parser must reject missing or unknown normative fields and embed every accepted field that affects behavior. Application processing headroom belongs in Feed configuration, not a Python fallback.

Disabled Social has no outcome. Enabled Social with no enabled accounts is a static configuration error rather than an ambiguous empty check. The final production selection enables 但斌 only after all activation gates; migration and pre-activation rollout keep the Provider disabled.

### 4. Two independent failure planes

Use closed acquisition failures rather than catch-all exception suppression:

| Condition | Social evidence | Feed result when core passes |
| --- | --- | --- |
| Complete, nonempty | Current entire slice | Healthy |
| Complete, empty | Empty | Healthy |
| Missing Cookie | Empty | Degraded, credential_unavailable |
| Source-confirmed rejected Cookie | Empty | Degraded, credential_rejected |
| Missing backend, failed provisioning, wrong pin | Empty | Degraded, backend_unavailable |
| Observed blocking / unavailable account | Empty | Degraded, source-supported reason |
| Raw unsupported shape / unproved coverage / local budget | Empty | Degraded, acquisition_incomplete or deadline_exceeded |
| Invalid FTM canonical item, identity invariant or serialization defect | None published | Failure |
| Invalid config/manifest, missing outcome, durable rate error, global deadline | None published | Failure |

An observed HTTP 432 can justify a sanitized upstream-blocking reason when verified, but does not become `availability=blocked`: that existing enum classification is reserved for concrete HTTP 401/403. No inferred credential-rejection diagnosis.

Keep one ProviderOutcome. Stage raw and normalized candidates locally until all enabled accounts complete. Discard the whole candidate set on typed acquisition failure, keep truthful counters/observations, and publish zero Social items. Distinguish source identity not proven (acquisition incomplete) from an FTM item violating an established identity invariant (hard failure). Missing output is an acquisition failure; an invalid normalized Feed item is not. Preserve core blocked exemptions exactly.

Consumer validation must mirror producer optionality from embedded contracts. Merely attaching a permitted reason string must not launder an invalid item or missing outcome. `assess_pipeline()` alone is not the whole integration: `cli.py` execution failures, snapshot selection and semantic validation must agree.

### 5. Request safety and bounded process lifecycle

Retain the existing rate registry, lease, durable debit and per-send reconciliation; add the Weibo scope only through the existing first-use/arming path. Include its policy in hosted crash-recovery validation. Credentials remain request-only and only on verified Weibo hosts; redirects independently re-enter host validation and never forward Cookie to unauthorized targets.

Let `D` be the command-start deadline, `R` the existing commit reserve, `H` the explicit processing/staging headroom, `K` the bounded process termination/cleanup allowance, and `B` the manifest acquisition budget. With monotonic current time `now`, admit a Social stop deadline no later than `min(now + B, D - R - H - K)`. No remaining admissible budget means typed Social unavailability without starting the child. Static request-shape/rate-floor checks must establish the configured bound can complete; runtime checks remain mandatory. Do not shrink core rate intervals or extend the global deadline implicitly.

On local expiry, stop dispatch, terminate then force-kill as bounded, reap the entire process group and fence late results before reporting the outcome. A child that cannot be fenced or a corrupted rate state is a hard execution failure, not safe degraded success. Do not let `pool.shutdown(wait=True)` wait for an unmanaged indefinitely running child.

Alternative rejected: allow Social to run to the global timeout and then downgrade its status. At that point core publication may already be impossible.

### 6. Secret and output isolation

Read `WEIBO_COOKIE` only during acquisition. Use a minimal child environment with explicit timezone and no unrelated credentials; no Cookie in argv. If backend configuration must contain the Cookie, use an access-restricted ephemeral file with a verified cleanup path. Suppress raw stdout/stderr from public logs; translate only verified typed facts into bounded reason codes. Do not rely on GitHub masking of transformed values.

Because the handoff reports output under the backend source directory, verify the resolved writer path before execution and arrange an ephemeral execution layout that directs writes into the isolated area without editing crawler source. Validate output type, size and location and reject symlink/path escapes or stale files. No SQLite, scheduler, append state, durable raw dump or uploaded raw artifact.

The workflow must retain a publication credential for existing finalization, but the backend must not have access to it. Resolve the exact process/filesystem isolation under gate 2 before deployment; avoiding inheritance does not hide `.git/config` from a same-user process.

### 7. Social mapping is explicit attributed evidence

Use the existing stable item-ID helper with Provider identity and a canonical Weibo post identifier; do not derive it from text, display name or retrieval time. The account registry selects sources, while source-side evidence verifies identity. A nickname change alone is not an identity change, and a configured UID echo is not independent evidence.

Payload v1 includes only platform, account, external post identity, content kind, top-level authored text and references. Keep `links` and `attachments` out of the P0 closed schema rather than adding empty future placeholders. Set `source.kind=social_account`, tier `Tier 3` and safe source URL. Use closed reference relation `reshare_of`, resolution `available` or `unavailable`, and a source-supported snapshot only when available. Never invent a missing nested author/ID/time. Top-level text overflow fails acquisition; nested truncation is allowed only with `truncated=true` and deterministic prefix/block rules documented before mapping is activated. Raw HTML remains transient, not reader evidence.

Pin the precise structural original/reshare rule after inspecting the accepted revision. Preserve emoji represented by image alt text where that verified shape requires it; never use `转发微博` or `//@` alone as classifiers. Retain authored commentary separately from the original author's snapshot. Same-ID conflicting records are incomplete; exact duplicates collapse deterministically; distinct Social post IDs survive near-text deduplication.

Supported naive absolute publication time is interpreted as Asia/Shanghai, then UTC-normalized and independently filtered. Publication is knowledge time only for supported unedited evidence. Relative-time precision and edited-content cutoff rules must be demonstrated at the feasibility gate; unsupported ambiguity fails acquisition, never substitutes collection time. The Feed promises supported observable evidence, not a historical snapshot of every post ever published.

### 8. Failure disclosure is Feed-derived and cannot be compressed away

Add DigestContext v3 with `social_post`, `social` domain, `weibo_social` scope and `published_at` authority. Exactly one top-level current item produces one unit; references stay nested. Whitelist reader fields and retain trace. No semantic clustering or independent inference.

Add a closed `social_acquisition_unavailable` limitation with Provider ID, ordered enabled account identities/display labels, window start/end, sanitized reason and `automatic_backfill=false`. Derive all values from the embedded Feed snapshot/outcome/window. Reuse `availability_reason` for the closed reason instead of adding a duplicate runtime authority. Suppress a redundant generic Provider limitation for the same Social failure.

Use `current_updates_available`, `no_current_update`, `provider_unavailable`, `not_configured` for the Social scope. Do not infer enabled failure from absence of items or confuse disabled with complete-empty. With Provider-wide atomicity, disclosure says the selected accounts' coverage is unavailable, not that each account individually failed.

Update `references/digest/domains/social.md`, the global/compression references, `SKILL.md`, invocation and responsibility contracts. Even with `content.updates=[]`, Social failure disclosure remains mandatory. No generated prose renderer is added: deterministic tests verify exact descriptors and static presentation constraints; a documented Host-Agent acceptance case checks reader output. Source predictions remain attributed; reposting is not endorsement; source text is untrusted data, not instructions.

A reader who skips that Feed receives no separate notification. A later successful context cannot reconstruct old gaps; this limitation was explicitly accepted.

### 9. Version and contract migration is coordinated, not a parallel product

Logical Feed/manifest 6, artifact 3 and DigestContext 3 are one rollout. Append Social to the existing domain authority and update schema, semantic validation, bundle reconstruction, remote loading, publication, allowlists and identity tests coherently. Keep the five existing payload contracts and their Provider-specific compatibility behavior unchanged except for version binding. Do not leave broad v4 bundle reads alongside v5 migration.

Modify existing requirement blocks rather than add contradictory parallel requirements. Some accepted requirement titles contain historical version/domain labels; retain their identity while updating their full normative bodies and scenarios in this delta. Main-spec Purpose text and current-facing architectural descriptions must be brought into alignment during accepted spec synchronization, not silently edited during planning. Archived Changes remain untouched.

## Risks / Trade-offs

- [No compatible unmodified backend integration seam] -> Stop before dependent runtime work; seek a revised decision rather than weakening managed-send safety.
- [Prior captures unavailable] -> Accept the supplied findings; label synthetic tests honestly and require new bounded acceptance evidence before declaring production operational.
- [Reported lack of explicit backend license and Social text republication permission] -> Require an explicit acceptable permission/distribution disposition before production activation; non-vendoring is not a legal conclusion.
- [Cookie expires or anti-bot behavior changes] -> Closed unavailable outcome and mandatory current-feed disclosure; no automated refresh or evasion.
- [Failed windows are lost and older posts may be deleted or edited] -> Clearly bounded observable-window promise and no automatic backfill, not archive completeness.
- [One account invalidates all monitored coverage] -> Provider-wide atomicity is deliberate P0 simplicity; adding many accounts increases degradation likelihood and stays within manifest bounds.
- [Large Social text could exhaust bundle limits] -> Static account/content/reference bounds and existing total Feed-size gate; never publish silently truncated top-level content.
- [Shared runner credential exposure] -> Verify actual filesystem/process isolation, not only env filtering or temporary directory naming.
- [Host-Agent wording could omit a caveat] -> Typed nonempty limitation, explicit non-omission instructions, static regressions and a reviewed no-updates failure example; no claim that offline unit tests guarantee every future model response.

## Migration Plan

1. Complete the feasibility gate and record exact supported seam, terminal conditions, classification, identity/time rules and justified bounds in this design. If incompatible, pause; the remaining tasks are not authorized to choose a different architecture silently.
2. Implement and verify contracts/fixtures offline, keeping production Weibo disabled. Reconcile accepted architecture instructions before introducing runtime code under the new exception.
3. Deploy v6-capable producer/consumer together with Social disabled. Run explicit v5-to-v6 migration with zero Provider work and exact existing lease/checkpoint/allowlist validation; it creates structural empty Social, not successful Social coverage. A previous-major rejection during rollout must be explicit, never fallback consumption.
4. Resolve licensing/content-use disposition and obtain separate authorization for a bounded GitHub-hosted acceptance run using an operator-provided Secret. Capture only sanitized contract-relevant evidence. Planning does not authorize live requests or Secret setup.
5. Once all gates pass, enable `weibo_social` with 但斌 in existing production configuration and provide `WEIBO_COOKIE` only to the collection step. The subsequent normal run performs real acquisition. Backend installation failure must enter the typed optional path, not abort an earlier workflow step.
6. Verify success, complete-empty and forced missing-Cookie degraded behavior, matching checkpoint/bundle finalization and current-digest disclosure. Do not mark activation complete merely because the Actions job is green.
7. Operational rollback disables Weibo but retains v6, the sixth empty artifact and DigestContext v3, yielding `not_configured`. Never force-reset the checkpoint or downgrade bundle bytes to v5. Re-enabling starts at the then-current global window without recovery of disabled or failed periods.
