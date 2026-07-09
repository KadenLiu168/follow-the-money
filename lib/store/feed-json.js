import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { atomicWriteJSON } from './atomic-write.js';

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
    return {
      ...DEFAULTS(),
      ...parsed,
      thirteenF: parsed.thirteenF ?? [],
      stats: parsed.stats ?? { thirteenFFilings: 0, thirteenFHoldings: 0 },
    };
  } catch {
    return DEFAULTS();
  }
}

export function writeFeedJson(path, feed) {
  mkdirSync(dirname(path), { recursive: true });
  atomicWriteJSON(path, feed);
}

// Pure in-memory merge: stamp the unit marker, apply the history-dedupe-by-accession
// merge, and recompute feed stats. Returns a NEW feed object (does not mutate input
// and does not touch disk), so callers can accumulate entries in memory and write
// once. SEC 13F <value> is officially in thousands of dollars, so the canonical unit
// is 'thousands'; stamping here (the single 13F merge path) makes future snapshots
// self-describing and prevents mixed-unit debt from re-introducing itself.
// See openspec/changes/repair-feed-units and openspec/changes/medium-followups.
export function merge13FFiling(feed, entry) {
  const stamped = { ...entry, valueUnit: 'thousands' };
  const next = { ...feed, thirteenF: feed.thirteenF.slice() };
  const idx = next.thirteenF.findIndex(
    (e) => e.filerCik === entry.filerCik && e.periodOfReport === entry.periodOfReport,
  );
  if (idx >= 0) {
    const old = next.thirteenF[idx];
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
    const priorHistory =
      old.history?.filter((h) => h.accessionNumber !== oldSnapshot.accessionNumber) ?? [];
    next.thirteenF[idx] = {
      ...stamped,
      history: [...priorHistory, oldSnapshot, newHistoryEntry],
    };
  } else {
    next.thirteenF.push(stamped);
  }
  next.generatedAt = new Date().toISOString();
  next.stats = computeStats(next);
  return next;
}

// Thin disk wrapper for single-shot callers and backward compatibility. The
// aggregator (pipeline-a) instead accumulates via merge13FFiling and writes once.
export function upsert13FFiling(path, entry) {
  writeFeedJson(path, merge13FFiling(readFeedJson(path), entry));
}

export function computeStats(feed) {
  const holdings = feed.thirteenF.reduce((s, e) => s + (e.holdings?.length ?? 0), 0);
  return { thirteenFFilings: feed.thirteenF.length, thirteenFHoldings: holdings };
}
