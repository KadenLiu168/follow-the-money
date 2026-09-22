## Purpose

Define closed, configuration-driven Weibo evidence acquisition and provenance within the single canonical Evidence Feed, including optional failure, Secret isolation and bounded current-window completeness.

## ADDED Requirements

### Requirement: Social account selection is closed and configuration-owned

The application configuration SHALL contain `social_accounts` with exactly `id`, `platform`, `external_user_id`, `display_name` and `enabled` per account. P0 platform SHALL be only `weibo`; IDs SHALL be non-empty, Weibo external IDs SHALL be ASCII decimal strings, and both account ID and `(platform, external_user_id)` SHALL be unique. The production initial selection SHALL be `dan_bin_weibo`, `1249424622`, `但斌`, enabled. Adding supported accounts within declared safety bounds SHALL require configuration only. Canonical snapshots and acquisition SHALL order accounts by account ID. Provider activation SHALL remain in Provider activation policy, not in account rows. An enabled Provider with no enabled account SHALL fail configuration validation; a disabled Provider SHALL produce `not_configured` reader status without a synthetic outcome. All static failures SHALL precede Provider requests and persistent mutation.

#### Scenario: More supported accounts are configured
- **WHEN** second and third unique valid enabled Weibo accounts are added within the manifest bounds
- **THEN** planning receives those accounts in canonical order without Provider code changes

#### Scenario: Account configuration is invalid
- **WHEN** an account has an unknown field, unsupported platform, duplicate identity, non-ASCII or nonnumeric external ID, or missing required field
- **THEN** startup fails before acquisition or persistent mutation

#### Scenario: Account is disabled
- **WHEN** one configured account is disabled while another remains enabled
- **THEN** only the enabled account belongs to acquisition and failure-disclosure scope

### Requirement: Weibo acquisition uses an explicit verified external backend contract

The Weibo Provider SHALL declare the external backend revision, authentication, HTTPS fetch/redirect/source-link policies, identity verification, payload type `social`, event-driven freshness, complete-empty semantics, acquisition limits, and fixture provenance in its authoritative manifest and embedded contract. P0 SHALL pin `dataabc/weibo-crawler` revision `a3bfe515e9886b84151c609debdc636cbb0e9730`. The execution environment SHALL verify revision, absence of backend source modifications and reproducible dependency resolution before acquisition. The backend SHALL NOT be vendored, modified, or promoted to Feed, identity, rate, checkpoint, scheduler, health or persistent-evidence authority.

Generated backend configuration SHALL force original and reshare acquisition, `only_crawl_original=0`, `remove_html_tag=0`, `download_comment=0`, `download_repost=0`, every media download disabled, and JSON-only output. Account configuration SHALL NOT override these invariants. Output SHALL be read only from the verified expected location in an isolated, bounded, ephemeral work area and removed after termination; database, append-mode, scheduler and Flask paths SHALL remain disabled.

#### Scenario: Backend revision or contents differ
- **WHEN** the installed acquisition backend does not match its declared immutable revision or has modified source
- **THEN** it is not executed and the Social acquisition is unavailable, without silently substituting another backend

#### Scenario: Output is written elsewhere
- **WHEN** execution does not produce the exact expected isolated output
- **THEN** the acquisition is incomplete and no old file or implicit default directory supplies evidence

#### Scenario: Caller attempts to change extraction behavior
- **WHEN** account configuration supplies an extraction, database, scheduler or download override
- **THEN** configuration is rejected rather than weakening the fixed backend settings

### Requirement: Every Social request remains inside existing safety guarantees

Every possible Social network send, including profile, listing, detail, pagination, retry and redirect sends, SHALL satisfy the existing per-send durable rate, concurrency, cancellation, deadline, HTTPS host and response-limit contracts. Cookie attachment SHALL be limited to explicitly authorized targets and SHALL NOT survive an unauthorized redirect. Backend request counters, sleeps, process exit codes and subprocess duration SHALL NOT substitute for these controls. Production integration SHALL require a demonstrated supported request-control seam and observable acquisition completion; absent either, activation SHALL remain blocked, without a generic proxy framework, hidden monkey patch, unmanaged-send exception or source modification.

Social SHALL have a manifest-owned bounded acquisition budget and cleanup bound admitted before the global pre-commit boundary, with application-owned processing headroom and the unchanged commit reserve. Account and request-path bounds SHALL fit that budget under resolved rate policy. Reaching the Social budget before completion SHALL terminate and reap the entire backend process group and discard the candidate slice. Global deadline, durable rate or publication failures SHALL remain hard Feed failures.

