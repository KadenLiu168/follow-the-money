## ADDED Requirements

### Requirement: Provider availability is explicit and evidence-based
The Feed SHALL classify Provider availability independently from pipeline status using the closed states `success`, `blocked`, `failed`, and `disabled`. A concrete upstream HTTP 401 or HTTP 403 response SHALL classify the affected Provider as `blocked`; no timeout, transport error, parser error, schema error, unexpected status, missing outcome, or other unconfirmed failure SHALL be inferred to be `blocked`. `degraded` SHALL remain reserved for future Provider partial-data availability and SHALL NOT be produced as a Provider availability state by this Change. A disabled Provider SHALL remain outside the actual run plan and SHALL NOT create a synthetic Provider outcome or completeness obligation.

Every serialized planned-Provider outcome in the new production schema major SHALL expose its Provider identity, availability, bounded reason or null, and affected configured coverage groups in deterministic order. Availability SHALL agree with the underlying terminal evidence: completed healthy or contract-permitted-empty work is `success`; confirmed access denial is `blocked`; all other incomplete or unexpected work is `failed`. A confirmed access denial after accepted evidence or incomplete sub-request, role, or page work SHALL remain partial and non-exempt rather than making partial-data publication acceptable.

#### Scenario: HTTP 403 is blocked
- **WHEN** an enabled planned Provider returns a concrete HTTP 403 response before any evidence is accepted
- **THEN** its availability is `blocked`, its bounded reason identifies HTTP 403, and no Provider-specific exception is required

#### Scenario: HTTP 401 is blocked
- **WHEN** an enabled planned Provider returns a concrete HTTP 401 response before any evidence is accepted
- **THEN** its availability is `blocked` and its bounded reason identifies HTTP 401

#### Scenario: Timeout remains failed
- **WHEN** Provider work ends in a timeout without a concrete HTTP 401 or HTTP 403 response
- **THEN** its availability is `failed` and it is ineligible for blocked exemption

#### Scenario: Parser error remains failed
- **WHEN** a Provider response cannot be parsed or normalized under its verified contract
- **THEN** its availability is `failed` and it is ineligible for blocked exemption

#### Scenario: Access denial follows accepted evidence
- **WHEN** a Provider accepts evidence from one sub-request, role, or page and later receives HTTP 401 or HTTP 403 before completing its planned work
- **THEN** diagnostics preserve the access-denial reason but the Provider remains partial, non-exempt, and pipeline-failing

#### Scenario: Disabled Provider is not synthesized
- **WHEN** authoritative registry policy disables a Provider before run planning
- **THEN** its availability is `disabled` in planning semantics but no Provider outcome, coverage obligation, or synthetic warning is emitted

## MODIFIED Requirements

### Requirement: Feed bundle is the serialized external contract
Every published bundle SHALL validate against the supported major versions of its manifest and domain-artifact schemas and their semantic invariants. Newly produced logical Feeds and manifests SHALL use the Provider-availability-capable major, while the immediately preceding freshness-capable major SHALL remain read-compatible as a fully validated active-bundle input for bounded migration and carry-forward; new production SHALL NOT emit the preceding major. The bundle SHALL retain the existing fixed acquisition window, truthful collection timestamps, Provider outcomes with semantic freshness results and explicit availability diagnostics, canonical redacted Feed configuration snapshot, enabled-Provider contract snapshots, producer descriptor, canonical logical `content_digest`, cutoff-derived `run_id`, pipeline semantics, and exactly one supported typed payload per evidence item. Consumers SHALL validate from embedded producer contracts without requiring equality with the current consumer build or Provider manifests. The new major SHALL require deterministic Provider availability, bounded reason, and affected-coverage fields; the preceding major SHALL continue to validate under its original contract without invented availability.

#### Scenario: Producer and consumer builds differ
- **WHEN** a valid bundle was produced by another build with supported schema majors
- **THEN** the consumer validates it from the manifest and embedded producer descriptors without requiring current build or manifest hashes to match

#### Scenario: Payload type and artifact domain disagree
- **WHEN** an item is stored outside the artifact matching its supported payload discriminator
- **THEN** closed bundle validation rejects it

#### Scenario: Previous-major active bundle is read
- **WHEN** the active bundle uses the immediately preceding supported major and passes its complete original contract
- **THEN** it may supply a prior Provider slice to a new Provider-availability-capable candidate, which records the slice's original embedded Provider-contract hash without inventing prior availability fields

#### Scenario: New production attempts the preceding major
- **WHEN** a producer candidate omits required freshness or Provider availability results or declares the preceding logical/manifest major
- **THEN** new-production validation rejects it before publication

### Requirement: Explicit degradation and coverage outcomes
One Provider failure SHALL NOT stop collection already planned for other Providers. The Feed SHALL record attempted, succeeded, empty, partially valid, failed, skipped, fetched, accepted, and rejected outcomes together with explicit availability diagnostics. Provider membership for completeness assessment SHALL derive only from the actual resolved run plan, and the resolved Provider contract SHALL be the sole authority for `empty_valid_for_window`; disabled Providers and unverified mappings excluded from that plan SHALL create no completeness obligation.

