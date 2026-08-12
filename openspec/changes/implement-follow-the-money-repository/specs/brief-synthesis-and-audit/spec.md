## ADDED Requirements

### Requirement: Fixed Morning Brief structure
The system SHALL render the Morning Money Brief in Chinese with the fixed ordered headings `市场仪表盘`, `市场状态`, `重点事件`, `其他重要事件`, conditional `资金流与持仓`, `未来 24 小时关注`, and `结论`. Every editor-owned narrative slot SHALL declare `zh-CN` and pass the design's deterministic Han-script minimum after allowed ticker/proper-name/number spans are excluded; all-English narrative SHALL fail closed while legitimate configured Latin names and tickers MAY remain.

#### Scenario: Normal Brief is rendered
- **WHEN** validated selected events and dashboard data are available
- **THEN** the output follows the required heading order and displays generation time and actual Asia/Shanghai evidence window

### Requirement: Compact market dashboard
The v1 dashboard SHALL cover the design-defined S&P 500, CSI 300, Hang Seng, VIX, US 2-year yield, US 10-year yield, China 10-year yield, DXY, USD/CNH, copper, WTI, gold, and BTC roles, expose unavailable roles, and emphasize absolute current-excluded z-scores of at least `2.0` without becoming a complete market terminal.

#### Scenario: All configured observations are available
- **WHEN** valid data exists for the configured dashboard instruments
- **THEN** the Brief reports their compact moves and highlights deterministic anomalies

#### Scenario: Instrument data is missing
- **WHEN** one configured instrument lacks fresh valid data
- **THEN** it is marked unavailable or stale rather than filled or omitted without notice

### Requirement: Data-derived market regime
Scripts SHALL derive the Market State Vector and regime before LLM explanation using the design-defined v1 role votes, per-dimension minimums, five-dimension denominator, required known Risk Appetite plus at least 4-of-5 coverage, and non-overlapping `risk_off`/`risk_on`/`neutral` precedence rules, returning `unknown` when coverage fails; the informational regime SHALL NOT affect event scoring or selection.

#### Scenario: Equities rise, rates fall, USD weakens, and volatility falls
- **WHEN** configured deterministic rules classify the observed vector
- **THEN** the LLM may explain that state but cannot replace its classification

#### Scenario: Regime coverage is insufficient
- **WHEN** the configured minimum instrument or dimension coverage is not met
- **THEN** the regime is `unknown` with missing inputs rather than forced to `neutral`

### Requirement: Tiered event detail
Up to three qualifying events SHALL receive the complete analysis format, while subsequent selected events SHALL use a compact format; v1 SHALL target 10 total events, enforce `maxItems = 12` after final stable sorting, and honor quality, confidence, and component-coverage thresholds before count targets.

Each full-event entry SHALL contain a referenced fact summary, why-it-matters mechanism/implication, measured reaction and bounded attribution, price-in status, final money-flow status, affected-asset mappings with horizon, alternative interpretation/uncertainty, evidence confidence, and source links. Each compact entry SHALL contain a referenced fact summary, one bounded why-it-matters statement, one bounded uncertainty statement, confidence, and source links; absent optional evidence SHALL remain `unknown` or omitted according to the closed schema rather than being invented.

#### Scenario: Ten qualifying events exist
- **WHEN** ten events survive selection and at least three are full-event eligible
- **THEN** exactly three use full analysis and the remainder use the compact key-event format

#### Scenario: Fewer than three selected events are full-event eligible
- **WHEN** the final selected set contains only zero, one, or two full-event-eligible entries
- **THEN** exactly those eligible entries use full analysis, every other selected event remains compact, and no ineligible event is promoted to fill a full-event slot

#### Scenario: Only two full-event-eligible events qualify
- **WHEN** only two events survive every gate and both are full-event eligible
- **THEN** exactly those two use full analysis and the Brief carries a sparse-result warning without filling a third slot

#### Scenario: More than twelve events qualify
- **WHEN** thirteen or more events survive every gate
- **THEN** only the first twelve in final stable order are selected, up to the first three eligible entries use full format, and no later event is emitted