#### Scenario: Detail fetch is not included in backend counters
- **WHEN** the backend sends a detail request without incrementing its own request count
- **THEN** that send still independently receives all FTM request admission and reconciliation controls

#### Scenario: Social exceeds its local budget
- **WHEN** the Social acquisition budget expires while core work can still complete within the global budget
- **THEN** Social becomes unavailable with `deadline_exceeded`, no child continues sending, and core publication remains eligible

#### Scenario: Safe integration is unavailable
- **WHEN** the pinned backend cannot expose a supported control seam or completion observations
- **THEN** production activation remains blocked and implementation does not silently weaken the Feed contract

### Requirement: Session credentials are acquisition-only secrets

Only `weibo_social` SHALL read `WEIBO_COOKIE`, at acquisition time. Package import, static configuration resolution, canonical Feed consumption and the eight core Providers SHALL require no such credential. Missing or confirmed rejected credentials SHALL make Social unavailable, not healthy empty. Unconfirmed failures SHALL NOT be labeled credential rejection.

Cookie values, authentication headers, raw backend diagnostics and secret-bearing paths SHALL NOT enter logs, stderr, exception representations, fixtures, status diagnostics, account/Provider/config snapshots, Feed items, canonical bytes, identities, checkpoints or durable state. Any required secret-bearing temporary file SHALL be access-restricted and ephemeral, never uploaded or staged. Backend environment SHALL exclude unrelated credentials and backend execution SHALL be isolated from repository publication credentials. Secret masking alone SHALL NOT establish this isolation. Automated login or refresh SHALL NOT be introduced.

#### Scenario: Cookie is absent
- **WHEN** acquisition starts without `WEIBO_COOKIE`
- **THEN** Social reports `credential_unavailable`, no Social request is sent, and an otherwise valid core Feed can publish degraded

#### Scenario: Sentinel credential is exercised
- **WHEN** success, rejection, timeout, malformed output and backend exceptions are tested with a synthetic sentinel Cookie
- **THEN** no public, durable, logged or exception surface contains the sentinel

### Requirement: Social completeness is positive and Provider-atomic

A Social acquisition SHALL be complete only when every configured enabled account has independently supported source identity, parsed expected output, valid supported records, and an observed source-supported terminal traversal condition proving coverage of the requested window within all safety bounds. Completeness SHALL mean completion of the declared accessible source traversal under the active session, not proof of deleted, hidden or unreturned posts. Exit zero, some returned posts, minimum observed timestamp, file existence, echoed configured UID, display name alone, and backend request count SHALL NOT establish completeness.

The verification contract SHALL identify the exact observable terminal conditions and distinguish normal exhaustion/window completion from blocked, repeated, truncated, malformed or interrupted pages. Unprovable pagination or identity, unsupported upstream shape, unavailable selected content, bound excess, and incomplete account work SHALL discard the entire Provider candidate slice. Complete traversal with zero eligible posts SHALL produce `empty`, availability `success`, and `no_snapshot`; incomplete traversal SHALL never become healthy empty. No public account-level outcomes SHALL be introduced.

#### Scenario: Successful process omits output
- **WHEN** the backend exits zero but expected account output or completion proof is missing
- **THEN** the whole Social slice is unavailable with `acquisition_incomplete`

#### Scenario: One account fails
- **WHEN** two configured accounts complete and a third cannot establish identity or complete traversal
- **THEN** no account's candidate items are published and the disclosure scope covers the whole enabled selection

#### Scenario: Window is verifiably empty
- **WHEN** all enabled accounts complete verified traversal and half-open filtering selects no posts
- **THEN** Social is successful empty rather than unavailable

#### Scenario: Source presents a misleading terminal page
- **WHEN** a login, blocked, repeated or malformed page resembles an empty terminal page
- **THEN** the verified terminal-condition check rejects it rather than claiming complete-empty coverage

### Requirement: Social source identity and times are explicit and conservative

Top-level item identity SHALL derive only from `weibo_social` and a canonical stable source post ID; the contract SHALL select one canonical representation and reject conflicting ID aliases. Source-side evidence SHALL bind the monitored account to the configured external UID independently of configuration echo. Nicknames and verification descriptions SHALL be auxiliary identity evidence, not unique identity authority.

Backend execution SHALL use `TZ=Asia/Shanghai`. Supported naive absolute `created_at` values SHALL be interpreted in that zone and normalized to UTC. Relative-time conversion and source precision SHALL be explicitly verified; fabricated seconds or collection time SHALL NOT establish eligibility. Ambiguous boundary membership SHALL make acquisition incomplete. FTM SHALL independently apply `window.start <= published_at < evidence_cutoff_at` to a backend-fetched superset. `knowledge_available_at` SHALL use the verified source publication authority for supported unedited posts, never retrieval time. Supported edits SHALL require source-backed content-availability semantics and cutoff admission; ambiguous or post-cutoff edited content SHALL not be represented as a pre-cutoff snapshot.

