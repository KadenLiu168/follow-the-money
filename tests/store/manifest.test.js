import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readManifest, writeManifest } from '../../lib/store/manifest.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

describe('manifest', () => {
  it('returns defaults when missing', () => {
    const m = readManifest(dir);
    expect(m.schemaVersion).toBe(1);
    expect(m.years).toEqual({});
  });

  it('round-trips', () => {
    const m = { schemaVersion: 1, currentYear: 2026, years: { '2026': { file: 'feed-13dg/2026.ndjson', count: 5, firstDate: '2026-01-01', lastDate: '2026-06-25' } } };
    writeManifest(dir, m);
    expect(readManifest(dir)).toEqual(m);
  });
});