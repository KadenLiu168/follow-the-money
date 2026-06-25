import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { config as loadEnv } from 'dotenv';

const HOME = process.env.HOME || homedir();
const CONFIG_PATH = join(HOME, 'config.json');
const ENV_PATH = join(HOME, '.env');

if (existsSync(ENV_PATH)) {
  try {
    loadEnv({ path: ENV_PATH, quiet: true });
  } catch (err) {
    console.error(`ERROR: failed to load ${ENV_PATH}: ${err.message}`);
    process.exit(1);
  }
}

const args = process.argv.slice(2);
const textIdx = args.indexOf('--text');
const text = textIdx >= 0 ? args[textIdx + 1] : '';
if (!text) { console.error('ERROR: --text required'); process.exit(1); }

let config;
try {
  config = existsSync(CONFIG_PATH) ? JSON.parse(readFileSync(CONFIG_PATH, 'utf8')) : { delivery: { method: 'stdout' } };
} catch (err) {
  console.error(`ERROR: failed to parse ${CONFIG_PATH}: ${err.message}`);
  process.exit(1);
}
const method = config.delivery?.method ?? 'stdout';

if (method === 'stdout' || method === 'any') {
  console.log(text);
  process.exit(0);
}

if (method === 'telegram') {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) { console.error('ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required'); process.exit(1); }
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }) });
  if (!res.ok) { console.error(`Telegram HTTP ${res.status}: ${await res.text()}`); process.exit(1); }
  console.log(text);
  process.exit(0);
}

if (method === 'email') {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.EMAIL_TO;
  if (!apiKey || !to) { console.error('ERROR: RESEND_API_KEY and EMAIL_TO required'); process.exit(1); }
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: 'follow-the-money@resend.dev', to, subject: 'follow-the-money digest', text }),
  });
  if (!res.ok) { console.error(`Resend HTTP ${res.status}: ${await res.text()}`); process.exit(1); }
  console.log(text);
  process.exit(0);
}

console.error(`Unknown delivery method: ${method}`);
process.exit(1);