### Requirement: Conditional flow section
The Money Flow & Positioning section SHALL appear only when selected analysis contains audited `confirmed` or explicitly labelled `indicated` flow or positioning evidence.

#### Scenario: No valid flow evidence exists
- **WHEN** all selected events have `money_flow = no_evidence`
- **THEN** the Money Flow & Positioning section is absent

### Requirement: Focused 24-hour watchlist
Scripts SHALL first prove `calendar_horizon_end >= brief_generated_at + 24h`, then select up to six configured `critical` or `high` calendar events in `[brief_generated_at, brief_generated_at + 24h)` using the injected clock, sorting `critical` before `high`, then `scheduled_at` and stable ID ascending without filling from lower priorities; the editor-pass LLM SHALL be limited to explaining importance, sensitive assets, and key observation points.

#### Scenario: More than six calendar items exist
- **WHEN** the next 24 hours contain more than six valid calendar entries
- **THEN** deterministic filters select no more than six without turning the section into a complete calendar

#### Scenario: Fewer than three calendar items exist
- **WHEN** the next 24 hours contain zero, one, or two qualifying entries
- **THEN** the section contains only those entries or an explicit no-data state and never invents filler events

#### Scenario: Feed calendar horizon is too short
- **WHEN** `brief_generated_at + 24h` exceeds the persisted `calendar_horizon_end`
- **THEN** normal publication is blocked rather than claiming a complete 24-hour watchlist

### Requirement: Concise Bottom Line
The Bottom Line SHALL contain at most three evidence-consistent points that summarize the dominant market logic without recommendations.

#### Scenario: Editor returns four points
- **WHEN** structured synthesis contains more than three Bottom Line entries
- **THEN** schema validation rejects the Brief object

### Requirement: Structured synthesis and deterministic Markdown
Before the editor call, scripts SHALL construct the design-defined ordered projection of at most 61 editor-fillable claim slots and SHALL NOT pass complete packets, full Analysis objects, or URL targets. The only v1 slot kinds/allocation SHALL be one `market_state_explanation`; eight exact kinds per full-formatted Event for count `F` in `0..3` (`event_fact_summary`, `why_it_matters`, `reaction_attribution`, `price_in`, `money_flow`, `asset_mapping`, `alternative`, `uncertainty`); three exact kinds per every other compact-formatted selected Event for count `C` in `0..(12-F)` (`event_fact_summary`, `why_it_matters`, `uncertainty`); one `watchlist_explanation` per at-most-six selected items; and exactly `min(3, F+C)` first-selected-Event-owned `bottom_line_point` allocation slots, each optional for the editor to fill. Compact count MAY reach 12 when `F = 0`; the exact conditional maximum is `1 + max(8F + 3C) + 6 + 3 = 1 + (3*8 + 9*3) + 6 + 3 = 61`, not a nine-compact selection limit. No Bottom Line slot SHALL exist with zero selected Events, and no unlisted kind/owner SHALL be accepted. Each slot SHALL contain at most 768 canonical UTF-8 bytes of validated source values/text plus at most 8 existing reference aliases; outer metadata SHALL remain within 4 KiB and the complete projection within 72 KiB. Equality SHALL pass and any slot/projection one byte or reference over SHALL fail `editor_input_capacity` before sending without truncation.

Each source payload SHALL be the closed canonical view defined in design for its kind: script-owned market-state dimensions/missing roles; Event label/confidence and ordered key facts; ordered analyst mechanisms/implications; ordered script reaction observations plus matching attribution; the one price-in object; script-final flow plus ordered direct/indirect support; exact-nine-group-ordered asset mappings; schema-ordered alternatives; packet confidence/verification/conflicts/unknown reasons; deterministic calendar priority/time/label/assets/observation fields; or the owning selected Event's label/confidence/final-priority/fact/why-it-matters refs for Bottom Line. Scripts SHALL append only whole ordered records while the complete payload remains within 768 bytes, retain exact included/omitted counts, derive the at-most-eight reference aliases only from included records in tier/knowledge-time/evidence-ID order, and fail before send on scalar-envelope overflow, count/order mismatch, or any implementation-selected truncation/field extension.

