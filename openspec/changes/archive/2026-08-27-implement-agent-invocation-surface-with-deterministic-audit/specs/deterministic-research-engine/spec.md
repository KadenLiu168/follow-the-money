## MODIFIED Requirements

### Requirement: Deterministic safety audit with bounded invocation
The deterministic safety audit SHALL expose workflow-neutral internal Python boundaries for text safety auditing and structured claim auditing. Text safety auditing SHALL accept submitted text without requiring a claim inventory, presentation section, Brief, Editor, or Agent object, SHALL associate a claim identity with a finding only when one is supplied, and SHALL apply the existing configured Chinese and English prohibited trading-instruction terms and descriptive exceptions without changing their matching semantics.

Structured claim auditing SHALL accept only the information required by its retained rules: required claim identities, claim text, whether each claim requires direct evidence references, supplied evidence references, independently supplied submitted/rendered claim identities, and confirmed-flow ownership information. It SHALL reject an empty required inventory, duplicate identities, missing or invalid required identities, submitted/rendered identities outside the inventory, evidence-required claims without evidence references, and confirmed flows without an owning Event. Evidence policy SHALL be expressed as an explicit per-claim obligation and SHALL NOT depend on dashboard, Editor, Brief, full, compact, watchlist, bottom-line, money-flow-section, or other presentation/workflow classifications.

All violations SHALL be reported deterministically through the existing audit result and finding model, critical findings SHALL fail the submitted candidate, and the auditor SHALL NOT silently rewrite rejected text. The Audit implementation boundary SHALL remain an internal typed library contract with no LLM/model/credential dependency, Feed caller, caller-controlled policy, or requirement to serialize its Python structures directly. The private `agent-runtime-invocation-contract` boundary SHALL be its only approved production caller, SHALL explicitly map accepted Agent-facing values to and from these internal semantics, and SHALL NOT alter finding content, severity, category, order, or pass state.

#### Scenario: Trading instruction is submitted
- **WHEN** standalone submitted text contains a configured Chinese trading instruction without a configured descriptive exception
- **THEN** the audit produces a critical `trading_instruction` finding and fails without requiring a structured claim or workflow object

#### Scenario: English trading instruction is submitted as text
- **WHEN** standalone submitted text contains a configured English trading instruction without a configured descriptive exception
- **THEN** the audit produces a critical `trading_instruction` finding and fails without requiring a structured claim or workflow object

#### Scenario: Descriptive text matches an exception
- **WHEN** standalone submitted text contains a configured descriptive exception
- **THEN** the existing exception semantics remain accepted and the auditor does not rewrite the text

#### Scenario: Optional text claim identity is available
- **WHEN** standalone submitted text fails the trading-instruction rule and the caller supplied a claim identity
- **THEN** the resulting finding carries that identity without requiring any other claim, Brief, Editor, or Agent state

#### Scenario: Text audit is repeated
- **WHEN** the same text, optional identity, and Skill-owned `SafetyLexicon` are audited repeatedly
- **THEN** the complete audit result is identical and no LLM, model, credential, network, mutable workflow state, or caller-controlled policy is consulted

#### Scenario: Structured inventory is empty
- **WHEN** structured claim auditing receives an empty required claim inventory
- **THEN** the audit fails with the existing `empty_inventory` semantics

#### Scenario: Structured claim identity is missing or invalid
- **WHEN** a structured inventory or submitted/rendered assertion lacks a required non-empty string claim identity
- **THEN** the audit fails deterministically through audit-result semantics rather than allowing an incidental mapping-access or type error to escape

#### Scenario: Structured claim identities are duplicated
- **WHEN** more than one structured inventory claim has the same valid identity
- **THEN** the audit fails with the existing `duplicate_claim_id` semantics

#### Scenario: Submitted assertion is outside the inventory
- **WHEN** an independently supplied submitted/rendered claim identity is absent from the structured inventory
- **THEN** the audit fails with `outside_inventory` instead of deriving submitted membership from the inventory itself

#### Scenario: Factual claim lacks evidence
- **WHEN** a structured claim explicitly requires direct evidence references and supplies none
- **THEN** the audit fails with `missing_evidence` rather than inventing references or editing the claim

#### Scenario: Claim does not require direct evidence
- **WHEN** a structured claim explicitly does not require direct evidence references and supplies none
- **THEN** the absence of per-claim references does not itself create a finding and no presentation classification is consulted

#### Scenario: Confirmed flow has no owner
- **WHEN** structured audit input identifies a flow as confirmed but supplies no owning Event identity
- **THEN** the audit fails with the existing `flow_ownership` semantics

#### Scenario: Flow is not confirmed
- **WHEN** structured audit input identifies a flow as not confirmed and supplies no owning Event identity
- **THEN** the confirmed-flow ownership rule does not create a finding or promote the flow to confirmed

#### Scenario: Structured claim contains a trading instruction
- **WHEN** structured claim text contains a prohibited instruction under the configured lexicon and exception semantics
- **THEN** the same deterministic text safety rule produces a critical `trading_instruction` finding for that claim

#### Scenario: Auditor caller status is inspected
- **WHEN** the Audit module, Agent invocation boundary, Feed, legacy workflow paths, and unrelated capability modules are traced after ECO-50
- **THEN** internal Python structures remain internal, exactly the approved invocation adapter calls Audit, and Feed, Event, Market, Watchlist, Confidence, Scoring, Ranking, and legacy workflow modules do not call it

## RENAMED Requirements

- FROM: `### Requirement: Deterministic safety audit retained without orchestration`
- TO: `### Requirement: Deterministic safety audit with bounded invocation`
