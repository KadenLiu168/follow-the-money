import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { atomicWriteJSON } from './atomic-write.js';

const DEFAULTS = { lastUpdated: '1970-01-01T00:00:00.000Z', seenFilings: {} };

// Evict seenFilings entries older than this window. seenFilings is a *dedup
// cache* only — the feed remains the source of truth because upsert13FFiling
// dedups by filerCik+periodOfReport, so eviction at worst triggers a redundant
// fetch, never data loss.
export const SEEN_FILINGS_TTL_DAYS = 90;
const TTL_MS = SEEN_FILINGS_TTL_DAYS * 24 * 60 * 60 * 1000;

export function pruneSeenFilings(state, now = Date.now()) {
  const cutoff = now - TTL_MS;
  const seen = state.seenFilings || {};
  const kept = {};
  // Keep only numeric timestamps within the TTL. Non-numeric entries (from an
  // older/partial schema) are dropped — seenFilings is a cache, never a source
  // of truth, so losing them is harmless.
  for (const [accession, ts] of Object.entries(seen)) {
    if (typeof ts === 'number' && ts >= cutoff) kept[accession] = ts;
  }
  return { ...state, seenFilings: kept };
}

export function readStateJson(path) {
  if (!existsSync(path)) return structuredClone(DEFAULTS);
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8'));
    const merged = { ...DEFAULTS, ...parsed };
    return pruneSeenFilings(merged);
  } catch {
    return structuredClone(DEFAULTS);
  }
}

export function writeStateJson(path, state) {
  mkdirSync(dirname(path), { recursive: true });
  atomicWriteJSON(path, state);
}