The editor SHALL return only a closed `editor-output.schema.json` containing at most one single-line `zh-CN` bounded wording fragment and existing references for each of at most 61 script-allocated editor claim slots for selected events, market state, watchlist, and Bottom Line; the separate 13 dashboard claim slots are filled only by deterministic templates. The total filled inventory SHALL contain at most 74 claims. The editor SHALL NOT own claim IDs/classes, facts, numbers, scores, statuses, URLs, ordering, section membership, Markdown, HTML, or links and SHALL NOT merge, split, reorder, or invent slots. Scripts SHALL derive every stable `claim_id` without prose from schema version, section, owning object ID, slot kind, and ordinal, own the slot's `is_factual`/`is_causal` flags, reject a missing required slot, validate and merge only editor-owned wording into the authoritative `brief.schema.json` claim inventory, and render the final Markdown without allowing the editor to replace any Event, Analysis, or deterministic field. The authoritative inventory SHALL contain exactly filled/rendered slots; permitted optional unfilled definitions remain only in the allocation trace and are excluded from audit coverage and metrics. Each inventory slot SHALL be one claim-audit and metric unit regardless of punctuation or clause count. Fixed section headings, field labels, URLs, provenance, and visibility warnings SHALL NOT be inventory claims; script-derived event display labels MAY remain non-inventory only because their exact versioned template output and contributing fact/evidence references are deterministically audited and no LLM title field exists. Every analyst/editor/audit prose or reason field SHALL be NFC-normalized, single-line, at most 192 UTF-8 bytes, and reject `Cc`/`Cf`/`Cs`/`Zl`/`Zp`. Renderer-owned structure SHALL canonicalize/strip whitespace, entity-encode `&<>`, backslash-escape every other ASCII punctuation code point in the four design-defined ranges, disallow raw input markup, and create links only from canonical provider-bound HTTPS targets revalidated against the input Feed's embedded owning-provider runtime-contract snapshot. Scripts SHALL choose at most one representative source link per dashboard role, selected Event, and watchlist item by the design's stable tier/knowledge-time/evidence-ID order, retain all other evidence refs in the bundle, and reject actual Markdown over 96 KiB without truncation.

All analyst/editor/language-audit prose and reason values SHALL decode as strict UTF-8, contain only Unicode scalar values, reject lone high/low surrogates plus `Cc`/`Cf`/`Cs`/`Zl`/`Zp`, and then undergo NFC and UTF-8 byte counting before merge or canonical response measurement.

Editor-citable slot refs SHALL be only the first at-most-eight evidence aliases from the included records' verified transitive support closure, deduplicated and ordered by tier, knowledge time descending, and evidence ID ascending, with exact omitted-reference count; unresolved/cyclic/cross-owner closure and returned fact/observation/Event/Analysis aliases SHALL fail before authoritative merge. Complete support SHALL remain in the bundle even when only a bounded evidence-ref subset is exposed to the editor.

#### Scenario: Editor changes a sourced number
- **WHEN** synthesis contains a factual number that does not match its referenced ledger entry
- **THEN** script audit rejects publication

#### Scenario: Editor attempts to reorder selected events
- **WHEN** `editor-output` includes section membership, ordering, score, status, or another script-owned field
- **THEN** strict schema or ownership validation rejects the output before the authoritative Brief is assembled

#### Scenario: Twelve compact Events are selected
- **WHEN** twelve Events survive selection but none is full-formatted
- **THEN** scripts allocate three compact slot kinds for each of all twelve Events, allocate no full-only kind, remain below the 61-editor-slot maximum, and do not drop the tenth through twelfth Events

#### Scenario: Editor source view is assembled out of order
- **WHEN** a per-kind source projection skips an earlier complete record that fits, includes a later record first, truncates a record, or reports incorrect included/omitted counts
- **THEN** projection validation fails `editor_input_capacity` before any editor request rather than accepting an implementation-selected summary

