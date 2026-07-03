import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { read13DFilings, validateManifest } from '../lib/store/feed-ndjson.js';
import { readManifest } from '../lib/store/manifest.js';
import { ALERT_FORMS } from '../lib/alert/classify.js';
import { mergeByIssuer } from '../lib/feed/merge-by-issuer.js';
import { mergeAmendmentsForAlert } from '../lib/alert/merge-amendments.js';

const REPO = process.cwd();
const FEED_DIR = process.env.FOLLOW_THE_MONEY_FEED_DIR || REPO;
const FEED_13DG_DIR = join(FEED_DIR, 'feed-13dg');
const CONFIG_PATH = join(homedir(), '.follow-the-money', 'config.json');

let config = {};
try {
  config = existsSync(CONFIG_PATH) ? JSON.parse(readFileSync(CONFIG_PATH, 'utf8')) : {};
} catch (err) {
  console.error(`[check-alerts] failed to parse ${CONFIG_PATH}: ${err.message}`);
  process.exit(1);
}
const lastAlert = config.lastAlertTimestamp || '1970-01-01T00:00:00.000Z';

const manifest = existsSync(FEED_13DG_DIR) ? readManifest(FEED_13DG_DIR) : { years: {}, currentYear: new Date().getUTCFullYear() };
// Spec §NDJSON robustness: validate line counts on startup
if (existsSync(FEED_13DG_DIR)) {
  const v = validateManifest(FEED_13DG_DIR, manifest);
  if (!v.ok) console.warn(`[check-alerts] feed-13dg manifest mismatch: ${v.warnings.join('; ')}`);
}
// Read both current and prior year so amendments filed late December
// are not dropped on the year boundary. feed-ndjson.js defaults to
// [currentYear, currentYear - 1] when no `years` is passed.
const raw = read13DFilings(FEED_13DG_DIR, manifest);
const newCritical = raw.filter(f => ALERT_FORMS.has(f.formType) && f.filingDate > lastAlert);
if (newCritical.length === 0) { process.stdout.write(JSON.stringify({ alerts: [], capped: false, summary: null })); process.exit(0); }

const groups = mergeByIssuer(newCritical);
const alerts = mergeAmendmentsForAlert(groups);

const DETAIL_CAP = 8;
let payload;
if (alerts.length <= DETAIL_CAP) {
  payload = { alerts, capped: false, summary: null };
} else {
  payload = { alerts: alerts.slice(0, DETAIL_CAP), capped: true, summary: `📊 另 ${alerts.length - DETAIL_CAP} 条 13D/G 详见 digest` };
}
process.stdout.write(JSON.stringify(payload, null, 2));