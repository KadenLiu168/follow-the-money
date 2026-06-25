import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { append13DFiling, read13DFilings, validateManifest } from '../../lib/store/feed-ndjson.js';
import { readManifest } from '../../lib/store/manifest.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

const e1 = { filerCik: '0000932470', filerName: 'ICAHN CARL C', issuerCik: '0001717393', issuerName: 'Jet.AI Inc', issuerTicker: 'JTAI', formType: 'SC 13D', filingDate: '2026-06-20', ownershipPercent: 6.8, sharesOwned: 4500000, intent: 'active', accessionNumber: '0000932470-26-000045', primaryDocUrl: 'https://www.sec.gov/...' };
const e2 = { filerCik: '0000893855', filerName: 'ELLIOTT', issuerCik: '0001315098', issuerName: 'ATVI', issuerTicker: 'ATVI', formType: 'SC 13G', filingDate: '2026-06-18', ownershipPercent: 5.1, sharesOwned: 4900000, intent: 'passive', accessionNumber: '0000893855-26-000078', primaryDocUrl: 'https://www.sec.gov/...' };

describe('feed-ndjson', () => {
  it('appends to year file and updates manifest', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, e1);
    append13DFiling(dir, m, e2);
    const after = readManifest(dir);
    expect(after.years['2026'].count).toBe(2);
    expect(after.years['2026'].lastDate).toBe('2026-06-20');
    expect(after.years['2026'].firstDate).toBe('2026-06-18');
  });

  it('read13DFilings across years merges + sorts desc by date', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, { ...e1, filingDate: '2025-12-30' });
    append13DFiling(dir, m, e2);
    const m2 = readManifest(dir);
    const all = read13DFilings(dir, m2);
    expect(all).toHaveLength(2);
    expect(all[0].filingDate).toBe('2026-06-18');
  });

  it('read13DFilings with explicit years', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, { ...e1, filingDate: '2025-12-30' });
    append13DFiling(dir, m, e2);
    const m2 = readManifest(dir);
    expect(read13DFilings(dir, m2, { years: [2025] })).toHaveLength(1);
  });

  it('validateManifest flags count mismatch', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, e1);
    const m2 = readManifest(dir);
    m2.years['2026'].count = 99; // corrupt the manifest
    const r = validateManifest(dir, m2);
    expect(r.ok).toBe(false);
    expect(r.warnings.length).toBeGreaterThan(0);
  });
});