### Requirement: Deterministic claim audit
Before publication, scripts SHALL validate the complete unique claim inventory and rendered claim-to-slot mapping, deterministic event-label templates and their fact/evidence references, `zh-CN` minimum, Unicode/control/Markdown/HTML escaping, schemas, the input Feed's embedded owning-provider runtime-contract `source_link_hosts` membership for every canonical HTTPS source URL without network dereference or current-manifest substitution, evidence and ledger references, numeric provenance, Feed freshness, price-in support, direct-flow ownership, section constraints, and prohibited trading instructions; every claim-bearing assertion SHALL map to exactly one known `claim_id`, and any invalid candidate artifact SHALL be blocked and SHALL NOT be silently edited in place.

#### Scenario: Confirmed flow lacks direct evidence
- **WHEN** a Brief claims confirmed Money Flow without a referenced Flow or Positioning item
- **THEN** publication is blocked

#### Scenario: Source URL is absent
- **WHEN** a factual claim references evidence without a valid source URL
- **THEN** publication of that artifact is blocked; any corrected artifact must be regenerated and pass the full validation and audit sequence

#### Scenario: Source URL does not belong to its provider
- **WHEN** referenced evidence carries an HTTPS URL whose canonical host, port, or query is outside the input Feed's embedded owning-provider runtime-contract `source_link_hosts` rules, even when a different current local manifest would allow it
- **THEN** Feed/Brief validation blocks it without dereferencing the URL, even when the domain name resembles a trusted source

### Requirement: LLM language audit
The final language audit SHALL inspect the complete ordered claim inventory and the design-defined deterministic audit projection containing every rendered heading/label/warning/claim in exact order while replacing already script-validated URL targets with request-local aliases. The projection SHALL be at most 72 KiB and SHALL preserve the claim-to-render mapping; equality passes and one byte over fails before the call without truncation. URL validity and exact full-Markdown bytes remain script-audit responsibilities. The language audit SHALL check causal overclaim, inference presented as fact, unsupported conclusions, wrong output language, attempted fact modification, trading instructions, inappropriate certainty, and missing uncertainty language, SHALL return only a closed `language-audit-output.schema.json` covering exactly the 0..74 filled claim IDs with at most 32 findings referencing existing claim IDs/evidence and one at-most-192-byte rationale, and SHALL NOT modify factual values, claim classes, or evidence; missing, duplicate, or unknown claim coverage SHALL fail semantic validation, while scripts SHALL merge findings into the authoritative audit object, treat `wrong_language` as critical, apply the other versioned severity mappings, and own the publication decision.

#### Scenario: Concurrent move is written as caused by an event
- **WHEN** final wording asserts direct causality but attribution is only `concurrent`
- **THEN** the audit reports a critical causal-overclaim finding and normal publication is blocked

### Requirement: Investment-assistance safety boundary
The final Brief and deterministic degraded report SHALL provide financial intelligence and uncertainty but SHALL NOT output direct Chinese or English buy, sell, add/reduce, position sizing, entry, exit, stop, target-price, or equivalent trading instructions in structured or rendered fields.

#### Scenario: Trading instruction appears anywhere
- **WHEN** structured or rendered output contains a prohibited trading instruction
- **THEN** validation blocks publication

#### Scenario: Descriptive word is not an instruction
- **WHEN** a fixture contains a permitted historical or descriptive use of a safety-lexicon word without an imperative recommendation
- **THEN** the context-aware rule and audit fixture do not create a false publication failure

### Requirement: Visible degraded and stale state
Any stale Feed, missing critical dashboard data, source conflict, partial provider coverage, or unresolved event SHALL remain visible in the applicable normal Brief or deterministic degraded report rather than being hidden by editorial synthesis.

#### Scenario: Feed is degraded
- **WHEN** the consumed Feed has `pipeline.status = degraded`
- **THEN** the applicable normal Brief or deterministic degraded report includes a concise coverage warning derived from the Feed warnings

