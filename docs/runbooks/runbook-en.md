# Runbooks (English)

## Configuration

```bash
uv sync --frozen --all-groups
cp .env.example .env   # fill OPENAI_API_KEY / OPENAI_MODEL
```

The repository reads explicit `--config` / `--output-root` paths and never
reads `~/.follow-the-money/config.json` implicitly. Configured secrets must
contain at least 8 UTF-8 bytes and are never logged.

## Feed generation

```bash
# Dry run (no publication):
uv run follow-the-money feed --dry-run

# Real run with an explicit output root:
uv run follow-the-money feed --output-root feeds
```

Exit `0` for a healthy or degraded Feed (warnings on stderr/status), `1` for
generation/publication failure, `2` for usage/config. No financial-data or
LLM credential is required.

## Brief (full)

```bash
uv run follow-the-money brief \
  --feed feeds/latest.json \
  --output out.md \
  --status-file brief-status.json
```

Requires one OpenAI credential and a configured compatible model. Delivery
happens only after the atomic run bundle commits; the bundle-contained
Markdown is authoritative.

## Brief (deterministic degraded report)

```bash
uv run follow-the-money brief --degraded-report --feed feeds/latest.json --output degraded.md
```

Emitted only when explicitly requested; never labelled a normal Morning
Money Brief; no LLM required.

## Replay

```bash
uv run follow-the-money replay runs/<brief_run_id>/
```

Offline; no network/LLM. Exits `1` on any build/integrity/tamper/drift
mismatch.

## Tests

```bash
uv run pytest            # full credential-free suite
uv run follow-the-money eval   # golden-day dataset validation
```

## Evaluation

Offline: `uv run follow-the-money eval --mode offline` (default; invalid
fixtures or failed gates exit 1). Live (credentialed, opt-in): specify
`--mode live`, repetitions, and `--max-cost-usd`; requires the local price
table; `incomplete` exits 1.

## GitHub deployment

The scheduled Feed workflow (`generate-feed.yml`) is a template. Before
enabling:

1. Set `FOLLOW_THE_MONEY_FEED=true` (repository/environment variable).
2. Provision a dedicated self-hosted runner labelled
   `follow-the-money-feed`.
3. Mount a persistent shared output root shared by every invocation for the
   relevant provider scopes, containing the deployment persistence marker
   (`.follow-the-money-persistent`) and durable rate-state paths.
4. Grant `contents: write` and confirm branch policy (protected-branch
   rejection fails visibly; the output is uploaded as an artifact).

Cross-root concurrent use of the same provider/rate scope is unsupported:
cooperating CLI processes sharing a provider scope MUST share the same output
root (the application collection lock is rooted there).

## Durable output-root registry (operational contract)

- The output root holds `rate-registry.json` (versioned) plus one
  per-`scope_id` state file, all updated by same-directory atomic replace
  plus file/parent `fsync` under the collection lock.
- New scope: recoverable `initializing -> full-capacity state -> active`
  first-use sequence. Recovery may complete an `initializing` entry only
  after validating no request was admitted.
- An active scope with missing/partial/corrupt/unknown-schema state, or a
  marked persistent root with missing/corrupt registry, fails closed.
- Policy changes use the explicit zero-send conservative migration (new
  fingerprint, zero tokens, cooldown no earlier than old cooldown and now +
  new refill period) and never reset implicitly.
- Wall-clock rollback grants no tokens; refill uses only non-negative
  injected UTC elapsed time.
- Every possible send durably debits one token and installs the 24-hour
  provisional crash cooldown; confirmed pre-send failure may refund;
  controlled terminal outcomes retain the debit but reconcile to
  policy/`Retry-After`.

## External scheduling

Reconcile the external delivery schedule so Brief execution occurs after
successful Feed publication. Do not run the Brief before its input cutoff is
available; v1 marks a Feed stale when lag > 30 minutes and refuses normal
mode over 2 hours.

## Known limitations

- Live model output is non-deterministic; repeated live evaluation is
  evidence, not a release gate.
- Versioned heuristic scores bias events with missing data; component
  coverage is exposed and priority scores are never returns or
  recommendations.
- The language audit is performed by the same configured model that
  generates language: a bounded editorial check, not independent assurance.
- The repo is not a Git checkout and contains no enabled workflow or
  license until separately authorized.
