## 1. Script rename and rewrite

- [ ] 1.1 `git mv scripts/deliver.js scripts/print.js` to preserve history
- [ ] 1.2 Rewrite `scripts/print.js` body: remove `dotenv` import, `homedir`/`readFileSync` config read, telegram/email branches; implement `--text`/`--file` → stdout with exit codes per `specs/delivery/spec.md`
- [ ] 1.3 Add a one-line source comment at the top of `print.js` referencing this change: `// Stdout-only delivery (see openspec/changes/stdout-only-delivery/)`

## 2. Test rewrite

- [ ] 2.1 `git mv tests/scripts/deliver.test.js tests/scripts/print.test.js`
- [ ] 2.2 Trim `tests/scripts/print.test.js` to 4 cases: stdout default, `--file` reads contents, missing-args exits non-zero, `--file` path missing exits non-zero (covers spec requirement 5 scenarios)
- [ ] 2.3 Run `npm test` and confirm green (32 existing passing tests + 4 new = 36 expected)

## 3. Dependency cleanup

- [ ] 3.1 Remove `"dotenv": "^17.4.2"` from `package.json` `dependencies`
- [ ] 3.2 Run `npm install` to regenerate `package-lock.json` (no `dotenv` entry should remain)
- [ ] 3.3 Verify with `npm ls dotenv` that nothing transitively requires it (expect "empty")

## 4. Documentation updates

- [ ] 4.1 `README.md`: remove all Telegram/Email mentions; update push channel line to "stdout"; remove `.env` block; update `scripts/deliver.js` references to `scripts/print.js`; remove `references/delivery-setup.md` link
- [ ] 4.2 `SKILL.md`: remove Telegram/Email options from Step 5; rewrite the `deliver.js` retry policy clause; update secrets mention; replace `references/delivery-setup.md` link with "n/a (stdout only)"
- [ ] 4.3 `references/onboarding.md`: collapse Step 4 to stdout-only; delete Step 6 (API Keys) and renumber subsequent steps; update the "Config Changes via Conversation" table
- [ ] 4.4 `references/architecture.md`: replace "stdout / Telegram / Email" with "stdout" in diagram + table; remove line 64 about delivery secrets
- [ ] 4.5 `references/alert-rules.md`: replace "fall back to stdout" wording with "All delivery is stdout"
- [ ] 4.6 `references/cron-setup.md`: update confirmation step from "stdout / Telegram / email" to "stdout / cron log"
- [ ] 4.7 `git rm references/delivery-setup.md`

## 5. Local config and tooling cleanup

- [ ] 5.1 `.claude/settings.local.json`: remove the ~5 `Bash(...)` permission entries that referenced `TELEGRAM_BOT_TOKEN`, `dotenv/config`, and the old `scripts/deliver.js` test invocations
- [ ] 5.2 `docs/code-quality-review-2026-07-08.md`: edit H1 row to note "Resolved by openspec/changes/stdout-only-delivery (feature removed rather than path fixed)"

## 6. Course material sync

- [ ] 6.1 `course/index.html`: remove Telegram-as-opening-scene framing; replace with stdout framing; remove Telegram/Email mentions in upgrade-path text
- [ ] 6.2 `course/modules/01-intro.html`: same edits as index.html (it duplicates index content)
- [ ] 6.3 `course/modules/02-actors.html`: rewrite Layer 4 description to stdout-only; replace the deliver.js code-walkthrough screen with a print.js walkthrough (or remove the code screen entirely); update the "actor" caption from "stdout/Telegram/Email" to "stdout"
- [ ] 6.4 `course/modules/04-flow.html`: update the flow annotation "deliver.js 按 config 推送(stdout / Telegram / Email)" to reflect stdout-only
- [ ] 6.5 `course/modules/05-bugs.html`: remove the "Telegram 推送失败" troubleshooting block; update the "deliver.js — 推送格式错了" item to reference print.js + stdout errors

## 7. Final verification

- [ ] 7.1 `grep -rn "telegram\|Telegram\|TELEGRAM\|resend\|Resend\|RESEND\|EMAIL_\|deliver\.js\|delivery-setup\|delivery\.method" . --include='*.js' --include='*.json' --include='*.md' --include='*.html'` returns no unintended hits (course material edited in step 6 should be clean)
- [ ] 7.2 `grep -rn "dotenv" . --include='*.js' --include='*.json'` returns no hits
- [ ] 7.3 `npm test` green
- [ ] 7.4 `openspec status --change "stdout-only-delivery"` shows all artifacts complete
- [ ] 7.5 Commit: `git commit -am "feat(delivery): stdout-only; drop telegram/email + dotenv" -m "..."` and push branch