Every planned Provider SHALL have exactly one unambiguous terminal outcome matching its planned Provider identity. A planned Provider SHALL be complete only when its outcome is `healthy`, or when its outcome is `empty` and its resolved `empty_valid_for_window` contract is true. A `failed`, `partial`, or `skipped` outcome, a non-permitted `empty` outcome, or a missing, duplicate, ambiguous, or identity-mismatched terminal outcome SHALL be incomplete. Accepted and fetched item counts SHALL NOT determine Provider completeness. A Provider SHALL be blocked-exempt only when a concrete HTTP 401 or HTTP 403 establishes `availability = blocked`, no evidence was accepted, and no partial sub-request, role, or page result exists.

Mandatory coverage SHALL count only complete planned Providers that belong to the configured group. A contract-permitted empty Provider SHALL count toward the configured minimum without contributing an evidence item; an incomplete Provider SHALL not count. For each non-optional group, the effective minimum SHALL equal `max(0, configured minimum - blocked-exempt planned members in that group)`. This exemption SHALL NOT alter configured membership or minimum values, and every exempt member and affected group SHALL remain visible in deterministic diagnostics. A non-exempt incomplete planned Provider or a group below its effective minimum SHALL produce `pipeline.status = failure` regardless of evidence returned by other Providers. A Provider SHALL be `partial` when it retains accepted evidence but also has rejected items or incomplete later sub-request, role, or page work; retained valid evidence and outcome counters SHALL remain available for diagnostics but SHALL NOT make the failed run publishable.

The total accepted evidence count and final `items` length SHALL NOT independently determine pipeline health. When every planned Provider is complete or blocked-exempt, every mandatory group meets its effective minimum, and all existing non-source hard-failure boundaries succeed, the Feed SHALL be `degraded` if at least one Provider is blocked-exempt and otherwise SHALL remain eligible for the existing healthy or otherwise accepted non-source status even when `items` is empty. Unknown or non-exempt source incompleteness SHALL NOT produce `degraded`. Provider-specific and coverage-group diagnostics SHALL identify every blocked exemption or source-completeness cause used to determine pipeline status.

#### Scenario: Blocked Provider is published with warnings
- **WHEN** a planned Provider is blocked-exempt, all other planned Providers are complete, every mandatory group meets its effective minimum, and all non-source hard boundaries pass
- **THEN** the Feed is `degraded`, exits successfully, remains eligible for publication, and identifies the unavailable Provider and affected coverage groups

#### Scenario: Every member of a group is blocked
- **WHEN** every planned member of a mandatory coverage group is blocked-exempt and no other hard failure exists
- **THEN** that group's effective minimum is zero, the Feed is `degraded`, and diagnostics truthfully report the complete unavailable coverage

#### Scenario: One provider fails and another succeeds
- **WHEN** one planned Provider fails or times out without blocked exemption while another contributes valid evidence
- **THEN** the Feed run fails, exits non-zero, retains both Provider outcomes for diagnostics, and does not replace the active bundle

#### Scenario: Mandatory group is deficient with accepted evidence
- **WHEN** the pipeline accepts at least one valid item but fewer complete planned Provider outcomes contribute than a non-optional coverage group's effective minimum
- **THEN** the Feed run fails, exits non-zero, does not publish, and identifies the deficient coverage group

#### Scenario: Permitted empty contributes to coverage
- **WHEN** a Provider returns no accepted item and its `empty_valid_for_window` contract is true
- **THEN** its `empty` outcome contributes to coverage without contributing an accepted evidence item

#### Scenario: Non-permitted empty does not contribute to coverage
- **WHEN** a planned Provider reaches `empty` and its `empty_valid_for_window` contract is false
- **THEN** the Provider is incomplete, contributes no coverage, and makes the Feed run fail regardless of evidence from other Providers

#### Scenario: Every provider returns no accepted item
- **WHEN** every planned Provider reaches `healthy` or contract-permitted `empty`, mandatory coverage is satisfied, all other hard-failure boundaries succeed, and the final Feed has `items: []`
- **THEN** zero accepted evidence does not fail the run and the empty Feed remains eligible for normal successful publication

#### Scenario: An item is partially invalid
- **WHEN** a Provider produces accepted items and rejects one or more other normalized items
- **THEN** accepted items and rejection counters are retained, the Provider is partial, and source incompleteness makes the Feed run fail rather than degrade

#### Scenario: Later provider work fails after valid evidence
- **WHEN** a Provider retains accepted evidence from one sub-request, role, or page and later work fails or is incomplete
- **THEN** the retained evidence remains, the Provider is partial rather than healthy or wholly failed, and the Feed run fails without publication

#### Scenario: Later provider work is access denied after valid evidence
- **WHEN** a Provider retains accepted evidence from one sub-request, role, or page and later work receives HTTP 401 or HTTP 403
- **THEN** the retained evidence and access-denial diagnostics remain, the Provider is partial and non-exempt, and the Feed run fails without publication

#### Scenario: Planned Provider is skipped
- **WHEN** a Provider exists in the actual run plan but its terminal outcome is `skipped`
- **THEN** the Provider is incomplete and the Feed run fails

