import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync, existsSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  readStateJson,
  writeStateJson,
  pruneSeenFilings,
  SEEN_FILINGS_TTL_DAYS,
} from '../../lib/store/state-json.js';

let dir;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-'));
});
afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe('state-json', () => {
  it('returns defaults when file missing', () => {
    const s = readStateJson(join(dir, 'missing.json'));
    expect(s).toEqual({ lastUpdated: '1970-01-01T00:00:00.000Z', seenFilings: {} });
  });

  it('round-trips via write + read (recent seenFilings preserved)', () => {
    const p = join(dir, 'state.json');
    const now = Date.now();
    const s = {
      lastUpdated: '2026-05-15T08:00:00.000Z',
      seenFilings: { a: now - 1000, b: now - 2000 },
    };
    writeStateJson(p, s);
    expect(readStateJson(p)).toEqual(s);
  });

  it('writes atomically (temp file cleaned up)', () => {
    const p = join(dir, 'state.json');
    writeStateJson(p, { lastUpdated: 'x', seenFilings: {} });
    expect(existsSync(p)).toBe(true);
    const tempFiles = readdirSync(dir).filter((f) => f.includes('.tmp'));
    expect(tempFiles).toEqual([]);
  });

  it('merges DEFAULTS when file exists but lacks seenFilings (older schema)', () => {
    const p = join(dir, 'state.json');
    writeFileSync(p, JSON.stringify({ lastUpdated: '2026-05-15T08:00:00.000Z' }));
    const s = readStateJson(p);
    expect(s.seenFilings).toEqual({});
    expect(s.lastUpdated).toBe('2026-05-15T08:00:00.000Z');
  });

  it('prunes seenFilings entries older than the TTL on read', () => {
    const now = Date.now();
    const stale = now - (SEEN_FILINGS_TTL_DAYS + 1) * 24 * 60 * 60 * 1000;
    const p = join(dir, 'state.json');
    const s = {
      lastUpdated: '2026-05-15T08:00:00.000Z',
      seenFilings: { fresh: now - 1000, stale1: stale, stale2: stale - 5000 },
    };
    writeStateJson(p, s);
    const read = readStateJson(p);
    expect(read.seenFilings).toEqual({ fresh: now - 1000 });
  });

  it('pruneSeenFilings keeps entries within the TTL', () => {
    const now = Date.now();
    const out = pruneSeenFilings({ seenFilings: { a: now, b: now - 10 } });
    expect(out.seenFilings).toEqual({ a: now, b: now - 10 });
  });

  it('pruneSeenFilings drops entries older than the TTL', () => {
    const now = Date.now();
    const stale = now - (SEEN_FILINGS_TTL_DAYS + 5) * 24 * 60 * 60 * 1000;
    const out = pruneSeenFilings({ seenFilings: { fresh: now, old: stale } });
    expect(out.seenFilings).toEqual({ fresh: now });
  });
});
