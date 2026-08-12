---
name: follow-the-money
description: |
  Deterministic daily financial intelligence: evidence-only Feed from free
  China/US official and public sources, canonical events, constrained LLM
  analysis, and the fixed Chinese Morning Money Brief. Script-first, LLM-last.
  Triggers on "/money", on a schedule, or when the user asks for a morning
  money brief / fund flow digest / macro policy roundup.
---

# Follow the Money — Skill Orchestration Contract

This Skill is the orchestration layer over the local repository. It delegates
every network call and every deterministic step to the Python CLI under
`follow-the-money`; the Skill runtime stays a thin coordinator and never
re-implements pipeline logic.

## Investment-assistance boundary

Output the Brief exactly as rendered. It contains financial intelligence and
uncertainty but must **never** be rewritten to add buy, sell, add, reduce,
position-size, entry, exit, stop-loss, or target-price instructions. If a
step fails, surface the exact stderr and stop — do not silently substitute a
partial digest or invent events.

## Non-Go boundary (do not claim)

- This repository is **not** a Git checkout; there is no license, remote, or
  enabled workflow unless separately authorized.
- GitHub Actions does **not** invoke this Skill at 08:30. External scheduling
  is configured by the deployment environment after Feed publication.
- The Brief reflects one fixed evidence cutoff captured before provider
  requests; it never claims coverage through collection completion or a
  nominal 08:30 value.

## Pipeline

```text
follow-the-money feed          # evidence-only Feed, no LLM
  -> follow-the-money brief    # full Brief (requires one OpenAI credential)
     or follow-the-money brief --degraded-report   # deterministic, no LLM
  -> follow-the-money replay <bundle>              # audit/replay
  -> follow-the-money eval     # offline or credentialed live evaluation
```

## CLI exit-code contract

- `0` complete success
- `1` runtime/domain/schema/reference/integrity/deadline/publication/delivery failure
- `2` usage/config/missing credential/startup capability error

## Daily flow (scheduled or /money)

1. **Feed**: `uv run follow-the-money feed` (or `scripts/feed/follow-the-money-feed`).
   Exit 0 with healthy or degraded Feed; warnings are on stderr and in status.
   A Feed failure means no Brief should run.
2. **Brief**: `uv run follow-the-money brief --feed feeds/latest.json --output out.md`.
   Requires `OPENAI_API_KEY` + configured model. Without a credential, only
   `--degraded-report` may succeed. Delivery happens only after the atomic
   run bundle commits; the bundle-contained Markdown is authoritative.
3. **Output**: render the committed Markdown to the conversation. Never
   summarize away uncertainty or coverage warnings.
4. **Replay/audit**: `uv run follow-the-money replay runs/<brief_run_id>/` —
   offline, no network/LLM, fails on any drift or integrity mismatch.

If a required step fails, surface the exact stderr and stop. Partial output is
worse than no output.

## Credentials

Only one OpenAI credential is required, only for `brief` and live `eval`.
The Feed needs none. Provider secrets (if any) must be at least 8 UTF-8 bytes
and are never logged; source URLs are credential-free by validation.
