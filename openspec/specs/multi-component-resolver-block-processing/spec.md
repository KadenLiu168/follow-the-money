# multi-component-resolver-block-processing Specification

## Purpose
TBD - created by archiving change fix-multi-component-resolver-blocks. Update Purpose after archive.
## Requirements
### Requirement: Item-level resolver component ownership
The resolver SHALL receive one bounded packed block containing an ordered array of one or more component projections, and every returned proposal and unresolved group SHALL carry exactly one request-local `component_alias` naming an existing component in that block. The resolver output SHALL NOT use a single top-level component alias, and the runtime SHALL reject old, mixed, missing, or unknown alias shapes rather than infer ownership.

#### Scenario: Packed block contains two disconnected components
- **WHEN** one resolver request contains component aliases `c0` and `c1`
- **THEN** every proposal and unresolved group names either `c0` or `c1` on the item itself and the complete response has no top-level `component_alias`

#### Scenario: Resolver returns an unknown alias
- **WHEN** any proposal or unresolved group names an alias absent from the current block
- **THEN** semantic validation rejects the complete resolver response before any Event is constructed

#### Scenario: Recorded output uses the old shape
- **WHEN** a live response, fixture, or replay input contains only the former top-level `component_alias`
- **THEN** closed-schema validation rejects it without assigning its items to a default component

### Requirement: Atomic block-wide semantic validation
Scripts SHALL validate the complete resolver response as one atomic block result before constructing any Event. Across proposals and unresolved groups, every input seed in the block SHALL occur exactly once, and each defining seed, supporting fact, evidence reference, and entity reference SHALL be permitted by the projection of the item's named component. Missing, duplicate, non-seed, invented, out-of-block, or cross-component membership SHALL reject the complete result.

#### Scenario: Every component is covered exactly once
- **WHEN** proposals and unresolved groups collectively assign every seed from every component in the block exactly once using only their named component projections
- **THEN** block validation succeeds and Event construction may begin

#### Scenario: Proposal crosses a component boundary
- **WHEN** a proposal names `c0` but references a seed, supporting fact, evidence ID, or entity available only to `c1`
- **THEN** the complete resolver response is rejected even if block-wide seed coverage would otherwise be complete

#### Scenario: Later component is invalid
- **WHEN** an earlier component has valid proposals but any later component has an invalid alias, reference, or seed partition
- **THEN** the complete block fails and no Event or normalized unresolved result from that block is returned

### Requirement: Complete multi-component Event construction
After atomic validation succeeds, scripts SHALL construct Events from proposals belonging to every component in the packed block. Construction SHALL process components in canonical block order and preserve proposal-array order within each component; no implementation SHALL select only the first component or pass another component's proposals into component-local Event construction.

#### Scenario: Two components each produce an Event
- **WHEN** a valid packed-block response contains one proposal for `c0` and one proposal for `c1`
- **THEN** scripts construct and retain both canonical Events without `ResolutionError` or omission

#### Scenario: One component has no proposal
- **WHEN** one component assigns all of its seeds to valid unresolved groups while another component produces proposals
- **THEN** scripts construct only the proposed Events and retain the other component's normalized unresolved groups without treating them as Events

### Requirement: Component-local family and coexistence boundaries
Proposal position aliases SHALL remain unique and canonical across the complete proposal array, while story-family labels and coexistence relations SHALL be evaluated only among proposals carrying the same component alias. Cross-component family membership or coexistence references SHALL reject the complete block result.

#### Scenario: Same family label appears in two components
- **WHEN** proposals in `c0` and `c1` use the same non-unknown family label without relations between them
- **THEN** scripts treat them as separate component-local families and derive no shared family identity

#### Scenario: Coexistence relation crosses components
- **WHEN** a proposal in `c0` references a proposal position belonging to `c1`
- **THEN** semantic validation rejects the complete resolver response before Event construction

### Requirement: Unresolved resolver audit retention
For each valid block, scripts SHALL normalize every unresolved group from request-local aliases to canonical component, seed-fact, and evidence identifiers; expose the ordered normalized groups separately on the pipeline result; and persist them as a dedicated indexed run-Bundle artifact. Unresolved groups SHALL NOT enter analyst packets, Event selection, or Brief Event rendering.

#### Scenario: Later component is unresolved
- **WHEN** a valid block proposes Events for its first component and returns unresolved groups for a later component
- **THEN** the pipeline result and Bundle contain the normalized later-component unresolved groups even though no Event is created for them

#### Scenario: All block seeds are unresolved
- **WHEN** every seed in a valid block is assigned exactly once to unresolved groups
- **THEN** the block produces no Events but retains all normalized unresolved groups and continues through the explicitly sparse normal path

### Requirement: Deterministic recording and replay
Repository-owned resolver fixtures, golden outputs, and run-Bundle replay inputs SHALL use only the item-level component ownership contract. Bundle replay SHALL reconstruct and compare normalized unresolved groups in addition to existing pipeline artifacts, and any schema, ownership, Event, unresolved, or Bundle-member drift SHALL fail closed without provider or LLM calls.

#### Scenario: Multi-component Bundle replay is unchanged
- **WHEN** a valid Bundle records a packed block with proposals or unresolved groups for multiple components
- **THEN** offline replay reconstructs identical Events and normalized unresolved groups with zero provider and zero LLM calls

#### Scenario: Unresolved artifact is tampered
- **WHEN** the dedicated normalized unresolved Bundle member is missing, unindexed, or differs from deterministic reconstruction
- **THEN** Bundle integrity or replay reports failure rather than accepting the run

