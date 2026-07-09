## Context

SEC 13F filings expose the cover page and the information table as separate files. `fetchThirteenFXml` currently ranks `.xml` files by byte size and takes the largest, assuming the cover page is always smaller. That assumption is not contractually guaranteed and has produced empty holdings when the cover page dominates. The fallback to `primaryDocument` (a cover page) is actively wrong as a holdings source.

## Goals / Non-Goals

**Goals:**
- Select the infoTable by canonical filename `form13fInfoTable.xml` whenever present.
- Keep a heuristic fallback only when the canonical name is absent.
- Fail loudly on empty holdings.

**Non-Goals:**
- Parsing multiple infoTable splits (not observed in practice).
- Caching EDGAR responses (handled elsewhere).

## Decisions

- **Canonical-name-first selection.** In `index.json`, look for an item whose `name` matches `form13fInfoTable.xml` (case-insensitive) and use it directly. Rationale: deterministic, matches SEC's published filename; removes reliance on size ordering.
- **Heuristic fallback only when canonical name absent.** If no `form13fInfoTable.xml` exists, fall back to the largest `.xml` (rare/older filings). Rationale: preserves current behavior for edge cases without making it the primary path.
- **Never use `primaryDocument` as holdings.** Remove it from the fallback chain; if both canonical and heuristic fail, throw.
- **Empty-holdings sanity check in `parseThirteenF`.** If parsed `holdings` is empty, throw a descriptive error so `pipeline-a`/`pipeline-b` can surface it.

## Risks / Trade-offs

- [Risk] Some very old filings may name the infoTable differently. → Mitigation: heuristic fallback covers them; if both fail, the error is explicit and logged rather than silent.
- [Risk] Throwing on empty holdings could abort a pipeline run. → Mitigation: callers catch and skip that filing with a warning, per existing error handling.
