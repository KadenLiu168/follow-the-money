// One-time repair for the mixed-unit data debt in feed-13f.json.
//
// SEC 13F <value> is officially in thousands of dollars. The committed feed
// has 374 filer×period snapshots where some are stored in DOLLARS
// (max single holding raw >= 1e9) and others in THOUSANDS. After
// fix-value-units-config (P1-1) made normalizeValueUnits apply a uniform
// ×1000, the dollar-stored snapshots were over-stated 1000×.
//
// This script detects per-snapshot unit, normalizes dollar-stored snapshots to
// thousands (÷1000 on holdings.valueUsd and summary.totalValueUsd), stamps a
// `valueUnit: 'thousands'` marker on every entry (self-describing, prevents
// recurrence), and writes the feed back atomically. Idempotent: a repaired
// feed (all maxRaw < 1e9) converts 0 snapshots.
//
// See openspec/changes/repair-feed-units.

import { readFileSync } from 'node:fs';
import { writeFeedJson } from '../lib/store/feed-json.js';

// Threshold: a single holding in thousands can be at most (dollars / 1000).
// A $1B holding in thousands is raw = 1e6, never 1e9. Thus maxRaw >= 1e9
// uniquely identifies a snapshot stored in dollars. Math-ambiguous.
export const DOLLARS_THRESHOLD = 1e9;

export function isDollarStored(holdings) {
  let maxRaw = 0;
  for (const h of holdings || []) {
    const v = Number(h.valueUsd) || 0;
    if (v > maxRaw) maxRaw = v;
  }
  return maxRaw >= DOLLARS_THRESHOLD;
}

// Pure: returns { feed, converted } without touching disk.
export function repairFeed(feed) {
  const thirteenF = (feed.thirteenF || []).map((entry) => {
    const holdings = entry.holdings || [];
    const dollarStored = isDollarStored(holdings);
    const factor = dollarStored ? 1 / 1000 : 1;

    // Defensive copy; clear any legacy valueUnitAdjusted ambiguity.
    const next = { ...entry };
    delete next.valueUnitAdjusted;

    if (dollarStored) {
      next.holdings = holdings.map((h) => ({
        ...h,
        valueUsd: (Number(h.valueUsd) || 0) * factor,
      }));
      if (next.summary && typeof next.summary.totalValueUsd === 'number') {
        next.summary = {
          ...next.summary,
          totalValueUsd: next.summary.totalValueUsd * factor,
        };
      }
    }

    next.valueUnit = 'thousands';
    return next;
  });

  const converted = (feed.thirteenF || []).filter((e) => isDollarStored(e.holdings)).length;
  return { feed: { ...feed, thirteenF }, converted };
}

function main() {
  const path = process.argv[2] || 'feed-13f.json';
  const feed = JSON.parse(readFileSync(path, 'utf8'));
  const { feed: repaired, converted } = repairFeed(feed);
  writeFeedJson(path, repaired);
  console.log(`Converted ${converted} snapshot(s) to thousands. Feed rewritten: ${path}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { main };
