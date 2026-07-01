import { describe, it, expect } from 'vitest';
import { normalizeValueUnits } from '../../lib/enrich/normalize-value-units.js';

const cfg = [
  { cik: '0001067983', name: 'Berkshire Hathaway Inc', style: 'value' },
  { cik: '0001061768', name: 'Baupost Group', style: 'value' },
  { cik: '0001649339', name: 'Scion Asset Management, LLC', style: 'deep-value' },
  { cik: '0000000099', name: 'Tiny Tagged Fund', style: 'small-fund' },
];

const makeHolding = (cusip, shares, valueUsd) => ({
  cusip, issuerName: 'X', shares, valueUsd, votingAuthority: { sole: shares, shared: 0, none: 0 },
});

const makeEntry = (cik, name, holdings) => ({
  filerCik: cik, filerName: name, periodOfReport: '2026-03-31',
  latestFilingDate: '2026-05-15', latestFormType: '13F-HR',
  latestAccessionNumber: '0000000000-00-000000',
  holdings,
});

describe('normalizeValueUnits', () => {
  it('keeps large raw sum as dollars (Berkshire case)', () => {
    const entry = makeEntry('0001067983', 'Berkshire Hathaway Inc', [
      makeHolding('1', 100000000, 45000000000),
      makeHolding('2', 200000000, 218000000000),
    ]);
    const sum = 263_000_000_000;
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('dollars');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings[0].valueUsd).toBe(45000000000);
    expect(out.holdings.reduce((s, h) => s + h.valueUsd, 0)).toBe(sum);
  });

  it('multiplies by 1000 when raw sum is small (Baupost case)', () => {
    const entry = makeEntry('0001061768', 'Baupost Group', [
      makeHolding('1', 3118754, 649543),
      makeHolding('2', 8080112, 597208),
    ]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings[0].valueUsd).toBe(649543 * 1000);
    expect(out.holdings[1].valueUsd).toBe(597208 * 1000);
  });

  it('keeps Scion-size $1.4B raw as dollars (≥$1B → confident)', () => {
    const entry = makeEntry('0001649339', 'Scion Asset Management, LLC', [
      makeHolding('1', 1000000, 1381198076),
    ]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('dollars');
    expect(out.valueUnitAdjusted).toBeUndefined();
  });

  it('respects style: small-fund opt-out', () => {
    const entry = makeEntry('0000000099', 'Tiny Tagged Fund', [
      makeHolding('1', 100000, 50000000),
    ]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('unknown');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings[0].valueUsd).toBe(50000000);
  });

  it('handles empty holdings array', () => {
    const entry = makeEntry('0001067983', 'Berkshire Hathaway Inc', []);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('dollars');
    expect(out.valueUnitAdjusted).toBeUndefined();
    expect(out.holdings).toEqual([]);
  });

  it('handles unknown CIK with default dollar heuristic', () => {
    const entry = makeEntry('9999999999', 'Unknown Filer', [
      makeHolding('1', 100000, 50000000),
    ]);
    const out = normalizeValueUnits(entry, cfg);
    expect(out.valueUnit).toBe('thousands');
    expect(out.valueUnitAdjusted).toBe(true);
    expect(out.holdings[0].valueUsd).toBe(50000000 * 1000);
  });
});
