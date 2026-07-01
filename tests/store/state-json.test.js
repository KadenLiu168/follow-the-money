import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync, readFileSync, existsSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readStateJson, writeStateJson } from '../../lib/store/state-json.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('state-json', () => {
  it('returns defaults when file missing', () => {
    const s = readStateJson(join(dir, 'missing.json'));
    expect(s).toEqual({ lastUpdated: '1970-01-01T00:00:00.000Z', seenFilings: {} });
  });

  it('round-trips via write + read', () => {
    const p = join(dir, 'state.json');
    const s = { lastUpdated: '2026-05-15T08:00:00.000Z', seenFilings: { a: 1, b: 2 } };
    writeStateJson(p, s);
    expect(readStateJson(p)).toEqual(s);
  });

  it('writes atomically (temp file cleaned up)', () => {
    const p = join(dir, 'state.json');
    writeStateJson(p, { lastUpdated: 'x', seenFilings: {} });
    expect(existsSync(p)).toBe(true);
    const tempFiles = readdirSync(dir).filter(f => f.includes('.tmp'));
    expect(tempFiles).toEqual([]);
  });

  it('merges DEFAULTS when file exists but lacks seenFilings (older schema)', () => {
    const p = join(dir, 'state.json');
    writeFileSync(p, JSON.stringify({ lastUpdated: '2026-05-15T08:00:00.000Z' }));
    const s = readStateJson(p);
    expect(s.seenFilings).toEqual({});
    expect(s.lastUpdated).toBe('2026-05-15T08:00:00.000Z');
  });
});