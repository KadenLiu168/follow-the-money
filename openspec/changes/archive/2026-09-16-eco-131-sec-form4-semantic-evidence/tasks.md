## 1. Pin SEC v3 Contracts and Compatibility

- [x] 1.1 Add characterization tests for current SEC v2 13F payload bytes, v1/v2 bundle reads, supported-version rejection, and whole-slice behavior; verify the focused compatibility tests pass before changing production semantics.
- [x] 1.2 Extend strict configuration models/loaders with ordered `watched_form4_issuers`, ship only Berkshire CIK `0001067983`, embed the selection in `feed_config.snapshot`, and verify missing, unknown, duplicate, malformed, and reordered inputs through focused config tests.
- [x] 1.3 Extend Provider manifest resolution and embedded snapshots with test-local SEC v3 support, closed `max_filings_per_window = 20`, and `ownership_xml_schema_versions = [X0609]`; verify v3 requires these exact fields while v1/v2 and non-SEC contracts reject or omit them as specified, without bumping the production manifest yet.
- [x] 1.4 Add backward-readable closed JSON Schema definitions for `form13f` and structured `form4` payloads while preserving valid v1/v2 shapes; verify schema tests reject unknown subtype fields, generic facts, malformed unions, and unsupported payload combinations.

## 2. Build the Provider-Specific Form 4 Core

- [x] 2.1 Add SEC Form 4 listing-candidate records and recent-list selection with aligned-field, unique-accession, precise-acceptance-time, canonical selected-order, half-open-window, full-coverage, exact-form, and 20-filing-bound validation; verify focused selector tests cover both boundaries, source-row reordering, complete empty, incomplete history, duplicates, and bound exhaustion.
- [x] 2.2 Add narrowly validated raw ownership-XML URL derivation from safe SEC primary-document locators, including the verified XSL presentation prefix and accession archive root; verify tests reject absolute paths, credentials, traversal, unexpected nesting/extensions, issuer/accession mismatches, and transformed-HTML responses.
- [x] 2.3 Add production-shaped/recorded fixtures under `providers/sec_edgar/fixtures/form4/` for purchase, sale, award, amendment, multiple mixed transactions, derivative entries, standalone holdings, multiple owners, and footnote-supported nulls; record truthful manifest/reference provenance and verify every fixture is admitted by its intended pure-core test.
- [x] 2.4 Implement bounded ownership XML admission and issuer/reporting-owner/relationship parsing in `providers/sec_form4.py`; verify exact form/schema/issuer cross-checks, owner uniqueness/order, complete relationship fields, at-least-one relationship, and rejection of DTD/entity, unknown, duplicate, or unsupported structures.
- [x] 2.5 Implement non-derivative and derivative transaction/standalone-holding parsing with mixed source ordinals and applicable date, coding, security, underlying-security, post-state, and ownership fields; verify all four entry kinds are retained without owner duplication or silent omission.
- [x] 2.6 Reuse ECO-125 measured numeric facts for every Form 4 numeric branch and project canonical `shares`, `usd`, and `usd_per_share` values; verify branch exclusivity, nonnegative/bounded values, footnote-supported nullability, indirect-ownership nature, and ambient Decimal-context independence.
- [x] 2.7 Implement bounded filing footnotes, field-level references, remarks, and amendment evidence; verify numeric footnote ordering, NFC/whitespace normalization, 4,000-code-point and 2,000-character bounds, dangling/duplicate/malformed reference rejection, independent Form 4/A identity, and absence of `amends_accession` or effective-version semantics.
- [x] 2.8 Implement accession-based item IDs, accession/table/source-ordinal entry IDs, and canonical owner/table/entry/footnote ordering; verify repeated input yields identical canonical bytes and each material semantic mutation changes content identity without changing stable positional IDs.

## 3. Integrate SEC Acquisition and Outcomes

