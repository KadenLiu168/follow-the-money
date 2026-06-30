# Onboarding

The 8-step first-run flow. Load this when the agent detects that `~/.follow-the-money/config.json` is missing or `onboardingComplete: false`.

## Trigger Conditions

Onboarding runs when **both**:
- `~/.follow-the-money/config.json` does not exist, OR
- `~/.follow-the-money/config.json` exists but `onboardingComplete: false`

Otherwise, skip directly to digest or alert flow.

## The 8 Steps

### Step 1 — Introduction

Explain what the skill does, in plain language:

> 这个 skill 跟踪美国 SEC EDGAR 上的两类申报：
> 1. **8 位传奇基金经理的 13F 季报**（伯克希尔、Pershing Square、Scion 等）
> 2. **全美市场 13D/G 举牌 / 披露事件**（任何投资人、任何公司）
>
> 没有观点、没有预测、没有评论。直接看聪明钱在做什么。

Show the 8 fund list with their style tags (value / activist-value / growth / etc.).

### Step 2 — Frequency

Ask: `你想多久收到一次 digest？`

Options:
- **Daily** — 每天一份，覆盖最近 1 天的申报
- **Weekly** — 每周一份，覆盖最近 7 天

Default: `daily`. Save to `config.frequency`.

### Step 3 — Time + Timezone

Ask: `几点推送？用什么时区？`

Examples:
- `08:00 America/New_York` (美东早盘前)
- `09:00 Asia/Shanghai` (亚洲白天)
- `17:00 Europe/London` (欧洲收市后)

Default: `08:00 America/New_York`. Save to `config.deliveryTime` + `config.timezone`.

### Step 4 — Delivery Method

Ask: `怎么接收？`

Options:
- **stdout** — 直接在 agent 会话里看 (no setup needed)
- **Telegram** — 推送到 Telegram 机器人 (need bot setup, see `delivery-setup.md`)
- **Email** — 邮件 (need Resend API key, see `delivery-setup.md`)

Default: `stdout`. Save to `config.delivery.method`.

### Step 5 — Language

Ask: `用什么语言？`

Options:
- `en` — English
- `zh` — 中文
- `bilingual` — 中英双语 (each section both languages)

Default: `bilingual`. Save to `config.language`.

### Step 6 — API Keys (only if Telegram/Email)

If user chose Telegram:
- Walk them through BotFather setup (see `delivery-setup.md`)
- Save `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `~/.follow-the-money/.env`

If user chose Email:
- Walk them through Resend setup (see `delivery-setup.md`)
- Save `RESEND_API_KEY` and `EMAIL_TO` to `~/.follow-the-money/.env`

If stdout: skip this step.

### Step 7 — Show Sources

Display the full source list:

**8 13F Filers** (from `config/default-sources.json`):
| Fund | Style |
|---|---|
| Berkshire Hathaway | value |
| Pershing Square | activist-value |
| Scion Asset Management | deep-value |
| Baupost Group | value |
| Oaktree Capital | distressed-value |
| ARK Invest | thematic-growth |
| Tiger Global Management | growth |
| Coatue Management | growth |

**13D/G Scope**: Full US market. Any filer, any company. Forms: SC 13D, SC 13D/A, SC 13G, SC 13G/A.

### Step 8 — Settings Reminder + Cron Setup

Tell the user:
> 所有设置都可以随时通过对话修改。试试说：
> - "切换到 weekly"
> - "把时间改成 17:00"
> - "翻译成中文"
> - "改用 Telegram"
> - "显示我的设置"

Then point them to `references/cron-setup.md` for the OS-specific cron install.

After cron is set, run the **welcome digest** immediately:
- `node scripts/prepare-digest.js`
- Apply prompts
- `node scripts/deliver.js --file <digest>`

Ask: `看到第一份 digest 了。有什么想调整的？` — collect feedback, set `onboardingComplete: true`, atomic-write the config.

## Config Schema After Onboarding

```json
{
  "schemaVersion": 1,
  "platform": "any",
  "language": "bilingual",
  "timezone": "America/New_York",
  "frequency": "daily",
  "deliveryTime": "08:00",
  "delivery": { "method": "stdout" },
  "lastAlertTimestamp": "2026-06-25T08:00:00.000Z",
  "onboardingComplete": true
}
```

## Config Changes via Conversation

Recognize these phrases and update config:

| Phrase | Action |
|---|---|
| "Switch to weekly" | `frequency: "weekly"` |
| "Change time to X" | `deliveryTime: "X"` |
| "Translate to Chinese" | `language: "zh"` |
| "Send to Telegram" | `delivery.method: "telegram"` + onboarding for setup |
| "Show my settings" | read config.json, display human-readable |

All updates use atomic write (temp + rename).
