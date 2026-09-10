## REMOVED Requirements

### Requirement: Runtime classifies stdin as a request before dispatch
**Reason**: The private Agent invocation runtime is outside the Feed-only product boundary.
**Migration**: No replacement invocation exists; consumers use the published Feed through the normal Skill path.

### Requirement: Invocation uses a private local one-shot JSON process boundary
**Reason**: The repository no longer exposes independent Agent-callable operations.
**Migration**: Remove callers of the private process boundary.

### Requirement: Requests use one closed versioned envelope
**Reason**: The Agent request envelope is removed with the invocation capability.
**Migration**: No version-1 request is accepted after this breaking change.

### Requirement: Operation addressing is static and contract-governed
**Reason**: `audit.text`, `audit.claims`, and `event.structure` are removed.
**Migration**: Consume the Feed; no replacement operation registry is introduced.

### Requirement: Audit text input is minimal and closed
**Reason**: Deterministic Audit is removed.
**Migration**: Host-Agent output remains governed by the information-digest evidence and judgment boundaries.

### Requirement: Structured Audit input promotes only necessary Agent-facing values
**Reason**: Deterministic Audit and its Agent DTO are removed.
**Migration**: No structured Audit request is supported.

### Requirement: Successful responses carry bounded Audit and Event results
**Reason**: Audit/Event invocation responses are removed.
**Migration**: No response replacement is provided.

### Requirement: Invocation errors are typed and separate from capability results
**Reason**: The invocation process and its error contract are removed.
**Migration**: Feed production and consumption retain their own typed failures.

### Requirement: One major version governs the Agent-facing boundary
**Reason**: The Agent-facing boundary is deleted rather than versioned forward.
**Migration**: Version 1 has no compatibility successor.

### Requirement: Invocation preserves ownership provenance and bounded authority
**Reason**: No non-Feed invocation crosses the Skill-Agent boundary.
**Migration**: Feed provenance and Host-Agent ownership remain governed by Feed-only contracts.

### Requirement: Phase 5 activation decisions change status only after verified callers
**Reason**: The activation matrix and non-Feed capability catalog are removed.
**Migration**: Evidence Feed is the sole live repository capability.

### Requirement: Common invocation contract does not prescribe a research pipeline
**Reason**: There is no common invocation contract after this change.
**Migration**: The normal Skill path remains published Feed to Host Agent without repository orchestration.

### Requirement: Event Structuring input is minimal closed and structured
**Reason**: Event Structuring is removed.
**Migration**: No Agent-facing Event DTO is retained.

### Requirement: Event Structuring derives identities and enforces provenance consistency
**Reason**: Canonical Event construction is outside the Feed-only product.
**Migration**: Feed item identity and provenance remain unchanged; Event identity has no replacement.

### Requirement: Event Structuring uses invocation-local deterministic state only
**Reason**: Event Structuring and invocation-local Ledger state are removed.
**Migration**: No stateful or stateless Event operation remains.

### Requirement: Event Structuring result is closed canonical and bounded
**Reason**: Event results are removed from the repository surface.
**Migration**: Consumers receive only the validated published Feed.
