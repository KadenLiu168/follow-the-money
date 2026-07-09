import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync, readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { append13DFiling, read13DFilings, validateManifest } from '../../lib/store/feed-ndjson.js';
import { readManifest } from '../../lib/store/manifest.js';

let dir;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), 'ftm-'));
});
afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

const e1 = {
  filerCik: '0000932470',
  filerName: 'ICAHN CARL C',
  issuerCik: '0001717393',
  issuerName: 'Jet.AI Inc',
  issuerTicker: 'JTAI',
  formType: 'SC 13D',
  filingDate: '2026-06-20',
  ownershipPercent: 6.8,
  sharesOwned: 4500000,
  intent: 'active',
  accessionNumber: '0000932470-26-000045',
  primaryDocUrl: 'https://www.sec.gov/...',
};
const e2 = {
  filerCik: '0000893855',
  filerName: 'ELLIOTT',
  issuerCik: '0001315098',
  issuerName: 'ATVI',
  issuerTicker: 'ATVI',
  formType: 'SC 13G',
  filingDate: '2026-06-18',
  ownershipPercent: 5.1,
  sharesOwned: 4900000,
  intent: 'passive',
  accessionNumber: '0000893855-26-000078',
  primaryDocUrl: 'https://www.sec.gov/...',
};

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
    const { entries: all } = read13DFilings(dir, m2);
    expect(all).toHaveLength(2);
    expect(all[0].filingDate).toBe('2026-06-18');
  });

  it('read13DFilings with explicit years', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, { ...e1, filingDate: '2025-12-30' });
    append13DFiling(dir, m, e2);
    const m2 = readManifest(dir);
    expect(read13DFilings(dir, m2, { years: [2025] }).entries).toHaveLength(1);
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

  it('N appends produce exactly N lines (no full rewrite / duplication)', () => {
    const m = readManifest(dir);
    for (let i = 0; i < 3; i++) append13DFiling(dir, m, { ...e1, accessionNumber: `acc-${i}` });
    const file = join(dir, '2026.ndjson');
    const lines = readFileSync(file, 'utf8').split('\n').filter(Boolean);
    expect(lines).toHaveLength(3);
    for (const line of lines) expect(JSON.parse(line).filerName).toBe('ICAHN CARL C');
  });

  it('read13DFilings counts corrupt lines as skipped', () => {
    const file = join(dir, '2026.ndjson');
    writeFileSync(file, `${JSON.stringify(e1)}\nthis is not json\n${JSON.stringify(e2)}\n`);
    const { entries, skipped } = read13DFilings(dir, { years: [2026], currentYear: 2026 });
    expect(entries).toHaveLength(2);
    expect(skipped).toBeGreaterThanOrEqual(1);
  });

  it('invalid filingDate is skipped and creates no NaN file', () => {
    const m = readManifest(dir);
    append13DFiling(dir, m, { ...e1, filingDate: 'not-a-date' });
    const files = readdirSync(dir);
    expect(files.some((f) => f.includes('NaN'))).toBe(false);
    expect(readManifest(dir).years['NaN']).toBeUndefined();
  });

  it('validateManifest reports corrupt lines in diagnostics', () => {
    const file = join(dir, '2026.ndjson');
    writeFileSync(file, `${JSON.stringify(e1)}\nbroken line\n`);
    const r = validateManifest(dir, { years: { 2026: { count: 1 } }, currentYear: 2026 });
    expect(r.ok).toBe(false);
    expect(r.warnings.some((w) => /corrupt/.test(w))).toBe(true);
  });
});
