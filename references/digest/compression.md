# Digest Compression Contract

These rules apply once to all five Feed domains. Compression is editorial
presentation owned by the Host Agent over the prepared `DigestContext` and its
current validated Feed evidence; it is not a deterministic Feed result.

## Per-Domain Accounting

For each domain, reconcile every item using exactly one representation category:

```text
domain total = individually summarized + represented through consolidation + omitted
```

Report the domain total and all three category counts, including zero counts.
The category counts must reconcile exactly to the number of validated items in
that domain. An item represented in a consolidated summary is counted in the
consolidated category even when the body contains one paragraph or heading for
several items.

## Consolidation Traceability

A consolidated summary must preserve traceability to every supporting item. Use
the supporting Feed item IDs and enough source attribution to let a reader
identify all evidence behind the consolidation. Do not merge an item into a
summary whose factual content is not supported by that item. Consolidation may
remove repetition, but it may not create a new fact, causal link, sentiment,
direction, or market interpretation.

## Omission Disclosure

An item absent from the Digest body is counted as omitted and the Digest
discloses the omission as editorial compression. Do not describe omitted items
as unimportant or irrelevant, and do not use importance or relevance as an
omission rationale. The accounting is a coverage and presentation limitation,
not a ranking.

The same rules apply when a domain is empty: its total and zero
representation counts remain visible. Do not use a historical Feed,
checkpoint, external source, or `raw_metadata` to fill a compressed or omitted
item.
