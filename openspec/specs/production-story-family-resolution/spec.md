# production-story-family-resolution Specification

## Purpose
Define fail-closed materialization of resolver `story_family_label` and coexistence-relation semantics into canonical family IDs and unordered Event-ID pairs, propagate that canonical data through live and replay pipelines into deterministic selection, and enforce the frozen-first-member 15-point routine-family penalty with its exact-pair exemption.

## Requirements

### Requirement: Resolver family semantics are materialized into canonical Events
Scripts SHALL consume every resolver proposal's exact response-position alias, `story_family_label`, and `coexistence_relations` while constructing canonical Events. Scripts SHALL first derive every canonical Event ID, then derive each non-singleton family ID from the sorted member Event IDs. Literal `unknown` and every non-unknown one-member family SHALL remain Event-ID-specific singleton families. Response-local labels SHALL NOT be persisted as authoritative family IDs.

#### Scenario: Routine proposals share a non-singleton family
- **WHEN** two or more proposals in one component and resolver response carry the same non-unknown family label
- **THEN** all resulting Events carry the same family ID derived from their sorted canonical Event IDs

#### Scenario: Unknown proposals remain independent
- **WHEN** multiple proposals carry the literal `unknown` family label
- **THEN** every resulting Event receives its own `fam_single_<event_id>` family and no two unknown proposals are grouped together

#### Scenario: Non-unknown singleton remains event-specific
- **WHEN** exactly one proposal carries a particular non-unknown family label
- **THEN** its resulting Event receives its Event-specific singleton family ID and cannot carry a coexistence relation

### Requirement: Coexistence relations are validated and canonicalized fail closed
Scripts SHALL accept `distinct_material_development` only between two different proposals in the same component, resolver response, and non-unknown multi-member family. Each directed declaration SHALL occur exactly once on each side, and scripts SHALL convert the valid symmetric declarations into one sorted unordered Event-ID pair after Event IDs exist. Each Event SHALL retain its exact incident canonical pairs in stable sorted order. Incorrect position aliases and dangling, self, duplicate, asymmetric, cross-family, cross-component, cross-block, relation-on-singleton, or over-limit relations SHALL reject the complete resolver response without fallback or partial family materialization.

#### Scenario: Symmetric relation becomes one canonical pair
- **WHEN** two proposals in one non-unknown family reference each other exactly once as `distinct_material_development`
- **THEN** scripts retain one unordered pair of their sorted canonical Event IDs and expose that pair to deterministic selection

#### Scenario: Asymmetric relation is rejected
- **WHEN** one proposal declares a relation to another proposal but the target does not declare the exact reciprocal relation
- **THEN** the complete resolver response fails semantic validation and normal publication does not continue

#### Scenario: Relation crosses a semantic boundary
- **WHEN** a relation is self-referential, dangling, duplicated, attached to an unknown or singleton family, or crosses a family, component, response, or block boundary
- **THEN** the complete resolver response fails semantic validation rather than dropping or repairing the relation

#### Scenario: Pairwise semantics remain non-transitive
- **WHEN** valid pairs exist for A-B and B-C but no valid pair exists for A-C
- **THEN** scripts retain exactly A-B and B-C and SHALL NOT infer A-C

### Requirement: Production selection consumes canonical family and pair data
The normal and replay pipelines SHALL pass the materialized canonical family ID and canonical coexistence-pair data into the single deterministic selection pipeline. Selection SHALL freeze eligible Events in base-priority descending, `fully_known_at` descending, Event-ID ascending order before identifying each family's first member. Every later member of a non-singleton family SHALL receive the configured 15-point routine-family penalty exactly once unless the validated unordered pair between that later Event and the frozen first member exists. The exemption SHALL be computed inside selection from canonical pair membership and SHALL NOT be accepted as a caller-supplied boolean assertion.

#### Scenario: Routine later member is penalized
- **WHEN** two eligible Events share a non-singleton family and have no validated coexistence pair
- **THEN** the first Event in frozen base order is unpenalized and the later Event loses exactly 15 priority points before thresholds are reapplied

#### Scenario: Exact first-to-later pair grants exemption
- **WHEN** a later family member has a validated canonical pair with that family's frozen first member
- **THEN** the later member receives no routine-family penalty

#### Scenario: Later-to-later pair grants no exemption
- **WHEN** a three-Event family has a valid pair only between its second and third members in frozen base order
- **THEN** both later members remain subject to their separate exact-pair comparison with the first member

#### Scenario: Penalty changes threshold eligibility
- **WHEN** a later member qualifies before the routine-family penalty but falls below both applicable final thresholds after the 15-point subtraction
- **THEN** selection excludes that Event from the final result

### Requirement: Family behavior is deterministic across live and replay execution
Live execution and saved replay SHALL run the same resolver-family materialization and selection logic. Equivalent resolver semantics that differ only in input ordering and consistently updated response-position aliases SHALL produce identical canonical family IDs, canonical coexistence pairs, penalties, and ordered selected Event IDs. Recorded regression data SHALL include at least one valid non-singleton family, one ordinary penalized later member, and one valid non-empty coexistence pair.

#### Scenario: Equivalent proposal order is replayed
- **WHEN** identical proposals and relations are supplied in a different order with canonical position aliases updated to match that order
- **THEN** live and replay execution produce the same canonical family IDs, pair set, final priorities, and selected Event order

#### Scenario: Recorded fixture exercises both branches
- **WHEN** the regression suite evaluates its story-family replay fixture
- **THEN** it observes both a real 15-point family penalty and an exact-pair exemption through `run_pipeline` rather than constructing selection inputs directly

