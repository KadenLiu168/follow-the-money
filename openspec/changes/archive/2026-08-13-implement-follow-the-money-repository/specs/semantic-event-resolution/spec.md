## ADDED Requirements

### Requirement: Single configured LLM runtime
All four LLM passes SHALL use the OpenAI Responses API and one configured model that supports the required strict structured-output schemas, set `store: false`, use no provider-side conversation state, model routing, ensemble, automatic fallback, tools, retrieval, file access, or arbitrary URL access, and keep Feed generation independent of that runtime.

#### Scenario: Different semantic prompts execute
- **WHEN** resolver, analyst, editor, and language-audit passes run
- **THEN** they use the same configured model while applying pass-specific prompts and schemas

#### Scenario: Model call fails
- **WHEN** the configured model is unavailable
- **THEN** the system reports the pass failure and does not silently call another model

#### Scenario: Configured model cannot satisfy a response schema
- **WHEN** startup validation determines that the selected model or schema cannot use required strict Structured Outputs
- **THEN** the full Brief command fails before sending evidence

### Requirement: Typed LLM failure state machine
Each LLM pass SHALL enforce the design-defined v1 canonical byte/context reservation, exact resolver/analyst/editor/language-audit output-token caps `72k/72k/72k/56k`, complete-response caps `64/64/64/48 KiB`, request-local-reference/cardinality/string/control-character maxima, 30/45-second per-attempt limits, at-most-two-attempts-per-logical-invocation, concurrency, 40-resolver-block, 20-analyst-packet, and 300-second pre-commit Brief-generation deadline with its exact 15-second commit reserve. Startup SHALL prove the configured model's context and maximum-output capabilities, strict schema compatibility, zero-reasoning mode, and generated all-max canonical-response feasibility. Known input/allocation overflow SHALL fail `response_contract_capacity` before sending. A response one item or canonical byte over SHALL fail non-retryable `response_capacity_exceeded`; invalid UTF-8 or prohibited `Cc`/`Cf`/`Cs`/`Zl`/`Zp`, including any lone high/low surrogate, in any prose/reason field SHALL fail non-retryable `response_content_invalid`; neither outcome is truncated or heuristically repaired. The runtime SHALL also distinguish deadline exceeded, refusal, incomplete output, timeout, HTTP/transport failure, invalid structure, and semantic-reference failure. Each resolver block, analyst packet, editor call, and language-audit call is one logical invocation. Only connection failure, attempt timeout, or HTTP `408|409|429|5xx` MAY receive that invocation's single same-model retry when the full retry timeout plus commit reserve fits the remaining deadline; HTTP `400|401|403|404|422`, refusal, incomplete, context/capability, structure/reference/capacity/content, cancellation, and global-deadline outcomes SHALL NOT retry, and exhaustion SHALL fail closed without prose recovery.

#### Scenario: Responses API returns a refusal
- **WHEN** any required pass returns a refusal object
- **THEN** the pass records `refused`, performs no heuristic parsing, and follows the configured publication-blocking rule

#### Scenario: Resolver block fails after retries
- **WHEN** one resolver block exhausts its allowed attempts
- **THEN** normal publication is blocked because event-set completeness cannot be established

#### Scenario: Analyst event fails after retries
- **WHEN** one shortlisted event cannot produce a valid analysis
- **THEN** that event is excluded with a visible degraded warning and thresholds are not lowered to replace it

#### Scenario: Every attempted analyst event fails
- **WHEN** the analyst shortlist is non-empty and no event produces a valid analysis
- **THEN** normal publication is blocked rather than treating the systemic pass failure as a naturally sparse result

#### Scenario: Editor or language audit fails
- **WHEN** structured synthesis or final language audit cannot complete validly
- **THEN** normal Brief publication is blocked

#### Scenario: Brief cannot reach irreversible commit admission
- **WHEN** any pass/audit/staging operation cannot finish by second 285 with the 15-second commit reserve intact
- **THEN** in-flight calls are cancelled, completed outcomes are retained only in a best-effort failed audit bundle, and no partial normal Brief is published

#### Scenario: Admitted bundle commit crosses the nominal deadline
- **WHEN** fully staged and `fsync`ed bytes enter the no-replace rename by second 285 but rename or parent `fsync` completes after second 300
- **THEN** the non-cancellable transaction finishes normally and reports `commit_elapsed_overrun` only in external machine-readable command status/stderr on success, leaves all hashed Feed/bundle member bytes unchanged, and neither times out, rolls back, nor exposes late background mutation

