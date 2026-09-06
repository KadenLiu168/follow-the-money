## Context

See `proposal.md` for motivation. The remote consumer uses one streaming helper for the manifest and every artifact. Its current preflight compares HTTP `Content-Length` with the applicable decoded-byte limit, while the HTTP client transparently decodes `iter_bytes()`. Those values describe different representations when `Content-Encoding` is present. Exact artifact length, SHA-256, canonical JSON, generation, identity, and Feed semantics are already validated after retrieval.

## Goals / Non-Goals

**Goals:**

- Distinguish encoded wire length from transfer-decoded content length at the existing retrieval boundary.
- Preserve early rejection when `Content-Length` describes an identity-encoded body.
- Preserve streaming decoded-size enforcement and all final bundle validation.

**Non-Goals:**

- Adding retries, fallback sources, persistent caching, or Provider collection.
- Changing artifact serialization, manifest fields, Feed schemas, or size limits.
- Introducing a custom compression/decompression layer or dependency.

## Decisions

### 1. Treat manifest artifact size as decoded canonical bytes

The consumer will continue using the manifest `size_bytes` as the maximum and exact final length of bytes returned by the HTTP client's decoded byte iterator. This aligns the retrieval check with the bytes hashed, written to temporary storage, and parsed by bundle validation.

Alternative considered: redefine `size_bytes` as encoded wire size. Rejected because HTTP content encoding is negotiated transport metadata, can vary between requests, and is not part of the published canonical artifact identity.

### 2. Apply the `Content-Length` preflight only when it describes the identity representation

When `Content-Encoding` is absent or explicitly `identity`, `Content-Length` can be compared directly with the applicable content limit. For any non-identity content encoding, the consumer will not compare encoded `Content-Length` with the decoded limit; it will rely on the existing decoded streaming counter and exact post-read validation.

Alternative considered: force `Accept-Encoding: identity`. Rejected as the sole fix because intermediaries can still return encoded responses and the consumer should validate the representation it actually receives.

Alternative considered: add a guessed compression-overhead allowance. Rejected because no fixed allowance correctly models all valid encodings and it would create a second artifact-size rule.

### 3. Add one focused encoded-response regression

A deterministic HTTP mock will return a gzip-encoded canonical artifact with encoded `Content-Length` greater than its decoded manifest size. The test will prove successful complete Feed consumption and retain existing oversized decoded-response regressions.

## Risks / Trade-offs

- [An encoded response can have more wire bytes than the decoded artifact limit] -> Existing request timeout remains finite, while decoded streaming remains byte-bounded and prevents decompression expansion from bypassing the manifest limit; no encoded bytes are persisted or trusted.
- [Header handling could accidentally weaken identity-response preflight rejection] -> Retain the current oversized and invalid `Content-Length` tests and add explicit identity-encoding coverage if needed by the focused implementation test.

## Migration Plan

No data or schema migration is required. Deploy the consumer and regression together. Rollback is a code-only revert; published bundles remain unchanged and valid.