- [x] 3.1 Add a `SecForm4Adapter` acquisition unit that performs one issuer submissions request followed by every selected raw XML request through the existing managed client in deterministic order; verify zero-event, one-event, multi-event, retry, deadline, and partial-progress adapter tests.
- [x] 3.2 Extend production SEC adapter construction to append watched-issuer Form 4 units after sorted 13F units under one `sec_edgar` outcome and rate scope; verify adapter order, Provider identity, exact request counts, user-agent/host policy, and no ninth Provider or independent outcome.
- [x] 3.3 Update SEC request-budget regression coverage for the existing 13F resources plus one listing and at most 20 Form 4 XML resources; verify the resolved minimum-interval floor remains below the 285-second pre-commit boundary with documented headroom.
- [x] 3.4 Verify outcome aggregation fails closed when listing coverage, any selected XML, parsing, or later SEC unit is incomplete, preserving accepted diagnostics and existing blocked/non-exempt progress semantics without prior-slice fallback.

## 4. Validate SEC v3 Semantics and Snapshot Selection

- [x] 4.1 Add SEC v3 semantic dispatch that requires `form13f` for the unchanged complete 13F structure and `form4` for the complete structured ownership payload, while retaining exact v1/v2 read behavior; verify focused Feed-boundary tests for all supported and unsupported Provider/version/subtype combinations.
- [x] 4.2 Add Form 4 semantic validation for configured issuer membership, source/acceptance/window consistency, relationship combinations, all entry unions, IDs/order, numeric units/nullability, ownership, amendment, remarks, and footnote resolution; verify malformed or prohibited evidence fails closed.
- [x] 4.3 Extend pre-snapshot and final-candidate SEC completeness checks to require the exact watched 13F CIK set plus the selector-proven current-window Form 4 accession set; verify missing, duplicate, extra, wrong-issuer, or legacy-shaped v3 items prevent publication.
- [x] 4.4 Apply existing exact-set whole-Provider replacement to SEC v3 mixed slices; verify new Form 4 events replace the slice, prior-window events disappear without carry/union, byte-identical complete slices may carry unchanged, and partial Form 4 work remains `not_evaluated` and pipeline-failing.
- [x] 4.5 Add evidence-only boundary tests proving Form 4 payloads reject `signal`, `bullish`, `bearish`, `sentiment`, `confidence`, `importance`, `recommendation`, inferred `holding_delta`, calculated transaction value, generic facts, and amendment-effectiveness fields.

## 5. Activate the Production Contract Atomically

- [x] 5.1 Bump the checked-in SEC EDGAR manifest to contract v3 only after the working configuration, adapter, pure core, schema, semantic validation, fixtures, and snapshot path are present; verify resolved production embeds v3, Berkshire selection, exact Form 4 bounds/schema versions, and unchanged eight-Provider/five-domain coverage.
- [x] 5.2 Run an end-to-end deterministic fixture Feed with existing eight watched 13F companies plus the Berkshire Form 4 unit; verify one SEC outcome, correct filing subtypes, complete provenance, canonical artifact bytes, stable digest/run identity at a fixed cutoff, and no regression in CFTC or the other six Providers.
- [x] 5.3 Verify source-complete zero-Form-4 and multiple-transaction/amendment fixture runs, plus same-input repeated generation, produce the expected whole SEC slice and byte-identical canonical artifacts without history accumulation.

## 6. Documentation and Final Verification

- [x] 6.1 Update the Feed contract, configuration, architecture, Provider-source verification, semantic evidence documentation, README/SKILL-facing truthful capability text, and fixture provenance to describe SEC v3 13F/Form 4 support and its limits; verify documentation tests contain no unsupported analysis, amendment-linkage, historical-query, or credential claims.
- [x] 6.2 Run focused config, manifest, SEC 13F, Form 4, semantic numeric, Feed boundary, snapshot, determinism, provider-session, pipeline, bundle, and documentation tests; verify all pass and existing ECO-124/ECO-125 characterization bytes remain valid where compatibility requires.
- [x] 6.3 Run `.venv/bin/python scripts/quality_gate.py`, `openspec doctor`, `openspec validate eco-131-sec-form4-semantic-evidence --strict`, and `openspec validate --all --strict`; record actual results and resolve every in-scope failure before marking the Change complete.
