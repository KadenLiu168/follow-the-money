## ADDED Requirements

### Requirement: Evidence-backed market mapping contract
Every Provider market-role mapping SHALL remain in the owning Provider's existing resolved `role_mappings` contract and SHALL bind one exact tuple of Provider identity, canonical role identity, Provider instrument, and unit. A mapping declared verified SHALL include one authoritative mapping-level verification-provenance declaration that is explicit, non-empty, auditable, and associated with that exact tuple. A mapping declared unverified SHALL include a non-empty deterministic reason and SHALL NOT be treated as runnable canonical market capability. No second market-mapping registry or independently authoritative mapping-provenance source SHALL be introduced.

Static resolution SHALL validate mapping provenance without making a network request solely for verification. A checked-in repository reference SHALL have valid repository-relative syntax, remain within the repository, exist, belong to the owning Provider contract, and identify the declared tuple through its mapping declaration; when a structured Yahoo chart fixture is used, its explicit `meta.symbol` SHALL equal the declared instrument. An authoritative HTTPS reference SHALL satisfy the owning Provider's declared verification host policy and SHALL be bound to the declared tuple. Arbitrary text or document content SHALL NOT be treated as deterministically proving financial semantics.

#### Scenario: Verified mapping has valid checked-in evidence
- **WHEN** a verified mapping declaration structurally binds its Provider, role, instrument, and unit tuple and its checked-in Provider-owned evidence exposes an explicit structured instrument identity matching the declared instrument
- **THEN** static resolution retains the mapping as verified and preserves its verification provenance in the resolved Provider contract

#### Scenario: Verified mapping omits provenance
- **WHEN** `mapping_verified` is true but mapping-level verification provenance is absent or empty
- **THEN** static resolution fails through the existing configuration/startup failure category

#### Scenario: Unverified mapping omits reason
- **WHEN** `mapping_verified` is false but the mapping has no non-empty explicit reason
- **THEN** static resolution fails through the existing configuration/startup failure category

#### Scenario: Repository evidence is unavailable or escapes its boundary
- **WHEN** verified mapping provenance names a missing path, an absolute path, a repository-escaping path, or evidence outside the owning Provider contract
- **THEN** static resolution rejects the mapping before normal Feed execution

#### Scenario: HTTPS verification reference violates Provider policy
- **WHEN** a verified mapping declares a malformed, non-HTTPS, credential-bearing, or disallowed-host verification reference
- **THEN** static resolution rejects the mapping without making a verification network request

#### Scenario: Verification evidence belongs to another tuple
- **WHEN** verification provenance is associated with another Provider, role, instrument, or unit
- **THEN** static resolution rejects the verified claim instead of transferring evidence between mappings

#### Scenario: Structured Yahoo symbol disagrees
- **WHEN** a checked-in Yahoo chart fixture is used as mapping evidence and its explicit `meta.symbol` differs from the declared instrument
- **THEN** static resolution rejects the verified claim

#### Scenario: Compatibility mapping declaration disagrees
- **WHEN** any retained canonical-role compatibility declaration differs from the manifest authority for instrument, unit, or `mapping_verified`
- **THEN** static resolution fails closed and the compatibility declaration does not independently control execution

### Requirement: Verified mappings gate canonical Feed identity
Production planning for an enabled market Provider SHALL create canonical market-role acquisition work only for mappings that passed the evidence-backed verification contract. An unverified mapping SHALL NOT emit a Feed item whose `market_data.instrument_id` asserts that canonical role identity, and SHALL NOT be made eligible by attaching an item-level unverified flag after acquisition. All mappings SHALL remain visible in deterministic order in the resolved Provider contract and corresponding Feed `provider_contracts` snapshot, including verification provenance for verified mappings and reasons for unverified mappings. The Feed schema SHALL remain unchanged.

#### Scenario: Production market adapters are planned
- **WHEN** an enabled market Provider has both verified and unverified resolved role mappings
- **THEN** production planning creates adapters only for the verified mappings in canonical role order

#### Scenario: Unverified mapping cannot emit canonical role evidence
- **WHEN** a role mapping remains unverified
- **THEN** no production adapter is planned for that mapping and no Feed item can enter through that path with its canonical `market_data.instrument_id`

#### Scenario: Provider contract snapshot is built
- **WHEN** the resolved Provider contract contains verified and unverified mappings
- **THEN** its deterministic snapshot exposes every mapping with the verified provenance or unverified reason required by its state

#### Scenario: Verification fails before runtime mutation
- **WHEN** any mapping verification, evidence-reference, tuple-association, or mapping-parity check fails during static resolution
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace a dated or latest Feed

### Requirement: Market coverage is bounded by verified runnable capability
Provider-level coverage policy SHALL claim no market capability broader than the enabled Provider's verified runnable mappings. Coverage SHALL NOT claim all configured roles, China/HK market support, or cross-asset completeness unless the verified runnable mappings establish that breadth. Unsupported claims SHALL be removed or narrowed within the existing Provider-level coverage model; no role-level coverage engine SHALL be introduced. An enabled market Provider with zero verified runnable mappings SHALL fail through the existing configuration/startup category unless registry policy explicitly disables it.

#### Scenario: Only a subset of market mappings is verified
- **WHEN** fewer than all configured market mappings are verified and runnable
- **THEN** coverage omits `market_data_all_13_roles` and any China/HK or cross-asset capability not supported by that verified subset

#### Scenario: Coverage claim exceeds runnable mappings
- **WHEN** a configured Provider-level market capability is not a subset of verified runnable mappings
- **THEN** static resolution rejects the unsupported coverage contract before Provider requests or runtime mutation

#### Scenario: Enabled market Provider has no verified mapping
- **WHEN** an enabled market Provider resolves with zero verified runnable mappings
- **THEN** startup fails through the existing configuration/startup category rather than reporting a healthy zero-work Provider outcome

#### Scenario: Market Provider is explicitly disabled
- **WHEN** registry policy disables a market Provider with zero verified runnable mappings
- **THEN** no adapter work is planned for that Provider and the disabled state is handled by the existing activation and coverage contracts
