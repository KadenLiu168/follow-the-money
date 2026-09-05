## MODIFIED Requirements

### Requirement: Minimal internal Feed entry reports bundle outcomes
Exactly one minimal internal Feed producer entry SHALL preserve existing configuration, explicit product/runtime roots, deterministic clock/window injection, deadline, status, `--dry-run`, source-completeness, Provider-availability diagnostics, and typed exit behavior. A successful publication status SHALL expose `feed-manifest.json` as the product entry path and matching `run_id` and cutoff. Dry-run SHALL build and validate the same in-memory manifest and domain artifacts without writing bundle products or advancing the checkpoint. Existing Provider work, rate-state, lock, and exit-code semantics SHALL remain unchanged. This producer entry SHALL NOT be the normal Skill consumption entry.

For an otherwise publishable healthy or degraded candidate, serialized Feed size SHALL equal the byte length of its canonical manifest plus the byte lengths of every canonical artifact in the manifest's complete fixed inventory. The producer SHALL require that total to be less than or equal to the configured `max_serialized_feed_bytes` before reporting dry-run success or attempting publication. An oversized candidate SHALL fail closed through the existing typed producer-failure boundary without truncation, publication, active-bundle replacement, or checkpoint advancement. A source-completeness `pipeline.status = failure` SHALL retain its existing authoritative failure and diagnostics rather than being replaced by this publishable-candidate size check.

#### Scenario: Successful publication is reported
- **WHEN** a healthy or accepted degraded bundle is within the configured serialized Feed limit and is durably activated
- **THEN** the producer command exits `0` and status names `feed-manifest.json` with matching identity and cutoff

#### Scenario: Dry run succeeds
- **WHEN** dry-run produces a valid healthy or degraded bundle candidate within the configured serialized Feed limit
- **THEN** the producer command exits `0`, reports the candidate, creates or replaces no bundle product, and does not advance the checkpoint

#### Scenario: Publishable candidate exceeds the serialized Feed limit
- **WHEN** the canonical manifest bytes plus all canonical artifact bytes for a healthy or degraded candidate exceed `max_serialized_feed_bytes`
- **THEN** the producer reports a typed failure, exits `1`, publishes no candidate bytes, leaves the active bundle unchanged, and does not advance the checkpoint

#### Scenario: Candidate exactly meets the serialized Feed limit
- **WHEN** the canonical manifest bytes plus all canonical artifact bytes equal `max_serialized_feed_bytes`
- **THEN** the size boundary admits the otherwise valid healthy or degraded candidate

#### Scenario: Blocked degradation is reported
- **WHEN** blocked exemption is the only source-acquisition issue and the resulting bundle is within the configured serialized Feed limit
- **THEN** the producer command exits `0` with `degraded` status and deterministic diagnostics naming each blocked Provider, reason, and affected coverage group

#### Scenario: Source completeness fails
- **WHEN** planned source work has non-exempt incompleteness
- **THEN** the producer command preserves deterministic Provider diagnostics, exits `1`, and does not admit a bundle to publication or replace that failure with the publishable-candidate size check
