## ADDED Requirements

### Requirement: Digest presentation is content-first while remaining auditable
The Digest presentation SHALL make presentable current-window Feed updates its
primary substantive surface while preserving all required status, evidence cutoff,
coverage, Provider and source availability, provenance, freshness, warnings,
degraded-state, compression-reconciliation, and limitation information as an
auditable secondary surface. Content-first is a semantic priority and MUST NOT
prescribe fixed headings, heading levels, section order, visual style, importance,
ranking, significance, analysis, or a relevance filter. Provenance or attribution
needed to support a factual statement, source-authored analysis, or consolidated
summary SHALL remain sufficiently close to the supported content; global Provider,
coverage, and reconciliation metadata MAY remain in the secondary audit surface.

#### Scenario: Healthy Feed has presentable current updates
- **WHEN** the Host Agent presents a healthy valid Feed with one or more presentable current-window updates
- **THEN** those updates are the primary substantive reading surface and the complete required audit information remains visible as secondary context rather than preceding the content as an audit report

#### Scenario: Degraded but usable Feed needs a material caveat
- **WHEN** a valid usable Feed has degradation or a source limitation that materially affects interpretation of the current-window content
- **THEN** the Host Agent may place a concise data-limitation caveat before the affected content without presenting the Feed as healthy, and SHALL still preserve the complete status, coverage, freshness, warning, availability, and limitation information in the secondary audit surface

#### Scenario: Valid Feed has no presentable current updates
- **WHEN** the Host Agent presents a valid Feed with zero presentable current-window updates
- **THEN** the primary message accurately states that the current Feed window has no presentable updates, creates no content, and is followed by auditable status, evidence cutoff, coverage, Provider or source availability, and applicable limitations that distinguish an empty window from collection or Provider problems

#### Scenario: Content is compressed
- **WHEN** current-window items are individually summarized, represented through consolidation, or omitted for editorial compression
- **THEN** content-first presentation preserves exact per-domain reconciliation, traceability to every item supporting a consolidation, and omission disclosure without using importance or relevance as the presentation or omission rationale

#### Scenario: Local provenance supports presented content
- **WHEN** provenance or source attribution is necessary to support a factual statement, source-authored analysis, or consolidated summary
- **THEN** that provenance or attribution remains sufficiently close to the supported content and is not moved exclusively into global audit metadata

#### Scenario: Retrieval validation or preparation fails
- **WHEN** current Feed retrieval, validation, or deterministic preparation fails
- **THEN** the existing fail-closed behavior produces no normal Digest and content-first presentation does not alter or bypass the failure path
