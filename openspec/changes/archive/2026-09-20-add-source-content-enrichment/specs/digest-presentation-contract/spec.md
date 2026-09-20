## ADDED Requirements

### Requirement: Bounded official source content supports evidence-preserving summaries

The news, macro-release, and policy domain contracts SHALL list `payload.source_content.text`, `payload.source_content.format`, and `payload.source_content.truncated` as closed supporting evidence for current units. The Host Agent MAY summarize factual statements and source-authored analysis explicitly present in that text, subject to the existing attribution, authority, claim support, compression, and forbidden-interpretation rules. It SHALL NOT claim that bounded source content is a complete document when `truncated = true`, expose extraction method or document hash, access the source URL, or treat source wording as a Feed, Skill, or Host-Agent conclusion.

#### Scenario: Official text supports a concise summary

- **WHEN** a current unit contains bounded official source text supporting factual statements
- **THEN** the Host Agent may produce a concise attributed summary whose claims remain supported and traceable to that unit and its Feed item

#### Scenario: Official source text contains analysis

- **WHEN** whitelisted official source content itself contains analytical, causal, predictive, or policy-purpose wording
- **THEN** the Host Agent may summarize it only with clear source attribution and without adopting or upgrading that wording as its own conclusion

#### Scenario: Source content is truncated

- **WHEN** a current unit carries `source_content.truncated = true`
- **THEN** the Host Agent does not characterize the bounded text as the complete official document or infer facts from omitted content

#### Scenario: Extraction provenance exists only in the Feed

- **WHEN** the validated Feed contains an extraction method and document digest but DigestContext excludes them
- **THEN** presentation neither reconstructs nor prints those Feed-only provenance values

## MODIFIED Requirements

### Requirement: Missing evidence remains missing

Domain presentation contracts and deterministic preparation SHALL preserve null values, explicit unavailability, and absent or legacy-omitted fields as missing evidence. Whitelisted `source_content.text` MAY directly support attributed factual statements, but preparation and presentation MUST NOT use it, titles, `raw_metadata`, another item, a historical Feed or checkpoint, external knowledge, or an unstated calculation to reconstruct an absent structured semantic field or claim that omitted source content is known.

#### Scenario: Legacy semantic context is absent

- **WHEN** a valid legacy `news`, `macro_release`, or `policy` item omits `semantic_context` but may contain other eligible evidence
- **THEN** preparation and presentation use only eligible evidence actually present and do not reconstruct semantic context from source content, title, or another field

#### Scenario: Optional evidence is null or unavailable

- **WHEN** a whitelisted field is null or explicitly unavailable
- **THEN** `DigestContext` preserves that state and the Digest preserves or accurately discloses the limitation instead of inventing a value or interpretation