#### Scenario: Absolute Shanghai timestamp is normalized
- **WHEN** a supported source timestamp is `2026-09-21T09:15:00` without an offset
- **THEN** its canonical publication time is `2026-09-21T01:15:00Z`

#### Scenario: Publication lies at a window boundary
- **WHEN** publication equals the start or the cutoff
- **THEN** the start value is included and the cutoff value is excluded

#### Scenario: Account ID is configuration echo
- **WHEN** output reports only the configured UID with no sufficient independent source-side binding
- **THEN** identity is unproven and Social is incomplete rather than silently monitoring an assumed account

#### Scenario: Edited content lacks a valid cutoff authority
- **WHEN** current visible text was edited after cutoff or its source-backed content time is ambiguous
- **THEN** it is not admitted as content known at cutoff and the affected acquisition is incomplete rather than silently dropping selected evidence

### Requirement: Social payload preserves attributed post evidence without interpretation

A Social item SHALL reuse the Feed item envelope with payload type `social`, platform `weibo`, configured account ID and external UID, source-supported display name, canonical external post ID, content kind, authored top-level plain text or null, and bounded references. Source kind SHALL be `social_account`, provenance tier SHALL remain `Tier 3`, and its safe canonical post URL and source times SHALL remain explicit. Verified provenance SHALL establish attribution, not truth of a post's financial assertions. All payload and nested objects SHALL be closed to unknown fields.

Content kind SHALL be exactly `original`, `reshare` or `reshare_with_comment`, determined from the accepted backend's structural evidence, not equality to `转发微博` or a `//@` prefix. Emoji-only authored commentary SHALL remain commentary. HTML SHALL be deterministically converted into NFC plain text while retaining supported emoji semantics and separating authored text from referenced text. Top-level text SHALL be complete within a declared bound; overflow or an unexpanded selected long post SHALL make acquisition incomplete, not silently truncate. Reference snapshots SHALL preserve source-supported author, text, source URL, post identity and publication time where available; unavailable references SHALL explicitly retain unavailable resolution without invented content. Reference truncation SHALL be deterministic and explicitly flagged. Historical referenced content SHALL not become another top-level event unless independently selected for a monitored account.

P0 SHALL NOT add separate extracted links or attachment metadata, media downloads, comment/reply/thread acquisition, `semantic_context`, `source_content`, engagement analysis, sentiment, topic, importance, prediction, recommendation or market impact. The acquisition scope SHALL be the verified timeline post types, not an unsupported claim to semantically detect every reply-like authored post.

#### Scenario: Emoji is the only authored reshare comment
- **WHEN** structural source evidence contains an authored emoji comment and a referenced post
- **THEN** the item is `reshare_with_comment`, retains the emoji and keeps the referenced author's text nested

#### Scenario: Pure reshare is available
- **WHEN** structural evidence proves a reshare with no authored comment
- **THEN** top-level authored text is null and the item does not attribute the original author's statement to the monitored account

#### Scenario: Referenced original is unavailable
- **WHEN** supported source evidence identifies a reshare whose original content is unavailable
- **THEN** the reference explicitly records unavailable resolution without reconstructing text or inventing a source identity

#### Scenario: Canonical Social payload is invalid
- **WHEN** FTM emits an invalid item, analytical field or forbidden `semantic_context` or `source_content`
- **THEN** Feed validation fails rather than treating the internal defect as optional upstream unavailability

### Requirement: Activation evidence and dependency constraints are truthful

Prior findings supplied by the user SHALL be recorded as accepted handoff findings rather than newly reproduced verification. Synthetic fixtures SHALL be labeled synthetic; unavailable historical fixtures SHALL NOT be fabricated or claimed restored. Production activation SHALL require documented request-control and completion conformance, deterministic offline tests, an explicit acceptable licensing and content-republication disposition, and a separately authorized bounded GitHub-hosted acceptance run. Public source availability and non-vendoring SHALL NOT be treated as sufficient license permission. No Cookie SHALL be committed as verification evidence.

#### Scenario: Only the handoff remains available
- **WHEN** the original Spike report and captures are unavailable
- **THEN** planning preserves the accepted findings and testing records honest provenance without claiming independent live verification

#### Scenario: Activation prerequisites are unmet
- **WHEN** request safety, completion, dependency permission or hosted acceptance remains unverified
- **THEN** the production Provider remains disabled and the Change is not reported operationally complete