### Requirement: Brief CLI and replay outcomes
The `follow-the-money brief` command SHALL publish a normal artifact only after every required pass and audit succeeds and the atomic create-only run bundle is finalized, SHALL treat the bundle-contained Markdown as authoritative and emit identical bytes to an explicit output/stdout only after that commit, SHALL require explicit `--degraded-report` selection for the separate deterministic mode, and SHALL use exit `0/1/2` under the design-wide success/runtime-or-integrity/usage-or-configuration contract. A bundle-producing attempt SHALL begin only after successful CLI/config/output-root/input-Feed startup validation, effective-config redaction, and attempt-ID allocation. Before that boundary, usage/config/credential/output-root-capability rejection SHALL be `startup_rejection` exit 2, while input Feed schema/digest/reference/domain/integrity rejection SHALL be `pre_attempt_domain_failure` exit 1; neither promises a bundle. Subsequent failures preserve a redacted failed bundle when storage remains available. The successful-generation SLA SHALL use the design's 300-second pre-commit deadline and exact 15-second reserve: reversible work/staging `fsync` finishes by second 285, after which an admitted rename/parent-`fsync` completes non-cancellably and MAY report `commit_elapsed_overrun` only in external command status; immutable bundle members retain their pre-commit generation status. Failure-record bundle finalization and post-commit delivery are outside that success SLA. The `replay` command SHALL accept only an explicit valid run bundle, enforce the recorded application build/schema fingerprints and integrity closure, inject recorded run clocks/mode rather than the current wall clock, perform no network or LLM call, compare every deterministic saved artifact, and use the same exit-code contract.

#### Scenario: Normal Brief succeeds
- **WHEN** every required stage and audit succeeds
- **THEN** the command exits zero and emits the fully audited normal Brief plus its run bundle

#### Scenario: Required normal stage fails
- **WHEN** resolver, all attempted analyst calls, editor, language audit, schema, reference, or critical audit processing fails under its normal-mode blocking rule
- **THEN** the command exits non-zero and publishes no normal Brief

#### Scenario: Bundle finalization fails
- **WHEN** all content audits pass but the create-only run bundle cannot be atomically finalized
- **THEN** the command exits non-zero and writes no Brief or degraded-report bytes to the requested output or stdout

#### Scenario: Admitted bundle commit outlasts the nominal deadline
- **WHEN** complete staged member bytes and staging `fsync` pass the second-285 admission check but directory rename or parent `fsync` returns after second 300
- **THEN** the command does not cancel or retroactively deny the transaction; it reports `commit_elapsed_overrun` or the applicable durability failure only outside the immutable bundle, leaves bundle bytes unchanged, and performs delivery only after durable success

#### Scenario: Convenience delivery fails after commit
- **WHEN** the authoritative bundle commits but copying its artifact to the requested output or stdout fails
- **THEN** the command exits non-zero, reports the committed bundle path on stderr, and neither deletes nor overwrites the authoritative bundle

### Requirement: Separate deterministic degraded report
When `--degraded-report` is explicitly requested because a required LLM pass cannot run, the system SHALL emit a separately typed `deterministic_degraded_report` containing only Feed health, dashboard facts, deterministic analytics, unresolved counts, cutoff/provenance, and warnings; it SHALL omit event interpretation, causal attribution, price-in, asset implications, Bottom Line conclusions, and other LLM-owned fields. Its headings/labels/warnings SHALL use closed script-owned `zh-CN` templates, every retained untrusted provider/source label SHALL use the same NFC/one-line whitespace, `Cc`/`Cf`/`Cs`/`Zl`/`Zp`, CommonMark/HTML text-node escaping and instruction controls as normal rendering, and every link SHALL be renderer-owned and revalidated from the input Feed's embedded owning-provider runtime contract. It SHALL pass the same applicable schema, reference, URL, numeric, Unicode/rendering, deterministic-language-template, and instruction audits without invoking an editor or language-audit LLM.

#### Scenario: LLM credential is absent and degraded mode is requested
- **WHEN** validated Feed and deterministic analytics exist but no LLM credential is configured
- **THEN** the command may successfully emit the audited separate degraded report and never label it a normal Morning Money Brief

