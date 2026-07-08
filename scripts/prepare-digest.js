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

// Reference time ("now") seam: --now flag > FTM_NOW env > wall clock.
// All date-derived values (lookback cutoff, manifest year, generatedAt) use
// this single value, so digests are deterministic and as-of backfill works.
// See openspec/changes/add-digest-time-seam (capability: digest-lookback).
const nowIdx = args.indexOf('--now');
let now;
let nowSource; // 'flag' | 'env' | 'wall' — wall-clock is always valid; flag/env must parse
if (nowIdx >= 0) {
  // Flag present: a value MUST follow (consistent with --lookback). A missing
  // value would otherwise silently fall back to env/wall-clock — a footgun for
  // backfill operators. new Date(undefined) is Invalid Date → caught below.
  nowSource = 'flag';
  now = new Date(args[nowIdx + 1]);
} else if (process.env.FTM_NOW) {
  nowSource = 'env';
  now = new Date(process.env.FTM_NOW);
} else {
  nowSource = 'wall';
  now = new Date();
}
if (nowSource !== 'wall' && Number.isNaN(now.getTime())) {
  if (nowSource === 'flag' && args[nowIdx + 1] === undefined) {
    console.error('[prepare-digest] --now requires a value, e.g. --now 2026-03-31');
  } else {
    const label = nowSource === 'flag' ? args[nowIdx + 1] : process.env.FTM_NOW;
    console.error(`[prepare-digest] invalid --now/FTM_NOW: ${label}`);
  }
  process.exit(1);
}

const f13 = existsSync(FEED_13F) ? readFeedJson(FEED_13F) : { thirteenF: [] };
const manifest = existsSync(FEED_13DG_DIR) ? readManifest(FEED_13DG_DIR) : { years: {}, currentYear: now.getUTCFullYear() };
// Spec §NDJSON robustness: validate line counts on startup
if (existsSync(FEED_13DG_DIR)) {
  const v = validateManifest(FEED_13DG_DIR, manifest);
  if (!v.ok) console.warn(`[prepare-digest] feed-13dg manifest mismatch: ${v.warnings.join('; ')}`);
}
const dgRaw = read13DFilings(FEED_13DG_DIR, manifest);
const dgFiltered = filterByLookback(dgRaw, { lookbackDays, now });

// Normalize the full feed ONCE so periodDiff can find a prior entry that
// shares the same unit regime as the current entry. If only the current
// entry were normalized, deltaPct would compare normalized current totals
// to raw prior totals (off by 1000x for filers like Baupost).
const normalizedFeed = f13.thirteenF.map((f) => normalizeValueUnits(f, defaultSources.thirteenF));
// 13F entries expose `latestFilingDate` (not `filingDate`); window on it via
// the `field` option so 13F and 13DG share one filter function and one `now`.
const f13Filtered = filterByLookback(normalizedFeed, { lookbackDays, now, field: 'latestFilingDate' });

// Pass defaultSources.thirteenF so periodDiff's defensive normalizeValueUnits
// can correctly identify small-fund style prior entries (e.g. tiny CIKs that
// publish in dollars rather than thousands). Per
// openspec/specs/value-units-normalization, normalizeValueUnits is idempotent
// on entries with `valueUnitAdjusted === true`, so re-normalizing already-
// normalized prior entries is a safe no-op.
const enriched = f13Filtered.map((f) => periodDiff(f, normalizedFeed, defaultSources.thirteenF));

const out = {
  schemaVersion: 1,
  generatedAt: now.toISOString(),
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
