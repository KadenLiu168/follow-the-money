import { describe, it, expect } from 'vitest';
import { periodDiff } from '../../lib/enrich/period-diff.js';

const aapl = { cusip: '037833100', issuerName: 'APPLE INC', shares: 300000000, valueUsd: 58200000000, votingAuthority: { sole: 300000000, shared: 0, none: 0 } };
const goog = { cusip: '02079K305', issuerName: 'ALPHABET INC', shares: 10000000, valueUsd: 17000000000, votingAuthority: { sole: 10000000, shared: 0, none: 0 } };
const oldco = { cusip: '999999999', issuerName: 'OLDCO', shares: 1, valueUsd: 1, votingAuthority: { sole: 1, shared: 0, none: 0 } };

const baseEntry = (cik, period, holdings) => ({
  filerCik: cik, filerName: 'Test Filer', periodOfReport: period,
  latestFilingDate: '2026-05-15', latestFormType: '13F-HR',
  latestAccessionNumber: '0000000000-00-000000',
  holdings,
});

describe('periodDiff', () => {
  it('produces rich newPositions/closedPositions with prior + delta fields', () => {
    const current = baseEntry('0001067983', '2026-03-31', [aapl, goog]);
    const prior = baseEntry('0001067983', '2025-12-31', [
      { ...aapl, shares: 200000000, valueUsd: 38800000000 },
      oldco,
    ]);
    const all = [current, prior];
    const out = periodDiff(current, all);

    expect(out.summary).not.toBeNull();
    expect(out.summary.newPositions).toEqual([
      { cusip: '02079K305', issuerName: 'ALPHABET INC', shares: 10000000, valueUsd: 17000000000 },
    ]);
    expect(out.summary.closedPositions).toEqual([
      { cusip: '999999999', issuerName: 'OLDCO', sharesAtClose: 1, valueUsdAtClose: 1 },
    ]);
    expect(out.summary.increasedPositions).toBe(1);
    expect(out.summary.decreasedPositions).toBe(0);
    expect(out.summary.totalValueUsd).toBe(58200000000 + 17000000000);
    expect(out.summary.priorTotalValueUsd).toBe(38800000000 + 1);
    expect(out.summary.deltaPct).toBeCloseTo((75200000001 - 38800000001) / 38800000001, 5);
  });

  it('returns summary: null when no prior period exists', () => {
    const current = baseEntry('0001067983', '2026-03-31', [aapl]);
    const out = periodDiff(current, [current]);
    expect(out.summary).toBeNull();
  });

  it('uses the most recent prior when multiple exist', () => {
    const current = baseEntry('0001067983', '2026-03-31', [aapl]);
    const priorOld = baseEntry('0001067983', '2025-06-30', [
      { ...aapl, shares: 100000000, valueUsd: 19400000000 },
    ]);
    const priorRecent = baseEntry('0001067983', '2025-12-31', [
      { ...aapl, shares: 200000000, valueUsd: 38800000000 },
    ]);
    const all = [current, priorOld, priorRecent];
    const out = periodDiff(current, all);
    expect(out.summary.priorTotalValueUsd).toBe(38800000000);
  });

  it('only diffs within same CIK (never cross-CIK)', () => {
    const current = baseEntry('0001067983', '2026-03-31', [aapl]);
    const otherPrior = baseEntry('0001336528', '2025-12-31', [goog]);
    const out = periodDiff(current, [current, otherPrior]);
    expect(out.summary).toBeNull();
  });
});