#### Scenario: Degraded source label contains active markup
- **WHEN** a provider warning or source label contains English-only injected prose, Markdown/HTML/link syntax, bidi/zero-width controls, or a prohibited instruction
- **THEN** the deterministic degraded path applies the same template, text-node, embedded-provider-URL, and instruction gates and blocks or safely escapes it according to the normal renderer contract

#### Scenario: LLM credential is absent in normal mode
- **WHEN** full Brief generation is requested without the required LLM runtime
- **THEN** the command exits with failure and publishes no normal Brief

### Requirement: Replayable run audit bundle
Every Brief or degraded-report attempt SHALL use unpredictable same-parent/same-device private staging and atomically write a durable create-only local `runs/<brief_run_id>/` bundle under a run-root lock using create-only member writes, file/staging-directory `fsync`, a platform atomic no-replace directory rename, and parent-directory `fsync`; unavailable primitives SHALL fail startup capability validation. Failure before rename SHALL expose no final bundle/output bytes. Rename success followed by parent-`fsync` failure SHALL return `commit_durability_unknown`, leave and report the final-path candidate without convenience delivery, overwrite, rollback, or durable-publication claim, and require later full integrity inspection/recovery. The terminal manifest SHALL contain a closed ordered path/size/SHA-256 index for every other regular member and its canonical `bundle_digest` SHALL omit its own field and `brief_run_id`; the distinct directory ID SHALL derive from that digest plus the input Feed run ID, generation instant, mode, mandatory non-Git-capable application-build/configuration/prompt fingerprints, and an injected collision-resistant attempt ID. No indexed member SHALL contain `brief_run_id` or `bundle_digest`; those values SHALL exist only in the terminal manifest, directory name, and post-commit external status, while members use the independent attempt ID and Feed ID. The bundle SHALL include exact canonical validated `input/feed.json`, a canonical fully resolved redacted non-secret effective-config snapshot, Feed/producer digest and run ID, package version, closed production-code/lockfile build fingerprint, optional Git metadata, schema/config/prompt/model fingerprints, frozen ledger, verified packets, validated structured LLM outcomes, claim inventory, analytics and selection traces, rendered output, audit findings, and indexed `generation_status`; a success candidate status SHALL be exactly `ready_for_commit`, SHALL NOT preclaim durability/delivery, and SHALL remain byte-identical after commit. Commit/delivery outcomes SHALL exist only in post-transaction external machine-readable status/logging. Feed/config fingerprints and all evidence roots SHALL recompute from saved members; build/schema/Feed/config mismatch, unlisted files, unsafe paths, symlinks, member/manifest/digest/ID mismatch, an indexed-member forbidden ID, or an ID collision SHALL fail without overwrite, and only rename plus successful parent `fsync` SHALL be the publication point. Normal daily execution SHALL NOT consume prior bundles.

#### Scenario: Published claim is traced
- **WHEN** an auditor follows a final factual claim reference
- **THEN** the bundle resolves it through the frozen ledger to an evidence ID and the exact input Feed digest

#### Scenario: Saved bundle is tampered with
- **WHEN** a member is changed, added, removed, renamed, or replaced, a manifest field/index is changed, or a digest, directory ID, or cross-reference no longer recomputes
- **THEN** replay fails closed before using any saved LLM outcome or producing a result

#### Scenario: Live model output is replayed
- **WHEN** a valid saved bundle is supplied to the replay command
- **THEN** replay validates the exact saved Feed and effective configuration, injects the recorded generation/completion clocks, attempt ID and mode, re-runs the full deterministic path from Feed validation using saved structured responses without network or model calls, and requires every saved deterministic object and rendered byte to match

#### Scenario: Application build differs
- **WHEN** current package/runtime-file or lockfile fingerprint differs from the bundle manifest even when no Git SHA exists
- **THEN** replay exits with runtime/integrity failure and does not claim reproduction under different deterministic code

#### Scenario: Same-clock attempts run concurrently
- **WHEN** two Brief attempts use the same Feed, injected generation instant, mode, and fingerprints
- **THEN** their injected attempt IDs create distinct bundles and neither attempt can overwrite the other
