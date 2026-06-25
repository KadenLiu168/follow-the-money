import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { filterByLookback } from '../lib/feed/filter-by-lookback.js';
import { readFeedJson } from '../lib/store/feed-json.js';
import { read13DFilings, validateManifest } from '../lib/store/feed-ndjson.js';
import { readManifest } from '../lib/store/manifest.js';

const REPO = process.cwd();
const FEED_13F = join(REPO, 'feed-13f.json');
const FEED_13DG_DIR = join(REPO, 'feed-13dg');

const args = process.argv.slice(2);
const lookbackIdx = args.indexOf('--lookback');
const lookbackDays = lookbackIdx >= 0 ? Number(args[lookbackIdx + 1]) : 1;

const f13 = existsSync(FEED_13F) ? readFeedJson(FEED_13F) : { thirteenF: [] };
const manifest = existsSync(FEED_13DG_DIR) ? readManifest(FEED_13DG_DIR) : { years: {}, currentYear: new Date().getUTCFullYear() };
// Spec §NDJSON robustness: validate line counts on startup
if (existsSync(FEED_13DG_DIR)) {
  const v = validateManifest(FEED_13DG_DIR, manifest);
  if (!v.ok) console.warn(`[prepare-digest] feed-13dg manifest mismatch: ${v.warnings.join('; ')}`);
}
const dgRaw = read13DFilings(FEED_13DG_DIR, manifest);
const dgFiltered = filterByLookback(dgRaw, { lookbackDays });

const f13Filtered = f13.thirteenF.filter(e => {
  const cutoff = new Date(Date.now() - lookbackDays * 86400000).toISOString().slice(0, 10);
  return e.latestFilingDate >= cutoff;
});

const out = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  lookbackDays,
  thirteenF: f13Filtered,
  thirteenDG: dgFiltered,
  stats: {
    thirteenFFilings: f13Filtered.length,
    thirteenDGFilings: dgFiltered.length,
  },
};
process.stdout.write(JSON.stringify(out, null, 2));
