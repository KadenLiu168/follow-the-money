## ADDED Requirements

### Requirement: Remote artifact size validation respects HTTP content encoding
The canonical-main Feed consumer SHALL interpret each manifest artifact `size_bytes` as the exact length of the transfer-decoded canonical artifact bytes presented to bundle validation. It SHALL NOT reject an otherwise valid artifact solely because an HTTP content-encoded representation has a wire `Content-Length` greater than `size_bytes`. The consumer SHALL retain bounded transfer decoding and SHALL reject decoded bytes that exceed `size_bytes`, decoded bytes whose final length differs from `size_bytes`, or bytes whose digest or bundle semantics do not match the validated manifest.

#### Scenario: Encoded representation is larger than the canonical artifact
- **WHEN** a required artifact is returned with HTTP content encoding, its encoded `Content-Length` exceeds the manifest `size_bytes`, and its decoded canonical bytes exactly match the declared size, digest, and bundle semantics
- **THEN** the consumer accepts that artifact as part of the complete valid bundle

#### Scenario: Decoded response exceeds the manifest size
- **WHEN** transfer decoding yields more bytes than the artifact's manifest `size_bytes`
- **THEN** retrieval stops at the bounded decoded-size check and the consumer exposes no logical Feed

#### Scenario: Decoded response has an invalid final size or digest
- **WHEN** transfer decoding completes but the decoded artifact length or digest differs from the validated manifest entry
- **THEN** the complete bundle is rejected without fallback or partial evidence output

#### Scenario: Identity-encoded response declares an oversized body
- **WHEN** a response without content encoding declares a `Content-Length` greater than the applicable retrieval limit
- **THEN** the consumer rejects it before accepting the response body