#### Scenario: Planned outcome is missing or ambiguous
- **WHEN** a planned Provider has no valid terminal outcome, more than one competing outcome, or an outcome whose identity does not match the planned Provider
- **THEN** completeness assessment fails closed instead of inferring success from counters, other outcomes, or evidence items

#### Scenario: Work is outside the actual plan
- **WHEN** a Provider is disabled or a market mapping is unverified and therefore excluded by authoritative resolved production planning
- **THEN** no synthetic skipped outcome or completeness requirement is created for that unplanned work

#### Scenario: Evidence quantity does not determine coverage
- **WHEN** a planned Provider is complete with zero accepted evidence
- **THEN** it remains eligible to satisfy configured mandatory coverage according to its terminal state and resolved empty-window contract

#### Scenario: Partial provider cannot satisfy full coverage
- **WHEN** a partial Provider belongs to a mandatory coverage group
- **THEN** it contributes no full mandatory coverage even though its accepted items remain usable in the failed Feed candidate

### Requirement: Snapshot carry-forward is validation-gated and failure-isolated
The Feed MAY carry a Provider slice only after complete current acquisition establishes that every accepted current item has an exact canonical semantic match under the same identity in the prior slice and the current active bundle has passed full schema, integrity, semantic identity, provenance, pipeline-consumability, and item validation. Carry-forward SHALL reuse the prior Provider items byte-for-byte in semantic form, including stable IDs, payloads, original source publication/update and knowledge times, provenance, and source lineage; it SHALL preserve the originating embedded Provider-contract hash and SHALL NOT merge successive slices into unbounded history. A current slice containing a new identity or changed canonical semantic content under an existing identity SHALL replace, rather than merge with, the prior slice.

Failed, partial, blocked, skipped, missing, duplicate, ambiguous, identity-mismatched, or non-permitted-empty current acquisition SHALL set freshness to `not_evaluated` and SHALL NOT consult retained evidence as a substitute. A blocked-exempt acquisition MAY produce a degraded publishable Feed without that Provider's prior slice; every other listed condition SHALL retain source-incomplete pipeline failure and no-publication behavior. Absence or invalidity of the active bundle SHALL disable carry-forward without weakening current Provider outcome, availability, or coverage rules.

#### Scenario: Valid prior slice is carried
- **WHEN** current Provider acquisition is complete with no new observation and the active bundle plus that Provider slice validate fully
- **THEN** the new candidate carries exactly the prior semantic items, records the prior `run_id`, and preserves their originating Provider-contract hash

#### Scenario: Prior bundle is invalid
- **WHEN** the active manifest, inventory, artifact, semantic identity, pipeline consumability, or prior Provider slice fails validation
- **THEN** no prior item is carried and current acquisition is evaluated without fallback

#### Scenario: Current acquisition fails with a previous snapshot
- **WHEN** current Provider acquisition fails without blocked exemption while a prior valid Provider slice exists
- **THEN** the Provider remains failed with freshness `not_evaluated`, the pipeline remains source-incomplete, and the prior slice cannot convert the run into success or publication

#### Scenario: Current acquisition is blocked with a previous snapshot
- **WHEN** current Provider acquisition is blocked-exempt while a prior valid Provider slice exists
- **THEN** freshness is `not_evaluated`, no prior item is carried for that Provider, and the degraded Feed reports the current coverage unavailability

#### Scenario: New slice replaces prior slice
- **WHEN** complete acquisition returns an identity absent from the prior Provider slice or different canonical semantic content under an existing identity
- **THEN** the current Provider slice becomes the snapshot without unioning prior items into Feed history

### Requirement: Minimal internal Feed entry reports bundle outcomes
Exactly one minimal internal Feed entry SHALL preserve existing configuration, explicit product/runtime roots, deterministic clock/window injection, deadline, status, `--dry-run`, source-completeness, Provider-availability diagnostics, and typed exit behavior. A successful publication status SHALL expose `feed-manifest.json` as the product entry path and matching `run_id` and cutoff. Dry-run SHALL build and validate the same in-memory manifest and domain artifacts without writing bundle products or advancing the checkpoint. Existing Provider work, rate-state, lock, and exit-code semantics SHALL remain unchanged.

#### Scenario: Successful publication is reported
- **WHEN** a healthy or accepted degraded bundle is durably activated
- **THEN** the command exits `0` and status names `feed-manifest.json` with matching identity and cutoff

#### Scenario: Dry run succeeds
- **WHEN** dry-run produces a valid healthy or degraded bundle candidate
- **THEN** it exits `0`, reports the candidate, creates or replaces no bundle product, and does not advance the checkpoint

#### Scenario: Blocked degradation is reported
- **WHEN** blocked exemption is the only source-acquisition issue
- **THEN** the command exits `0` with `degraded` status and deterministic diagnostics naming each blocked Provider, reason, and affected coverage group

#### Scenario: Source completeness fails
- **WHEN** planned source work has non-exempt incompleteness
- **THEN** the command preserves deterministic Provider diagnostics, exits `1`, and does not admit a bundle to publication