### Requirement: Untrusted evidence isolation
Titles, snippets, URLs, and metadata SHALL be treated as bounded untrusted data, canonicalized and structurally delimited from instructions, and SHALL NOT be able to change prompts, request tools, expose secrets, or broaden the response schema.

#### Scenario: Evidence contains prompt-injection text
- **WHEN** a title or snippet asks the model to ignore instructions, call a tool, reveal a secret, or invent a source
- **THEN** the request still exposes no such capability and any out-of-schema or out-of-evidence output is rejected

### Requirement: Candidate-block-only resolver input
The semantic resolver SHALL receive a stably sorted bounded candidate block containing an ordered array of explicit component aliases/projections, each with only its evidence IDs, allowed fact IDs, titles, snippets, metadata, and deterministic entity/time/category hints rather than unrestricted Feed content or all-pairs inputs. Packing SHALL preserve component boundaries and duplicate bridge evidence projections across components when their allowed facts differ.

#### Scenario: Resolver is invoked
- **WHEN** a candidate block requires semantic resolution
- **THEN** only evidence/facts from that block are present, and every proposal or unresolved group names one component alias and references only that component's projection

### Requirement: Atomic event extraction
Before the resolver call, scripts SHALL designate as `atomic_event_seed_fact_ids` every candidate ledger entry whose type is `FACT` or `CLAIM` and whose origin payload is exactly `news`, `macro_release`, `policy`, `filing`, `flow`, or `positioning`, with no predicate allowlist; `market_data`, `calendar`, `OBSERVATION`, and `INFERENCE` entries SHALL never be seeds. Each component and packed block SHALL contain at most 24 seeds. The resolver SHALL be permitted to map one evidence item to multiple atomic events and multiple evidence items to one event when supplied evidence supports those mappings, but each proposal SHALL consume 1..24 disjoint existing seed fact IDs as its exact event-defining set. Across the complete response every input seed SHALL occur exactly once, either in one of at most 24 proposals or one of at most 24 structured unresolved groups; supporting non-seed facts MAY be shared. Missing, duplicate, cross-component, non-seed-defining, or extra seed membership SHALL reject the result, so the proposal cap cannot silently omit a 25th possible Event.

#### Scenario: Article contains two supported events
- **WHEN** a title and snippet clearly describe two independently meaningful financial events
- **THEN** the resolver can emit two separate event proposals that reference the shared evidence item and distinct existing event-defining fact-ID sets

#### Scenario: Article cannot be split into existing facts
- **WHEN** one evidence item appears to mention several events but deterministic preprocessing produced no distinct supported fact IDs for them
- **THEN** the resolver returns unresolved instead of creating free-text discriminators or new facts

#### Scenario: Resolver omits the final seed
- **WHEN** a response assigns only 23 of a block's 24 deterministic event seeds to proposals/unresolved groups, or assigns one seed twice
- **THEN** semantic validation rejects the whole response rather than accepting a truncated event set

#### Scenario: Several reports describe one event
- **WHEN** several evidence items describe the same atomic event
- **THEN** the resolver can group their evidence IDs under one event proposal

### Requirement: Resolver abstention
The resolver SHALL support `unresolved` and empty-event results and SHALL NOT infer missing facts from general knowledge when title, snippet, and metadata are insufficient.

#### Scenario: Bridge article is ambiguous
- **WHEN** supplied evidence cannot establish whether two mentions represent one event or two
- **THEN** the resolver returns an unresolved relationship rather than force-merging them

### Requirement: Resolver scope restrictions
Resolver output SHALL be limited to atomic event membership, a closed event-type fallback, story-family relationship, and bounded non-prose semantic resolution metadata; it SHALL NOT contain a title/display label, free-text summary, investment analysis, asset direction, price-in, importance, market regime, or ranking. Scripts SHALL derive the canonical Chinese event display label from a versioned template over only the closed event type, resolved entity display names, and structured values/units of existing `key_fact_ids`, and SHALL retain the contributing fact/evidence references.

#### Scenario: Resolver emits asset direction
- **WHEN** structured output includes a bullish, bearish, or equivalent asset assessment
- **THEN** semantic validation rejects the output

