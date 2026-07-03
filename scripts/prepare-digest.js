import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { filterByLookback } from '../lib/feed/filter-by-lookback.js';
import { readFeedJson } from '../lib/store/feed-json.js';
import { read13DFilings, validateManifest } from '../lib/store/feed-ndjson.js';
import { readManifest } from '../lib/store/manifest.js';
import { normalizeValueUnits } from '../lib/enrich/normalize-value-units.js';
import { periodDiff } from '../lib/enrich/period-diff.js';
import defaultSources from '../config/default-sources.json' with { type: 'json' };

const REPO = process.cwd();
const FEED_DIR = process.env.FOLLOW_THE_MONEY_FEED_DIR || REPO;
const FEED_13F = join(FEED_DIR, 'feed-13f.json');
const FEED_13DG_DIR = join(FEED_DIR, 'feed-13dg');

const args = process.argv.slice(2);
const lookbackIdx = args.indexOf('--lookback');
// 13F is quarterly, so a 1-day lookback returns nothing on non-filing days.
// Default to 90 (one quarter) so manual `/money` triggers have context;
// cron callers that want "today's new filings only" can pass --lookback 1.
const lookbackDays = lookbackIdx >= 0 ? Number(args[lookbackIdx + 1]) : 90;
if (!Number.isInteger(lookbackDays) || lookbackDays <= 0) {
  console.error(`[prepare-digest] --lookback must be a positive integer, got: ${args[lookbackIdx + 1]}`);
  process.exit(1);
}

const f13 = existsSync(FEED_13F) ? readFeedJson(FEED_13F) : { thirteenF: [] };
const manifest = existsSync(FEED_13DG_DIR) ? readManifest(FEED_13DG_DIR) : { years: {}, currentYear: new Date().getUTCFullYear() };
// Spec §NDJSON robustness: validate line counts on startup
if (existsSync(FEED_13DG_DIR)) {
  const v = validateManifest(FEED_13DG_DIR, manifest);
  if (!v.ok) console.warn(`[prepare-digest] feed-13dg manifest mismatch: ${v.warnings.join('; ')}`);
}
const dgRaw = read13DFilings(FEED_13DG_DIR, manifest);
const dgFiltered = filterByLookback(dgRaw, { lookbackDays });

const cutoff = new Date(Date.now() - lookbackDays * 86400000).toISOString().slice(0, 10);
// Normalize the full feed ONCE so periodDiff can find a prior entry that
// shares the same unit regime as the current entry. If only the current
// entry were normalized, deltaPct would compare normalized current totals
// to raw prior totals (off by 1000x for filers like Baupost).
const normalizedFeed = f13.thirteenF.map((f) => normalizeValueUnits(f, defaultSources.thirteenF));
const f13Filtered = normalizedFeed.filter(e => e.latestFilingDate >= cutoff);

// Pass defaultSources.thirteenF so periodDiff's defensive normalizeValueUnits
// can correctly identify small-fund style prior entries (e.g. tiny CIKs that
// publish in dollars rather than thousands). Idempotent for already-normalized
// entries.
const enriched = f13Filtered.map((f) => periodDiff(f, normalizedFeed, defaultSources.thirteenF));

const out = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  lookbackDays,
  thirteenF: enriched,
  thirteenDG: dgFiltered,
  stats: {
    thirteenFFilings: enriched.length,
    thirteenDGFilings: dgFiltered.length,
  },
  diagnostics: {
    valueUnitsAdjusted: enriched.filter((f) => f.valueUnitAdjusted).map((f) => f.filerName),
    summaryMissing: enriched.filter((f) => f.summary === null).map((f) => f.filerName),
  },
};
process.stdout.write(JSON.stringify(out, null, 2));
