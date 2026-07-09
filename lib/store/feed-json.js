import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const DEFAULTS = () => ({
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  lookbackDays: 90,
  thirteenF: [],
  stats: { thirteenFFilings: 0, thirteenFHoldings: 0 },
});

export function readFeedJson(path) {
  if (!existsSync(path)) return DEFAULTS();
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8'));
    return { ...DEFAULTS(), ...parsed, thirteenF: parsed.thirteenF ?? [], stats: parsed.stats ?? { thirteenFFilings: 0, thirteenFHoldings: 0 } };
  } catch {
    return DEFAULTS();
  }
}

export function writeFeedJson(path, feed) {
  mkdirSync(dirname(path), { recursive: true });
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(tmp, JSON.stringify(feed, null, 2));
  renameSync(tmp, path);
}

export function upsert13FFiling(path, entry) {
  const feed = readFeedJson(path);
  // Stamp the unit marker on every 13F entry we persist. SEC 13F <value>
  // is officially in thousands of dollars, so the canonical unit is 'thousands'.
  // Stamping here (the single 13F feed-writer) makes future snapshots
  // self-describing and prevents mixed-unit debt from re-introducing itself.
  // See openspec/changes/repair-feed-units.
  const stamped = { ...entry, valueUnit: 'thousands' };
  const idx = feed.thirteenF.findIndex(e => e.filerCik === entry.filerCik && e.periodOfReport === entry.periodOfReport);
  if (idx >= 0) {
    const old = feed.thirteenF[idx];
    const oldSnapshot = {
      filingDate: old.latestFilingDate,
      formType: old.latestFormType,
      accessionNumber: old.latestAccessionNumber,
    };
    const newHistoryEntry = {
      filingDate: stamped.latestFilingDate,
      formType: stamped.latestFormType,
      accessionNumber: stamped.latestAccessionNumber,
    };
    const priorHistory = old.history?.filter(h => h.accessionNumber !== oldSnapshot.accessionNumber) ?? [];
    feed.thirteenF[idx] = {
      ...stamped,
      history: [...priorHistory, oldSnapshot, newHistoryEntry],
    };
  } else {
    feed.thirteenF.push(stamped);
  }
  feed.generatedAt = new Date().toISOString();
  feed.stats = computeStats(feed);
  writeFeedJson(path, feed);
}

export function computeStats(feed) {
  const holdings = feed.thirteenF.reduce((s, e) => s + (e.holdings?.length ?? 0), 0);
  return { thirteenFFilings: feed.thirteenF.length, thirteenFHoldings: holdings };
}
