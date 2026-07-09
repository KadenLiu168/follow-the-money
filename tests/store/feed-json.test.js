import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readFeedJson, writeFeedJson, upsert13FFiling, computeStats } from '../../lib/store/feed-json.js';

let dir;
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'ftm-')); });
afterEach(() => { rmSync(dir, { recursive: true, force: true }); });

const newEntry = (over = {}) => ({
  filerCik: '0001067983', filerName: 'Berkshire Hathaway Inc',
  latestFilingDate: '2026-05-15', latestFormType: '13F-HR',
  latestAccessionNumber: '0001067983-26-000123', periodOfReport: '2026-03-31',
  history: [{ filingDate: '2026-05-15', formType: '13F-HR', accessionNumber: '0001067983-26-000123' }],
  holdings: [{ cusip: '037833100', issuerName: 'APPLE INC', shares: 300000000, valueUsd: 58200000000, votingAuthority: { sole: 300000000, shared: 0, none: 0 } }],
  summary: { totalHoldingsCount: 1, totalValueUsd: 58200000000, newPositions: ['037833100'], closedPositions: [], increasedPositions: 0, decreasedPositions: 0 },
  ...over,
});

describe('feed-json', () => {
  it('returns defaults when missing', () => {
    const f = readFeedJson(join(dir, 'missing.json'));
    expect(f.thirteenF).toEqual([]);
    expect(f.schemaVersion).toBe(1);
  });

  it('upsert new entry when no matching (filer, period)', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry());
    const f = readFeedJson(p);
    expect(f.thirteenF).toHaveLength(1);
  });

  it('upsert overwrites + appends history on 13F-HR/A same period', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry());
    const amended = newEntry({
      latestFilingDate: '2026-06-10', latestFormType: '13F-HR/A',
      latestAccessionNumber: '0001067983-26-000456',
      holdings: [{ cusip: '037833100', issuerName: 'APPLE INC', shares: 310000000, valueUsd: 60140000000, votingAuthority: { sole: 310000000, shared: 0, none: 0 } }],
      summary: { totalHoldingsCount: 1, totalValueUsd: 60140000000, newPositions: [], closedPositions: [], increasedPositions: 1, decreasedPositions: 0 },
    });
    upsert13FFiling(p, amended);
    const f = readFeedJson(p);
    expect(f.thirteenF).toHaveLength(1);
    expect(f.thirteenF[0].latestFormType).toBe('13F-HR/A');
    expect(f.thirteenF[0].holdings[0].shares).toBe(310000000);
    expect(f.thirteenF[0].history).toHaveLength(2);
    expect(f.thirteenF[0].history[0].formType).toBe('13F-HR');
    expect(f.thirteenF[0].history[1].formType).toBe('13F-HR/A');
  });

  it('does NOT collapse different periods for the same filer', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry({ periodOfReport: '2025-12-31' }));
    upsert13FFiling(p, newEntry({ periodOfReport: '2026-03-31' }));
    expect(readFeedJson(p).thirteenF).toHaveLength(2);
  });

  it('computeStats counts holdings across all filers', () => {
    const f = { thirteenF: [newEntry(), newEntry({ filerCik: '0001336528', filerName: 'Pershing' })] };
    expect(computeStats(f)).toEqual({ thirteenFFilings: 2, thirteenFHoldings: 2 });
  });

  it('stamps valueUnit: thousands on every upserted entry (prevent recurrence)', () => {
    const p = join(dir, 'f.json');
    upsert13FFiling(p, newEntry());
    const f = readFeedJson(p);
    // Source entries don't declare valueUnit; the 13F feed writer MUST stamp it.
    expect(f.thirteenF[0].valueUnit).toBe('thousands');
    // Amendment path also stamps.
    upsert13FFiling(p, newEntry({
      latestFilingDate: '2026-06-10', latestFormType: '13F-HR/A',
      latestAccessionNumber: '0001067983-26-000456',
    }));
    const f2 = readFeedJson(p);
    expect(f2.thirteenF[0].valueUnit).toBe('thousands');
  });
});
