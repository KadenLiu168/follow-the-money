## Context

Two NDJSON stores (`feed-13dg/<year>.ndjson`, `state-13dg.ndjson`) are currently written by reading the entire file, concatenating one line, and rewriting the whole file. This is correct but O(n²) under repeated appends. The readers also `catch { /* skip corrupt line */ }` with no counter, and the year is derived from `filingDate` without validation, so a bad date yields a `NaN.ndjson` that the manifest ignores.

## Goals / Non-Goals

**Goals:**
- Make every append O(1) (append a single line).
- Count and surface skipped corrupt lines.
- Reject/quarantine invalid `filingDate` instead of emitting a NaN year file.

**Non-Goals:**
- Changing the NDJSON line schema or manifest shape.
- Sharding files by month (future optimization, not in scope).

## Decisions

- **Append mode over rewrite.** Use `fs.appendFileSync` (or open fd once and write) to add a single line. Rationale: O(1) per append vs O(filesize). Alternative (in-memory accumulation + periodic flush) rejected: complicates crash semantics and the existing atomic tmp+rename is preserved per write.
- **Keep atomic tmp+rename per append.** Each append still writes to `${file}.${pid}.${Date.now()}.tmp` then renames, preserving crash safety. (pid+Date.now suffix already present.)
- **Corrupt-line counter surfaced via return value + `validateManifest` diagnostics.** Readers return `{ entries, skipped }`; `prepare-digest` includes `skipped` in its diagnostics.
- **Validate `filingDate` with `^\d{4}-\d{2}-\d{2}$` before computing year.** Invalid entries are `console.warn`-ed and skipped (not written), never producing a NaN file.

## Risks / Trade-offs

- [Risk] Append without full rewrite loses the "re-serialize whole file" normalization. → Mitigation: lines are already JSON; append preserves format; `validateManifest` still reconciles counts.
- [Risk] `console.warn` for invalid dates could spam in bulk. → Mitigation: warn once per distinct bad entry; consider a quarantine file if needed (out of scope).
