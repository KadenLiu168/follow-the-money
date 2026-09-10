## REMOVED Requirements

### Requirement: Internal deterministic contracts and wiring status
**Reason**: The retained research-engine layer is removed so the repository contains only Feed behavior.
**Migration**: No post-Feed research library or caller is retained.

### Requirement: Immutable evidence ledger
**Reason**: Ledger structures exist only for removed Event/research processing.
**Migration**: Feed item provenance and identity remain the evidence record; no Ledger API replaces them.

### Requirement: Deterministic entity resolution and candidate grouping
**Reason**: Candidate Event preparation is outside the information-digest Feed boundary.
**Migration**: Host-Agent editorial grouping remains evidence-preserving presentation and does not use a repository candidate engine.

### Requirement: Canonical Event and family utilities
**Reason**: Event, family, coexistence, and display-label construction are removed.
**Migration**: Feed evidence IDs remain stable; no Event identity replacement is introduced.

### Requirement: Deterministic market snapshot
**Reason**: Raw market-data collection and post-Feed market analytics are removed.
**Migration**: The five-domain Feed contains no market snapshot.

### Requirement: Deterministic breadth, surprise, and Market State
**Reason**: These calculations produce analytical classifications outside the evidence-only product.
**Migration**: The digest SHALL NOT reconstruct regime, anomaly, surprise-vote, or market-state conclusions.

### Requirement: Deterministic confidence and watchlist rules
**Reason**: Source-tier confidence conversion and priority-bounded watchlist selection are outside the current digest contract.
**Migration**: Feed provenance/freshness remains explicit and digest compression remains transparent without confidence or watchlist ranking.

### Requirement: Versioned deterministic scoring
**Reason**: Significance, relevance, and priority scoring are removed as obsolete financial-judgment machinery.
**Migration**: Host-Agent presentation SHALL NOT claim a deterministic score or importance result.

### Requirement: Deterministic ranking and family penalty
**Reason**: Event ranking and family penalties conflict with the unranked evidence-digest boundary.
**Migration**: Digest ordering remains a disclosed presentation choice and no ranking API replaces this library.

### Requirement: Deterministic safety audit with bounded invocation
**Reason**: Deterministic Audit and its only approved invocation boundary are removed under the Feed-only decision.
**Migration**: Feed validation continues to reject analytical fields, and the Host Agent remains prohibited from adding investment or trading judgment to the digest.