#### Scenario: Resolver invents a supported title
- **WHEN** resolver output contains a prose title, display label, or summary even when it resembles input evidence
- **THEN** strict schema validation rejects it and scripts generate the display label only from the referenced structured facts

### Requirement: Closed story-family and coexistence semantics
Every resolver proposal SHALL carry its canonical response-position alias `p00` through `p23`, exactly one `story_family_label` equal to literal `unknown` or matching `f[0-9]{1,2}`, and zero to eight closed `coexistence_relations`. A non-unknown label SHALL partition only proposals in the same component and resolver response and SHALL NOT join components or blocks. Each relation SHALL reference one different proposal in that same component and non-unknown family, use only `distinct_material_development`, be declared symmetrically exactly once, and remain pairwise rather than transitive. Scripts SHALL derive each non-singleton canonical `story_family_id` from sorted member Event IDs after canonical construction, convert relations to unordered Event-ID pairs, and treat unknown or singleton families as Event-ID-specific singletons. A later family member SHALL avoid the routine penalty only when its pair with the frozen base-order first member is present; absence means the penalty applies. Missing/incorrect position aliases and dangling, self, duplicate, asymmetric, cross-family, cross-component, cross-block, or over-eight relations SHALL reject the complete resolver response.

#### Scenario: Routine related proposals share a family
- **WHEN** two proposals in one component use the same non-unknown family label without a valid coexistence pair
- **THEN** scripts derive one family ID from their sorted canonical Event IDs and the later base-order member receives the routine family penalty

#### Scenario: Distinct material developments may coexist
- **WHEN** two proposals in one component and family symmetrically reference each other as `distinct_material_development`
- **THEN** scripts retain one canonical unordered Event-ID coexistence pair and waive the later member's routine penalty only when the other Event is that family's frozen first member

#### Scenario: Family relationship crosses a component
- **WHEN** a family label or coexistence relation attempts to join proposals from different components or resolver blocks
- **THEN** semantic validation rejects the complete resolver response rather than creating a cross-boundary story family

### Requirement: Evidence-bound event facts
Every resolver event proposal SHALL name exactly one existing input component and reference one or more evidence IDs and existing fact IDs from only that component's projection; the resolver SHALL NOT cross component boundaries or introduce new facts, fact IDs, URLs, sources, evidence IDs, numeric values, or entities unsupported by that component.

#### Scenario: Resolver invents an evidence ID
- **WHEN** output references an identifier absent from the candidate block
- **THEN** validation fails and no canonical event is created from that output

#### Scenario: Resolver merges packed disconnected components
- **WHEN** a proposal names one component but references an evidence/fact alias belonging only to another packed component, including another projection of the same bridge evidence
- **THEN** semantic validation rejects the entire resolver result rather than constructing a cross-component Event

### Requirement: Script-assigned canonical identity
Scripts SHALL assign deterministic event IDs from the versioned canonical tuple of sorted evidence IDs, event type, normalized resolved entity IDs, and an atomic discriminator made from the sorted complete canonical keys of the proposal's existing event-defining facts. Every discriminator fact key SHALL retain its normalized subject entity ID or stable raw-subject identity, predicate, economic effective/reference instant or date plus precision/granularity, normalized object/value, and unit, so swapping values between subjects or times cannot collide; provider/evidence-scoped fact IDs themselves SHALL NOT replace this semantic key. All source free text is excluded. Scripts SHALL also recompute `fully_known_at`, validate event schemas, and validate the fact-referenced deterministic display label after semantic resolution; the LLM SHALL NOT determine canonical identifiers, knowledge/effective instants, or labels, author fact membership outside its candidate block, or mutate existing Feed evidence.

#### Scenario: Input order changes
- **WHEN** the same evidence block is presented in a different order and resolves to the same event facts
- **THEN** the script assigns the same canonical event identity

### Requirement: Structured output enforcement
The resolver SHALL return data conforming to a closed `resolver-output.schema.json` supported by strict OpenAI Structured Outputs, and scripts SHALL then apply full repository-schema and semantic-reference validation; invalid, incomplete, or refused outputs SHALL be rejected rather than parsed heuristically from prose.

#### Scenario: Model returns unstructured prose
- **WHEN** the model response does not satisfy the resolver schema
- **THEN** the pass fails validation and produces no silently recovered events
