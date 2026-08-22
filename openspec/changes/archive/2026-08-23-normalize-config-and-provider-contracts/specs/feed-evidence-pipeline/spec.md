## ADDED Requirements

### Requirement: Single authoritative production configuration
Production configuration SHALL assign exactly one authoritative checked-in source to each normative field: application and deterministic-domain runtime fields to `config/config.yaml`, Provider-specific contract facts to the owning Provider manifest, and Provider activation plus coverage policy to `config/providers.yaml`. Static startup resolution SHALL require, parse, validate, and explicitly materialize every normative field from its authority without silently substituting a Python or loader default. A duplicated field retained for compatibility SHALL be validation-only, SHALL match its authority, and SHALL NOT independently affect runtime behavior. Coverage membership SHALL derive only from the coverage matrix and SHALL support one Provider belonging to multiple coverage groups without a Provider-level single-group authority.

#### Scenario: YAML-owned value changes
- **WHEN** a valid representative application, Feed, scoring, Market State, calendar, safety, rate-registry, or other YAML-owned runtime value changes
- **THEN** the resolved runtime configuration reflects that declared value without requiring a Python-code change

#### Scenario: Required normative value is missing
- **WHEN** a required normative field is absent from its authoritative checked-in source
- **THEN** static startup fails through the existing configuration/startup failure category instead of using a language-level or loader fallback

#### Scenario: Compatibility mirror disagrees
- **WHEN** a retained duplicate declaration differs from its authoritative field
- **THEN** static startup fails closed and neither declaration independently controls runtime behavior

#### Scenario: Provider belongs to multiple coverage groups
- **WHEN** the coverage matrix lists one Provider in more than one row
- **THEN** coverage assessment uses every declared matrix membership and ignores any Provider-level single-group value as coverage authority

#### Scenario: Static resolution fails before runtime mutation
- **WHEN** configuration, manifest, version, identity, verification, or cross-source reference validation fails
- **THEN** the Feed makes zero Provider network requests, performs no normal collection work, does not create or mutate rate-registry state, and does not publish or replace a dated or latest Feed

## MODIFIED Requirements

### Requirement: Credential-free verified provider contracts
The Feed SHALL resolve every enabled Provider by strictly composing activation and coverage policy with that Provider's supported checked-in verified manifest before normal execution. The manifest SHALL be authoritative for Provider identity and contract version, verification and evidence metadata, authentication and protocol requirements, fetch and redirect hosts, evidence source-link rules, charset and content-type rules, request and response limits, rate policy, pagination, empty-window semantics, Provider-specific runtime behavior, mapping declarations already present in the manifest, and fixture provenance. The resulting single resolved Provider contract SHALL drive adapter construction and behavior, rate handling, empty-window decisions, host-concurrency planning, enablement, coverage assessment, and the embedded Feed `provider_contracts` snapshot; runtime consumers SHALL NOT re-read or independently reinterpret a second Provider contract after resolution. The shipped core Provider set SHALL require no paid financial-data key, and every accepted evidence URL SHALL be HTTPS, credential-free, canonicalized once under its owning resolved host/path/query policy, and validated before identity or publication.

#### Scenario: Default providers run without credentials
- **WHEN** the minimal Feed entry loads the shipped default configuration without any paid financial-data credential
- **THEN** it can initialize and attempt every enabled verified free Provider without reading an API key

#### Scenario: Enabled Provider contract cannot be resolved
- **WHEN** an enabled Provider manifest is missing, invalid, has an unsupported contract version or mismatched Provider identity, or fails the required verification contract
- **THEN** static startup fails closed before that or any other Provider request and before normal persistent Feed runtime mutation

#### Scenario: Provider contract is incomplete
- **WHEN** an enabled Provider manifest omits a required contract fact or an adapter emits evidence outside its resolved source-link policy
- **THEN** configuration or item validation fails closed before the Provider or item can count toward Feed coverage

#### Scenario: Manifest-owned runtime value changes
- **WHEN** a valid authoritative manifest-owned runtime value changes for an enabled Provider
- **THEN** the resolved adapter behavior and corresponding embedded Provider contract snapshot both reflect that same value without an independent matching runtime definition elsewhere

#### Scenario: Provider is disabled
- **WHEN** registry policy marks a Provider disabled
- **THEN** collection neither initializes nor contacts that Provider even when its manifest is otherwise valid and verified
