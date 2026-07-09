import { describe, it, expect } from 'vitest';
import { periodDiff } from '../../lib/enrich/period-diff.js';
import { normalizeValueUnits } from '../../lib/enrich/normalize-value-units.js';

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
    // Prior is already normalized (valueUnitAdjusted) — periodDiff's defensive
    // normalizeValueUnits must be a no-op on it (config-driven model).
    const prior = { ...baseEntry('0001067983', '2025-12-31', [
      { ...aapl, shares: 200000000, valueUsd: 38800000000 },
      oldco,
    ]), valueUnitAdjusted: true };
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
    const priorOld = { ...baseEntry('0001067983', '2025-06-30', [
      { ...aapl, shares: 100000000, valueUsd: 19400000000 },
    ]), valueUnitAdjusted: true };
    const priorRecent = { ...baseEntry('0001067983', '2025-12-31', [
      { ...aapl, shares: 200000000, valueUsd: 38800000000 },
    ]), valueUnitAdjusted: true };
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

  it('breaks periodOfReport ties by latestFilingDate desc (Coatue Q4+Q1 double-filing)', () => {
    const current = baseEntry('0001067983', '2026-03-31', [aapl]);
    const priorSame = {
      ...baseEntry('0001067983', '2025-12-31', [
        { ...aapl, shares: 200000000, valueUsd: 38800000000 },
      ]),
      valueUnitAdjusted: true,
      latestFilingDate: '2026-02-14', // earlier than priorTie
    };
    // Same periodOfReport as priorSame but later latestFilingDate
    const priorTie = {
      ...baseEntry('0001067983', '2025-12-31', [
        { ...aapl, shares: 150000000, valueUsd: 29100000000 },
      ]),
      valueUnitAdjusted: true,
      latestFilingDate: '2026-05-15', // later than priorSame
    };
    const all = [current, priorSame, priorTie];
    const out = periodDiff(current, all);
    // Should pick priorTie (later latestFilingDate) → prior total = 29100000000
    expect(out.summary.priorTotalValueUsd).toBe(29100000000);
  });

  it('normalizes prior entry units to match current (Baupost-style units mismatch)', () => {
    // Current: Baupost Q1 2026 — already normalized to dollars (valueUnitAdjusted: true).
    // Holdings are in post-×1000 dollars.
    const current = {
      ...baseEntry('0001061768', '2026-03-31', [
        { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 100000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
      ]),
      valueUnit: 'thousands',
      valueUnitAdjusted: true,
    };
    // Prior: Baupost Q4 2025 — raw (would also be thousands but not yet normalized).
    // Holdings are in raw thousands.
    const prior = baseEntry('0001061768', '2025-12-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 110000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const cfg = [{ cik: '0001061768', name: 'Baupost Group', style: 'value' }];
    const out = periodDiff(current, [current, prior], cfg);
    // After fix: prior gets normalized → priorTotalValueUsd = 110000 * 1000 = 110,000,000
    // Before fix: priorTotalValueUsd = 110000 (raw) → deltaPct wildly wrong
    expect(out.summary.priorTotalValueUsd).toBe(110000000);
    // Real deltaPct = (100,000,000 - 110,000,000) / 110,000,000 = -9.09%
    expect(out.summary.deltaPct).toBeCloseTo(-0.0909, 4);
  });

  it('idempotent: leaves prior entry alone when already normalized (defense does not double-normalize)', () => {
    // Simulate post-normalizeValueUnits state: prior already carries
    // valueUnitAdjusted, so the defensive normalizeValueUnits short-circuits.
    const current = baseEntry('0001061768', '2026-03-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 1000000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const prior = { ...baseEntry('0001061768', '2025-12-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 1100000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]), valueUnitAdjusted: true };
    const cfg = [{ cik: '0001061768', name: 'Baupost Group', style: 'value' }];
    const out = periodDiff(current, [current, prior], cfg);
    // valueUnitAdjusted guard → prior valueUsd unchanged (no ×1000).
    expect(out.summary.priorTotalValueUsd).toBe(1100000000);
    // deltaPct = (1B - 1.1B) / 1.1B = -0.0909...
    expect(out.summary.deltaPct).toBeCloseTo(-0.0909, 4);
  });

  it('honors small-fund style flag on prior: does not normalize even when sum < $1B', () => {
    // Prior sum < $1B BUT CIK matches small-fund config → should NOT ×1000.
    const current = baseEntry('0001061768', '2026-03-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 30000000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const prior = baseEntry('0001061768', '2025-12-31', [
      { cusip: '1', issuerName: 'X', shares: 100, valueUsd: 30, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const cfg = [{ cik: '0001061768', name: 'Tiny Filer', style: 'small-fund' }];
    const out = periodDiff(current, [current, prior], cfg);
    // small-fund style → valueUnit: 'unknown' → prior valueUsd stays raw.
    expect(out.summary.priorTotalValueUsd).toBe(30);
  });

  it('does not double-normalize prior when prior is from a pre-normalized feed (small filer, raw sum < $1M)', () => {
    // ARK 2017-09-30 (current) vs ARK 2017-06-30 (prior) shape.
    // Prior raw sum ($513,594) is < $1M, so after the first ×1000 it is
    // still < $1B and the second call used to re-multiply → ×1,000,000 total.
    // After the fix, the second call sees valueUnitAdjusted=true and returns
    // the once-normalized prior unchanged.
    const rawPrior = baseEntry('0001697748', '2017-06-30', [
      { cusip: 'A', issuerName: 'X', shares: 100, valueUsd: 200000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
      { cusip: 'B', issuerName: 'Y', shares: 100, valueUsd: 313594, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);
    const cfg = [{ cik: '0001697748', name: 'ARK Investment Management LLC', style: 'deep-value' }];

    // Simulate the prepare-digest.js pipeline: normalize the feed ONCE, then
    // pass it as allFilings to periodDiff.
    const normalizedPrior = normalizeValueUnits(rawPrior, cfg);
    // The guard in normalizeValueUnits keys off this marker on input; pin it.
    expect(normalizedPrior.valueUnitAdjusted).toBe(true);
    const current = baseEntry('0001697748', '2017-09-30', [
      { cusip: 'A', issuerName: 'X', shares: 100, valueUsd: 200000 * 1000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
      { cusip: 'B', issuerName: 'Y', shares: 100, valueUsd: 619306 * 1000, votingAuthority: { sole: 100, shared: 0, none: 0 } },
    ]);

    const out = periodDiff(current, [current, normalizedPrior], cfg);

    // Once-normalized prior sum = (200,000 + 313,594) × 1000 = 513,594,000
    // Before the fix: 513,594,000,000 (×1000 again)
    expect(out.summary.priorTotalValueUsd).toBe(513594000);
    // current total = (200,000 + 619,306) × 1000 = 819,306,000
    // true deltaPct = (819,306,000 - 513,594,000) / 513,594,000 ≈ +0.5952
    // Before the fix: (819,306,000 - 513,594,000,000) / 513,594,000,000 ≈ -0.9984
    expect(out.summary.deltaPct).toBeCloseTo(0.5952, 4);
  });
});
