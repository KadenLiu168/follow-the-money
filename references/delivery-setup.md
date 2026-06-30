# Delivery Setup

Step-by-step for Telegram and Email delivery. Load this during onboarding Step 6 (API keys) or whenever the user asks to switch delivery method.

All secrets live in `~/.follow-the-money/.env`. The skill loads it via `dotenv` on every script run. Do not commit `.env` to git (already in `.gitignore`).

## Telegram

### Step 1 — Create a bot via @BotFather

1. Open Telegram, search for `@BotFather`, start a chat
2. Send `/newbot`
3. BotFather asks for a name (shown to users). Pick anything, e.g. `Follow The Money`
4. BotFather asks for a username. Must end in `bot`, e.g. `follow_the_money_bot`
5. BotFather replies with the **bot token** — a long string like `123456789:AAH...`

Save the token:

```bash
# macOS / Linux
echo 'TELEGRAM_BOT_TOKEN=123456789:AAH...' >> ~/.follow-the-money/.env

# Windows (PowerShell)
Add-Content -Path $env:USERPROFILE\.follow-the-money\.env -Value "TELEGRAM_BOT_TOKEN=123456789:AAH..."
```

### Step 2 — Get your chat ID

1. Open a chat with your new bot (search for the username you chose) and send `/start`
2. Visit this URL in a browser (replace `<TOKEN>` with your bot token):

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

3. Find the `"chat":{"id":123456789}` field. That number is your `TELEGRAM_CHAT_ID`
4. Save it:

```bash
# macOS / Linux
echo 'TELEGRAM_CHAT_ID=123456789' >> ~/.follow-the-money/.env

# Windows (PowerShell)
Add-Content -Path $env:USERPROFILE\.follow-the-money\.env -Value "TELEGRAM_CHAT_ID=123456789"
```

### Step 3 — Test

```bash
# macOS / Linux
node $FTM_SKILL_DIR/scripts/deliver.js --text "test from follow-the-money"

# Windows (PowerShell)
node "$env:FTM_SKILL_DIR\scripts\deliver.js" --text "test from follow-the-money"
```

You should see the message in your Telegram chat within seconds. If not, check:
- Both env vars are set (`cat ~/.follow-the-money/.env`)
- You messaged the bot **before** calling `getUpdates` (the chat must exist)
- Token has no stray whitespace or quotes

### Optional — Group chat

To send to a group instead of a personal chat:
1. Add the bot to the group
2. Send any message in the group
3. Call `getUpdates` again — the chat id will be a negative number (e.g. `-1001234567890`)
4. Set that as `TELEGRAM_CHAT_ID`

## Email (Resend)

### Step 1 — Create a Resend account

1. Go to https://resend.com and sign up
2. Verify your sending domain (or use the sandbox `onboarding@resend.dev` for testing)

### Step 2 — Verify your domain

In the Resend dashboard:
1. Click **Domains** → **Add Domain**
2. Enter your sending domain (e.g. `alerts.yourdomain.com`)
3. Add the DNS records Resend shows you:
   - Typically an `MX` record
   - One or more `TXT` records for SPF / DKIM
4. Wait for Resend to confirm verification (usually minutes, sometimes longer)

If you only want to test, skip domain verification and use the sandbox sender `onboarding@resend.dev`. Emails will only deliver to the address you signed up with.

### Step 3 — Generate an API key

1. In Resend dashboard, go to **API Keys** → **Create API Key**
2. Name it (e.g. `follow-the-money`)
3. Permission: **Full access** (or scoped to "Sending access")
4. Copy the key — it starts with `re_` and is shown only once

Save the key:

```bash
# macOS / Linux
echo 'RESEND_API_KEY=re_your_api_key_here' >> ~/.follow-the-money/.env

# Windows (PowerShell)
Add-Content -Path $env:USERPROFILE\.follow-the-money\.env -Value "RESEND_API_KEY=re_your_api_key_here"
```

### Step 4 — Set the recipient

```bash
# macOS / Linux
echo 'EMAIL_TO=you@example.com' >> ~/.follow-the-money/.env

# Windows (PowerShell)
Add-Content -Path $env:USERPROFILE\.follow-the-money\.env -Value "EMAIL_TO=you@example.com"
```

The sender comes from the verified domain in your Resend account (or `onboarding@resend.dev` for sandbox).

### Step 5 — Test

```bash
# macOS / Linux
node $FTM_SKILL_DIR/scripts/deliver.js --text "test from follow-the-money"

# Windows (PowerShell)
node "$env:FTM_SKILL_DIR\scripts\deliver.js" --text "test from follow-the-money"
```

Check the recipient inbox (and spam folder on first send).

## Switching Back to stdout

To stop using Telegram/Email and return to agent-session output:

```bash
# macOS / Linux — remove or comment out the vars
sed -i '' '/^TELEGRAM_/d' ~/.follow-the-money/.env
sed -i '' '/^RESEND_/d' ~/.follow-the-money/.env
sed -i '' '/^EMAIL_/d' ~/.follow-the-money/.env
```

Then update `~/.follow-the-money/config.json`:

```json
{
  "delivery": { "method": "stdout" }
}
```

The skill falls back to stdout automatically if Telegram/Email delivery fails (see `alert-rules.md` for failure handling).

## Verifying the `.env` File

```bash
# macOS / Linux
cat ~/.follow-the-money/.env

# Windows (PowerShell)
Get-Content $env:USERPROFILE\.follow-the-money\.env
```

Expected content for Telegram:

```
TELEGRAM_BOT_TOKEN=123456789:AAH...
TELEGRAM_CHAT_ID=123456789
```

Expected content for Email:

```
RESEND_API_KEY=re_your_api_key_here
EMAIL_TO=you@example.com
```

Never commit `.env` to the repo. The `.gitignore` already excludes it.
