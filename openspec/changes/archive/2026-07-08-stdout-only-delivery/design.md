## Context

The local skill's delivery layer (`scripts/deliver.js`) currently supports three methods selected via `config.delivery.method`: `stdout` (default), `telegram`, `email`. Two of those branches — Telegram (Bot API) and Email (Resend) — have never actually executed in production. The bug is at `scripts/deliver.js:7`:

```js
const CONFIG_PATH = join(HOME, 'config.json');   // wrong: should be ~/.follow-the-money/config.json
```

The correct path is `join(homedir(), '.follow-the-money', 'config.json')` (as already used in `scripts/check-alerts.js:13`). Every agent-driven run reads the missing config file, the file-not-found path returns the inline default `{ delivery: { method: 'stdout' } }`, and Telegram/Email branches are dead code.

Stakeholders:
- **End user**: agent runtime consumer (🅰️) or local cron consumer (🅱️). Today's observable behavior is stdout; this change keeps that behavior while removing dead code.
- **Maintainer**: less code, fewer deps, no secret management, no outbound PII surface.
- **Future contributor**: should not rediscover the H1 path bug and "fix" it — a clear rename and a spec capture the decision.

Constraints:
- Zero data-file changes (`state-*.json`, `feed-*.json`, `*.ndjson`).
- `scripts/check-alerts.js`, `scripts/aggregate.js`, `scripts/prepare-digest.js` are out of scope.
- Tests must remain green; coverage may shrink but must not regress on stdout behavior.

## Goals / Non-Goals

**Goals:**
- Single source of truth for "local skill emits text": `scripts/print.js` writes content to stdout and exits.
- Eliminate `dotenv` dependency and the `~/.follow-the-money/.env` file convention.
- Eliminate the H1 config-path bug by removing the config read entirely.
- Update all user-facing docs (README, SKILL, references/, course/) to reflect the simplified contract.
- Keep behavior identical for existing users (stdout has been the only effective path).

**Non-Goals:**
- Re-introducing push notification channels in any form.
- Changing how the agent renders digest/alert text (that happens upstream of `print.js`).
- Touching `lib/`, `scripts/aggregate.js`, `scripts/fetch-feed.js`, `scripts/verify-edgar.js`, `scripts/check-alerts.js`, `scripts/eval.js`.
- Adding a new HTTP client, retry policy, or external integration.
- Providing a graceful migration path for users who set up Telegram/Email but never saw it work (they had no working state to migrate from).

## Decisions

### Decision 1: Rename `deliver.js` → `print.js`

**Choice**: Rename the file. Do not just trim it in place.

**Rationale**: The word "delivery" implies a delivery channel (push, email, queue). After this change the script only writes to stdout, which is fundamentally a print/emit operation. Keeping the old name would mislead every future reader into looking for the (now-removed) Telegram/Email branches.

**Alternatives considered**:
- _Keep `deliver.js`, trim body_: rejected. Name–behavior mismatch accumulates tech debt and re-introduces the wrong search target.
- _Inline the print logic into `prepare-digest.js` and remove the script entirely_: rejected. `prepare-digest.js` produces JSON for the agent; the agent then renders it; `print.js` is the stable stdout hook point that downstream agents (cron, scripts) can rely on. Keeping it as a separate, tiny, single-purpose script preserves the contract.

### Decision 2: Drop config read entirely

**Choice**: `print.js` does not read `~/.follow-the-money/config.json`. The `delivery.method` field is removed from the config schema.

**Rationale**: The only thing the config was selecting was which branch to take. With one branch remaining, there is nothing to select. Reading config for `print.js` would reintroduce the H1-style bug surface (path resolution) for zero benefit.

**Alternatives considered**:
- _Read config, default to `stdout`, error on `telegram`/`email`_: rejected. Carries dead config and a hidden error path that triggers when users have stale configs. Just remove the field.
- _Read config, accept any value as `stdout`_: rejected. Same dead-config problem.

### Decision 3: Remove `dotenv` dependency

**Choice**: Remove `dotenv` from `package.json` and regenerate `package-lock.json` with `npm install`.

**Rationale**: After dropping telegram/email branches, `dotenv` has zero consumers in this repo (verified by grep: only `scripts/deliver.js:4` imports it). Carrying an unused dep is exactly the kind of soft debt this change exists to eliminate.

**Alternatives considered**:
- _Keep `dotenv` for future use_: rejected. YAGNI; reintroduce when there's a real consumer.

### Decision 4: Drop the `~/.follow-the-money/.env` file convention

**Choice**: The `.env` file is no longer part of the skill's contract. It is not created, loaded, or documented.

**Rationale**: Without secrets to manage, the `.env` mechanism is overhead. The `.gitignore` entry for `.env` stays (harmless, future-proofs accidental commits), but docs no longer instruct users to create one.

### Decision 5: Update SKILL.md retry policy

**Choice**: Remove the retry-with-backoff clause for `print.js`. New rule: surface the error verbatim.

**Rationale**: `print.js` has no transient failure modes. It either can read `--file` and print, or it can't. There is no network call, no 5xx, no rate limit. The old retry policy was written for HTTP retries that no longer apply.

### Decision 6: Update `alert-rules.md` "fallback to stdout" semantics

**Choice**: Replace "Delivery (Telegram/email) errors | Log + fall back to stdout" with "All delivery is stdout. Agent session displays the alert directly."

**Rationale**: The fallback path becomes the only path. Calling it "fallback" misrepresents the architecture.

### Decision 7: Rename `tests/scripts/deliver.test.js` → `tests/scripts/print.test.js`

**Choice**: Rename the test file alongside the script rename. Keep three test cases.

**Rationale**: Test files should mirror the script name they cover. Keeping 3 cases (stdout default, `--file` reads contents, missing-args exits non-zero) preserves meaningful regression coverage without dead-path assertions.

### Decision 8: Mark `docs/code-quality-review-2026-07-08.md` H1 as resolved-by-removal

**Choice**: Edit the H1 row to indicate it was resolved by this change rather than by a path fix.

**Rationale**: Future readers consulting the review doc must not be tempted to "fix H1" by editing `deliver.js` (which no longer exists).

### Decision 9: Course material is in-scope, not optional

**Choice**: Update `course/index.html` and `course/modules/*.html` to remove Telegram/Email references (about 30+ sites across 5 module files + index).

**Rationale**: Course material teaches the system. If a learner runs the system as described in the course and finds a Telegram branch that does not exist, the lesson is "the docs lie." That is worse than missing material. This is ~2-3 hours of focused edits, scoped and separable from the code change.

The proposal marked course updates as optional; this design elevates them to in-scope based on the user-impact reasoning above.

## Risks / Trade-offs

- [Risk] Users who configured `delivery.method: "telegram"` or `"email"` in their config will get an unknown-field warning (or silent ignore) after upgrade → **Mitigation**: explicitly state in the change summary that the `delivery` block can be deleted from `~/.follow-the-money/config.json`; nothing breaks if it stays. The `print.js` script does not read config at all.
- [Risk] Future contributor re-adds Telegram/Email branches without re-reading this change → **Mitigation**: leave a one-line `// Stdout-only delivery (see openspec/changes/stdout-only-delivery/)` comment at the top of `print.js`, plus the `delivery` spec capability entry capturing the "stdout only" requirement.
- [Risk] Doc/test rename creates noisy git diff (file deletions + additions) → **Mitigation**: use `git mv` for renames so history is preserved; commit message explains the rename.
- [Risk] Someone's external automation expects `scripts/deliver.js` to exist at that path → **Mitigation**: SKILL.md and README.md list `print.js` as the new entry point; the old name is not referenced in any current automation (verified by grep across the repo).
- [Trade-off] Lose push-notification capability for users running unattended local cron without an agent → **Accepted**: documented in proposal as a Non-goal. The 🅰️ agent runtime covers the user-present case; for 🅱️ cron, `cron.log` capture is the existing substitute and has been the de facto behavior since release.
- [Trade-off] Course update adds ~2-3 hours to the change → **Accepted**: keeping course in sync with system is non-negotiable for teaching quality; isolated as its own task.

## Migration Plan

This change has no runtime migration:

1. Land the change in one PR.
2. Users running on a stale config keep their existing `~/.follow-the-money/config.json`; the `delivery` block becomes dead config that `print.js` ignores. No action required.
3. Users with an existing `~/.follow-the-money/.env` from prior setup attempts can leave it or delete it; nothing reads it.

Rollback: revert the PR. The previous `deliver.js` would be restored with all branches intact.

## Open Questions

_None — all decisions resolved. Ready for `tasks.md`._